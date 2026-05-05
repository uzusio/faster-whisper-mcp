# faster-whisper-mcp

動画ファイルから高品質な字幕を生成するMCPサーバ＆CLIツール。[Faster Whisper](https://github.com/guillaumekln/faster-whisper)を使用し、ローカルGPU/CPUで高速に音声認識を実行します。

## 特徴

- **MCPサーバ対応** - Claude Desktop等のMCPクライアントから直接利用可能
- **Claude Skill対応** - `skills/whisper.skill` で安定した実行
- **高速処理** - Faster Whisper (CTranslate2) による最適化された推論
- **多言語対応** - 59言語の自動検出・翻訳
- **マルチリンガル対応** - フレーズ単位で言語を自動検出し、多言語混在の音声を正確に文字起こし
- **柔軟な入力** - ローカルファイル / URL（YouTube等）両対応
- **GPU/CPU対応** - CUDA GPU または CPU で実行可能

## インストール

```bash
git clone https://github.com/uzusio/faster-whisper-mcp.git
cd faster-whisper-mcp

pip install uv
uv venv
uv pip install -e .
```

## MCPサーバとして使用

### Claude Desktopに登録

`%APPDATA%\Claude\claude_desktop_config.json`（Windows）または `~/Library/Application Support/Claude/claude_desktop_config.json`（Mac）に追加:

```json
{
  "mcpServers": {
    "faster-whisper": {
      "command": "uv",
      "args": ["--directory", "/path/to/faster-whisper-mcp", "run", "python", "mcp_server.py"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

> **Note**: `OPENAI_API_KEY` は翻訳機能使用時のみ必要です。

### 提供ツール

| ツール | 説明 |
|--------|------|
| `transcribe_from_file` | ローカル動画/音声ファイルから字幕生成 |
| `transcribe_from_url` | URLから動画をダウンロードして字幕生成 |
| `get_supported_languages` | サポート言語一覧を取得 |

詳細なパラメータは `skills/whisper/` を参照。

### 使用例

```
この動画の字幕を生成して: C:\Videos\meeting.mp4
```

```
https://www.youtube.com/watch?v=xxxxx この動画を日本語字幕付きで文字起こしして
```

## CLIとして使用

```bash
# 基本
python main.py video.mp4

# デバイス指定
python main.py video.mp4 --device cpu

# 翻訳付き
python main.py video.mp4 --input-lang ja --output-lang en

# URLから処理
python main.py https://www.youtube.com/watch?v=xxxxx
```

### マルチリンガルモード

複数言語が混在する音声をフレーズ単位で言語検出しながら文字起こしします。

```bash
# 基本（全言語から自動検出）
python main.py --multilingual video.mp4

# 言語ホワイトリスト指定（誤検出を防ぎ精度向上）
python main.py --multilingual --languages ja,en,ko,zh,fr video.mp4

# 言語タグ付きSRT出力（[ja] こんにちは のように言語を明示）
python main.py --multilingual --lang-tag video.mp4

# 言語別にSRTファイルを分割出力
python main.py --multilingual --split-by-language video.mp4

# 全オプション組み合わせ + 日本語に翻訳
python main.py --multilingual --languages ja,en,ko,zh --lang-tag --split-by-language --output-lang ja video.mp4
```

| オプション | 説明 |
|-----------|------|
| `--multilingual` | マルチリンガルモード有効化 |
| `--languages` | 候補言語をカンマ区切りで指定。候補外の言語を検出した場合、候補内の最高確率言語で再推論 |
| `--lang-tag` | 各セグメントに `[ja]` 等の言語タグを付与 |
| `--split-by-language` | 言語ごとに個別のSRTファイルを出力 |

主要オプション: `--device`, `--model`, `--input-lang`, `--output-lang`

全オプションは `python main.py --help` で確認。

## 環境要件

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- GPU使用時: CUDA Toolkit 12.x + cuDNN 9.x
- 翻訳機能: OpenAI APIキー（`.env`に設定）

## 出力

- **形式**: SRT
- **出力先**: ローカルファイルは同ディレクトリ、URLは`output/`
- **ファイル名**: `{元ファイル名}_{言語コード}.srt`
- **マルチリンガル**: `{元ファイル名}_multilingual.srt`（`--split-by-language` 時は言語ごとに分割）

## ライセンス

MIT License

## 関連リンク

- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Model Context Protocol](https://modelcontextprotocol.io/)
