"""faster-whisper MCP Server

動画ファイルから字幕を生成するMCPサーバ
"""

import json
import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path
from typing import Optional

import srt
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP, Context
from pydantic import BaseModel

from whisper_manager import WhisperManager
from genSrt import download_video, get_unique_filepath
from translator import Translator
from multilingual_transcriber import transcribe_multilingual, results_to_srt

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# 環境変数読み込み
load_dotenv()


# =============================================================================
# Pydantic Models
# =============================================================================

class TranscribeResult(BaseModel):
    """文字起こし結果"""
    success: bool
    srt_path: str = ""
    translated_srt_path: Optional[str] = None
    detected_language: str = ""
    segment_count: int = 0
    error: Optional[str] = None


class LanguageInfo(BaseModel):
    """言語情報"""
    code: str
    name: str


class SupportedLanguagesResult(BaseModel):
    """サポート言語一覧"""
    languages: list[LanguageInfo]


# =============================================================================
# App Context
# =============================================================================

@dataclass
class AppContext:
    """アプリケーションコンテキスト"""
    language_map: dict[str, str]


@asynccontextmanager
async def app_lifespan(server: FastMCP):
    """アプリケーションのライフサイクル管理"""
    logger.info("Starting faster-whisper MCP server...")

    # 言語マップを読み込み
    conf_path = Path(__file__).parent / "conf" / "language_code.json"
    with open(conf_path, "r", encoding="utf-8") as f:
        language_map = json.load(f)

    try:
        yield AppContext(language_map=language_map)
    finally:
        # サーバ終了時にモデルをアンロード
        WhisperManager.unload()
        logger.info("Server shutting down")


def load_initial_prompt_file() -> str:
    """initial_prompt.txt からデフォルトのプロンプトを読み込む"""
    prompt_file = Path(__file__).parent / "initial_prompt.txt"
    if prompt_file.exists():
        return prompt_file.read_text(encoding="utf-8").strip()
    return ""


def build_initial_prompt(additional: str = None) -> str:
    """ファイルのデフォルトプロンプトとオプション指定を結合する"""
    base = load_initial_prompt_file()
    parts = [p for p in [base, additional] if p]
    return ", ".join(parts) if parts else None


# MCPサーバ初期化
mcp = FastMCP("faster-whisper-mcp", lifespan=app_lifespan)


# =============================================================================
# Helper Functions
# =============================================================================

def get_app_context(ctx: Context) -> AppContext:
    """コンテキストからAppContextを取得"""
    return ctx.request_context.lifespan_context


