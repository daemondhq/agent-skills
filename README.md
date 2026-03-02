# Agent Skills

A collection of skills that extend AI agents with multimodal capabilities — image generation, audio transcription, and visual understanding.

## Skills

| Skill | Description | Auth |
|---|---|---|
| **nano-banana-all** | Generate and edit images using Google's Nano Banana models (versions 1, 1-pro, 2) | `GEMINI_API_KEY` |
| **openai-whisper** | Transcribe audio files using OpenAI Whisper / GPT-4o | `OPENAI_API_KEY` |
| **gemini-vision** | Analyze and understand images using Gemini 2.5 Flash | `GEMINI_API_KEY` |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) — scripts are self-contained with inline dependencies, `uv run` handles everything automatically

## Structure

Each skill is a folder containing:

```
skill-name/
├── SKILL.md              # Skill definition (triggers, usage, examples)
└── scripts/              # Executable scripts
```

`SKILL.md` is what the agent reads to know when and how to use the skill. Scripts are invoked via `uv run` with no manual setup required.

## License

MIT
