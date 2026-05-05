---
name: whisper
description: 動画/音声ファイルからSRT字幕を生成。Faster Whisperによるローカル音声認識で、ファイルパスまたはURL（YouTube等）から文字起こし・翻訳が可能。「文字起こし」「字幕生成」「transcribe」「SRT」などのリクエスト時に使用。
---

# Whisper 文字起こしスキル

動画/音声ファイルからSRT形式の字幕を生成する。

## 重要事項

**処理は数分〜数十分かかる。MCPツール呼び出し後、必ず完了まで待機すること。途中で処理を止めない。**

## ワークフロー

1. 入力を確認（ファイルパス or URL）
2. 適切なMCPツールを呼び出す
3. 完了まで待機（途中で止めない）
4. 結果を報告

## MCPツール

### transcribe_from_file
ローカルファイルから字幕生成。

```
file_path: ファイルの絶対パス（必須）
device: "cuda" or "cpu"（デフォルト: cuda）
```

### transcribe_from_url
URLから動画をダウンロードして字幕生成。

```
url: 動画URL（必須）
device: "cuda" or "cpu"（デフォルト: cuda）
```

### 共通オプション
- `input_lang`: 入力言語（省略で自動検知）
- `output_lang`: 翻訳先言語（省略で翻訳なし）
- `initial_prompt`: 追加の専門用語ヒント（`initial_prompt.txt` の内容に追記される）
- `multilingual`: マルチリンガルモード（フレーズ単位で言語自動検出）
- `languages`: 言語ホワイトリスト（カンマ区切り、例: `"ja,en,ko,zh,fr"`）。`multilingual=true` 時のみ有効。候補外言語の検出時にホワイトリスト内の最高確率言語で再推論する。
- `lang_tag`: 言語タグ付きSRT出力（例: `[ja] こんにちは`）。`multilingual=true` 時のみ有効。
- `split_by_language`: 言語別にSRTファイルを分割出力。`multilingual=true` 時のみ有効。
- `output_lang`: マルチリンガルモード時、検出言語と異なるセグメントのみ翻訳。同じ言語はそのまま保持。

詳細パラメータは [parameters.md](references/parameters.md) を参照。

## マルチリンガルモード

複数言語が混在する音声を、フレーズ単位で言語検出しながら文字起こしする。

### 使用例

```
この動画は日本語と英語が混在しています。マルチリンガルモードで文字起こしして: C:\Videos\meeting.mp4
→ multilingual=true

言語は日本語、英語、韓国語だけです
→ multilingual=true, languages="ja,en,ko"

言語タグ付きで出力して
→ multilingual=true, lang_tag=true

言語ごとにファイルを分けて
→ multilingual=true, split_by_language=true

全部日本語に翻訳して
→ multilingual=true, output_lang="ja"
  （検出言語がjaのセグメントはそのまま、他言語のみ翻訳）
```

### マルチリンガル結果報告

成功時:
```
字幕ファイルを生成しました:
- 原文: {srt_path}
- 翻訳: {translated_srt_path}（翻訳時のみ）
- 言語別SRT: {lang}_srt_path（split_by_language時のみ）
- 検出言語: multilingual ({言語分布})
- セグメント数: {segment_count}
```

## initial_prompt（用語補正）

プロジェクトルートの `initial_prompt.txt` に固有名詞・専門用語を記載しておくと、全ての文字起こしでデフォルト適用される。

```
# initial_prompt.txt の例
天羽うずしお丸, VRChat, Friday Night Funkin', FNF
```

MCPツールやCLIの `initial_prompt` パラメータで追加指定すると、ファイル内容の後ろに結合される。

## 結果報告

成功時:
```
字幕ファイルを生成しました:
- 原文: {srt_path}
- 翻訳: {translated_srt_path}（翻訳時のみ）
- 検出言語: {detected_language}
- セグメント数: {segment_count}
```

失敗時:
```
エラーが発生しました: {error}
```