async def transcribe_with_progress(
    file_path: str,
    output_path: str,
    device: str,
    input_lang: Optional[str],
    output_lang: Optional[str],
    ctx: Context,
    progress_start: int = 0,
    progress_end: int = 100,
    model_size: str = "large-v3",
    initial_prompt: Optional[str] = None,
    condition_on_previous_text: bool = True,
    temperature: float = 0.0,
    no_speech_threshold: float = 0.6,
    compression_ratio_threshold: float = 2.4,
    vad_filter: bool = False,
    multilingual: bool = False,
    languages: Optional[list[str]] = None,
) -> TranscribeResult:
    """プログレス報告付きで文字起こしを実行

    Args:
        file_path: 動画ファイルパス
        output_path: SRT出力先ディレクトリ
        device: 使用デバイス
        input_lang: 入力言語（Noneで自動検知）
        output_lang: 翻訳先言語（Noneで翻訳なし）
        ctx: MCPコンテキスト
        progress_start: プログレス開始値
        progress_end: プログレス終了値
        model_size: Whisperモデルサイズ
        initial_prompt: 追加の専門用語ヒント（initial_prompt.txtの内容に追記される）
        condition_on_previous_text: 前のセグメントを参照して文脈維持
        temperature: 温度パラメータ（0.0で最も決定的）
        no_speech_threshold: 無音判定の閾値
        compression_ratio_threshold: 繰り返し検出の閾値
        vad_filter: 音声区間検出フィルタを使用
        multilingual: マルチリンガルモード（フレーズ単位で言語検出）
        languages: 言語ホワイトリスト（例: ["ja","en","ko"]）。マルチリンガルモード時のみ有効。
    """
    app_ctx = get_app_context(ctx)

    # プログレス範囲を計算
    model_load_end = progress_start + int((progress_end - progress_start) * 0.1)
    transcribe_end = progress_start + int((progress_end - progress_start) * 0.7)
    translate_end = progress_end

    try:
        # モデルロード
        await ctx.report_progress(progress_start, progress_end, "モデルをロード中...")
        model = WhisperManager.get_model(device, model_size)
        await ctx.report_progress(model_load_end, progress_end, "モデルロード完了")

        # 文字起こし実行
        await ctx.report_progress(model_load_end, progress_end, "文字起こし中...")

        # マルチリンガルモード
        if multilingual:
            async def on_segment_complete(index, total, seg):
                progress = model_load_end + int(
                    (transcribe_end - model_load_end) * (index + 1) / total
                )
                await ctx.report_progress(
                    progress, progress_end,
                    f"マルチリンガル文字起こし中... ({index + 1}/{total}) [{seg.language}]"
                )

            # 同期コールバックでプログレス更新（asyncは使えないのでログのみ）
            def sync_callback(index, total, seg):
                logger.info(f"Segment {index+1}/{total}: {seg.language} ({seg.language_probability:.2f})")

            merged_prompt = build_initial_prompt(initial_prompt)

            ml_results = transcribe_multilingual(
                file_path=file_path,
                model=model,
                initial_prompt=merged_prompt,
                temperature=temperature,
                no_speech_threshold=no_speech_threshold,
                compression_ratio_threshold=compression_ratio_threshold,
                languages=languages,
                on_segment_complete=sync_callback,
            )

            await ctx.report_progress(transcribe_end, progress_end, f"文字起こし完了 ({len(ml_results)} セグメント)")

            # 出力ディレクトリ作成
            os.makedirs(output_path, exist_ok=True)

            base_filename = os.path.splitext(os.path.basename(file_path))[0]
            srt_file_path = os.path.join(output_path, f"{base_filename}_multilingual.srt")
            srt_file_path = get_unique_filepath(srt_file_path)

            with open(srt_file_path, 'w', encoding='utf-8') as f:
                f.write(results_to_srt(ml_results))

            logger.info(f"SRT saved: {srt_file_path}")

            # 言語統計
            lang_counts = {}
            for seg in ml_results:
                lang_counts[seg.language] = lang_counts.get(seg.language, 0) + 1

            await ctx.report_progress(progress_end, progress_end, "完了")

            return TranscribeResult(
                success=True,
                srt_path=srt_file_path,
                detected_language=f"multilingual ({lang_counts})",
                segment_count=len(ml_results),
            )

        # 通常モード: transcribeパラメータを構築
        transcribe_params = {
            'beam_size': 5,
            'word_timestamps': True,
            'condition_on_previous_text': condition_on_previous_text,
            'temperature': temperature,
            'no_speech_threshold': no_speech_threshold,
            'compression_ratio_threshold': compression_ratio_threshold,
            'vad_filter': vad_filter,
        }

        merged_prompt = build_initial_prompt(initial_prompt)
        if merged_prompt:
            transcribe_params['initial_prompt'] = merged_prompt

        if input_lang:
            transcribe_params['language'] = input_lang

        segments, info = model.transcribe(file_path, **transcribe_params)

        if input_lang:
            detected_lang = input_lang
        else:
            detected_lang = info.language

        logger.info(f"Detected language: {detected_lang}")

        # セグメントをリストに変換しながらプログレス報告
        segments_list = []
        segment_count = 0

        for segment in segments:
            segments_list.append(segment)
            segment_count += 1

            # 100セグメント毎にプログレス更新
            if segment_count % 100 == 0:
                progress = model_load_end + int(
                    (transcribe_end - model_load_end) * min(segment_count / 1000, 1.0)
                )
                await ctx.report_progress(
                    progress, progress_end,
                    f"文字起こし中... ({segment_count} セグメント)"
                )

        await ctx.report_progress(transcribe_end, progress_end, f"文字起こし完了 ({segment_count} セグメント)")

        # 出力ディレクトリ作成
        os.makedirs(output_path, exist_ok=True)

        # SRTファイル生成
        base_filename = os.path.splitext(os.path.basename(file_path))[0]
        srt_file_path = os.path.join(output_path, f"{base_filename}_{detected_lang}.srt")
        srt_file_path = get_unique_filepath(srt_file_path)

        subs = []
        for index, segment in enumerate(segments_list):
            sub = srt.Subtitle(
                index=index + 1,
                start=timedelta(seconds=segment.start),
                end=timedelta(seconds=segment.end),
                content=segment.text
            )
            subs.append(sub)

        with open(srt_file_path, 'w', encoding='utf-8') as f:
            f.write(srt.compose(subs))

        logger.info(f"SRT saved: {srt_file_path}")

        # 翻訳処理
        translated_srt_path = None
        if output_lang and output_lang != detected_lang:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY not set, skipping translation")
            else:
                await ctx.report_progress(transcribe_end, progress_end, "翻訳中...")

                translator = Translator(api_key, output_lang)
                translated_subs = []

                for index, segment in enumerate(segments_list):
                    translated_text = translator.translation(segment.text)
                    sub = srt.Subtitle(
                        index=index + 1,
                        start=timedelta(seconds=segment.start),
                        end=timedelta(seconds=segment.end),
                        content=translated_text
                    )
                    translated_subs.append(sub)

                    # 10セグメント毎にプログレス更新
                    if (index + 1) % 10 == 0:
                        progress = transcribe_end + int(
                            (translate_end - transcribe_end) * (index + 1) / len(segments_list)
                        )
                        await ctx.report_progress(
                            progress, progress_end,
                            f"翻訳中... ({index + 1}/{len(segments_list)})"
                        )

                translated_srt_path = os.path.join(output_path, f"{base_filename}_{output_lang}.srt")
                translated_srt_path = get_unique_filepath(translated_srt_path)
                with open(translated_srt_path, 'w', encoding='utf-8') as f:
                    f.write(srt.compose(translated_subs))

                logger.info(f"Translated SRT saved: {translated_srt_path}")

        await ctx.report_progress(progress_end, progress_end, "完了")

        return TranscribeResult(
            success=True,
            srt_path=srt_file_path,
            translated_srt_path=translated_srt_path,
            detected_language=detected_lang,
            segment_count=segment_count,
        )

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return TranscribeResult(
            success=False,
            error=str(e),
        )


