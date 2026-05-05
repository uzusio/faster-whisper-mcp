# faster-whisper-mcp — Capabilities

切り抜き動画パイプラインのオーケストレーション層 (`auto-kirinuki/CLAUDE.md`) から `@import` で参照される能力宣言。**インターフェース契約**として扱い、内部実装詳細は書かない（実装は本リポジトリの `CLAUDE.md` / `README.md` を参照）。

## できること

- **URL から文字起こし** — YouTube 等の動画 URL を渡すと音声を取得して SRT 生成
- **ローカル動画/音声から文字起こし** — ファイルパスを渡して SRT 生成
- **マルチリンガル文字起こし** — フレーズ単位で言語を自動検出（`--multilingual`）
- **翻訳付き出力** — `--input-lang` → `--output-lang` で SRT を翻訳
- **サポート言語一覧取得**

## 呼び出し方

### CLI

```bash
cd faster-whisper-mcp
uv run python main.py <URL or path> [options]
```

全オプションは `uv run python main.py --help`。

### MCP ツール

| ツール名 | 用途 |
|---|---|
| `transcribe_from_url` | URL 入力 |
| `transcribe_from_file` | ファイル入力 |
| `get_supported_languages` | サポート言語一覧 |

詳細パラメータは `.claude/skills/whisper/` を参照。

## 出力

| 入力種別 | 出力先 | ファイル名規則 |
|---|---|---|
| URL | `faster-whisper-mcp/output/` | `{元ファイル名}_{言語コード}.srt` |
| ローカルファイル | 入力ファイルと同じディレクトリ | `{元ファイル名}_{言語コード}.srt` |
| `--multilingual` | 上記に準じる | `{元ファイル名}_multilingual.srt`（`--split-by-language` 時は言語別ファイル） |

**重要**: 出力先は固定。`--output-dir` 等の上書きオプションは未提供のため、別の場所で扱いたい場合は親側でコピー/移動する。

## 環境要件

- Python 3.11
- uv
- GPU 使用時: CUDA Toolkit 12.x + cuDNN 9.x
- 翻訳機能使用時: OpenAI API キー（`.env` に設定）

## 既定値（テスト時）

`--device cuda --model large-v3`
