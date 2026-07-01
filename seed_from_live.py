#!/usr/bin/env python3
"""
Seed the build/ directory from the currently-deployed Pages site.

Run by the deploy workflow BEFORE fetch_feeds.py. Downloads the live
manifest.json and every image it references into build/, so
fetch_feeds.py's "keep last good copy on failure" and "only re-download
when due" logic has its prior state. This is the persistence store — the
just-deployed site seeds the next run. No git state, no cache.

Best-effort by design: on the very first deploy there is no live site yet,
so nothing is seeded and fetch_feeds.py simply starts clean.

Usage: seed_from_live.py <BASE_URL>   (e.g. https://user.github.io/baytube)
Output dir honors BAYDASH_OUTPUT_DIR (default: build).

Standard library only.
"""

import json
import os
import sys
import urllib.request
import urllib.error

OUTPUT_DIR = os.environ.get("BAYDASH_OUTPUT_DIR", "build")
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.json")
STATS_PATH = os.path.join(OUTPUT_DIR, "stats.json")
USER_AGENT = "BayDash-seed/1.0"
TIMEOUT = 30


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
        return resp.read()


def seed_file(base, rel):
    """Download one images/<rel> from the live site into build/images/<rel>."""
    dest = os.path.join(IMAGES_DIR, rel)
    try:
        data = fetch(f"{base}/images/{rel}?cb=seed")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "wb") as out:
            out.write(data)
        print(f"seeded {rel} ({len(data) // 1024} KB)")
    except (urllib.error.URLError, OSError) as e:
        print(f"skip {rel}: {e}")


def main():
    if len(sys.argv) < 2:
        print("usage: seed_from_live.py <BASE_URL>")
        return 2
    base = sys.argv[1].rstrip("/")
    os.makedirs(IMAGES_DIR, exist_ok=True)
    run_id = os.environ.get("GITHUB_RUN_ID", "seed")

    # stats.json is best-effort: lets fetch_stats.py carry values forward.
    try:
        raw_stats = fetch(f"{base}/stats.json?cb={run_id}")
        json.loads(raw_stats)
        with open(STATS_PATH, "wb") as f:
            f.write(raw_stats)
        print("seeded stats.json")
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"no live stats.json ({e})")

    try:
        raw = fetch(f"{base}/manifest.json?cb={run_id}")
        manifest = json.loads(raw)
    except (urllib.error.URLError, OSError, ValueError) as e:
        print(f"No live manifest yet ({e}) - starting clean.")
        return 0

    with open(MANIFEST_PATH, "wb") as f:
        f.write(raw)
    print(f"Seeded manifest.json from {base}")

    # manifest.tabs: image tabs carry `file`, frame tabs carry `frames: [...]`
    for tab in manifest.get("tabs", []):
        if tab.get("file"):
            seed_file(base, tab["file"])
        for rel in tab.get("frames", []) or []:
            seed_file(base, rel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
