#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "openai>=1.0.0",
# ]
# ///
"""
Transcribe audio files using OpenAI's Whisper / GPT-4o transcription API.

Usage:
    uv run transcribe.py --file audio.mp3 [--model gpt-4o-mini-transcribe] [--format text] [--language en] [--api-key KEY]
"""

import argparse
import os
import sys
from pathlib import Path

MODELS = [
    "gpt-4o-transcribe",
    "gpt-4o-mini-transcribe",
    "whisper-1",
]

FORMAT_BY_MODEL = {
    "gpt-4o-transcribe": ["text", "json"],
    "gpt-4o-mini-transcribe": ["text", "json"],
    "whisper-1": ["text", "json", "verbose_json", "srt", "vtt"],
}

MAX_FILE_SIZE_MB = 25


def get_api_key(provided_key: str | None) -> str | None:
    if provided_key:
        return provided_key
    return os.environ.get("OPENAI_API_KEY")


def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio using OpenAI Whisper / GPT-4o"
    )
    parser.add_argument(
        "--file", "-f",
        required=True,
        help="Path to audio file (mp3, mp4, mpeg, mpga, m4a, wav, webm)"
    )
    parser.add_argument(
        "--model", "-m",
        choices=MODELS,
        default="gpt-4o-mini-transcribe",
        help="Transcription model (default: gpt-4o-mini-transcribe)"
    )
    parser.add_argument(
        "--format", "-F",
        default="text",
        help="Output format: text, json (all models); verbose_json, srt, vtt (whisper-1 only)"
    )
    parser.add_argument(
        "--language", "-l",
        default=None,
        help="ISO-639-1 language code (e.g., en, fr, es) for improved accuracy"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save transcription to file instead of stdout"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="OpenAI API key (overrides OPENAI_API_KEY env var)"
    )

    args = parser.parse_args()

    audio_path = Path(args.file)
    if not audio_path.exists():
        print(f"Error: File not found: {audio_path}", file=sys.stderr)
        sys.exit(1)

    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    if file_size_mb > MAX_FILE_SIZE_MB:
        print(f"Error: File is {file_size_mb:.1f}MB, exceeds {MAX_FILE_SIZE_MB}MB limit", file=sys.stderr)
        sys.exit(1)

    allowed_formats = FORMAT_BY_MODEL.get(args.model, ["text", "json"])
    if args.format not in allowed_formats:
        print(f"Error: Format '{args.format}' not supported by {args.model}. Use: {', '.join(allowed_formats)}", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set OPENAI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    from openai import OpenAI

    client = OpenAI(api_key=api_key)

    print(f"Transcribing: {audio_path.name} ({file_size_mb:.1f}MB)", file=sys.stderr)
    print(f"Model: {args.model} | Format: {args.format}", file=sys.stderr)

    kwargs = {
        "model": args.model,
        "file": audio_path,
        "response_format": args.format,
    }
    if args.language:
        kwargs["language"] = args.language

    try:
        result = client.audio.transcriptions.create(**kwargs)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.format == "text":
        output = result
    else:
        output = result.model_dump_json(indent=2) if hasattr(result, "model_dump_json") else str(result)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(output, encoding="utf-8")
        print(f"\nTranscription saved: {out_path.resolve()}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
