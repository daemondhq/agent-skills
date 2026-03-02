#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "google-genai>=1.0.0",
#     "pillow>=10.0.0",
# ]
# ///
"""
Analyze images using Google's Gemini 2.5 Flash model.

Usage:
    uv run analyze.py --image photo.png [--prompt "What's in this image?"] [--output result.txt] [--api-key KEY]
"""

import argparse
import os
import sys
from pathlib import Path

SUPPORTED_FORMATS = {".png", ".jpg", ".jpeg", ".webp", ".heic", ".heif"}


def get_api_key(provided_key: str | None) -> str | None:
    if provided_key:
        return provided_key
    return os.environ.get("GEMINI_API_KEY")


def main():
    parser = argparse.ArgumentParser(
        description="Analyze images using Gemini 2.5 Flash"
    )
    parser.add_argument(
        "--image", "-i",
        required=True,
        help="Path to image file (png, jpg, webp, heic, heif)"
    )
    parser.add_argument(
        "--prompt", "-p",
        default="Describe this image in detail.",
        help="Question or instruction about the image (default: describe)"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save response to file instead of stdout"
    )
    parser.add_argument(
        "--api-key", "-k",
        help="Gemini API key (overrides GEMINI_API_KEY env var)"
    )

    args = parser.parse_args()

    image_path = Path(args.image)
    if not image_path.exists():
        print(f"Error: File not found: {image_path}", file=sys.stderr)
        sys.exit(1)

    if image_path.suffix.lower() not in SUPPORTED_FORMATS:
        print(f"Error: Unsupported format '{image_path.suffix}'. Use: {', '.join(sorted(SUPPORTED_FORMATS))}", file=sys.stderr)
        sys.exit(1)

    api_key = get_api_key(args.api_key)
    if not api_key:
        print("Error: No API key provided.", file=sys.stderr)
        print("  1. Provide --api-key argument", file=sys.stderr)
        print("  2. Set GEMINI_API_KEY environment variable", file=sys.stderr)
        sys.exit(1)

    from google import genai
    from google.genai import types
    from PIL import Image as PILImage

    client = genai.Client(api_key=api_key)

    try:
        image = PILImage.open(image_path)
    except Exception as e:
        print(f"Error loading image: {e}", file=sys.stderr)
        sys.exit(1)

    width, height = image.size
    file_size_mb = image_path.stat().st_size / (1024 * 1024)
    print(f"Analyzing: {image_path.name} ({width}x{height}, {file_size_mb:.1f}MB)", file=sys.stderr)
    print(f"Prompt: {args.prompt}", file=sys.stderr)

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[image, args.prompt],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT"],
            ),
        )

        text = response.text
        if not text:
            print("Error: No text response from model.", file=sys.stderr)
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"\nResponse saved: {out_path.resolve()}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
