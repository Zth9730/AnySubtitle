import os
import ffmpeg
import whisper
import argparse
import warnings
import tempfile
from .utils import filename, str2bool, write_srt
from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
from .const import LANGUAGES, FAIRSEQ_LANGUAGE_CODES, NLLB_MODEL

def main():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("video", nargs="+", type=str,
                        help="paths to video files to transcribe")
    parser.add_argument("--whis_model", default="small",
                        choices=whisper.available_models(), help="name of the Whisper model to use")
    parser.add_argument("--nllb_translate", "-t", type=bool, default=False,
                        help="whether to translate the transcript")
    parser.add_argument("--nllb_model", default='small', choices=NLLB_MODEL.keys(),
                        help="name of the NLLB model to use")
    parser.add_argument("--target_language", "-l", choices=FAIRSEQ_LANGUAGE_CODES, default='zho_Hans', 
                        help="target language to translate")
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
    nllb_translate: bool = args.pop("nllb_translate")
    nllb_model_name: str = NLLB_MODEL[args.pop("nllb_model")]
    target_language: str = args.pop("target_language")
    output_dir: str = args.pop("output_dir")
    output_srt: bool = args.pop("output_srt")
    srt_only: bool = args.pop("srt_only")
    os.makedirs(output_dir, exist_ok=True)

    if whisper_model_name.endswith(".en"):
        warnings.warn(
            f"{whisper_model_name} is an English-only model, forcing English detection.")
        args["language"] = "en"
    
    audios = get_audio(args.pop("video"))
    whisper_model = whisper.load_model(whisper_model_name)

    subtitles = get_subtitles(
        audios, output_srt or srt_only, output_dir, nllb_translate, nllb_model_name, target_language,
        lambda audio_path: whisper_model.transcribe(audio_path, **args), 
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


def get_subtitles(audio_paths: list, 
                  output_srt: bool, 
                  output_dir: str, 
                  nllb_translate: bool, 
                  nllb_model_name: str,
                  target_language: str,
                  transcribe: callable):
    subtitles_path = {}

    for path, audio_path in audio_paths.items():
        srt_path = output_dir if output_srt else tempfile.gettempdir()
        srt_path = os.path.join(srt_path, f"{filename(path)}.srt")
        
        print(
            f"Generating subtitles for {filename(path)}... This might take a while."
        )

        warnings.filterwarnings("ignore")
        transcribe_result = transcribe(audio_path)
        warnings.filterwarnings("default")

        if nllb_translate:
            print(
                f"Translating subtitles for {filename(path)}... This might take a while."
            )
            language=transcribe_result["language"]
            nllb_tokenizer = AutoTokenizer.from_pretrained(nllb_model_name, src_lang=LANGUAGES[language])
            nllb_model = AutoModelForSeq2SeqLM.from_pretrained(nllb_model_name)

            inputs = nllb_tokenizer([segment['text'] for segment in transcribe_result['segments']], return_tensors="pt", padding = True)
            translated_tokens = nllb_model.generate(
                **inputs, forced_bos_token_id=nllb_tokenizer.lang_code_to_id[target_language])

            translate_results = nllb_tokenizer.batch_decode(translated_tokens, skip_special_tokens=True)
        
            result = []
            for i, segment in enumerate(transcribe_result['segments']):
                result.append({
                    "start": segment['start'],
                    "end": segment['end'],
                    "text": translate_results[i]
                })
        else:
            result = transcribe_result['segments']
                
        with open(srt_path, "w", encoding="utf-8") as srt:
            write_srt(result, file=srt)

        subtitles_path[path] = srt_path

    return subtitles_path


if __name__ == '__main__':
    main()
