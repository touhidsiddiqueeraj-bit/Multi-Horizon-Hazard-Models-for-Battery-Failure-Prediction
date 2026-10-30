#!/usr/bin/env python3
"""Programmatic layout QA for the ITEES PDFs: per-page ink coverage,
blank-page detection, margin-overflow detection (ink beyond the 2.5cm frame),
and figure-presence detection (colored pixel ratio)."""
from PIL import Image
import glob
import sys

def check(prefix, label, pages_expected):
    files = sorted(glob.glob(f"/tmp/render/{prefix}-*.jpg")) or \
            sorted(glob.glob(f"/tmp/render/{prefix}*.jpg"))
    if not files:
        print(f"{label}: NO PAGES FOUND"); return
    print(f"=== {label}: {len(files)} pages ===")
    issues = []
    for f in files:
        img = Image.open(f).convert("RGB")
        w, h = img.size
        # A4 at 60dpi: 496x702 px. Margin 2.5cm = 59px. Frame = x:[59, w-59]
        m = int(2.5 / 21.0 * w)  # 2.5cm of 21cm width
        px = img.load()
        dark = 0; colored = 0; total = w * h
        overflow = 0
        for y in range(0, h, 2):
            for x in range(0, w, 2):
                r, g, b = px[x, y]
                if r < 200 or g < 200 or b < 200:
                    dark += 1
                    if x < m - 2 or x > w - m + 2:
                        overflow += 1
                    if max(r, g, b) - min(r, g, b) > 30:
                        colored += 1
        sampled = (w // 2) * (h // 2)
        ink = dark / sampled
        page = f.split("/")[-1]
        status = []
        if ink < 0.005:
            status.append("NEARLY BLANK")
        if ink > 0.55:
            status.append("VERY DENSE")
        if overflow / max(dark, 1) > 0.02:
            status.append(f"INK OUTSIDE MARGINS ({overflow}/{dark})")
        print(f"{page}: ink={ink:.3f} colored={colored/sampled:.4f} {' '.join(status) or 'ok'}")
        if status:
            issues.append((page, status))
    print(f"{label}: {'ALL OK' if not issues else issues}")

check("m", "MAIN (main_itees.pdf)", 18)
check("s", "SUPPLEMENT (supplement_itees.pdf)", 5)
