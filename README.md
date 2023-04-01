# AnySubtitle
Make your videos accessible to a wider audience by adding subtitles in your target language, with support for any language vedio.

# Automatic subtitles in your videos

This repository uses `ffmpeg`, [OpenAI's Whisper](https://openai.com/blog/whisper) and [Fairseq's NLLB](https://ai.facebook.com/research/no-language-left-behind/)  to automatically generate, translate and overlay subtitles on any language video.

## Installation

To get started, you'll need install the binary by running the following command:

    pip install git+https://github.com/huggingface/transformers.git

    pip install git+https://github.com/Zth9730/AnySubtitle.git

You'll also need to install [`ffmpeg`](https://ffmpeg.org/), which is available from most package managers:

```bash
# on Ubuntu or Debian
sudo apt update && sudo apt install ffmpeg

# on MacOS using Homebrew (https://brew.sh/)
brew install ffmpeg

# on Windows using Chocolatey (https://chocolatey.org/)
choco install ffmpeg
```

## Usage

The following command will generate a `subtitled/video.mp4` file contained the input video with overlayed subtitles.

    auto_subtitle /path/to/video.mp4 -o subtitled/

The default setting (which selects the `small` model) works well for transcribing English. You can optionally use a bigger model for better results (especially with other languages). The available models are `tiny`, `tiny.en`, `base`, `base.en`, `small`, `small.en`, `medium`, `medium.en`, `large`.

    auto_subtitle /path/to/video.mp4 --model medium

Adding `--task translate` will translate the subtitles into English:

    auto_subtitle /path/to/video.mp4 --task translate

Run the following to view all available options:

    auto_subtitle --help

## Acknowledge
AnySubtitle refer to [auto-subtitle](https://github.com/m1guelpf/auto-subtitle).

## License

This script is open-source and licensed under the MIT License. For more details, check the [LICENSE](LICENSE) file.
