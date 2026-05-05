"""clips_index.json の各クリップを yt-dlp で twitch_to_youtube/clips/ にダウンロード。

既にダウンロード済みのファイルはスキップ。失敗したものは最後にサマリで表示。
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    index_path = root / "clips_index.json"
    clips_dir = root / "clips"
    clips_dir.mkdir(parents=True, exist_ok=True)

    if not index_path.exists():
        print(f"{index_path} not found. Run list_my_clips.py first.", file=sys.stderr)
        return 1
    index = json.loads(index_path.read_text(encoding="utf-8"))
    clips = index.get("clips", [])
    print(f"Downloading {len(clips)} clips to {clips_dir} ...", file=sys.stderr)

    failures: list[tuple[str, str]] = []
    skipped = 0
    downloaded = 0

    for i, clip in enumerate(clips, 1):
        slug = clip["slug"]
        url = clip["url"]
        out_path = clips_dir / f"{slug}.mp4"

        if out_path.exists() and out_path.stat().st_size > 0:
            skipped += 1
            print(f"  [{i}/{len(clips)}] SKIP (exists) {slug}", file=sys.stderr)
            continue

        cmd = [
            "yt-dlp",
            "-o",
            str(out_path),
            "--no-progress",
            "--quiet",
            "--no-warnings",
            url,
        ]
        print(f"  [{i}/{len(clips)}] DL {slug} — {clip.get('title','')[:50]}", file=sys.stderr)
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if proc.returncode != 0 or not out_path.exists() or out_path.stat().st_size == 0:
            err = (proc.stderr or proc.stdout or "unknown").strip().splitlines()[-1:] or ["unknown"]
            failures.append((slug, err[0]))
            print(f"    FAILED: {err[0]}", file=sys.stderr)
            if out_path.exists() and out_path.stat().st_size == 0:
                out_path.unlink()
        else:
            downloaded += 1

    print(
        f"\nDone. downloaded={downloaded}, skipped={skipped}, failed={len(failures)}",
        file=sys.stderr,
    )
    if failures:
        print("\nFailures:", file=sys.stderr)
        for slug, err in failures:
            print(f"  {slug}: {err}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
