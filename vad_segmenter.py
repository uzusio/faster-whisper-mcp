"""VADベースの音声セグメンター

Silero VAD (faster-whisper内蔵) を使用して、音声をフレーズ単位に分割する。
マルチリンガル文字起こしの前段処理として使用。
"""

from dataclasses import dataclass

import numpy as np
from faster_whisper.audio import decode_audio
from faster_whisper.vad import get_speech_timestamps, VadOptions

SAMPLE_RATE = 16000


@dataclass
class VadSegment:
    """VADで検出された音声セグメント"""
    start: float       # 開始時刻（秒）
    end: float         # 終了時刻（秒）
    audio: np.ndarray  # 音声データ（numpy配列のview）

    @property
    def duration(self) -> float:
        return self.end - self.start


def segment_audio(
    file_path: str,
    min_silence_duration_ms: int = 300,
    speech_pad_ms: int = 200,
    max_speech_duration_s: float = 30,
) -> list[VadSegment]:
    """音声ファイルをVADでフレーズ単位に分割する。

    Args:
        file_path: 音声/動画ファイルのパス
        min_silence_duration_ms: 無音と判定する最小長（ms）。
            小さいほど細かく分割される。300msが言語切替に適した値。
        speech_pad_ms: セグメント前後に追加するパディング（ms）
        max_speech_duration_s: 1セグメントの最大長（秒）

    Returns:
        VadSegmentのリスト（時系列順）
    """
    audio = decode_audio(file_path)

    vad_options = VadOptions(
        min_silence_duration_ms=min_silence_duration_ms,
        speech_pad_ms=speech_pad_ms,
        max_speech_duration_s=max_speech_duration_s,
    )

    timestamps = get_speech_timestamps(audio, vad_options)

    segments = []
    for ts in timestamps:
        start_sec = ts["start"] / SAMPLE_RATE
        end_sec = ts["end"] / SAMPLE_RATE
        # numpy viewとして取得（コピーなし）
        segment_audio = audio[ts["start"]:ts["end"]]
        segments.append(VadSegment(
            start=start_sec,
            end=end_sec,
            audio=segment_audio,
        ))

    return segments
