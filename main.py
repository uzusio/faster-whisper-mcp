import sys
import os
import argparse
from dotenv import load_dotenv
from genSrt import transcribe_video, download_video
from translator import Translator

def setup(translate_to_lang: str = 'none'):
    load_dotenv() # 環境変数を読み込む
    api_key = os.getenv("OPENAI_API_KEY")
    translator = Translator(api_key, translate_to_lang)
    return translator

def main():
    parser = argparse.ArgumentParser(description="Transcribe and translate videos.")
    parser.add_argument('input', type=str, help='URL or local path of the video')
    parser.add_argument('--device', type=str, choices=['cuda', 'cpu'], default='cuda', help='Device to use for inference (default: cuda)')
    parser.add_argument('--model', type=str, default='large-v3', help='Whisper model size (default: large-v3)')
    parser.add_argument('--input-lang', type=str, default=None, help='Input language code (default: auto-detect)')
    parser.add_argument('--output-lang', type=str, default=None, help='Output language code for translation (default: no translation)')
    # 精度向上オプション
    parser.add_argument('--initial-prompt', type=str, default=None, help='Initial prompt with hints for specialized terms')
    parser.add_argument('--condition-on-previous-text', action='store_true', help='Enable conditioning on previous text (default: disabled to prevent hallucination)')
    parser.add_argument('--temperature', type=float, default=0.0, help='Temperature for sampling (default: 0.0)')
    parser.add_argument('--no-speech-threshold', type=float, default=0.6, help='No speech threshold (default: 0.6)')
    parser.add_argument('--compression-ratio-threshold', type=float, default=2.4, help='Compression ratio threshold (default: 2.4)')
    parser.add_argument('--no-vad-filter', action='store_true', help='Disable VAD filter (default: enabled)')

    args = parser.parse_args()

    input_arg = args.input
    device = args.device
    model_size = args.model
    input_lang = args.input_lang
    output_lang = args.output_lang
    initial_prompt = args.initial_prompt
    condition_on_previous_text = args.condition_on_previous_text
    temperature = args.temperature
    no_speech_threshold = args.no_speech_threshold
    compression_ratio_threshold = args.compression_ratio_threshold
    vad_filter = not args.no_vad_filter

    translator = None
    if output_lang is not None:
        translator = setup(output_lang)

    # URLで始まる場合
    if input_arg.startswith("https://"):
        output_path = 'output'
        original_title, video_extension, timestamp = download_video(input_arg, output_path)
        downloaded_file_path = os.path.join(output_path, f"{timestamp}.{video_extension}")

    # ローカルファイルの場合
    else:
        downloaded_file_path = os.path.abspath(input_arg)
        output_path = os.path.dirname(downloaded_file_path)
        original_title = os.path.splitext(os.path.basename(downloaded_file_path))[0]
        video_extension = os.path.splitext(downloaded_file_path)[1][1:]

    print(f"output_path: {output_path}")
    transcribe_video(
        downloaded_file_path,
        output_path,
        translator,
        input_lang,
        output_lang,
        device,
        model_size,
        initial_prompt,
        condition_on_previous_text,
        temperature,
        no_speech_threshold,
        compression_ratio_threshold,
        vad_filter,
    )

if __name__ == "__main__":
    main()