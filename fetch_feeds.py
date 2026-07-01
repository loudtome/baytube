#!/usr/bin/env python3
"""
BayDash feed downloader.

Reads config.json, downloads each enabled feed's image into the output
directory's images/ folder on its own schedule, and writes manifest.json
describing what the display should show and how fresh each map is.

Designed to be run repeatedly (by GitHub Actions on a schedule). On each
run it only re-downloads a feed if enough time has passed since its last
success, so per-feed cadence lives in config.json.

Output paths are configurable via the BAYDASH_OUTPUT_DIR env var so the
CI workflow can point it at its build/ directory. Config path is
overridable via BAYDASH_CONFIG. Defaults keep it runnable locally too.

Standard library only - nothing to pip install on the runner.
"""

import json
import os
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("BAYDASH_CONFIG", os.path.join(BASE_DIR, "config.json"))
OUTPUT_DIR = os.environ.get("BAYDASH_OUTPUT_DIR", os.path.join(BASE_DIR, "build"))
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.json")

IMAGE_EXTS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}


def log(msg):
    stamp = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}] {msg}", flush=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest():
    """Previous manifest holds each feed's last-success time so we know
    when it's due and how stale it is. In CI the workflow seeds this file
    from the currently-deployed site before we run. Missing/corrupt ->
    start clean."""
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {feed["id"]: feed for feed in data.get("feeds", [])}
    except (FileNotFoundError, ValueError, KeyError):
        return {}


def write_json_atomic(path, obj):
    """Write to a temp file in the same dir, then rename, so a reader
    (the display) never sees a half-written file."""
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2)
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def pick_extension(url, content_type):
    path = url.split("?", 1)[0].split("#", 1)[0]
    _, ext = os.path.splitext(path)
    if ext.lower() in IMAGE_EXTS:
        return ext.lower()
    if content_type:
        subtype = content_type.split("/", 1)[-1].split(";", 1)[0].strip().lower()
        mapped = {"jpeg": ".jpg", "svg+xml": ".svg"}.get(subtype, "." + subtype)
        if mapped in IMAGE_EXTS:
            return mapped
    return ".img"


def download_image(url, timeout, user_agent):
    """Return (bytes, extension) or raise. Rejects error pages that come
    back as HTML so a 'feed down' page never gets shown as a map."""
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        if status != 200:
            raise ValueError(f"HTTP {status}")
        content_type = resp.headers.get("Content-Type", "")
        data = resp.read()

    if not data:
        raise ValueError("empty response")
    if "html" in content_type.lower() or data[:15].lstrip().lower().startswith(b"<!doctype") or data[:6].lower().startswith(b"<html"):
        raise ValueError("got an HTML page, not an image (source error?)")
    if content_type and not content_type.lower().startswith("image/") and "octet-stream" not in content_type.lower():
        raise ValueError(f"unexpected content-type: {content_type}")

    return data, pick_extension(url, content_type)


def human_time(iso_str):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str).astimezone()
        return dt.strftime("%b %-d, %-I:%M %p")
    except ValueError:
        return None


def process_feed(feed, settings, prev):
    """Decide whether to download, do it if due, and return a manifest record."""
    now = datetime.now(timezone.utc)
    rec = dict(prev)  # carry forward last_success, file, etc.
    rec.update({
        "id": feed["id"],
        "label": feed.get("label", feed["id"]),
        "kicker": feed.get("kicker", ""),
        "note": feed.get("note", ""),
        "dwell_seconds": feed.get("dwell_seconds", settings.get("default_dwell_seconds", 12)),
    })
    stale_after = feed.get("stale_after_minutes", settings.get("default_stale_after_minutes", 1440))
    refresh_minutes = feed.get("refresh_minutes", 60)

    last_success_iso = prev.get("last_success")
    due = True
    if last_success_iso:
        try:
            last_dt = datetime.fromisoformat(last_success_iso)
            age_min = (now - last_dt).total_seconds() / 60.0
            due = age_min >= refresh_minutes
        except ValueError:
            due = True

    if due:
        try:
            data, ext = download_image(
                feed["url"],
                settings.get("request_timeout_seconds", 20),
                settings.get("user_agent", "BayDash/1.0"),
            )
            filename = f"{feed['id']}{ext}"
            fd, tmp = tempfile.mkstemp(dir=IMAGES_DIR, suffix=".tmp")
            with os.fdopen(fd, "wb") as f:
                f.write(data)
            os.replace(tmp, os.path.join(IMAGES_DIR, filename))
            # remove a stale copy with a different extension, if any
            for old_ext in IMAGE_EXTS:
                old = os.path.join(IMAGES_DIR, f"{feed['id']}{old_ext}")
                if old_ext != ext and os.path.exists(old):
                    os.remove(old)
            rec["file"] = filename
            rec["last_success"] = now.isoformat()
            rec["ok"] = True
            rec["error"] = None
            log(f"{feed['id']}: downloaded {len(data) // 1024} KB -> {filename}")
        except (urllib.error.URLError, ValueError, OSError) as e:
            rec["ok"] = False
            rec["error"] = str(e)
            rec.setdefault("file", prev.get("file"))
            rec["last_success"] = prev.get("last_success")
            log(f"{feed['id']}: FAILED ({e}) - keeping last good copy")
    else:
        rec["ok"] = prev.get("ok", True)
        rec["error"] = prev.get("error")
        rec["file"] = prev.get("file")
        rec["last_success"] = prev.get("last_success")

    # freshness for the display
    if rec.get("last_success"):
        try:
            ls = datetime.fromisoformat(rec["last_success"])
            age_min = (now - ls).total_seconds() / 60.0
        except ValueError:
            age_min = None
    else:
        age_min = None

    rec["age_minutes"] = round(age_min, 1) if age_min is not None else None
    rec["stale"] = bool(age_min is not None and age_min > stale_after)
    rec["last_success_iso"] = rec.get("last_success")
    rec["updated_human"] = human_time(rec.get("last_success"))
    return rec


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    config = load_config()
    settings = config.get("settings", {})
    prev_by_id = load_manifest()

    records = []
    for feed in config.get("feeds", []):
        if not feed.get("enabled", True):
            continue
        if not feed.get("url") or feed["url"].startswith("PASTE_"):
            log(f"{feed.get('id')}: skipped (no url set)")
            continue
        records.append(process_feed(feed, settings, prev_by_id.get(feed["id"], {})))

    manifest = {
        "generated": datetime.now(timezone.utc).isoformat(),
        "generated_human": datetime.now().astimezone().strftime("%b %-d, %-I:%M %p"),
        "manifest_reload_seconds": settings.get("manifest_reload_seconds", 60),
        "page_reload_hours": settings.get("page_reload_hours", 8),
        "feeds": records,
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    log(f"wrote manifest with {len(records)} feed(s) -> {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
