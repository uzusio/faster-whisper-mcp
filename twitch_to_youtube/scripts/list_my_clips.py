"""Twitchの指定broadcasterチャンネルから、特定curator（=自分）が作成した全クリップを取得して JSON 保存する。

戦略:
  1. yt-dlp --flat-playlist で channel の ALL_TIME クリップ一覧を取得（paginationでintegrity checkに
     引っかかる user.clips GQLを避ける）。
  2. 各クリップの slug を使って単一クリップ GQLクエリで curator 情報を取得（こちらは
     integrity check 不要）。
  3. curator.login == 指定login のものだけを出力。
"""

from __future__ import annotations

import json
import shlex
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

GQL_ENDPOINT = "https://gql.twitch.tv/gql"
CLIENT_ID = "kimne78kx3ncx6brgo4mv6wki5h1ko"

CLIP_INFO_QUERY = """
query ClipInfo($slug: ID!) {
  clip(slug: $slug) {
    id
    slug
    title
    url
    durationSeconds
    createdAt
    viewCount
    language
    curator { id login displayName }
    broadcaster { id login displayName }
    game { id name }
  }
}
"""


def list_clip_slugs_via_ytdlp(broadcaster: str) -> list[dict]:
    """yt-dlp --flat-playlist で ALL_TIME フィルタのクリップ一覧を取得。"""
    url = f"https://www.twitch.tv/{broadcaster}/clips?filter=clips&range=all"
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        url,
    ]
    print(f"Running: {' '.join(shlex.quote(c) for c in cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if proc.returncode != 0:
        raise RuntimeError(f"yt-dlp failed: {proc.stderr[:500]}")
    entries = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entries.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return entries


def fetch_clip_info(slug: str) -> dict | None:
    payload = json.dumps(
        {"query": CLIP_INFO_QUERY, "variables": {"slug": slug}}
    ).encode("utf-8")
    req = urllib.request.Request(
        GQL_ENDPOINT,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Client-Id": CLIENT_ID,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"  HTTP error for slug={slug}: {e}", file=sys.stderr)
        return None
    if "errors" in data:
        print(f"  GQL errors for slug={slug}: {data['errors']}", file=sys.stderr)
        return None
    return data.get("data", {}).get("clip")


def slug_from_url(url: str) -> str:
    # https://www.twitch.tv/<login>/clip/<slug>
    return url.rstrip("/").split("/clip/")[-1]


def main() -> int:
    broadcaster = sys.argv[1] if len(sys.argv) > 1 else "auzusiomarutwitch"
    curator_login = (sys.argv[2] if len(sys.argv) > 2 else broadcaster).lower()
    out_path = Path(__file__).resolve().parent.parent / "clips_index.json"

    print(f"Step 1/2: Listing all clips for broadcaster={broadcaster} via yt-dlp...", file=sys.stderr)
    entries = list_clip_slugs_via_ytdlp(broadcaster)
    print(f"  Got {len(entries)} clips from yt-dlp", file=sys.stderr)

    slugs = []
    for e in entries:
        url = e.get("url") or e.get("webpage_url") or ""
        if "/clip/" in url:
            slugs.append(slug_from_url(url))
    # 重複除去（順序維持）
    seen = set()
    unique_slugs = []
    for s in slugs:
        if s not in seen:
            seen.add(s)
            unique_slugs.append(s)
    print(f"  Unique slugs: {len(unique_slugs)}", file=sys.stderr)

    print(f"Step 2/2: Fetching curator info for each clip (filter by curator={curator_login})...", file=sys.stderr)
    all_clips: list[dict] = []
    mine: list[dict] = []
    for i, slug in enumerate(unique_slugs, 1):
        info = fetch_clip_info(slug)
        if info is None:
            print(f"  [{i}/{len(unique_slugs)}] {slug}: FAILED", file=sys.stderr)
            continue
        all_clips.append(info)
        curator = info.get("curator")
        is_mine = bool(curator and curator.get("login", "").lower() == curator_login)
        tag = "MINE" if is_mine else "skip"
        if is_mine:
            mine.append(info)
        print(
            f"  [{i}/{len(unique_slugs)}] [{tag}] {slug} by "
            f"{curator.get('login') if curator else 'unknown'} — {info.get('title','')[:40]}",
            file=sys.stderr,
        )
        time.sleep(0.15)

    index = {
        "broadcaster": broadcaster,
        "curator_filter": curator_login,
        "total_clips_on_channel": len(all_clips),
        "own_clips_count": len(mine),
        "clips": mine,
    }
    out_path.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"\nDone. Total on channel (queried): {len(all_clips)}, "
        f"own: {len(mine)}. Wrote {out_path}",
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
