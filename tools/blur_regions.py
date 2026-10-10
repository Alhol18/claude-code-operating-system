#!/usr/bin/env python3
"""Hides rectangles on screenshot: pixelization plus Gaussian blur.

    python3 tools/blur_regions.py plan.json

plan.json:
    [{"src": "...png", "out": "...png", "pad": 8,
      "rects": [[x, y, w, h], ...]}]

Pixelization happens first and makes the operation irreversible. Text can sometimes
be recovered from blur alone, but blocks of 1/14 size make recovery impossible.
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageFilter


def hide(img, rects, pad=8, block=14):
    for x, y, w, h in rects:
        box = (max(0, x - pad), max(0, y - pad),
               min(img.width, x + w + pad), min(img.height, y + h + pad))
        if box[2] <= box[0] or box[3] <= box[1]:
            continue
        crop = img.crop(box)
        small = crop.resize((max(1, crop.width // block), max(1, crop.height // block)), Image.BILINEAR)
        crop = small.resize(crop.size, Image.NEAREST).filter(ImageFilter.GaussianBlur(9))
        img.paste(crop, box)
    return img


if __name__ == "__main__":
    plan = json.loads(Path(sys.argv[1]).read_text())
    for job in plan:
        img = Image.open(job["src"]).convert("RGB")
        img = hide(img, job["rects"], job.get("pad", 8), job.get("block", 14))
        out = Path(job["out"])
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(out, optimize=True)
        print(f"{out.name}  {len(job['rects'])} regions  {out.stat().st_size // 1024} KB")
