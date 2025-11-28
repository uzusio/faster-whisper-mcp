# faster-whisper-mcp

動画ファイルから高品質な字幕を生成するMCPサーバ＆CLIツール。[Faster Whisper](https://github.com/guillaumekln/faster-whisper)を使用し、ローカルGPU/CPUで高速に音声認識を実行します。

## 特徴

- **MCPサーバ対応** - Claude Desktop等のMCPクライアントから直接利用可能
- **高速処理** - Faster Whisper (CTranslate2) による最適化された推論
- **多言語対応** - 59言語の自動検出・翻訳
- **柔軟な入力** - ローカルファイル / URL（YouTube等）両対応
- **GPU/CPU対応** - CUDA GPU または CPU で実行可能

## MCPサーバとして使用

### インストール

```bash
# リポジトリをクローン
git clone https://github.com/uzusio/faster-whisper-mcp.git
cd faster-whisper-mcp

# uvをインストール（未インストールの場合）
pip install uv

# 仮想環境作成＆依存関係インストール
uv venv
uv pip install -e .
```

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

### ツールパラメータ

#### transcribe_from_file

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|:----:|-----------|------|
| file_path | string | Yes | - | 動画/音声ファイルの絶対パス |
| device | string | No | "cuda" | 推論デバイス ("cuda" / "cpu") |
| input_lang | string | No | null | 入力言語コード（省略時は自動検出） |
| output_lang | string | No | null | 翻訳先言語コード（省略時は翻訳なし） |

#### transcribe_from_url

| パラメータ | 型 | 必須 | デフォルト | 説明 |
|-----------|-----|:----:|-----------|------|
| url | string | Yes | - | 動画URL（YouTube等） |
| device | string | No | "cuda" | 推論デバイス ("cuda" / "cpu") |
| input_lang | string | No | null | 入力言語コード（省略時は自動検出） |
| output_lang | string | No | null | 翻訳先言語コード（省略時は翻訳なし） |

#### 戻り値

```json
{
  "success": true,
  "srt_path": "/path/to/output_ja.srt",
  "translated_srt_path": "/path/to/output_en.srt",
  "detected_language": "ja",
  "segment_count": 42,
  "error": null
}
```

### 使用例（Claude Desktop）

```
この動画の字幕を生成して: C:\Videos\meeting.mp4
```

```
https://www.youtube.com/watch?v=xxxxx この動画を日本語字幕付きで文字起こしして
```

## CLIとして使用

```bash
# 仮想環境を有効化
# Windows (Git Bash):
source .venv/Scripts/activate
# Windows (PowerShell):
.venv\Scripts\activate
# Mac/Linux:
source .venv/bin/activate

# 基本的な使用方法
python main.py video.mp4

# デバイス指定
python main.py video.mp4 --device cpu

# 翻訳付き（日本語→英語）
python main.py video.mp4 --input-lang ja --output-lang en

# URLから処理
python main.py https://www.youtube.com/watch?v=xxxxx
```

### CLIオプション

| オプション | 説明 |
|-----------|------|
| `input` | 動画ファイルパス または URL |
| `--device` | `cuda`（デフォルト）または `cpu` |
| `--input-lang` | 入力言語コード（省略時は自動検出） |
| `--output-lang` | 翻訳先言語コード（省略時は翻訳なし） |

## 環境要件

### 必須

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) （パッケージ管理）

### GPU使用時（推奨）

- NVIDIA GPU（CUDA対応）
- CUDA Toolkit 12.x
- cuDNN 9.x
  - cuDNNの`bin`フォルダをPATHに追加
  - 例: `C:\Program Files\NVIDIA\CUDNN\v9.16\bin\12.6`

### 翻訳機能使用時

- OpenAI APIキー（`.env`ファイルに`OPENAI_API_KEY`を設定）

## 出力

- **形式**: SRT（SubRip Subtitle）
- **出力先**:
  - ローカルファイル: 入力ファイルと同じディレクトリ
  - URL: `output/` ディレクトリ
- **ファイル名**: `{元ファイル名}_{言語コード}.srt`

## サポート言語

59言語に対応（`conf/language_code.json`で定義）:

日本語(ja), 英語(en), 中国語(zh), 韓国語(ko), スペイン語(es), フランス語(fr), ドイツ語(de), イタリア語(it), ポルトガル語(pt), ロシア語(ru), アラビア語(ar), ヒンディー語(hi), その他...

## ライセンス

MIT License

## 関連リンク

- [Faster Whisper](https://github.com/guillaumekln/faster-whisper)
- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
