# BayDash

A boating & weather dashboard for **Windmill Point / Kilmarnock, VA**. It cycles
through tabs of live conditions — an at-a-glance overview, wind (speed + compass +
regional map), waves (height + animated forecast map), tides (current state +
hi/lo schedule), radar, and sea nettles — with a persistent Small Craft Advisory
banner across the top.

All logic and data collection live **here in GitHub**, not on any device. A
Raspberry Pi runs Chromium in kiosk mode pointed at the page; it also works great
just opened on an **iPad** (the layout is responsive — left tab-rail in landscape,
bottom tab-strip in portrait). You edit `config.json` from your laptop; GitHub
fetches everything and hosts the page.

**Live: https://loudtome.github.io/baytube/**

## How it works

```
schedule (~30 min) ─► GitHub Actions runner
   1. seed build/ from the live site (last-good copy: images, frames, stats)
   2. fetch_feeds.py  ─► maps + animation frames → manifest.json
   3. fetch_stats.py  ─► tides / wind / waves / SCA (NOAA JSON) → stats.json
   4. copy index.html, config.json into build/
   5. upload-pages-artifact ─► deploy-pages
                                      │
  also on: push to main, manual       ▼
                                GitHub Pages ──► Pi / iPad polls & re-renders
```

Fetched data (images, frames, JSON) is bundled into the Pages artifact at deploy
time and **never enters git history**, so the repo stays tiny forever.

## Tabs & data sources (all keyless, verified for the Windmill Point area)

| Tab | Shows | Source |
|-----|-------|--------|
| **Now** | Overview: SCA, wind, waves, water temp, tide — one glance | (all below) |
| **Wind** | Speed (kt) + gust + compass/cardinal, a 48h line graph, and a 48h table | NDBC buoy **44058** (live, when fresh) + NWS gridpoint `AKQ/88,86` |
| **Waves** | Significant wave height (ft), a 48h line graph, and a 48h table | NWS gridpoint `waveHeight` |
| **Tides** | Current level + rising/falling + today's high/low times | NOAA CO-OPS **8636580 "Windmill Point"** (0.1 mi, live sensor) |
| **Radar** | KAKQ loop | NWS Wakefield |
| **Sea Nettles** | Rappahannock/York probability (8-day animation) | NOAA NCCOS (Box 6) |
| _banner_ | **Small Craft Advisory**: none / in-effect / expected ≤24h | NWS alerts, marine zones **ANZ630/631/635** |

Cycling: each tab auto-advances after its `dwell_seconds` (~10–16s). Tap/click a
tab to pin it; auto-cycling resumes 60s later.

## Feed types (in `config.json` → `tabs`)

- **`image`** — one map per tab, on its own `refresh_minutes` (radar, nettles).
- **`frames`** — a `frames` block. The fetcher scrapes the given `page_url`
  listing, regex-matches the current frame filenames (`frame_regex`), downloads
  them all under `frame_base`, and the display animates them `frame_ms` apart —
  building our own loop from sources that ship the frames separately. Frame
  indices shift each model run, so the live list is read every time.
  `frame_take: "first"` = soonest (forecast), `"last"` = most recent (nowcast).
- **`overview` / `wind` / `waves` / `tides`** — rendered from `stats.json`
  (wind/waves also embed their `frames` map).

## Files

| File | Role |
|------|------|
| `config.json` | **Your edit surface** — tabs, cadence, and `stats_sources`. |
| `index.html` | Responsive tabbed display (rail/strip, compass, cards, animation). |
| `fetch_feeds.py` | Downloads maps + animation frames → `manifest.json`. |
| `fetch_stats.py` | Pulls NOAA JSON (tides/wind/waves/SCA) → `stats.json`. |
| `seed_from_live.py` | Seeds `build/` from the live site (last-good copy). |
| `start-kiosk.sh` | Runs on the Pi: Chromium fullscreen at the Pages URL. |
| `.github/workflows/deploy.yml` | Scheduled fetch + Pages deploy. |
| `.github/workflows/keepalive.yml` | Monthly commit so the schedule isn't auto-disabled. |

`build/`, `manifest.json`, `stats.json`, and `images/` are generated at deploy
time and are **gitignored** — never commit them.

## On an iPad

Just open **https://loudtome.github.io/baytube/** in Safari. Add to Home Screen
for a full-screen, chrome-free version. Portrait puts the tabs along the bottom;
landscape uses the left rail. Timestamps show in the device's local time.

## On the Pi (kiosk)

1. Copy `start-kiosk.sh` to the Pi (URL is preset to the Pages address).
2. `chmod +x ~/start-kiosk.sh` and add it to autostart (Wayfire/labwc/X — see
   comments in the script). `raspi-config` → Desktop Autologin + disable screen
   blanking, and set the **time zone** correctly. Reboot.

The Pi needs only Chromium — no repo, Python, or cron.

## Editing

Edit `config.json`, commit, push → redeploys. Add a map = one `tabs` block. To
change the location entirely, update `stats_sources` (tide station, gridpoint,
buoy, marine zones) and the map `frames`/`url`s.

Per-feed knobs: `refresh_minutes`, `dwell_seconds`, `stale_after_minutes`,
`max_frames`, `frame_take`. Global: `tab_seconds`, `resume_after_seconds`,
`frame_ms`, `page_reload_hours` in `settings`.

## Notes

- **Cron is best-effort** — scheduled runs lag a few minutes; fine here.
- **Keepalive** — `keepalive.yml` makes a monthly commit so GitHub doesn't pause
  the schedule after 60 days of no commits.
- Each stats section is independent: if a NOAA source is down, that value carries
  forward from the last good `stats.json` and the rest of the screen keeps working.
