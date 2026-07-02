#!/usr/bin/env python3
"""
BayDash live-stats collector.

Pulls the numeric marine conditions for the Windmill Point / Kilmarnock VA
area from keyless NOAA endpoints and writes build/stats.json, which the
display renders as the Now / Wind / Tides tabs and the SCA banner.

Sources (all verified, all keyless — see config.json stats_sources):
  - Tides:  CO-OPS 8636580 "Windmill Point" — hi/lo predictions + live level
  - Waves:  NWS gridpoint AKQ/88,86 waveHeight (the bay buoy has no wave sensor)
  - Wind:   NWS gridpoint wind* forecast, plus live wind from NDBC buoy 44058
  - Water temp: NDBC buoy 44058
  - Small Craft Advisory: NWS active alerts for zones ANZ630/631/635

All times are stored as UTC ISO strings; the browser formats them to the
viewer's local zone. Each section is independent: if a source is down we
carry the previous value forward from the seeded stats.json and mark it
stale, so the rest of the screen keeps working.

Output honors BAYDASH_OUTPUT_DIR (default build). Standard library only.
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.environ.get("BAYDASH_CONFIG", os.path.join(BASE_DIR, "config.json"))
OUTPUT_DIR = os.environ.get("BAYDASH_OUTPUT_DIR", os.path.join(BASE_DIR, "build"))
STATS_PATH = os.path.join(OUTPUT_DIR, "stats.json")

COOPS = "https://api.tidesandcurrents.noaa.gov/api/prod/datagetter"
NDBC = "https://www.ndbc.noaa.gov/data/realtime2"
ALERTS = "https://api.weather.gov/alerts/active"

CARDINALS = ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE",
             "S", "SSW", "SW", "WSW", "W", "WNW", "NW", "NNW"]


def log(msg):
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{stamp}Z] {msg}", flush=True)


def now_utc():
    return datetime.now(timezone.utc)


def cardinal(deg):
    if deg is None:
        return None
    return CARDINALS[int((deg % 360) / 22.5 + 0.5) % 16]


def ms_to_kt(v):
    return round(v * 1.943844, 1)


def kmh_to_kt(v):
    return round(v / 1.852, 1)


def m_to_ft(v):
    return round(v * 3.280839895, 1)


def c_to_f(v):
    return round(v * 9.0 / 5.0 + 32.0, 1)


def parse_iso(s):
    """Parse an ISO time (with or without offset) to an aware UTC datetime."""
    if not s:
        return None
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        return None


def http(url, ua, timeout, as_json=True):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return json.loads(raw) if as_json else raw.decode("utf-8", "replace")


def load_prev():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


# ---------------------------------------------------------------------------
# sections
# ---------------------------------------------------------------------------

def get_tides(station, ua, timeout):
    """Hi/lo schedule + current level and rising/falling state (all UTC)."""
    begin = now_utc().strftime("%Y%m%d")
    pred = http(
        f"{COOPS}?product=predictions&application=BayDash&begin_date={begin}"
        f"&range=48&datum=MLLW&station={station}&time_zone=gmt&interval=hilo"
        f"&units=english&format=json", ua, timeout)
    events = []
    for p in pred.get("predictions", []):
        # CO-OPS 't' in GMT: "YYYY-MM-DD HH:MM"
        iso = p["t"].replace(" ", "T") + "+00:00"
        events.append({"iso": iso, "type": p["type"], "ft": round(float(p["v"]), 1)})

    now = now_utc()
    upcoming = [e for e in events if parse_iso(e["iso"]) and parse_iso(e["iso"]) > now]
    nxt = upcoming[0] if upcoming else None

    now_ft, obs_iso = None, None
    try:
        wl = http(
            f"{COOPS}?product=water_level&application=BayDash&date=latest"
            f"&datum=MLLW&station={station}&time_zone=gmt&units=english&format=json",
            ua, timeout)
        row = (wl.get("data") or [None])[0]
        if row:
            now_ft = round(float(row["v"]), 1)
            obs_iso = row["t"].replace(" ", "T") + "+00:00"
    except (urllib.error.URLError, OSError, ValueError, KeyError):
        pass

    # state: near an extreme -> high/low, else rising toward next H / falling toward next L
    state = None
    if nxt:
        mins_to_next = (parse_iso(nxt["iso"]) - now).total_seconds() / 60.0
        if mins_to_next <= 25:
            state = "high" if nxt["type"] == "H" else "low"
        else:
            state = "rising" if nxt["type"] == "H" else "falling"

    return {
        "ok": True, "obs_iso": obs_iso, "now_ft": now_ft, "state": state,
        "next": nxt, "events": events,
    }


def get_gridpoint(url, ua, timeout):
    """Wave height (m->ft) + wind (km/h->kt, deg) as current + 24h forecast."""
    d = http(url, ua, timeout)["properties"]
    now = now_utc()
    horizon = now + timedelta(hours=24)

    def series(key):
        out = []
        for v in d.get(key, {}).get("values", []):
            start = parse_iso(v["validTime"].split("/")[0])
            if start is not None and v.get("value") is not None:
                out.append((start, v["value"]))
        out.sort(key=lambda x: x[0])
        return out

    def current(series_vals):
        cur = None
        for start, val in series_vals:
            if start <= now:
                cur = val
            else:
                break
        return cur if cur is not None else (series_vals[0][1] if series_vals else None)

    wave_s = series("waveHeight")
    spd_s = series("windSpeed")
    dir_s = series("windDirection")
    gst_s = series("windGust")
    temp_s = series("temperature")  # air temp, Celsius (fallback for the buoy)

    def at(series_vals, t):
        """Value of the step-function at time t (last point at or before t)."""
        v = None
        for start, val in series_vals:
            if start <= t:
                v = val
            else:
                break
        return v if v is not None else (series_vals[0][1] if series_vals else None)

    wave_now = current(wave_s)
    # regular 3-hourly samples (48h) for a readable forecast table:
    # wave height plus the wind (speed + direction) at the same times.
    wave_fc = []
    base_t = now.replace(minute=0, second=0, microsecond=0)
    for h in range(0, 49, 3):
        t = base_t + timedelta(hours=h)
        wv = at(wave_s, t)
        if wv is None:
            continue
        ws = at(spd_s, t)
        wd = at(dir_s, t)
        wave_fc.append({
            "iso": t.isoformat(),
            "ft": m_to_ft(wv),
            "wind_kt": kmh_to_kt(ws) if ws is not None else None,
            "wind_dir_deg": round(wd) if wd is not None else None,
        })

    spd_now = current(spd_s)
    dir_now = current(dir_s)
    gst_now = current(gst_s)
    # regular 3-hourly wind forecast (48h) for the wind table
    wind_fc = []
    for h in range(0, 49, 3):
        t = base_t + timedelta(hours=h)
        ws = at(spd_s, t)
        if ws is None:
            continue
        wd = at(dir_s, t)
        wg = at(gst_s, t)
        wind_fc.append({
            "iso": t.isoformat(),
            "kt": kmh_to_kt(ws),
            "dir_deg": round(wd) if wd is not None else None,
            "gust_kt": kmh_to_kt(wg) if wg is not None else None,
        })

    air_now = current(temp_s)
    return {
        "wave_ft": m_to_ft(wave_now) if wave_now is not None else None,
        "wave_forecast": wave_fc,
        "wind_kt": kmh_to_kt(spd_now) if spd_now is not None else None,
        "wind_dir_deg": round(dir_now) if dir_now is not None else None,
        "wind_gust_kt": kmh_to_kt(gst_now) if gst_now is not None else None,
        "wind_forecast": wind_fc,
        "air_f": c_to_f(air_now) if air_now is not None else None,
    }


def get_buoy(station, ua, timeout):
    """Live wind + water temp from an NDBC realtime2 feed (MM = missing)."""
    txt = http(f"{NDBC}/{station}.txt", ua, timeout, as_json=False)
    lines = [ln for ln in txt.splitlines() if ln.strip()]
    header = lines[0].split()
    data = None
    for ln in lines:
        if not ln.startswith("#"):
            data = ln.split()
            break
    if not data:
        raise ValueError("no data rows")
    row = dict(zip(header, data))

    def num(key):
        v = row.get(key)
        if v is None or v == "MM":
            return None
        try:
            return float(v)
        except ValueError:
            return None

    obs_iso = None
    try:
        y, mo, dy, hr, mn = (int(row[k]) for k in ("#YY", "MM", "DD", "hh", "mm"))
        obs_iso = datetime(y, mo, dy, hr, mn, tzinfo=timezone.utc).isoformat()
    except (KeyError, ValueError):
        pass

    wspd = num("WSPD")
    gst = num("GST")
    wdir = num("WDIR")
    wtmp = num("WTMP")
    return {
        "wind_kt": ms_to_kt(wspd) if wspd is not None else None,
        "wind_gust_kt": ms_to_kt(gst) if gst is not None else None,
        "wind_dir_deg": round(wdir) if wdir is not None else None,
        "water_temp_f": c_to_f(wtmp) if wtmp is not None else None,
        "air_temp_f": c_to_f(num("ATMP")) if num("ATMP") is not None else None,
        "obs_iso": obs_iso,
    }


def get_sca(zones, ua, timeout):
    """Small Craft Advisory: active now, expected within 24h, or none."""
    d = http(f"{ALERTS}?zone={zones}", ua, timeout)
    now = now_utc()
    soon = now + timedelta(hours=24)
    active, expected = None, None
    for f in d.get("features", []):
        p = f["properties"]
        if "small craft advisory" not in (p.get("event", "").lower()):
            continue
        onset = parse_iso(p.get("onset") or p.get("effective"))
        ends = parse_iso(p.get("ends") or p.get("expires"))
        rec = {
            "headline": p.get("headline"),
            "starts_iso": onset.isoformat() if onset else None,
            "ends_iso": ends.isoformat() if ends else None,
            "area": p.get("areaDesc"),
        }
        if (onset is None or onset <= now) and (ends is None or ends >= now):
            active = rec
            break
        if onset is not None and now < onset <= soon:
            if expected is None or onset < parse_iso(expected["starts_iso"]):
                expected = rec
    if active:
        return {"status": "active", **active}
    if expected:
        return {"status": "expected", **expected}
    return {"status": "none"}


# ---------------------------------------------------------------------------

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        config = json.load(f)
    settings = config.get("settings", {})
    src = config.get("stats_sources", {})
    ua = settings.get("user_agent", "BayDash/1.0")
    timeout = settings.get("request_timeout_seconds", 20)
    prev = load_prev()

    stats = {
        "generated": now_utc().isoformat(),
        "location": config.get("location", {}).get("label", "Bay Conditions"),
    }

    # each section independent; carry forward + mark stale on failure
    def run(name, fn):
        try:
            val = fn()
            log(f"{name}: ok")
            return val
        except Exception as e:  # noqa: BLE001 - any failure -> carry forward
            log(f"{name}: FAILED ({e}) - carrying forward last good")
            old = prev.get(name)
            if isinstance(old, dict):
                return {**old, "stale": True}
            return {"ok": False, "stale": True}

    grid = run("_grid", lambda: get_gridpoint(src["gridpoint"], ua, timeout))
    buoy = run("_buoy", lambda: get_buoy(src["buoy"], ua, timeout))
    grid = {} if not isinstance(grid, dict) else grid
    buoy = {} if not isinstance(buoy, dict) else buoy

    # Wind: prefer the live buoy, but only if its reading is RECENT (the buoy
    # reports intermittently). If it's stale, use the NWS nowcast so the big
    # "now" number is actually current, not hours/days old.
    buoy_obs = parse_iso(buoy.get("obs_iso"))
    buoy_fresh = (buoy_obs is not None
                  and (now_utc() - buoy_obs).total_seconds() <= 3 * 3600
                  and buoy.get("wind_kt") is not None)
    if buoy_fresh:
        wind = {
            "speed_kt": buoy.get("wind_kt"), "gust_kt": buoy.get("wind_gust_kt"),
            "dir_deg": buoy.get("wind_dir_deg"), "source": "buoy 44058",
            "obs_iso": buoy.get("obs_iso"),
        }
    else:
        wind = {
            "speed_kt": grid.get("wind_kt"), "gust_kt": grid.get("wind_gust_kt"),
            "dir_deg": grid.get("wind_dir_deg"), "source": "NWS nowcast",
            "obs_iso": now_utc().isoformat(),
        }
    wind["forecast"] = grid.get("wind_forecast", [])
    wind["dir_cardinal"] = cardinal(wind["dir_deg"])
    stats["wind"] = wind

    stats["waves"] = {
        "height_ft": grid.get("wave_ft"),
        "forecast": grid.get("wave_forecast", []),
        "source": "NWS forecast",
    }
    stats["water"] = {"temp_f": buoy.get("water_temp_f"), "obs_iso": buoy.get("obs_iso")}
    stats["air"] = {
        "temp_f": buoy.get("air_temp_f") if buoy.get("air_temp_f") is not None else grid.get("air_f"),
        "obs_iso": buoy.get("obs_iso") if buoy.get("air_temp_f") is not None else None,
        "source": "buoy 44058" if buoy.get("air_temp_f") is not None else "NWS forecast",
    }
    stats["tide"] = run("tide", lambda: get_tides(src["tide_station"], ua, timeout))
    stats["sca"] = run("sca", lambda: get_sca(src["marine_zones"], ua, timeout))

    tmp = STATS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    os.replace(tmp, STATS_PATH)
    log(f"wrote {STATS_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
