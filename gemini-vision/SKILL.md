---
name: gemini-vision
description: "Analyze and understand images using Gemini 2.5 Flash. Use when the user provides an image, screenshot, photo, or document and wants it described, analyzed, read (OCR), or answered questions about. Supports png, jpg, webp, heic, heif."
---

# Gemini Vision — Image Understanding

Analyze images and answer questions about them using Google's Gemini 2.5 Flash.

## Preflight

- Verify `uv` is installed: `uv --version`
  - If missing: `curl -LsSf https://astral.sh/uv/install.sh | sh` (macOS/Linux) or `powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"` (Windows)
- Verify API key: `GEMINI_API_KEY` env var must be set (or pass `--api-key`)
- Verify image file exists and is a supported format

## Usage

```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "photo.png" [--prompt "What's in this image?"] [--output result.txt] [--api-key KEY]
```

Always run from the user's current working directory.

## Parameters

- `--image` (required): path to image file (png, jpg, webp, heic, heif)
- `--prompt` (optional): question or instruction about the image (default: "Describe this image in detail.")
- `--output` (optional): save response to file instead of stdout
- `--api-key` (optional): overrides `GEMINI_API_KEY` env var

## Supported Formats

png, jpg/jpeg, webp, heic, heif.

## Prompt Guidance

Pass the user's question as-is to `--prompt`. If no specific question is given, the default prompt describes the image in detail. Useful prompt patterns:

- "Describe this image in detail." (default)
- "What text is visible in this image?" (OCR)
- "What's wrong with this UI?" (design review)
- "Explain this chart/graph." (data analysis)
- "What programming language is this? Explain the code." (code screenshots)
- "List all items visible in this image." (inventory)

## Common Workflows

**Describe a photo:**
```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "photo.jpg"
```

**Read text from a screenshot (OCR):**
```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "screenshot.png" --prompt "Extract all text from this image"
```

**Analyze a chart:**
```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "chart.png" --prompt "Explain the trends shown in this chart and provide the key data points"
```

**Review a UI mockup:**
```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "mockup.png" --prompt "Review this UI design. What are the usability issues?"
```

**Save analysis to file:**
```bash
uv run ~/.codex/skills/gemini-vision/scripts/analyze.py --image "diagram.png" --prompt "Describe the architecture in this diagram" --output "analysis.txt"
```

**Compare images (multiple calls):**
Run the script once per image, then synthesize the results.

## Common Failures

- `File not found` → verify image path
- `Unsupported format` → convert to png/jpg first
- `Error: No API key provided` → set `GEMINI_API_KEY` or pass `--api-key`
- `Error loading image` → file may be corrupt or not a valid image
- "quota/permission/403" → wrong key, no access, or quota exceeded
