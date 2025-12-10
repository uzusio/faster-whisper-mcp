import os
import sys
import re
import subprocess
import json
from datetime import datetime
from datetime import timedelta
import itertools
import srt
from srt import Subtitle
from faster_whisper import WhisperModel
from tqdm import tqdm


def download_video(url: str, output_dir: str = 'output') -> (str, str, str):
    """
    指定されたURLから動画をダウンロードし、タイトル、拡張子、タイムスタンプを返します。

    Args:
    url (str): ダウンロードする動画のURL。
    output_dir (str): ダウンロードした動画を保存するディレクトリ。

    Returns:
    tuple: ダウンロードされた動画のタイトル、拡張子、タイムスタンプを含むタプル。
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    output_file_template = os.path.join(output_dir, f'{timestamp}.%(ext)s')

    command = [
        'yt-dlp',
        '--print-json',
        '-o', output_file_template,
        url
    ]

    result = subprocess.run(command, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, text=True)
    video_info = json.loads(result.stdout)
    # print(video_info)

    return video_info['title'],  video_info['ext'], timestamp


def result2subs(segments, desc="字幕生成"):
    """
    セグメントをSRT形式の字幕データに変換します。

    Args:
    segments: Whisperモデルから取得したセグメントのリスト。
    desc: プログレスバーの説明文。

    Returns:
    list: SRT形式の字幕データリスト。
    """
    subs = []
    segments_list = list(segments)

    for index, segment in enumerate(tqdm(segments_list, desc=desc)):
        start = segment.start
        end = segment.end
        text = segment.text
        sub = Subtitle(index=index + 1,
                       start=timedelta(seconds=start),
                       end=timedelta(seconds=end),
                       content=text)

        subs.append(sub)
    return subs


def transcribe_video(file_path: str, output_path: str = 'output', translator = None, input_lang: str = None, output_lang: str = None, device: str = 'cuda', model_size: str = 'large-v3'):
    """
    指定された動画ファイルをトランスクリプトし、結果をSRTファイルとして保存します。

    Args:
    file_path (str): トランスクリプトする動画ファイルのパス。
    output_path (str): SRTファイルを保存するディレクトリ。
    translator: Translatorインスタンス（翻訳時のみ）。
    input_lang (str): 入力言語コード（Noneの場合は自動検知）。
    output_lang (str): 出力言語コード（Noneの場合は翻訳なし）。
    device (str): 使用するデバイス（'cuda' または 'cpu'）
    model_size (str): Whisperモデルサイズ（デフォルト: 'large-v3'）

    """
    print(file_path)

    # Run on GPU with FP16
    if device == 'cuda':
        compute_type = 'float16'
    elif device == 'cpu':
        compute_type = 'int8'

    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    # 入力言語が指定されていれば使用、なければ自動検知
    if input_lang:
        segments, info = model.transcribe(
            file_path,
            beam_size=5,
            language=input_lang,
            vad_filter=False,  # VAD無効化
            word_timestamps=True,  # 単語レベルのタイムスタンプ
        )
        detected_lang = input_lang
        print(f"Using specified input language: {input_lang}")
    else:
        segments, info = model.transcribe(
            file_path,
            beam_size=5,
            vad_filter=False,  # VAD無効化
            word_timestamps=True,  # 単語レベルのタイムスタンプ
        )
        detected_lang = info.language
        print("Detected language '%s' with probability %f" %
              (info.language, info.language_probability))

    # SRTファイルを保存するディレクトリ
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    srt_file_path = os.path.join(
        output_path, f"{base_filename}_{detected_lang}.srt")
    srt_file_path = get_unique_filepath(srt_file_path)

    # segmentsイテレータを複製
    segments1, segments2 = itertools.tee(segments, 2)

    # 識別言語の処理を行う
    with open(srt_file_path, 'w', encoding='utf-8') as f:
        f.write(srt.compose(result2subs(segments1)))

    # 翻訳が必要な場合のみ（出力言語が指定されていて、かつ検知言語と異なる場合）
    if output_lang is not None and output_lang != detected_lang:
        # 翻訳処理を行う
        translated_segments = translate_segments(segments2, translator)

        translated_srt_file_path = os.path.join(
            output_path, f"{base_filename}_{output_lang}.srt")
        translated_srt_file_path = get_unique_filepath(translated_srt_file_path)
        # 翻訳されたセグメントをSRT形式の字幕データに変換して保存
        with open(translated_srt_file_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(result2subs(translated_segments)))
    elif output_lang is not None and output_lang == detected_lang:
        print(f"Skipping translation: input and output language are the same ({detected_lang})")


class TranslatedSegment:
    """翻訳されたセグメントを保持するクラス"""
    def __init__(self, start, end, text):
        self.start = start
        self.end = end
        self.text = text


def translate_segments(segments, translator):
    """
    セグメントを翻訳します。

    Args:
    segments: Whisperモデルから取得したセグメントのリスト。
    translator: Translatorクラスのインスタンス。

    Returns:
    list: 翻訳されたセグメントのリスト。
    """
    translated_segments = []
    segments_list = list(segments)

    for segment in tqdm(segments_list, desc="翻訳"):
        text = segment.text
        translated_text = translator.translation(text)
        translated_segment = TranslatedSegment(segment.start, segment.end, translated_text)
        translated_segments.append(translated_segment)

    return translated_segments


def rename_files(old_path: str, new_name: str, extension: str, output_dir: str = 'output'):
    """
    ファイル名を新しい名前に変更します。

    Args:
    old_path (str): 元のファイルパス。
    new_name (str): 新しいファイル名。
    extension (str): ファイルの拡張子。
    output_dir (str): ファイルを保存するディレクトリ。
    """
    counter = 1
    new_file_name = clean_filename(new_name)

    while os.path.exists(os.path.join(output_dir, f"{new_file_name}.{extension}")):
        new_file_name = f"{new_name}_{counter}"
        counter += 1
    os.rename(old_path, os.path.join(
        output_dir, f"{new_file_name}.{extension}"))


def clean_filename(filename: str) -> str:
    return re.sub(r'[/*?:"<>|]', '', filename)


def get_unique_filepath(filepath: str) -> str:
    """
    ファイルパスが既に存在する場合、連番を付与してユニークなパスを返します。

    Args:
        filepath (str): 元のファイルパス。

    Returns:
        str: ユニークなファイルパス。
    """
    if not os.path.exists(filepath):
        return filepath

    directory = os.path.dirname(filepath)
    filename = os.path.basename(filepath)
    name, ext = os.path.splitext(filename)

    counter = 1
    while True:
        new_filepath = os.path.join(directory, f"{name}_{counter}{ext}")
        if not os.path.exists(new_filepath):
            return new_filepath
        counter += 1
