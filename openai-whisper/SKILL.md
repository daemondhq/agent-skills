---
name: openai-whisper
description: "Transcribe audio files using OpenAI Whisper / GPT-4o transcription. Use when the user provides an audio file, voice message, or recording and wants it transcribed, summarized, or understood. Supports mp3, mp4, m4a, wav, webm, mpeg, mpga."
---

# OpenAI Whisper Transcription

Transcribe audio files to text using OpenAI's transcription API.

## Preflight

- Verify `uv` is installed: `uv --version`
  - If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)
- Verify API key: `OPENAI_API_KEY` env var must be set (or pass `--api-key`)
- Verify audio file exists and is under 25MB

## Usage

```bash
uv run ~/.codex/skills/openai-whisper/scripts/transcribe.py --file "audio.mp3" [--model gpt-4o-mini-transcribe] [--format text] [--language en] [--output transcript.txt] [--api-key KEY]
```

Always run from the user's current working directory.

## Models

| `--model` | Speed | Quality | Output formats |
|---|---|---|---|
| `gpt-4o-mini-transcribe` | Fastest (default) | Good | text, json |
| `gpt-4o-transcribe` | Fast | Best | text, json |
| `whisper-1` | Moderate | Good | text, json, verbose_json, srt, vtt |

Map user requests:
- No preference → `gpt-4o-mini-transcribe`
- "best accuracy", "highest quality" → `gpt-4o-transcribe`
- "subtitles", "srt", "vtt", "timestamps" → `whisper-1` (only model supporting srt/vtt)

## Parameters

- `--file` (required): path to audio file
- `--model`: transcription model (default: `gpt-4o-mini-transcribe`)
- `--format`: output format (default: `text`)
- `--language`: ISO-639-1 code (e.g., `en`, `fr`, `es`) — improves accuracy
- `--output`: save to file instead of printing to stdout
- `--api-key`: OpenAI API key (overrides `OPENAI_API_KEY` env var)

## Supported Audio Formats

mp3, mp4, mpeg, mpga, m4a, wav, webm — max 25MB per file.

## Common Workflows

**Transcribe and read result:**
```bash
uv run ~/.codex/skills/openai-whisper/scripts/transcribe.py --file "voice-message.m4a"
```

**Transcribe to file:**
```bash
uv run ~/.codex/skills/openai-whisper/scripts/transcribe.py --file "meeting.mp3" --output "meeting-transcript.txt"
```

**Generate subtitles:**
```bash
uv run ~/.codex/skills/openai-whisper/scripts/transcribe.py --file "video.mp4" --model whisper-1 --format srt --output "subtitles.srt"
```

**Transcribe non-English audio:**
```bash
uv run ~/.codex/skills/openai-whisper/scripts/transcribe.py --file "audio.mp3" --language fr
```

## Common Failures

- `File not found` → verify audio file path
- `File exceeds 25MB limit` → split the file with `ffmpeg -i input.mp3 -f segment -segment_time 600 -c copy chunk_%03d.mp3`, transcribe each chunk, concatenate results
- `Error: No API key provided` → set `OPENAI_API_KEY` or pass `--api-key`
- `Format not supported by model` → srt/vtt/verbose_json only work with `whisper-1`
