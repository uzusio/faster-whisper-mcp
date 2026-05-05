"""マルチリンガル文字起こしモジュール

VADでフレーズ分割した音声セグメントごとにWhisper推論を行い、
言語自動検出付きの文字起こし結果を返す。
"""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

import srt
from faster_whisper import WhisperModel
from srt import Subtitle

from vad_segmenter import VadSegment, segment_audio

logger = logging.getLogger(__name__)


@dataclass
class TranscribedSegment:
    """文字起こし済みセグメント"""
    index: int
    start: float            # 開始時刻（秒）
    end: float              # 終了時刻（秒）
    text: str
    language: str           # 検出言語コード
    language_probability: float


def _pick_language_from_whitelist(info, languages: list[str]) -> Optional[str]:
    """all_language_probs からホワイトリスト内の最高確率言語を返す。

    Returns:
        ホワイトリスト内の最高確率言語コード。該当なしの場合はNone。
    """
    if not info.all_language_probs:
        return None

    filtered = [(lang, prob) for lang, prob in info.all_language_probs if lang in languages]
    if not filtered:
        return None

    filtered.sort(key=lambda x: x[1], reverse=True)
    return filtered[0][0]


def transcribe_multilingual(
    file_path: str,
    model: WhisperModel,
    min_silence_duration_ms: int = 300,
    beam_size: int = 5,
    initial_prompt: str = None,
    temperature: float = 0.0,
    no_speech_threshold: float = 0.6,
    compression_ratio_threshold: float = 2.4,
    languages: Optional[list[str]] = None,
    on_segment_complete=None,
) -> list[TranscribedSegment]:
    """マルチリンガル文字起こしを実行する。

    1. VADでフレーズ単位に分割
    2. 各フレーズを個別にWhisper推論（language=None で言語自動検出）
    3. 言語ホワイトリスト指定時: 候補外言語を検出した場合、ホワイトリスト内の
       最高確率言語で再推論
    4. 元のタイムラインに合わせた結果を返す

    Args:
        file_path: 音声/動画ファイルのパス
        model: WhisperModelインスタンス
        min_silence_duration_ms: VADの無音判定閾値（ms）
        beam_size: ビームサーチ幅
        initial_prompt: 専門用語ヒント
        temperature: 温度パラメータ
        no_speech_threshold: 無音判定の閾値
        compression_ratio_threshold: 繰り返し検出の閾値
        languages: 言語ホワイトリスト（例: ["ja", "en", "ko"]）。
            Noneの場合は全言語から自動検出。
        on_segment_complete: セグメント完了時コールバック (index, total, segment) -> None

    Returns:
        TranscribedSegmentのリスト（時系列順）
    """
    # Phase 1: VADでフレーズ分割
    vad_segments = segment_audio(
        file_path,
        min_silence_duration_ms=min_silence_duration_ms,
    )

    languages_set = set(languages) if languages else None

    # Phase 2: 各セグメントを個別に推論
    results = []
    total = len(vad_segments)

    for i, vad_seg in enumerate(vad_segments):
        transcribe_params = {
            'language': None,  # まず言語自動検出で推論
            'beam_size': beam_size,
            'word_timestamps': True,
            'vad_filter': False,  # 既にVAD分割済み
            'temperature': temperature,
            'no_speech_threshold': no_speech_threshold,
            'compression_ratio_threshold': compression_ratio_threshold,
        }

        if initial_prompt:
            transcribe_params['initial_prompt'] = initial_prompt

        segments, info = model.transcribe(vad_seg.audio, **transcribe_params)
        segments_list = list(segments)

        detected_lang = info.language
        detected_prob = info.language_probability

        # 言語ホワイトリストによるフィルタリング
        if languages_set and detected_lang not in languages_set:
            best_lang = _pick_language_from_whitelist(info, languages)
            if best_lang:
                logger.info(
                    f"Segment {i+1}: detected '{detected_lang}' ({detected_prob:.3f}) "
                    f"not in whitelist, re-running with '{best_lang}'"
                )
                # ホワイトリスト内の最高確率言語で再推論
                transcribe_params['language'] = best_lang
                segments, info = model.transcribe(vad_seg.audio, **transcribe_params)
                segments_list = list(segments)
                detected_lang = best_lang
                detected_prob = info.language_probability

        text = " ".join(seg.text.strip() for seg in segments_list)

        result = TranscribedSegment(
            index=i + 1,
            start=vad_seg.start,
            end=vad_seg.end,
            text=text,
            language=detected_lang,
            language_probability=detected_prob,
        )
        results.append(result)

        if on_segment_complete:
            on_segment_complete(i, total, result)

    return results


def results_to_srt(
    segments: list[TranscribedSegment],
    lang_tag: bool = False,
) -> str:
    """文字起こし結果をSRT文字列に変換する。

    Args:
        segments: 文字起こし結果のリスト
        lang_tag: Trueの場合、各セグメントに [ja] 等の言語タグを付与
    """
    subs = []
    for seg in segments:
        content = f"[{seg.language}] {seg.text}" if lang_tag else seg.text
        sub = Subtitle(
            index=seg.index,
            start=timedelta(seconds=seg.start),
            end=timedelta(seconds=seg.end),
            content=content,
        )
        subs.append(sub)
    return srt.compose(subs)


def results_to_srt_by_language(
    segments: list[TranscribedSegment],
) -> dict[str, str]:
    """言語別にSRT文字列を生成する。

    Returns:
        {言語コード: SRT文字列} の辞書
    """
    by_lang: dict[str, list[TranscribedSegment]] = {}
    for seg in segments:
        by_lang.setdefault(seg.language, []).append(seg)

    result = {}
    for lang, segs in by_lang.items():
        subs = []
        for i, seg in enumerate(segs):
            sub = Subtitle(
                index=i + 1,
                start=timedelta(seconds=seg.start),
                end=timedelta(seconds=seg.end),
                content=seg.text,
            )
            subs.append(sub)
        result[lang] = srt.compose(subs)

    return result
