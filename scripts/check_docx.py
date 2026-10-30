"""Check the ITEES .docx deliverables for stale references to the removed companion study."""
import re
import sys
import zipfile

BASE = sys.argv[1] if len(sys.argv) > 1 else '/home/z/my-project/download'
FILES = [
    f'{BASE}/Cover_Letter_ITEES.docx',
    f'{BASE}/Submission_Checklist_ITEES.docx',
    f'{BASE}/Suggested_Reviewers_ITEES.docx',
]
PATTERNS = [
    (r'manuscript under review', 'STALE: "manuscript under review"'),
    (r'Calibration robustness of battery', 'STALE: removed paper title'),
    (r'shikdar2026robustness', 'STALE: removed cite key'),
    (r'\b39 (references|entries)', 'STALE: "39 refs"'),
    (r'\b38 (references|entries)', 'ok: "38 refs"'),
    (r'\[18\]', 'note: mentions [18]'),
    (r'\[10\]', 'ok: mentions [10]'),
    (r'6000810', 'ok: companion DOI'),
]

for f in FILES:
    try:
        xml = zipfile.ZipFile(f).read('word/document.xml').decode('utf8', 'ignore')
    except Exception as e:
        print(f, 'ERROR', e)
        continue
    text = re.sub(r'<[^>]+>', ' ', xml)
    text = re.sub(r'\s+', ' ', text)
    print('===', f.split("/")[-1], '===')
    for pat, label in PATTERNS[:4]:  # the potentially-stale ones
        for m in re.finditer(pat, text):
            s = max(0, m.start() - 90)
            print(f'  [{label}]')
            print(f'    ...{text[s:m.end() + 90]}...')
    print()
