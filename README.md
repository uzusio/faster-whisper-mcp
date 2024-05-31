# GenSrtForFasterWhisper 高品質な動画字幕生成ツール

## 概要

動画ファイルから字幕を高速に生成するためのPythonツールです。このツールは[Faster Whisper](https://github.com/guillaumekln/faster-whisper)という軽量で高速な音声認識エンジンを使用しており、ユーザーがローカル環境で動作させることができます。
動画のローカルファイル、または動画のURLを入力として受け取り、対応する字幕ファイル（SRT形式）を出力します。

動画編集や翻訳、字幕付きの動画視聴などに便利です

## インストール手順

### CUDA Toolkitのダウンロード

Faster WhisperはCUDA Toolkit 12.X 系には対応していないため、11.X 系をインストールする必要があります。

1. [CUDA Toolkit 11.8 ダウンロードページ](https://developer.nvidia.com/cuda-11-8-0-download-archive)にアクセス
2. 下記の設定でインストーラーをダウンロード
    - Operating System: Windows
    - Architecture: x86_64
    - Version: 11
    - Installer Type: exe(network)

### CUDA Toolkitのインストール

ダウンロードしたインストーラーを実行し、CUDA Toolkit 11.8をインストールします。（時間がかかる可能性があります）

### cuDNNのダウンロード

**注意: NVIDIA DEVELOPERアカウントが必要です。**

1. [cuDNNダウンロードページ](https://developer.nvidia.com/cudnn)にアクセス
2. CUDA 11.X 系に対応したcuDNNをダウンロード

### cuDNNの展開

ダウンロードしたzipファイルを展開し、以下のディレクトリにファイルを格納
- `bin`
- `include`
- `lib`

例： `C:\Program Files\NVIDIA\CUDNN\v8.9`

### 環境変数の追加

各binディレクトリをシステム環境変数に追加してください

## 使い方

このスクリプトは動画から字幕を生成します。

### 依存関係

`Pipfile` に記載されています。

### 使用例

このスクリプトを実行するには、以下のようにコマンドライン引数を指定してください。

#### 基本的な使用方法（デフォルトはGPUを使用）

```sh
python main.py [video_url | video_path]
```

#### デバイスを指定して実行する（GPUまたはCPU）

```sh
python main.py [video_url | video_path] --device [cuda | cpu]
```

#### 翻訳言語を指定して実行する

```sh
python main.py [video_url | video_path] --lang [language_code]
```

#### デバイスと翻訳言語の両方を指定して実行する

```sh
python main.py [video_url | video_path] --device [cuda | cpu] --lang [language_code]
```

### コマンドライン引数

- `input` : 動画のURLまたはローカルパスを指定します。
- `--device` : 使用するデバイスを指定します。`cuda`（デフォルト）または`cpu`を選択できます。
- `--lang` : 字幕を翻訳する言語のコードを指定します。デフォルトは`none`で翻訳なし。

### 例

#### GPUを使用してローカルファイルを処理する

```sh
python main.py video.mp4
```

#### CPUを使用してURLから動画を処理する

```sh
python main.py https://example.com/video.mp4 --device cpu
```

#### GPUを使用して動画を処理し、日本語に翻訳する

```sh
python main.py video.mp4 --lang ja
```

#### CPUを使用してURLから動画を処理し、スペイン語に翻訳する

```sh
python main.py https://example.com/video.mp4 --device cpu --lang es
```

## 依存関係のインストール

このプロジェクトはPipenvを用いて依存関係を管理しています。

### Pipenvのインストール

もしPipenvがインストールされていない場合は、次のコマンドでインストールできます。

```bash
pip install pipenv
```

### 依存関係のインストール

プロジェクトのルートディレクトリで以下のコマンドを実行し、依存関係をインストールします。

```bash
pipenv install
```

### 仮想環境の有効化

依存関係のインストール後、次のコマンドで仮想環境を有効化します。

```bash
pipenv shell
```

これで、プロジェクトに必要なすべての依存関係がインストールされ、仮想環境が有効になります。

## ToDo
- [x] MacやCuda以外の環境向けにCPUに対応
- [ ] Whisper APIを用いた実装