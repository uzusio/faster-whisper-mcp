"""GitHub Issue #3 に、各クリップの進捗（DL/文字起こし/メタデータ生成）をMarkdown表で
コメント反映する。マーカー付きコメントを探して編集、なければ新規作成。

gh CLI 経由で実行。認証済み前提。
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO = "uzusio/faster-whisper-mcp"
ISSUE_NUMBER = 3
MARKER = "<!-- twitch-to-youtube-progress-table -->"


def gh(args: list[str], input_text: str | None = None) -> subprocess.CompletedProcess:
    cmd = ["gh", *args]
    return subprocess.run(
        cmd,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def find_progress_comment() -> int | None:
    result = gh(
        [
            "api",
            f"repos/{REPO}/issues/{ISSUE_NUMBER}/comments",
            "--paginate",
        ]
    )
    if result.returncode != 0:
        print(f"Failed to fetch comments: {result.stderr}", file=sys.stderr)
        return None
    comments = json.loads(result.stdout)
    for c in comments:
        if MARKER in (c.get("body") or ""):
            return c["id"]
    return None


def build_table(root: Path) -> str:
    index_path = root / "clips_index.json"
    clips_dir = root / "clips"
    transcripts_dir = root / "transcripts"
    metadata_dir = root / "metadata"

    index = json.loads(index_path.read_text(encoding="utf-8"))
    clips = index.get("clips", [])

    # 作成日時の新しい順にソート（最近のものから見えるように）
    clips_sorted = sorted(
        clips,
        key=lambda c: c.get("createdAt") or "",
        reverse=True,
    )

    totals = {"dl": 0, "srt": 0, "meta": 0}
    rows = []
    for c in clips_sorted:
        slug = c["slug"]
        title = (c.get("title") or "").replace("|", "\\|").replace("\n", " ").strip()
        if len(title) > 38:
            title = title[:37] + "…"
        url = c.get("url") or f"https://www.twitch.tv/clip/{slug}"
        duration = int(c.get("durationSeconds") or 0)
        game = ((c.get("game") or {}).get("name") or "-").replace("|", "\\|")
        if len(game) > 20:
            game = game[:19] + "…"

        dl_ok = (clips_dir / f"{slug}.mp4").exists() and (clips_dir / f"{slug}.mp4").stat().st_size > 0
        srt_ok = (transcripts_dir / f"{slug}.srt").exists() and (transcripts_dir / f"{slug}.srt").stat().st_size > 0
        meta_ok = (metadata_dir / f"{slug}.json").exists() and (metadata_dir / f"{slug}.json").stat().st_size > 0

        if dl_ok:
            totals["dl"] += 1
        if srt_ok:
            totals["srt"] += 1
        if meta_ok:
            totals["meta"] += 1

        # メタデータ生成済みならYouTubeタイトルを見せる
        yt_title = ""
        if meta_ok:
            try:
                meta = json.loads((metadata_dir / f"{slug}.json").read_text(encoding="utf-8"))
                yt_title = (meta.get("youtube") or {}).get("title", "").replace("|", "\\|")
                if len(yt_title) > 38:
                    yt_title = yt_title[:37] + "…"
            except Exception:
                pass

        rows.append(
            f"| [{title}]({url}) | {duration}s | {game} | "
            f"{'✅' if dl_ok else '⬜'} | "
            f"{'✅' if srt_ok else '⬜'} | "
            f"{'✅' if meta_ok else '⬜'} | "
            f"{yt_title} |"
        )

    n = len(clips_sorted)
    ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
    header = [
        MARKER,
        "## クリップ別進捗",
        "",
        f"_Last updated: {ts}_",
        "",
        f"- 総数: **{n}** クリップ（broadcaster=`{index.get('broadcaster')}`, curator=`{index.get('curator_filter')}`）",
        f"- ダウンロード: **{totals['dl']}/{n}**",
        f"- 文字起こし: **{totals['srt']}/{n}**",
        f"- メタデータ生成: **{totals['meta']}/{n}**",
        "",
        "凡例: ✅ 完了 / ⬜ 未処理",
        "",
        "| # | Twitchタイトル | 長さ | ゲーム | DL | SRT | META | YouTubeタイトル |",
        "|---:|---|---:|---|:-:|:-:|:-:|---|",
    ]
    numbered = [
        row.replace("| [", f"| {i+1} | [", 1)
        for i, row in enumerate(rows)
    ]
    return "\n".join(header + numbered)


def main() -> int:
    root = Path(__file__).resolve().parent.parent
    body = build_table(root)

    existing_id = find_progress_comment()
    if existing_id is not None:
        result = gh(
            [
                "api",
                "-X", "PATCH",
                f"repos/{REPO}/issues/comments/{existing_id}",
                "-f", f"body={body}",
            ]
        )
        if result.returncode != 0:
            print(f"Failed to patch comment: {result.stderr}", file=sys.stderr)
            return 1
        print(f"Updated comment {existing_id}", file=sys.stderr)
    else:
        result = gh(
            [
                "issue", "comment", str(ISSUE_NUMBER),
                "--repo", REPO,
                "--body-file", "-",
            ],
            input_text=body,
        )
        if result.returncode != 0:
            print(f"Failed to create comment: {result.stderr}", file=sys.stderr)
            return 1
        print(f"Created comment. stdout: {result.stdout}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
