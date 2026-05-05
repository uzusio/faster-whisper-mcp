"""transcripts/*.srt と clips_index.json の各クリップに対し、
OpenAI でYouTubeアップロード用の title/description/tags を生成し、
metadata/{slug}.json に保存する。

入力コンテキスト:
  - 元Twitchタイトル
  - 配信ゲーム名
  - クリップ長さ
  - SRT本文（文字起こし）

出力:
  - title: 日本語、100文字以内
  - description: 200〜400字程度、ハッシュタグ数個含む
  - tags: 配列、全タグ合計500字以内
  - category: Gaming
"""

from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, Field


class YouTubeMetadata(BaseModel):
    title: str = Field(description="YouTube動画タイトル。日本語、100文字以内。ゲーム名やキーワードを含めて検索性を高める。")
    description: str = Field(
        description=(
            "YouTube動画説明文。200〜400文字程度。内容の要約、配信元Twitchへの言及、"
            "末尾にハッシュタグ3〜6個を含む。"
        )
    )
    tags: list[str] = Field(
        description=(
            "検索タグの配列。各タグは30文字以内、全体で500文字以内。"
            "ゲームタイトル、配信者名（天羽うずしお丸, うずちー）、Vtuber、"
            "コンテンツタイプ（切り抜き, ハイライト等）を含める。"
        )
    )
    category: str = Field(default="Gaming", description="YouTubeカテゴリ。Gaming固定。")


SYSTEM_PROMPT = """\
あなたはゲーム配信者 天羽うずしお丸（うずちー, Amaha Uzusiomaru）の
Twitchクリップ→YouTube転載用に、視聴者が見たくなる動画メタデータを作るエディタです。

入力:
- 元のTwitchクリップタイトル
- ゲーム名
- クリップ長さ（秒）
- Whisperによる文字起こし（誤認識を含む可能性あり）

出力制約:
- title: 日本語、100字以内。ゲーム名、キャラ名、印象的なフレーズを活用。煽りすぎない。
- description: 200〜400字。内容の短い要約＋元Twitchクリップへの導線（必要なら）＋末尾にハッシュタグ3〜6個。
- tags: 配列。各タグ30字以内、全体で500字以内。ゲームタイトル、キャラ名、配信者名、"切り抜き" "Vtuber" などを含める。
- 絵文字は控えめに（0〜2個）。
- 明らかな文字起こし誤認識（意味不明な語）は採用しない。
- 配信者の一人称は「俺」「僕」を使わず、中立的に記述。
"""


def srt_to_plain(srt_text: str) -> str:
    """SRTから字幕テキストだけを抽出して結合。"""
    lines = []
    for block in srt_text.strip().split("\n\n"):
        parts = block.split("\n")
        if len(parts) >= 3:
            lines.append(" ".join(parts[2:]).strip())
    return " ".join(lines)


def truncate_for_prompt(text: str, max_chars: int = 6000) -> str:
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 30] + "...(以下省略)"


def generate(
    llm,
    original_title: str,
    game_name: str,
    duration_sec: float,
    transcript_text: str,
) -> YouTubeMetadata:
    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", SYSTEM_PROMPT),
            (
                "user",
                "元Twitchタイトル: {title}\n"
                "ゲーム: {game}\n"
                "クリップ長さ: {duration:.0f}秒\n"
                "文字起こし:\n---\n{transcript}\n---\n\n"
                "上記を踏まえ、YouTubeアップロード用のメタデータをJSONで返してください。",
            ),
        ]
    )
    structured = llm.with_structured_output(YouTubeMetadata)
    chain = prompt | structured
    result = chain.invoke(
        {
            "title": original_title,
            "game": game_name or "(不明)",
            "duration": duration_sec,
            "transcript": truncate_for_prompt(transcript_text),
        }
    )
    return result


def main() -> int:
    load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY not set. Set it in .env.", file=sys.stderr)
        return 1

    model_name = os.environ.get("METADATA_MODEL", "gpt-4o-mini")
    llm = ChatOpenAI(openai_api_key=api_key, model=model_name, temperature=0.6)

    root = Path(__file__).resolve().parent.parent
    index_path = root / "clips_index.json"
    transcripts_dir = root / "transcripts"
    metadata_dir = root / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)

    index = json.loads(index_path.read_text(encoding="utf-8"))
    clips = index.get("clips", [])
    print(f"Generating metadata for up to {len(clips)} clips with model={model_name}...", file=sys.stderr)

    ok = 0
    fail = 0
    skip = 0
    missing_srt = 0
    for i, clip in enumerate(clips, 1):
        slug = clip["slug"]
        srt_path = transcripts_dir / f"{slug}.srt"
        out_path = metadata_dir / f"{slug}.json"

        if out_path.exists():
            skip += 1
            continue
        if not srt_path.exists() or srt_path.stat().st_size == 0:
            missing_srt += 1
            print(f"  [{i}/{len(clips)}] SKIP (no srt) {slug}", file=sys.stderr)
            continue

        srt_text = srt_path.read_text(encoding="utf-8")
        transcript_text = srt_to_plain(srt_text)

        try:
            meta = generate(
                llm,
                original_title=clip.get("title", ""),
                game_name=(clip.get("game") or {}).get("name", ""),
                duration_sec=float(clip.get("durationSeconds", 0)),
                transcript_text=transcript_text,
            )
        except Exception as e:
            fail += 1
            print(f"  [{i}/{len(clips)}] FAIL {slug}: {e}", file=sys.stderr)
            continue

        enriched = {
            "slug": slug,
            "source_url": clip.get("url"),
            "source_title": clip.get("title"),
            "game": (clip.get("game") or {}).get("name"),
            "duration_seconds": clip.get("durationSeconds"),
            "created_at": clip.get("createdAt"),
            "youtube": meta.model_dump(),
        }
        out_path.write_text(
            json.dumps(enriched, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        ok += 1
        tag_str = ", ".join(meta.tags[:5])
        print(
            f"  [{i}/{len(clips)}] OK {slug} → {meta.title[:40]} | tags: {tag_str[:60]}",
            file=sys.stderr,
        )
        time.sleep(0.1)

    print(
        f"\nDone. ok={ok}, skipped={skip}, missing_srt={missing_srt}, failed={fail}",
        file=sys.stderr,
    )
    return 0 if fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
