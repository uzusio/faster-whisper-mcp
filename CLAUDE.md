# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## タスク管理

GitHub Projectsで管理: https://github.com/users/uzusio/projects/3

タスク確認: `gh project item-list 3 --owner uzusio`

## 注意事項

セッション単位で記憶が消えるため、覚えておくべきことはこのファイルに適宜追記すること。

## プロジェクト概要

動画ファイル（ローカル/URL）から字幕を高速生成するPythonツール。Faster Whisper（軽量・高速な音声認識エンジン）を使用し、SRT形式の字幕ファイルを出力する。

## 開発コマンド

```bash
# セットアップ
uv venv && uv pip install -e .

# CLI実行
uv run python main.py [video_url | video_path]

# MCPサーバ起動
uv run python mcp_server.py

# ビルド
uv run python build_script.py
```

## アーキテクチャ

```
main.py            # CLI エントリーポイント
mcp_server.py      # MCPサーバ
genSrt.py          # 音声認識・SRT生成
translator.py      # 翻訳処理（LangChain + OpenAI）
whisper_manager.py # モデル管理
initial_prompt.txt # デフォルトの用語補正プロンプト
```

## MCPサーバ

提供ツール: `transcribe_from_file`, `transcribe_from_url`, `get_supported_languages`

パラメータ詳細は `.claude/skills/whisper/` を参照。

## Claude Skill

`.claude/skills/whisper/` に文字起こしスキルを定義。MCPツール実行時の安定した動作を提供。

## 環境要件

- Python 3.11
- CUDA Toolkit 12.x + cuDNN 9（GPU使用時）
- OpenAI APIキー（翻訳機能使用時）

## テスト時の注意

デフォルト設定（`--device cuda --model large-v3`）で実施。
