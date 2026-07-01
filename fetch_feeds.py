#!/usr/bin/env python3
"""
BayDash feed downloader (images + animation frames).

Reads config.json's `tabs` list and writes manifest.json describing the
display: the tab order/labels/types, single-map images, and multi-PNG
animation frame sets. The numeric stats (Now / Wind / Waves / Tides) come
from fetch_stats.py -> stats.json; this module handles everything image.

Two things it fetches:
  - `image` tabs: one map per tab, on its own refresh schedule (radar, nettles).
  - any tab with a `frames` block: scrape the given listing (an HTML page or a
    NOAA OFS "option" file), regex out the frame filenames, download them all,
    and record the ordered list. The display animates them frame_ms apart to
    build our own loop from sources that ship the frames separately.

Runs repeatedly (GitHub Actions). Only re-downloads a feed when its
refresh_minutes has elapsed; keeps the last good copy on failure. Output
paths honor BAYDASH_OUTPUT_DIR (default build). Standard library only.
"""

import json
import os
import re
import sys
import tempfile
import urllib.request
import urllib.error
from datetime import datetime, timezone
from urllib.parse import urljoin

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("BAYDASH_CONFIG", os.path.join(BASE_DIR, "config.json"))
OUTPUT_DIR = os.environ.get("BAYDASH_OUTPUT_DIR", os.path.join(BASE_DIR, "build"))
IMAGES_DIR = os.path.join(OUTPUT_DIR, "images")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.json")

IMAGE_EXTS = {".png", ".gif", ".jpg", ".jpeg", ".webp", ".bmp"}


def log(msg):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}Z] {msg}", flush=True)


def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def load_manifest():
    """Prior manifest -> per-tab last-success (due checks + last-good copy)."""
    try:
        with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            return {t["id"]: t for t in data.get("tabs", [])}
    except (FileNotFoundError, ValueError, KeyError):
        return {}


def write_json_atomic(path, obj):
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


def fetch_bytes(url, timeout, user_agent):
    req = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        status = getattr(resp, "status", 200)
        if status != 200:
            raise ValueError(f"HTTP {status}")
        return resp.headers.get("Content-Type", ""), resp.read()


def download_image(url, timeout, user_agent):
    """Return (bytes, extension). Rejects HTML error pages so a 'source down'
    page never gets shown as a map."""
    content_type, data = fetch_bytes(url, timeout, user_agent)
    if not data:
        raise ValueError("empty response")
    head = data[:64].lstrip().lower()
    if "html" in content_type.lower() or head.startswith(b"<!doctype") or head.startswith(b"<html"):
        raise ValueError("got an HTML page, not an image (source error?)")
    if content_type and not content_type.lower().startswith("image/") and "octet-stream" not in content_type.lower():
        raise ValueError(f"unexpected content-type: {content_type}")
    return data, pick_extension(url, content_type)


def age_minutes(iso_str, now):
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        return (now - dt).total_seconds() / 60.0
    except ValueError:
        return None


def is_due(prev_iso, refresh_minutes, now):
    age = age_minutes(prev_iso, now)
    return age is None or age >= refresh_minutes


def write_bytes_atomic(dest, data):
    d = os.path.dirname(dest)
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    with os.fdopen(fd, "wb") as f:
        f.write(data)
    os.replace(tmp, dest)


# ---------------------------------------------------------------------------
# per-type handlers
# ---------------------------------------------------------------------------

def process_image(tab, settings, prev, now):
    rec = {
        "id": tab["id"], "label": tab.get("label", tab["id"]),
        "type": "image", "kicker": tab.get("kicker", ""),
        "note": tab.get("note", ""),
        "dwell_seconds": tab.get("dwell_seconds", settings.get("default_dwell_seconds", 12)),
    }
    stale_after = tab.get("stale_after_minutes", settings.get("default_stale_after_minutes", 1440))
    refresh = tab.get("refresh_minutes", 60)
    url = tab.get("url")
    if not url or url.startswith("PASTE_"):
        log(f"{tab['id']}: skipped (no url)")
        rec.update({"file": None, "last_success_iso": None, "ok": False, "stale": True})
        return rec

    if is_due(prev.get("last_success_iso"), refresh, now):
        try:
            data, ext = download_image(url, settings.get("request_timeout_seconds", 20),
                                       settings.get("user_agent", "BayDash/1.0"))
            filename = f"{tab['id']}{ext}"
            write_bytes_atomic(os.path.join(IMAGES_DIR, filename), data)
            for old_ext in IMAGE_EXTS:
                old = os.path.join(IMAGES_DIR, f"{tab['id']}{old_ext}")
                if old_ext != ext and os.path.exists(old):
                    os.remove(old)
            rec.update({"file": filename, "last_success_iso": now.isoformat(), "ok": True})
            log(f"{tab['id']}: downloaded {len(data)//1024} KB -> {filename}")
        except (urllib.error.URLError, ValueError, OSError) as e:
            rec.update({"file": prev.get("file"), "last_success_iso": prev.get("last_success_iso"), "ok": False})
            log(f"{tab['id']}: FAILED ({e}) - keeping last good copy")
    else:
        rec.update({"file": prev.get("file"), "last_success_iso": prev.get("last_success_iso"),
                    "ok": prev.get("ok", True)})

    age = age_minutes(rec.get("last_success_iso"), now)
    rec["age_minutes"] = round(age, 1) if age is not None else None
    rec["stale"] = bool(age is not None and age > stale_after)
    return rec


