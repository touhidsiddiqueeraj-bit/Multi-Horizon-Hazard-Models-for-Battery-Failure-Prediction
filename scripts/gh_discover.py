"""Discover the GitHub account and accessible repos for the provided token (from GH_TOKEN env)."""
import json
import os
import sys
import urllib.request

TOKEN = os.environ.get("GH_TOKEN", "")
HDR = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/vnd.github+json",
    "User-Agent": "paper-push-script",
}


def get(url):
    req = urllib.request.Request(url, headers=HDR)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


if not TOKEN:
    print("GH_TOKEN not set")
    sys.exit(1)

try:
    me = get("https://api.github.com/user")
except Exception as e:
    print("AUTH FAILED:", e)
    sys.exit(1)

print("LOGIN:", me.get("login"), "| type:", me.get("type"), "| name:", me.get("name"))
print("--- ACCESSIBLE REPOS (sorted by pushed_at) ---")
repos = get(
    "https://api.github.com/user/repos?sort=pushed&per_page=50"
    "&affiliation=owner,collaborator,organization_member"
)
if not repos:
    print("(none)")
for r in repos:
    vis = "private" if r.get("private") else "public"
    can_push = r.get("permissions", {}).get("push")
    print(
        f"{r['full_name']:<45} | pushed={r.get('pushed_at', '?'):<20} | "
        f"default={r.get('default_branch', '?'):<10} | {r.get('size', 0):>7}KB | "
        f"{vis:<6} | push_perm={can_push}"
    )
