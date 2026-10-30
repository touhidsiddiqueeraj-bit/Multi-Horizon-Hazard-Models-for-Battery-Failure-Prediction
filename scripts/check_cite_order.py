"""Column-aware first-citation-order check for the IEEE TR manuscript.

Reading order per page: for a two-column IEEE layout, sort text lines by
(page, column, y). Full-width floats (table*/figure*) sit above the columns,
so their text is assigned to a "top" band read before both columns.
"""
import re
import sys
import fitz

PDF = "/home/z/my-project/download/paper_tr/main_tr.pdf"
doc = fitz.open(PDF)

# Find where References section starts (first references-list page)
ref_page = None
for pno in range(len(doc)):
    txt = doc[pno].get_text()
    if re.search(r"R\s+EFERENCES", txt):
        ref_page = pno
        break
print(f"Total pages: {len(doc)}; REFERENCES heading on page {ref_page + 1 if ref_page is not None else '?'}")

def reading_units(page):
    """Yield (order_key, text) in reading order for one page."""
    W = page.rect.width
    mid = W / 2
    units = []
    for b in page.get_text("blocks"):
        x0, y0, x1, y1, text = b[0], b[1], b[2], b[3], b[4]
        if not text.strip():
            continue
        # full-width blocks (floats spanning both columns) -> band 0
        if x0 < mid - 40 and x1 > mid + 40:
            band = 0
        elif x0 < mid:
            band = 1  # left column
        else:
            band = 2  # right column
        units.append(((band, round(y0), x0), text))
    units.sort(key=lambda t: t[0])
    return units

first = {}
for pno in range(len(doc)):
    if ref_page is not None and pno >= ref_page:
        break
    page = doc[pno]
    for (_, text) in reading_units(page):
        for m in re.finditer(r"\[(\d+)\]", text):
            n = int(m.group(1))
            if n not in first:
                first[n] = (pno + 1, text.strip()[:60].replace("\n", " "))

ok = True
prev_n, prev_pos = 0, None
for n in sorted(first):
    page, ctx = first[n]
    if n != prev_n + 1:
        print(f"ORDER PROBLEM: [{n}] appears but [{prev_n + 1}] was expected next "
              f"(first seen on p{page}: {ctx!r})")
        ok = False
    prev_n = n

missing = [n for n in range(1, 40) if n not in first]
print("Cited in body:", len(first), "of 39")
if missing:
    print("Not cited in body pages:", missing)
print("First-citation order:", "OK (strictly 1,2,3,...,39)" if ok else "CHECK ABOVE")
