"""Verify the Shikdar & Laaksonen ITEES companion-paper DOI via CrossRef.

1. Direct lookup of the DOI currently written in the manuscript.
2. Bibliographic search for the exact title.
3. Author search restricted to the journal (container-title).
Prints everything needed to confirm or correct the bibitem.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "doi-verify-script/1.0"}
BASE = "https://api.crossref.org"

DOI_IN_MS = "10.1155/etep/6000810"
TITLE = "Learning when not to use a battery: Multihorizon failure intelligence"
JOURNAL = "International Transactions on Electrical Energy Systems"


def fetch(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.load(r)


def show_item(it, prefix="  "):
    aus = ", ".join(
        f"{a.get('given', '')} {a.get('family', '')}".strip()
        for a in it.get("author", [])[:6]
    )
    print(f"{prefix}DOI     : {it.get('DOI')}")
    print(f"{prefix}title   : {(it.get('title') or ['?'])[0][:110]}")
    print(f"{prefix}journal : {(it.get('container-title') or ['?'])[0]}")
    print(f"{prefix}authors : {aus[:100]}")
    print(
        f"{prefix}issued  : {it.get('issued', {}).get('date-parts')} | "
        f"vol {it.get('volume')} | iss {it.get('issue')} | "
        f"art {it.get('article-number')} | pages {it.get('page')}"
    )
    print()


print("=== 1. DIRECT DOI LOOKUP:", DOI_IN_MS, "===")
try:
    m = fetch(f"{BASE}/works/{urllib.parse.quote(DOI_IN_MS)}")["message"]
    show_item(m)
except urllib.error.HTTPError as e:
    print(f"  HTTP {e.code} -> DOI NOT FOUND on CrossRef\n")
except Exception as e:
    print("  ERROR:", e, "\n")

print("=== 2. BIBLIOGRAPHIC SEARCH (title + journal) ===")
q = urllib.parse.quote(TITLE)
qj = urllib.parse.quote(JOURNAL)
try:
    d = fetch(f"{BASE}/works?query.bibliographic={q}&query.container-title={qj}&rows=5")
    for it in d["message"]["items"]:
        show_item(it)
except Exception as e:
    print("  ERROR:", e)

print("=== 3. AUTHOR SEARCH: Shikdar + Laaksonen (since 2023) ===")
qa = urllib.parse.quote("Shikdar Laaksonen")
try:
    d = fetch(
        f"{BASE}/works?query.author={qa}&rows=8&filter=from-pub-date:2023-01-01"
    )
    for it in d["message"]["items"]:
        aus = ", ".join(a.get("family", "") for a in it.get("author", [])[:4])
        print(
            f"  {it.get('DOI'):<38} | {aus[:45]:<45} | "
            f"{(it.get('title') or ['?'])[0][:75]}"
        )
except Exception as e:
    print("  ERROR:", e)