# =============================================================================
# MCP Tools
# =============================================================================

@mcp.tool()
async def get_supported_languages(ctx: Context) -> SupportedLanguagesResult:
    """サポートされている言語の一覧を取得します。

    翻訳可能な言語コードと言語名のリストを返します。
    """
    app_ctx = get_app_context(ctx)

    languages = [
        LanguageInfo(code=code, name=name)
        for code, name in app_ctx.language_map.items()
    ]

    return SupportedLanguagesResult(languages=languages)


@mcp.tool()
async def transcribe_from_file(
    file_path: str,
    device: str = "cuda",
    model_size: str = "large-v3",
    input_lang: Optional[str] = None,
    output_lang: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    condition_on_previous_text: bool = False,
    temperature: float = 0.0,
    no_speech_threshold: float = 0.6,
    compression_ratio_threshold: float = 2.4,
    vad_filter: bool = True,
    multilingual: bool = False,
    languages: Optional[str] = None,
    ctx: Context = None,
) -> TranscribeResult:
    """ローカルの動画/音声ファイルから字幕を生成します。

    Args:
        file_path: 動画/音声ファイルの絶対パス
        device: 推論に使用するデバイス ("cuda" または "cpu")
        model_size: Whisperモデルサイズ (デフォルト: "large-v3")
        input_lang: 入力言語コード（省略時は自動検知）
        output_lang: 翻訳先言語コード（省略時は翻訳なし）
        initial_prompt: 追加の専門用語ヒント（initial_prompt.txtの内容に追記される）
        condition_on_previous_text: 前のセグメントを参照して文脈維持 (デフォルト: False、ハルシネーション防止)
        temperature: 温度パラメータ（0.0で最も決定的、デフォルト: 0.0）
        no_speech_threshold: 無音判定の閾値 (デフォルト: 0.6)
        compression_ratio_threshold: 繰り返し検出の閾値 (デフォルト: 2.4)
        vad_filter: 音声区間検出フィルタを使用 (デフォルト: True、ハルシネーション防止)
        multilingual: マルチリンガルモード (デフォルト: False、フレーズ単位で言語自動検出)
        languages: 言語ホワイトリスト (カンマ区切り、例: "ja,en,ko")。multilingual=True時のみ有効

    Returns:
        生成されたSRTファイルのパスと検出された言語情報
    """
    # ファイル存在チェック
    if not os.path.exists(file_path):
        return TranscribeResult(
            success=False,
            error=f"File not found: {file_path}"
        )

    # 絶対パスに変換
    file_path = os.path.abspath(file_path)
    output_path = os.path.dirname(file_path)

    await ctx.report_progress(0, 100, "処理を開始...")

    return await transcribe_with_progress(
        file_path=file_path,
        output_path=output_path,
        device=device,
        input_lang=input_lang,
        output_lang=output_lang,
        ctx=ctx,
        progress_start=0,
        progress_end=100,
        model_size=model_size,
        initial_prompt=initial_prompt,
        condition_on_previous_text=condition_on_previous_text,
        temperature=temperature,
        no_speech_threshold=no_speech_threshold,
        compression_ratio_threshold=compression_ratio_threshold,
        vad_filter=vad_filter,
        multilingual=multilingual,
        languages=languages.split(',') if languages else None,
    )


