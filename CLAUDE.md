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
# uvインストール（初回のみ）
pip install uv

# 仮想環境作成
uv venv

# 仮想環境有効化
# Git Bash:
source .venv/Scripts/activate
# cmd/PowerShell:
.venv\Scripts\activate

# 依存関係インストール
uv pip install -e .

# スクリプト実行
python main.py [video_url | video_path]
python main.py [video_url | video_path] --device [cuda | cpu]
python main.py [video_url | video_path] --lang [language_code]

# 実行ファイル化（PyInstaller）
python build_script.py
```

## アーキテクチャ

```
main.py          # エントリーポイント（CLI引数パース、処理振り分け）
    ↓
genSrt.py        # メイン処理（動画DL、Whisper音声認識、SRT生成）
    ↓
translator.py    # 翻訳処理（LangChain + OpenAI GPT-3.5）
    ↓
conf/language_code.json  # 言語コード→言語名マッピング（59言語）
```

### 処理フロー

1. コマンドライン引数パース（main.py）
2. URLの場合：yt-dlpでダウンロード（genSrt.download_video）
3. Faster Whisper（large-v3モデル）で音声認識
   - CUDA時：float16、CPU時：int8
4. 原言語SRT出力
5. --lang指定時：OpenAI APIで翻訳SRT出力

### 主要関数

- `genSrt.download_video(url, output_dir)` - yt-dlpで動画ダウンロード
- `genSrt.transcribe_video(file_path, output_path, translator, translate_to_lang, device)` - 音声認識と字幕生成
- `genSrt.translate_segments(segments, translator)` - セグメント翻訳
- `Translator.translation(text)` - LangChainで翻訳実行

## 環境要件

- Python 3.11
- CUDA Toolkit 12.x + cuDNN 9（GPU使用時）
  - cuDNNのbinフォルダをPATHに追加（例：`C:\Program Files\NVIDIA\CUDNN\v9.16\bin\13.0`）
- OpenAI APIキー（翻訳機能使用時）- .envファイルに設定

## 出力仕様

- 出力先：`output/` ディレクトリ
- ファイル名形式：`{元ファイル名}_{言語コード}.srt`
