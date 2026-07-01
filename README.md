# BayDash

A public web page that cycles through Chesapeake Bay maps (sea nettles, radar,
tides, water temp…) near Windmill Point, VA. A Raspberry Pi at the house runs
Chromium in kiosk mode pointed at the page — but **all the logic lives here in
GitHub**, not on the Pi.

You edit `config.json` from your laptop; GitHub fetches the maps and hosts the
page; the Pi just re-renders. No SSH, no tunnel, no public IP on the Pi.

## How it works

```
schedule (every ~30 min) ─► GitHub Actions runner
                              1. seed build/ from the CURRENT live site (last-good copy)
                              2. run fetch_feeds.py  ─► downloads maps + writes manifest.json
                              3. copy index.html, config.json into build/
                              4. upload-pages-artifact ─► deploy-pages
   also on: push to main, manual dispatch    │
                                             ▼
                                       GitHub Pages  (https://USER.github.io/baytube/)
                                             │
                              Pi's Chromium polls it ─► re-renders
```

**The fetched images never touch git history.** The scheduled workflow bundles
them into the Pages artifact at deploy time, so the repo only ever holds source
files and stays tiny forever. This is why Pages is set to deploy from **GitHub
Actions**, not from a branch.

## Files

| File | Role |
|------|------|
| `config.json` | **Your edit surface.** The list of maps + per-feed cadence. |
| `index.html` | The full-screen display page (cycling, status, dwell bar). |
| `fetch_feeds.py` | Downloads each map on its schedule, writes `manifest.json`. Stdlib only. |
| `seed_from_live.py` | Pulls the live site's images into `build/` before a fetch (last-good copy). |
| `start-kiosk.sh` | Runs on the Pi: opens Chromium fullscreen at the Pages URL. |
| `.github/workflows/deploy.yml` | Scheduled fetch + Pages deploy. |
| `.github/workflows/keepalive.yml` | Monthly trivial commit so the schedule isn't auto-disabled. |

`build/`, `manifest.json`, and `images/` are **generated at deploy time and are
gitignored** — never commit them.

## One-time GitHub setup

1. Create a **public** repo named `baytube` and push these files.
   (Public keeps Actions minutes free; the NOAA imagery is public anyway.)
2. **Settings → Pages → Source: GitHub Actions.**
3. **Actions → "Fetch feeds and deploy to Pages" → Run workflow** to do the
   first deploy. The first run seeds nothing (no live site yet) and just
   fetches fresh — that's expected.
4. Your page is live at `https://<your-username>.github.io/baytube/`.

After that it redeploys automatically every ~30 minutes, on every push to
`main`, and via the manual button.

## On the Pi

The Pi no longer needs the repo, Python, or a cron job — just Chromium and this
one script.

1. Copy `start-kiosk.sh` to the Pi (e.g. `~/start-kiosk.sh`) and edit the `URL`
   line to your real Pages address (or `export BAYDASH_URL=...`).
2. `chmod +x ~/start-kiosk.sh`
3. Make it launch at login. On current Pi OS (Bookworm / Wayfire), add to
   `~/.config/wayfire.ini`:
   ```
   [autostart]
   baydash = /home/USER/start-kiosk.sh
   ```
   (labwc: add `/home/USER/start-kiosk.sh &` to `~/.config/labwc/autostart`.
   Older X11/LXDE: a `~/.config/autostart/baydash.desktop` entry.)
4. `raspi-config` → **System Options → Boot/Auto Login → Desktop Autologin**,
   and **Display Options → Screen Blanking → Disable**. Reboot.

Set the Pi's **time zone** correctly in `raspi-config` → Localisation — the
"Updated 8:04 AM" labels are formatted in the browser's local zone.

## Editing maps

Edit `config.json`, commit, push. The push triggers a redeploy; the display
picks up the new lineup on its next poll (within a minute), and design changes
to `index.html` reach the Pi at the next periodic page reload
(`settings.page_reload_hours`, default 8h).

- To **add** a map: copy a feed block, fill in `url`, set `"enabled": true`.
- To **remove** one: delete the block or set `"enabled": false`.

Per-feed knobs:
- `refresh_minutes` — how often to re-download (radar ~30, tides/nettles ~720).
  Note the workflow runs every ~30 min, so nothing refreshes faster than that.
- `dwell_seconds` — how long the map stays on screen.
- `stale_after_minutes` — once the newest copy is older than this, the screen
  marks the source offline instead of presenting an old map as current.

**Finding a feed's image URL:** open the source page, right-click the image →
**Copy image address**, paste into `url`. The URL should end in
`.png`/`.gif`/`.jpg` (a direct image, not a viewer page) and keep the same
filename each day. Some NOAA viewers are interactive with no direct image file —
those need a different approach.

## Local testing

```
BAYDASH_OUTPUT_DIR=build python3 fetch_feeds.py
python3 -m http.server 8080 --directory build
# open http://127.0.0.1:8080/  (copy index.html into build/ first, or symlink)
```

## Notes & gotchas

- **Cron is best-effort** — scheduled runs often lag a few minutes; fine here.
- **Scheduled-workflow auto-disable** — GitHub pauses schedules after ~60 days
  with no commits. `keepalive.yml` makes a monthly commit as insurance.
- **Cache** — the page busts the manifest with `?cb=timestamp` and images with
  `?v=last_success_iso`, so images refresh only when actually updated.
- **v2 (later):** a live-stats card (wind / air + water temp / tide level).
  Design: add `type: "stats"` feeds, fetch NOAA Tides & Currents + api.weather.gov
  JSON into a `stats.json`, render a stats template. Build maps-only v1 first.
