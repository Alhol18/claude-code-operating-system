#!/usr/bin/env python3
"""
Gemini Video: universal video/image/audio analysis via Google Gemini API.

Usage:
    python3 tools/gemini_video.py <input> --mode transcribe
    python3 tools/gemini_video.py <input> --mode form-check
    python3 tools/gemini_video.py <input> --mode custom --prompt "..."
    python3 tools/gemini_video.py <input> --mode transcribe --save out.md

Inputs supported:
    - YouTube URL          (passed directly to Gemini)
    - Instagram/TikTok URL (downloaded via yt-dlp, then analyzed)
    - Local file ≤20MB     (inlined)
    - Local file >20MB     (uploaded via File API, ~48h retention)
    - Image/audio file     (same routing rules)

Modes:
    transcribe : speech-to-text in original language
    form-check : analyze body position during exercises (timecoded)
    custom     : pass-through user prompt

Auth:
    Requires GEMINI_API_KEY in .env (https://aistudio.google.com/apikey, free).

Cost:
    Uses Google Gemini quota: does NOT touch Anthropic/Claude budget.
    Free tier: ~1500 requests/day on 2.5-flash.
"""

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

INLINE_MAX_BYTES = 20 * 1024 * 1024
# Model selection. Verified 2026-09-25: 2.x model names return 404
# "no longer available"; API directs to 3.x. List of live models:
# `venv/bin/python -c "from google import genai; ..."` or .tmp/list_models.py.
#
# Free tier limit: 20 requests per day PER MODEL. Depletes faster than expected
# if iterating on visuals. Workaround: spread runs across different models since
# quota is tracked per model separately.
DEFAULT_MODEL = "gemini-3.5-flash"
FALLBACK_MODELS = ["gemini-3.8-flash", "gemini-3.1-flash-lite", "gemini-flash-latest"]
DOWNLOAD_DIR = Path(__file__).resolve().parent.parent / ".tmp" / "video"

PROMPTS = {
    "transcribe": (
        "Transcribe the audio of this video completely in the original language. "
        "Preserve the natural flow of speech. Break into paragraphs by logical blocks. "
        "Do not add your own commentary, only the clean transcript."
    ),
    "form-check": (
        "Analyze body position at specific moments during exercise execution. "
        "For each key exercise, provide:\n"
        "- timecode (MM:SS)\n"
        "- exercise name or description\n"
        "- correct body position points (spine, pelvis, shoulders, knees, feet)\n"
        "- errors or risks if present\n\n"
        "Structure as markdown with lists."
    ),
    "workout-analyze": (
        "This is a training video. Provide complete multimodal analysis (audio + visual) in this format:\n\n"
        "## Transcript with timecodes\n"
        "Clean transcript in original language in format `[MM:SS] paragraph text`. "
        "New timecode for: section change, new exercise, position change, "
        "or every 30-45 seconds within same block. "
        "No personal commentary, only what the instructor says.\n\n"
        "## Block structure\n"
        "Break video into logical blocks (warmup, standing, floor, breathing, cooldown, etc). "
        "For each block:\n"
        "- `[MM:SS - MM:SS]` time range\n"
        "- block name\n"
        "- list of exercises/positions with entry timecodes and key visual details "
        "(starting position, main movement, focus)\n\n"
        "## Equipment\n"
        "List all equipment visible in frame or mentioned by instructor. "
        "For each: timecode of first appearance and brief usage note. "
        "If none used, write 'no equipment'.\n\n"
        "## Instructor and setting\n"
        "Visual setting description: filming location (studio/home/gym), number of people, "
        "instructor clothing, floor/surface type. Use short notes.\n\n"
        "Markdown with `##` headings. Timecodes required everywhere specified."
    ),
}

MIME_BY_EXT = {
    ".mp4": "video/mp4", ".mov": "video/quicktime", ".webm": "video/webm",
    ".avi": "video/x-msvideo", ".mkv": "video/x-matroska", ".m4v": "video/x-m4v",
    ".3gp": "video/3gpp", ".mpg": "video/mpeg", ".mpeg": "video/mpeg",
    ".mp3": "audio/mpeg", ".wav": "audio/wav", ".m4a": "audio/mp4",
    ".aac": "audio/aac", ".ogg": "audio/ogg", ".flac": "audio/flac",
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".heic": "image/heic", ".gif": "image/gif",
}

SOCIAL_DOMAINS = ("instagram.com", "tiktok.com", "fb.watch", "facebook.com")


def is_url(s):
    p = urlparse(s)
    return p.scheme in ("http", "https")


def is_youtube(url):
    return "youtube.com" in url or "youtu.be" in url


def is_social_media(url):
    return any(d in url for d in SOCIAL_DOMAINS)


def guess_mime(path: Path):
    return MIME_BY_EXT.get(path.suffix.lower(), "application/octet-stream")


