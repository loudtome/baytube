# sasha.guide

This repo builds and hosts **[sasha.guide](https://sasha.guide/)** — a small
personal site served for free from GitHub. It started as a boating & weather
dashboard and now also holds a trail-relay race plan. Everything here is built
as plain files (HTML + a little Python) and published automatically by GitHub.

Two things live on the site today:

| Path | What it is |
|------|------------|
| **[sasha.guide](https://sasha.guide/)** | **BayDash** — a live boating & weather dashboard for Windmill Point / Kilmarnock, VA (built for a Raspberry Pi kiosk or an iPad). |
| **[sasha.guide/at-relay/](https://sasha.guide/at-relay/)** | **AT Relay** — a plan for a 6-runner Appalachian Trail relay (Rockfish Gap → US-522): per-runner legs, maps, elevation, and van-driving notes. |

---

## ⚠️ Read this first — it's a PUBLIC website

**This repository is public.** Everything committed here is visible to *anyone
on the internet*, forever — the whole world can read it on GitHub, and the built
files are published live at **sasha.guide**. There is no password and nothing is
private.

**Even if you delete something later, it stays in the Git history and in Google's
cache.** Treat every commit as permanent and public.

So, whether you're a person or an AI assistant helping edit this repo:

- 🚫 **Never add personal information (PII).** No home addresses, phone numbers,
  personal email addresses, exact "where we'll be at this time" locations for
  named people, license plates, or anything you wouldn't put on a public
  billboard. First names are fine; a runner's full name + phone + live location
  is not.
- 🚫 **Never add secrets.** No passwords, API keys, tokens, `.env` files, or
  private URLs. (This project deliberately uses only free, keyless public data
  sources, so it never needs any — see below. If a task seems to require a
  secret, stop and ask a human instead.)
- 🚫 **Don't commit private files** — screenshots with personal info, private
  PDFs, contact lists, calendars, etc.
- ✅ **When in doubt, leave it out** and ask. It's much easier to never publish
  something than to un-publish it.

> **Note for AI coding agents:** This is a public GitHub Pages repo (custom
> domain `sasha.guide`). Before committing, scan the diff for PII and secrets and
> refuse to commit them. Do not paste in credentials, personal contact details,
> or real-time whereabouts of named individuals. Prefer public, keyless data
> sources. If a change appears to require a secret or exposes personal data, stop
> and flag it to the repository owner rather than proceeding.

---

# BayDash (the weather dashboard)

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

**Live: https://sasha.guide/**

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
| **Sea Nettles** | Rappahannock/York probability, today + tomorrow | NOAA NCCOS (Box 6) |
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
| `at-relay/` | The Appalachian Trail relay plan (static HTML + maps). |
| `.github/workflows/deploy.yml` | Scheduled fetch + Pages deploy. |
| `.github/workflows/keepalive.yml` | Monthly commit so the schedule isn't auto-disabled. |

`build/`, `manifest.json`, `stats.json`, and `images/` are generated at deploy
time and are **gitignored** — never commit them.

## On an iPad

Just open **https://sasha.guide/** in Safari. Add to Home Screen for a
full-screen, chrome-free version. Portrait puts the tabs along the bottom;
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

---

# AT Relay (the trail-race plan)

Lives at **[sasha.guide/at-relay/](https://sasha.guide/at-relay/)**. A plan for a
6-runner Appalachian Trail relay from **Rockfish Gap → US-522** — 18 legs,
~107.8 miles, ~14,000+ ft of climbing, strict 1→6 runner rotation.

It's a set of static pages (no build step, no data feeds):

| Page | Shows |
|------|-------|
| `at-relay/index.html` | The full relay plan — all 18 legs, mileage, elevation, runner assignments. |
| `at-relay/runner-1.html` … `runner-6.html` | One page per runner: just their legs. |
| `at-relay/loft-mountain-map.html` | The Loft Mountain exchange map. |
| `at-relay/van-instructions.html` | Driving notes for the support van. |
| `at-relay/legNN_map.png` / `legNN_elev.png` | Per-leg course map and elevation profile images. |

To edit, change the HTML files directly and push — GitHub Pages redeploys the
site. (Remember the public-repo rules above: keep runners' personal details off
these pages.)
