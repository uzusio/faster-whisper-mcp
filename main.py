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
    parser.add_argument('--lang', type=str, default='none', help='Language to translate the subtitles to (default: none)')

    args = parser.parse_args()

    input_arg = args.input
    device = args.device
    translate_to_lang = args.lang
    
    tranlator = None
    if translate_to_lang != 'none':
        translator = setup(translate_to_lang)

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
    transcribe_video(downloaded_file_path, output_path, translator, translate_to_lang, device)

if __name__ == "__main__":
    main()