def download_via_ytdlp(url: str) -> Path:
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    template = DOWNLOAD_DIR / "%(extractor)s_%(id)s.%(ext)s"
    cmd = [
        "yt-dlp",
        "-f", "best[ext=mp4]/best",
        "-o", str(template),
        "--no-playlist",
        "--print", "after_move:filepath",
        "--no-simulate",
        url,
    ]
    print(f"→ Downloading {url} via yt-dlp...", file=sys.stderr)
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    sys.stderr.write(result.stderr)
    paths = [Path(line.strip()) for line in result.stdout.splitlines() if line.strip()]
    if not paths:
        raise RuntimeError(f"yt-dlp finished but no path printed for {url}")
    path = paths[-1]
    if not path.exists():
        raise RuntimeError(f"yt-dlp printed {path} but file does not exist")
    return path


def upload_via_file_api(client, path: Path):
    print(f"→ Uploading {path.name} ({path.stat().st_size // 1024 // 1024}MB) via File API...",
          file=sys.stderr)
    f = client.files.upload(file=str(path))
    while f.state.name == "PROCESSING":
        time.sleep(2)
        f = client.files.get(name=f.name)
    if f.state.name == "FAILED":
        raise RuntimeError(f"File API upload failed for {path}")
    return f


def to_seconds(t: str) -> int:
    """'1:05:30' / '20:00' / '1200' to seconds."""
    sec = 0
    for chunk in str(t).split(":"):
        sec = sec * 60 + int(chunk)
    return sec


def build_part(client, source: str, start=None, end=None):
    """Return a Gemini Part for the input (URL, social URL, or local file).

    start/end trim video on Gemini side (video_metadata). Long video does not fit whole:
    2 hours of YouTube ~2M tokens, and transcript output hits limit and loops (broke
    gorbach-1 this way). Chunks of ~20 min each."""
    meta = None
    if start is not None or end is not None:
        meta = types.VideoMetadata(
            start_offset=f"{to_seconds(start)}s" if start is not None else None,
            end_offset=f"{to_seconds(end)}s" if end is not None else None,
        )
    if is_url(source):
        if is_youtube(source):
            return types.Part(file_data=types.FileData(file_uri=source), video_metadata=meta)
        if is_social_media(source):
            local = download_via_ytdlp(source)
            return build_part(client, str(local))
        # Generic URL: try as file_data (works for direct media URLs)
        return types.Part(file_data=types.FileData(file_uri=source))

    path = Path(source).expanduser().resolve()
    if not path.exists():
        sys.exit(f"ERROR: file not found: {path}")
    size = path.stat().st_size
    mime = guess_mime(path)
    if size <= INLINE_MAX_BYTES:
        return types.Part.from_bytes(data=path.read_bytes(), mime_type=mime)
    f = upload_via_file_api(client, path)
    return types.Part(file_data=types.FileData(file_uri=f.uri, mime_type=f.mime_type))


def analyze(client, source: str, model: str, prompt: str, _ytdlp_fallback_used: bool = False,
            start=None, end=None):
    """Build part + run generate_content. Auto-fallback to yt-dlp for unlisted YouTube (403)."""
    part = build_part(client, source, start, end)
    try:
        return client.models.generate_content(model=model, contents=[part, prompt])
    except Exception as e:
        msg = str(e)
        if (
            not _ytdlp_fallback_used
            and is_url(source)
            and is_youtube(source)
            and ("PERMISSION_DENIED" in msg or "403" in msg)
        ):
            print(
                "⚠ YouTube returned 403 (likely unlisted/private video). "
                "Falling back to yt-dlp download → File API upload...",
                file=sys.stderr,
            )
            local = download_via_ytdlp(source)
            return analyze(client, str(local), model, prompt, _ytdlp_fallback_used=True,
                           start=start, end=end)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="Universal Gemini video/image/audio analyzer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("input", help="URL or local file path")
    parser.add_argument("--mode", choices=["transcribe", "form-check", "workout-analyze", "custom"],
                        default="custom",
                        help="Preset prompt or 'custom' for free-form")
    parser.add_argument("--prompt", help="Custom prompt (required if --mode custom)")
    parser.add_argument("--save", help="Save output to markdown file")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Gemini model (default: {DEFAULT_MODEL})")
    parser.add_argument("--lang", help="Response language hint (uk/ru/en)")
    parser.add_argument("--prompt-file", help="Read custom prompt from file")
    parser.add_argument("--start", help="Clip start: 1:05:30 / 20:00 / seconds")
    parser.add_argument("--end", help="Clip end: same format")
    args = parser.parse_args()

    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("ERROR: GEMINI_API_KEY not set in .env. "
                 "Get one at https://aistudio.google.com/apikey")

    if args.prompt_file:
        args.prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if args.mode == "custom" and not args.prompt:
        sys.exit("ERROR: --mode custom requires --prompt \"...\"")

    prompt = args.prompt if args.mode == "custom" else PROMPTS[args.mode]
    if args.lang:
        prompt += f"\n\nResponse language: {args.lang}"

    client = genai.Client(api_key=api_key)

    print(f"→ Analyzing with {args.model}...", file=sys.stderr)
    response = analyze(client, args.input, args.model, prompt, start=args.start, end=args.end)
    text = response.text or ""

    if args.save:
        out = Path(args.save).expanduser().resolve()
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
        print(f"✓ Saved to {out}", file=sys.stderr)
    else:
        print(text)


if __name__ == "__main__":
    main()
