#!/usr/bin/env bash
#
# Starts the BayDash kiosk: opens Chromium fullscreen pointed at the public
# GitHub Pages URL. No local server, no repo, no Python needed on the Pi
# anymore — all fetching and hosting happens in GitHub. The page polls for
# new data on its own and periodically reloads itself to pick up design
# changes, so this script never has to run again once it's up.
#
# Meant to be launched once at login (see README -> "On the Pi").

set -u

# ---------------------------------------------------------------------------
# EDIT THIS: your published Pages URL. After enabling Pages (Settings → Pages
# → Source: GitHub Actions) it is https://<your-username>.github.io/<repo>/
URL="${BAYDASH_URL:-https://loudtome.github.io/baytube/}"
# ---------------------------------------------------------------------------

HERE="$(cd "$(dirname "$0")" && pwd)"

if [[ "$URL" == *YOUR_GITHUB_USERNAME* ]]; then
  echo "start-kiosk.sh: set URL to your real Pages address first (edit the script" >&2
  echo "or export BAYDASH_URL=...)." >&2
  exit 1
fi

# --- 1. quiet the screensaver / blanking on X sessions (no-op on Wayland) ---
if [ "${XDG_SESSION_TYPE:-}" = "x11" ]; then
  xset s off || true
  xset -dpms || true
  xset s noblank || true
fi

# --- 2. find the Chromium binary (name differs across Pi OS versions) ---
CHROME=""
for c in chromium-browser chromium chromium-browser-v7 google-chrome; do
  if command -v "$c" >/dev/null 2>&1; then CHROME="$c"; break; fi
done
if [ -z "$CHROME" ]; then
  echo "No Chromium found. Install with: sudo apt install -y chromium-browser" >&2
  exit 1
fi

# use a throwaway profile so there's never a 'restore pages?' prompt
PROFILE="$HERE/.chrome-profile"
mkdir -p "$PROFILE"

exec "$CHROME" \
  --kiosk "$URL" \
  --user-data-dir="$PROFILE" \
  --password-store=basic \
  --no-first-run \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --disable-features=Translate,InfiniteSessionRestore \
  --disable-pinch \
  --overscroll-history-navigation=0 \
  --autoplay-policy=no-user-gesture-required \
  --check-for-update-interval=31536000 \
  --start-fullscreen