def discover_frames(spec, timeout, user_agent):
    """Fetch the listing (HTML page or OFS option file), regex out frame
    filenames, and return ordered absolute URLs. The regex's group(1) is the
    numeric ordering key (forecast hour or timestamp)."""
    _, raw = fetch_bytes(spec["page_url"], timeout, user_agent)
    text = raw.decode("utf-8", "replace")
    rx = re.compile(spec["frame_regex"])
    seen, frames = set(), []
    for m in rx.finditer(text):
        name = m.group(0)
        if name in seen:
            continue
        seen.add(name)
        try:
            key = int(m.group(1))
        except (IndexError, ValueError):
            key = len(frames)
        frames.append((key, urljoin(spec["frame_base"], name)))
    frames.sort(key=lambda x: x[0])
    take = spec.get("frame_take", "last")
    n = spec.get("max_frames", 16)
    chosen = frames[-n:] if take == "last" else frames[:n]
    return [url for _, url in chosen]


def process_frames(tab, settings, prev, now):
    spec = tab["frames"]
    rec = {
        "id": tab["id"], "label": tab.get("label", tab["id"]),
        "type": tab.get("type", "frames"), "kicker": tab.get("kicker", ""),
        "note": spec.get("note", tab.get("note", "")),
        "dwell_seconds": tab.get("dwell_seconds", settings.get("default_dwell_seconds", 12)),
    }
    stale_after = spec.get("stale_after_minutes", settings.get("default_stale_after_minutes", 1440))
    refresh = spec.get("refresh_minutes", 120)
    timeout = settings.get("request_timeout_seconds", 20)
    ua = settings.get("user_agent", "BayDash/1.0")

    if not is_due(prev.get("frames_last_success"), refresh, now):
        rec.update({"frames": prev.get("frames", []),
                    "frames_last_success": prev.get("frames_last_success"),
                    "frames_ok": prev.get("frames_ok", True)})
    else:
        try:
            urls = discover_frames(spec, timeout, ua)
            if not urls:
                raise ValueError("no frames matched on the listing")
            out_dir = os.path.join(IMAGES_DIR, tab["id"])
            os.makedirs(out_dir, exist_ok=True)
            files = []
            for i, url in enumerate(urls):
                try:
                    data, ext = download_image(url, timeout, ua)
                except (urllib.error.URLError, ValueError, OSError) as e:
                    log(f"{tab['id']}: frame {i} failed ({e})")
                    continue
                fn = f"{i:03d}{ext}"
                write_bytes_atomic(os.path.join(out_dir, fn), data)
                files.append(f"{tab['id']}/{fn}")
            if not files:
                raise ValueError("all frame downloads failed")
            # drop any leftover frames from a longer previous run
            keep = set(os.path.basename(f) for f in files)
            for existing in os.listdir(out_dir):
                if existing not in keep and not existing.endswith(".tmp"):
                    os.remove(os.path.join(out_dir, existing))
            rec.update({"frames": files, "frames_last_success": now.isoformat(), "frames_ok": True})
            log(f"{tab['id']}: {len(files)} frames downloaded")
        except (urllib.error.URLError, ValueError, OSError) as e:
            rec.update({"frames": prev.get("frames", []),
                        "frames_last_success": prev.get("frames_last_success"),
                        "frames_ok": False})
            log(f"{tab['id']}: FAILED ({e}) - keeping last good frames")

    age = age_minutes(rec.get("frames_last_success"), now)
    rec["age_minutes"] = round(age, 1) if age is not None else None
    rec["stale"] = bool(age is not None and age > stale_after)
    return rec


def main():
    os.makedirs(IMAGES_DIR, exist_ok=True)
    config = load_config()
    settings = config.get("settings", {})
    prev_by_id = load_manifest()
    now = datetime.now(timezone.utc)

    tabs = []
    for tab in config.get("tabs", []):
        if tab.get("enabled") is False:
            continue
        prev = prev_by_id.get(tab["id"], {})
        if tab.get("frames"):
            tabs.append(process_frames(tab, settings, prev, now))
        elif tab.get("type") == "image":
            tabs.append(process_image(tab, settings, prev, now))
        else:
            # overview / stats-only tab: pure metadata, data comes from stats.json
            tabs.append({
                "id": tab["id"], "label": tab.get("label", tab["id"]),
                "type": tab.get("type", "stats"), "view": tab.get("view", tab.get("type")),
                "kicker": tab.get("kicker", ""),
                "dwell_seconds": tab.get("dwell_seconds", settings.get("default_dwell_seconds", 12)),
            })

    manifest = {
        "generated": now.isoformat(),
        "app_version": os.environ.get("BAYDASH_APP_VERSION", ""),
        "manifest_reload_seconds": settings.get("manifest_reload_seconds", 60),
        "stats_reload_seconds": settings.get("stats_reload_seconds", 120),
        "page_reload_hours": settings.get("page_reload_hours", 8),
        "tab_seconds": settings.get("tab_seconds", 10),
        "resume_after_seconds": settings.get("resume_after_seconds", 60),
        "frame_ms": settings.get("frame_ms", 1000),
        "location": config.get("location", {}).get("label", "Bay Conditions"),
        "tabs": tabs,
    }
    write_json_atomic(MANIFEST_PATH, manifest)
    log(f"wrote manifest with {len(tabs)} tab(s) -> {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
