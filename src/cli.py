import os
import ffmpeg
import whisper
import argparse
import warnings
import tempfile
from utils import filename, str2bool, write_srt
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from lang import LANGUAGES, FAIRSEQ_LANGUAGE_CODES

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("video", nargs="+", type=str,
                        help="paths to video files to transcribe")
    parser.add_argument("--whis_model", default="small",
                        choices=whisper.available_models(), help="name of the Whisper model to use")
    parser.add_argument("--nllb_model", default='facebook/nllb-200-distilled-600M')
    parser.add_argument("--target_language", choices=FAIRSEQ_LANGUAGE_CODES, default='eng_Latn')
    parser.add_argument("--output_dir", "-o", type=str,
                        default=".", help="directory to save the outputs")
    parser.add_argument("--output_srt", type=str2bool, default=False,
                        help="whether to output the .srt file along with the video files")
    parser.add_argument("--srt_only", type=str2bool, default=False,
                        help="only generate the .srt file and not create overlayed video")
    parser.add_argument("--verbose", type=str2bool, default=False,
                        help="whether to print out the progress and debug messages")

    parser.add_argument("--task", type=str, default="transcribe", choices=[
                        "transcribe", "translate"], help="whether to perform X->X speech recognition ('transcribe') or X->English translation ('translate')")

    args = parser.parse_args().__dict__
    whisper_model_name: str = args.pop("whis_model")
    nllb_model_name: str = args.pop("nllb_model")
    output_dir: str = args.pop("output_dir")
    output_srt: bool = args.pop("output_srt")
    srt_only: bool = args.pop("srt_only")
    os.makedirs(output_dir, exist_ok=True)

    if whisper_model_name.endswith(".en"):
        warnings.warn(
            f"{model_name} is an English-only model, forcing English detection.")
        args["language"] = "en"

    whisper_model = whisper.load_model(whisper_model_name)

    nllb_tokenizer = AutoTokenizer.from_pretrained(nllb_model_name)
    nllb_model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_name)
    
    audios = get_audio(args.pop("video"))
    subtitles = get_subtitles(
        audios, output_srt or srt_only, output_dir, 
        lambda audio_path: whisper_model.transcribe(audio_path, **args), 
        lambda text_input: nllb_tokenizer(text_input, **args),
        lambda text_embedding: nllb_model(text_embedding, **args)
    )

    if srt_only:
        return

    for path, srt_path in subtitles.items():
        out_path = os.path.join(output_dir, f"{filename(path)}.mp4")

        print(f"Adding subtitles to {filename(path)}...")

        video = ffmpeg.input(path)
        audio = video.audio

        ffmpeg.concat(
            video.filter('subtitles', srt_path, force_style="OutlineColour=&H40000000,BorderStyle=3"), audio, v=1, a=1
        ).output(out_path).run(quiet=True, overwrite_output=True)

        print(f"Saved subtitled video to {os.path.abspath(out_path)}.")


def get_audio(paths):
    temp_dir = tempfile.gettempdir()

    audio_paths = {}

    for path in paths:
        print(f"Extracting audio from {filename(path)}...")
        output_path = os.path.join(temp_dir, f"{filename(path)}.wav")

        ffmpeg.input(path).output(
            output_path,
            acodec="pcm_s16le", ac=1, ar="16k"
        ).run(quiet=True, overwrite_output=True)

        audio_paths[path] = output_path

    return audio_paths


def get_subtitles(audio_paths: list, output_srt: bool, output_dir: str, transcribe: callable,  nllb_model: callable):
    subtitles_path = {}

    for path, audio_path in audio_paths.items():
        srt_path = output_dir if output_srt else tempfile.gettempdir()
        srt_path = os.path.join(srt_path, f"{filename(path)}.srt")
        
        print(
            f"Generating subtitles for {filename(path)}... This might take a while."
        )

        warnings.filterwarnings("ignore")
        result = transcribe(audio_path)
        warnings.filterwarnings("default")

        language=result["language"]
        # nllb_tokenizer = AutoTokenizer.from_pretrained("facebook/nllb-200-distilled-600M")
        inputs = nllb_tokenizer(result["segments"]['text'], return_tensors="pt")
        translated_tokens = model.generate(
            inputs, forced_bos_token_id=tokenizer.lang_code_to_id["zho_Hans"])

        result["segments"]['text'] = tokenizer.decode(translated_tokens, skip_special_tokens=True)[0]
        with open(srt_path, "w", encoding="utf-8") as srt:
            write_srt(result, file=srt)

        subtitles_path[path] = srt_path

    return subtitles_path


if __name__ == '__main__':
    main()
