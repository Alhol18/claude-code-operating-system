#!/usr/bin/env python3
"""OCR via macOS Vision: returns lines with pixel coordinates.

    python3 tools/ocr_boxes.py <file.png> [--json]

No keys or network. Languages: uk, ru, en. To find content to blur:
sums, phone numbers, names, chat text: extract boxes and blur with PIL.
Secondary mode: `--qr <file>` decodes QR code for verification.
"""
import json
import sys

import Quartz
import Vision
from Foundation import NSURL


def _handler(path):
    url = NSURL.fileURLWithPath_(path)
    src = Quartz.CGImageSourceCreateWithURL(url, None)
    if src is None:
        raise SystemExit(f"cannot read: {path}")
    cg = Quartz.CGImageSourceCreateImageAtIndex(src, 0, None)
    w = Quartz.CGImageGetWidth(cg)
    h = Quartz.CGImageGetHeight(cg)
    return Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg, None), w, h


def read_text(path):
    handler, w, h = _handler(path)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(0)  # accurate
    req.setRecognitionLanguages_(["uk-UA", "ru-RU", "en-US"])
    req.setUsesLanguageCorrection_(False)
    handler.performRequests_error_([req], None)
    lines = []
    for obs in req.results() or []:
        cand = obs.topCandidates_(1)
        if not cand:
            continue
        box = obs.boundingBox()
        x, y = box.origin.x, box.origin.y
        bw, bh = box.size.width, box.size.height
        lines.append({
            "t": cand[0].string(),
            "x": int(x * w),
            "y": int((1 - y - bh) * h),
            "w": int(bw * w),
            "h": int(bh * h),
        })
    lines.sort(key=lambda r: (r["y"], r["x"]))
    return {"file": path, "w": w, "h": h, "lines": lines}


def read_qr(path):
    handler, _, _ = _handler(path)
    req = Vision.VNDetectBarcodesRequest.alloc().init()
    handler.performRequests_error_([req], None)
    return [o.payloadStringValue() for o in (req.results() or [])]


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "--qr":
        for payload in read_qr(args[1]):
            print(payload)
    else:
        print(json.dumps(read_text(args[0]), ensure_ascii=False))
