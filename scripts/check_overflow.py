#!/usr/bin/env python3
"""Formatting gate per AGENTS.md: render PDF pages and scan for ink past the
text block. Pages where the rightmost ink column exceeds ~0.94 of page width
indicate a float sticking out of the two-column layout."""
import sys
import subprocess
import tempfile
import os
from PIL import Image

def scan(pdf_path, threshold=0.94, dpi=150):
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", str(dpi), "-png", pdf_path, os.path.join(td, "p")],
                       check=True, capture_output=True)
        pages = sorted(f for f in os.listdir(td) if f.endswith(".png"))
        bad = []
        widths = {}
        for f in pages:
            img = Image.open(os.path.join(td, f)).convert("L")
            w, h = img.size
            px = img.load()
            max_x = 0
            for x in range(w - 1, -1, -1):
                col_has_ink = any(px[x, y] < 200 for y in range(0, h, 3))
                if col_has_ink:
                    max_x = x
                    break
            frac = max_x / w
            widths[f] = round(frac, 4)
            if frac > threshold:
                bad.append((f, frac))
        return widths, bad

if __name__ == "__main__":
    pdf = sys.argv[1]
    widths, bad = scan(pdf)
    worst = sorted(widths.items(), key=lambda kv: -kv[1])[:6]
    print("worst pages by max-ink-x fraction:", worst)
    if bad:
        print("OVERFLOW on pages:", bad)
        sys.exit(1)
    print("CLEAN: no page exceeds 0.94")
