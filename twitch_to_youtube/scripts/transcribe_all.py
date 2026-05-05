"""clips/ 内の全mp4を Faster Whisper で文字起こしし、transcripts/{slug}.srt として保存。

WhisperModelをループ外で1回だけロードしてコストを削減する。
language=ja 固定。既に出力済みのSRTは再生成しない。
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import srt
from faster_whisper import WhisperModel
from srt import Subtitle


def load_initial_prompt(project_root: Path) -> str | None:
    p = project_root / "initial_prompt.txt"
    if p.exists():
        return p.read_text(encoding="utf-8").strip() or None
    return None


def transcribe_one(model: WhisperModel, mp4_path: Path, srt_path: Path, initial_prompt: str | None) -> dict:
    t0 = time.time()
    params = {
        "language": "ja",
        "beam_size": 5,
        "word_timestamps": True,
        "condition_on_previous_text": True,
        "temperature": 0.0,
        "no_speech_threshold": 0.6,
        "compression_ratio_threshold": 2.4,
        "vad_filter": False,
    }
    if initial_prompt:
        params["initial_prompt"] = initial_prompt

    segments, info = model.transcribe(str(mp4_path), **params)
    subs = []
    for idx, seg in enumerate(segments):
        subs.append(
            Subtitle(
                index=idx + 1,
                start=timedelta(seconds=seg.start),
                end=timedelta(seconds=seg.end),
                content=seg.text,
            )
        )
    srt_path.parent.mkdir(parents=True, exist_ok=True)
    srt_path.write_text(srt.compose(subs), encoding="utf-8")
    elapsed = time.time() - t0
    return {
        "segments": len(subs),
        "audio_duration": info.duration,
        "language": info.language,
        "language_probability": info.language_probability,
        "elapsed_sec": elapsed,
    }


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    project_root = root.parent
    clips_dir = root / "clips"
    transcripts_dir = root / "transcripts"
    transcripts_dir.mkdir(parents=True, exist_ok=True)
    index_path = root / "clips_index.json"

    if not index_path.exists():
        print(f"{index_path} not found.", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    target_slugs = [c["slug"] for c in index.get("clips", [])]

    initial_prompt = load_initial_prompt(project_root)

    targets: list[tuple[str, Path, Path]] = []
    skipped = 0
    missing = 0
    for slug in target_slugs:
        mp4 = clips_dir / f"{slug}.mp4"
        out = transcripts_dir / f"{slug}.srt"
        if not mp4.exists():
            missing += 1
            continue
        if out.exists() and out.stat().st_size > 0:
            skipped += 1
            continue
        targets.append((slug, mp4, out))

    print(
        f"Targets: {len(targets)} (skipped existing: {skipped}, missing mp4: {missing})",
        file=sys.stderr,
    )
    if not targets:
        return 0

    print("Loading Whisper model (large-v3, cuda, float16)...", file=sys.stderr)
    model = WhisperModel("large-v3", device="cuda", compute_type="float16")

    stats = {"ok": 0, "failed": 0, "failures": []}
    total_audio = 0.0
    total_elapsed = 0.0
    for i, (slug, mp4, out) in enumerate(targets, 1):
        try:
            r = transcribe_one(model, mp4, out, initial_prompt)
            total_audio += r["audio_duration"]
            total_elapsed += r["elapsed_sec"]
            stats["ok"] += 1
            print(
                f"  [{i}/{len(targets)}] OK  {slug} | "
                f"{r['audio_duration']:.1f}s audio → {r['elapsed_sec']:.1f}s elapsed, "
                f"{r['segments']} segs",
                file=sys.stderr,
            )
        except Exception as e:
            stats["failed"] += 1
            stats["failures"].append((slug, str(e)))
            print(f"  [{i}/{len(targets)}] FAIL {slug}: {e}", file=sys.stderr)

    print(
        f"\nDone. ok={stats['ok']}, failed={stats['failed']}, "
        f"audio={total_audio:.0f}s, elapsed={total_elapsed:.0f}s "
        f"(RTF={total_elapsed/max(total_audio,1e-9):.2f})",
        file=sys.stderr,
    )
    if stats["failures"]:
        print("\nFailures:", file=sys.stderr)
        for slug, err in stats["failures"]:
            print(f"  {slug}: {err}", file=sys.stderr)
    return 0 if stats["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
