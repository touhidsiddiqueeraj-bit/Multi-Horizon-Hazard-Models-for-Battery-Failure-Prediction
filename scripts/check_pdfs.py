"""Find every remaining trace of the removed companion citation in compiled PDFs."""
import os
import re
import subprocess

os.chdir('/home/z/my-project/download')
PDFS = [
    'paper_tr/main_tr.pdf',
    'paper_itees/main_itees.pdf',
    'itees_package/main_itees.pdf',
    'paper_tr/supplement_tr.pdf',
    'itees_package/supplement_ITEES.pdf',
]

for f in PDFS:
    print(f'=== {f} ===')
    if not os.path.exists(f):
        print('  MISSING')
        continue
    txt = subprocess.run(['pdftotext', f, '-'], capture_output=True, text=True).stdout
    hits = list(re.finditer(r'Shikdar', txt))
    if not hits:
        print('  no "Shikdar" text found')
    for m in hits:
        s = max(0, m.start() - 90)
        ctx = ' '.join(txt[s:m.start() + 130].split())
        print('  SHIKDAR CTX:', ctx)
    # what sits at reference [18] (may match in-text citation too)
    for m in list(re.finditer(r'\[18\]', txt))[:3]:
        s = max(0, m.start() - 40)
        ctx = ' '.join(txt[s:m.start() + 150].split())
        print('  "[18]" CTX:', ctx)
    nums = sorted({int(x) for x in re.findall(r'\[(\d+)\]', txt)})
    print('  highest [n] seen:', nums[-1] if nums else '?')
    print()