@mcp.tool()
async def transcribe_from_url(
    url: str,
    device: str = "cuda",
    model_size: str = "large-v3",
    input_lang: Optional[str] = None,
    output_lang: Optional[str] = None,
    initial_prompt: Optional[str] = None,
    condition_on_previous_text: bool = False,
    temperature: float = 0.0,
    no_speech_threshold: float = 0.6,
    compression_ratio_threshold: float = 2.4,
    vad_filter: bool = True,
    multilingual: bool = False,
    languages: Optional[str] = None,
    ctx: Context = None,
) -> TranscribeResult:
    """URLから動画をダウンロードして字幕を生成します。

    Args:
        url: 動画のURL（YouTube等）
        device: 推論に使用するデバイス ("cuda" または "cpu")
        model_size: Whisperモデルサイズ (デフォルト: "large-v3")
        input_lang: 入力言語コード（省略時は自動検知）
        output_lang: 翻訳先言語コード（省略時は翻訳なし）
        initial_prompt: 追加の専門用語ヒント（initial_prompt.txtの内容に追記される）
        condition_on_previous_text: 前のセグメントを参照して文脈維持 (デフォルト: False、ハルシネーション防止)
        temperature: 温度パラメータ（0.0で最も決定的、デフォルト: 0.0）
        no_speech_threshold: 無音判定の閾値 (デフォルト: 0.6)
        compression_ratio_threshold: 繰り返し検出の閾値 (デフォルト: 2.4)
        vad_filter: 音声区間検出フィルタを使用 (デフォルト: True、ハルシネーション防止)
        multilingual: マルチリンガルモード (デフォルト: False、フレーズ単位で言語自動検出)
        languages: 言語ホワイトリスト (カンマ区切り、例: "ja,en,ko")。multilingual=True時のみ有効

    Returns:
        生成されたSRTファイルのパスと検出された言語情報
    """
    # URL検証
    if not url.startswith(("http://", "https://")):
        return TranscribeResult(
            success=False,
            error=f"Invalid URL: {url}"
        )

    output_path = "output"

    try:
        await ctx.report_progress(0, 100, "動画をダウンロード中...")

        # yt-dlpでダウンロード
        original_title, video_extension, timestamp = download_video(url, output_path)
        downloaded_file_path = os.path.join(output_path, f"{timestamp}.{video_extension}")

        await ctx.report_progress(10, 100, "ダウンロード完了")

        # 文字起こし実行
        return await transcribe_with_progress(
            file_path=downloaded_file_path,
            output_path=output_path,
            device=device,
            input_lang=input_lang,
            output_lang=output_lang,
            ctx=ctx,
            progress_start=10,
            progress_end=100,
            model_size=model_size,
            initial_prompt=initial_prompt,
            condition_on_previous_text=condition_on_previous_text,
            temperature=temperature,
            no_speech_threshold=no_speech_threshold,
            compression_ratio_threshold=compression_ratio_threshold,
            vad_filter=vad_filter,
            multilingual=multilingual,
            languages=languages.split(',') if languages else None,
        )

    except Exception as e:
        logger.error(f"Download failed: {e}")
        return TranscribeResult(
            success=False,
            error=f"Download failed: {str(e)}"
        )


# =============================================================================
# Entry Point
# =============================================================================

if __name__ == "__main__":
    mcp.run()
