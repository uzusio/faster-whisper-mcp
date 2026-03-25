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

詳細パラメータは [parameters.md](references/parameters.md) を参照。

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
