# Issue作成

バグ報告または機能リクエストのGitHub Issueを作成する。別セッションのClaude（または他の開発者）が見ても理解できるよう、十分な背景情報と関連ファイルへのリンクを含める。


## 引数

- `$ARGUMENTS`: Issueのタイトルまたは説明
- オプション: `with-claude` で @claude メンションを追加

## 手順

1. **背景情報の収集**:
   - なぜこのIssueが必要か（問題の発見状況、重要性）
   - 関連するコードや機能は何か
   - どのファイルが関係しているか

2. **関連ファイルのリンク作成**:
   - VSCode形式のマークダウンリンクで記載: `[ファイル名](相対パス)`
   - 行番号指定: `[ファイル名:42](相対パス#L42)`
   - 範囲指定: `[ファイル名:42-51](相対パス#L42-L51)`

3. **技術的詳細の記述**:
   - エラーログ、スタックトレース（ある場合）
   - 既存の類似実装へのリンク

4. **@claude メンションの処理**:
   - **デフォルト**: `@claude` なし（ローカル実装）
   - **`with-claude` 指定時**: `@claude` 付き（GitHub Actions自動処理）

5. **適切なLabelの設定**: bug/enhancement/documentation など

6. `gh issue create` でIssueを作成

## Issue本文の必須要素

別セッションのClaude（または他の開発者）が引き継げるよう、以下を含める:

### 1. 背景・文脈
- なぜこのIssueが必要か
- どういう状況で発見されたか

### 2. 現状の説明
- **バグの場合**: 再現手順、期待動作、実際の動作、エラー情報
- **機能リクエストの場合**: ユースケース、解決する問題
- **改善の場合**: 現状の問題点、改善後の姿

### 3. 技術的詳細
- 関連ファイルへのリンク（VSCode形式）:
  - `[ファイル名](相対パス)` - ファイルの役割
  - `[ファイル名:42](相対パス#L42)` - 具体的な行
- エラーログ・スタックトレース（ある場合）

### 4. 実装のヒント
- タスクリスト（チェックボックス形式）
- 参考にすべきコードやパターン
- 注意すべき制約事項

## アーキテクチャ参照

このプロジェクトの主要ファイル:

| ファイル | 役割 |
|----------|------|
| `main.py` | CLIエントリーポイント |
| `mcp_server.py` | MCPサーバ（transcribe_from_file, transcribe_from_url, get_supported_languages） |
| `genSrt.py` | 音声認識・SRT生成のコアロジック |
| `translator.py` | 翻訳処理（LangChain + OpenAI） |
| `whisper_manager.py` | Whisperモデル管理 |
| `initial_prompt.txt` | デフォルトの用語補正プロンプト |

## テンプレート例

```markdown
## バグ報告 / 機能リクエスト

### 概要
$ARGUMENTS

### 背景
（このIssueがどういう状況で発見・必要とされたか）

## 現状
（バグの場合: 再現手順、期待動作、実際の動作）
（機能の場合: ユースケース、解決したい問題）

### エラー情報（ある場合）
```
（エラーログ、スタックトレース）
```

## 関連コード
- [genSrt.py:XX](genSrt.py#LXX) - 該当処理の説明

## 実装タスク
- [ ] タスク1
- [ ] タスク2

### 制約事項
（注意すべき制約、環境要件など）
- Python 3.11 / CUDA 12.x + cuDNN 9
- デフォルトモデル: large-v3
```

## 実行例

### 基本的なIssue作成

```bash
gh issue create \
  --repo uzusio/faster-whisper-mcp \
  --title "transcribe_from_urlでYouTubeショートのダウンロードに失敗する" \
  --label "bug" \
  --body "..."
```

### 機能リクエスト

```bash
gh issue create \
  --repo uzusio/faster-whisper-mcp \
  --title "利用可能なWhisperモデル一覧を取得するAPIの追加" \
  --label "enhancement" \
  --body "..."
```

ユーザーの入力に基づいてIssueを作成し、URLを返す。

**デフォルト動作:**
- `@claude` なし → ローカル実装

**オプション:**
- `with-claude`: `@claude` メンションを追加（GitHub Actions自動処理）

**注意**: このリポジトリはProject #3に紐づいています。
