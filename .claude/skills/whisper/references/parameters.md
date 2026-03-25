# MCPツール パラメータ詳細

## transcribe_from_file / transcribe_from_url 共通パラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|-----------|------|
| device | str | "cuda" | "cuda" or "cpu" |
| model_size | str | "large-v3" | Whisperモデルサイズ |
| input_lang | str | None | 入力言語コード（自動検知） |
| output_lang | str | None | 翻訳先言語コード |
| initial_prompt | str | None | 追加の専門用語ヒント（`initial_prompt.txt` に追記される） |
| condition_on_previous_text | bool | False | 前セグメント参照（文脈維持） |
| temperature | float | 0.0 | 温度パラメータ |
| no_speech_threshold | float | 0.6 | 無音判定閾値 |
| compression_ratio_threshold | float | 2.4 | 繰り返し検出閾値 |
| vad_filter | bool | True | 音声区間検出フィルタ |

## 戻り値

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

## 言語コード例

| コード | 言語 |
|--------|------|
| ja | 日本語 |
| en | 英語 |
| zh | 中国語 |
| ko | 韓国語 |
| es | スペイン語 |
| fr | フランス語 |
| de | ドイツ語 |

59言語対応。`get_supported_languages` ツールで一覧取得可能。

## initial_prompt の動作

1. プロジェクトルートの `initial_prompt.txt` をデフォルトで読み込む
2. パラメータで `initial_prompt` が指定された場合、ファイル内容の後ろに `, ` 区切りで結合
3. どちらも空の場合は `initial_prompt` なしで実行

例: `initial_prompt.txt` が `天羽うずしお丸, VRChat` で、パラメータに `FNF` を指定した場合:
→ 実際のprompt: `天羽うずしお丸, VRChat, FNF`
