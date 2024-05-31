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


def result2subs(segments):
    """
    セグメントをSRT形式の字幕データに変換します。

    Args:
    segments: Whisperモデルから取得したセグメントのリスト。

    Returns:
    list: SRT形式の字幕データリスト。
    """
    subs = []

    for index, segment in enumerate(segments):
        start = segment.start
        end = segment.end
        text = segment.text
        sub = Subtitle(index=index + 1,
                       start=timedelta(seconds=start),
                       end=timedelta(seconds=end),
                       content=text)

        subs.append(sub)
    return subs


def transcribe_video(file_path: str, output_path: str = 'output', translator = None, translate_to_lang: str = 'none', device: str = 'cuda'):
    """
    指定された動画ファイルをトランスクリプトし、結果をSRTファイルとして保存します。

    Args:
    file_path (str): トランスクリプトする動画ファイルのパス。
    output_path (str): SRTファイルを保存するディレクトリ。
    device (str): 使用するデバイス（'cuda' または 'cpu'）

    """
    print(file_path)
    model_size = "large-v3"

    # Run on GPU with FP16
    if device == 'cuda':
        compute_type = 'float16'
    elif device == 'cpu':
        compute_type = 'int8'
        
    model = WhisperModel(model_size, device=device, compute_type=compute_type)

    segments, info = model.transcribe(file_path, beam_size=5)

    print("Detected language '%s' with probability %f" %
          (info.language, info.language_probability))

    # SRTファイルを保存するディレクトリ
    if not os.path.exists(output_path):
        os.makedirs(output_path)

    base_filename = os.path.splitext(os.path.basename(file_path))[0]
    srt_file_path = os.path.join(
        output_path, f"{base_filename}_{info.language}.srt")

    # segmentsイテレータを複製
    segments1, segments2 = itertools.tee(segments, 2)

    # 識別言語の処理を行う
    with open(srt_file_path, 'w', encoding='utf-8') as f:
        f.write(srt.compose(result2subs(segments1)))

    if translate_to_lang != 'none':
        # 翻訳処理を行う
        translated_segments = translate_segments(segments2, translator)

        translated_srt_file_path = os.path.join(
            output_path, f"{base_filename}_{translate_to_lang}.srt")
        # 翻訳されたセグメントをSRT形式の字幕データに変換して保存
        with open(translated_srt_file_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(result2subs(translated_segments)))


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

    for segment in segments:
        text = segment.text
        translated_text = translator.translation(text)
        translated_segment = segment._replace(text=translated_text)
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
