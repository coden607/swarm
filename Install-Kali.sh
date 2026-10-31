#!/bin/sh
# Swarm on Kali. Open Install-Kali.desktop, or run: sh Install-Kali.sh
# Installs into ~/swarm (a checkout is copied there) and opens the dashboard.
set -eu
HERE="$(cd "$(dirname "$0")" && pwd)"
TARGET="${SWARM_HOME:-$HOME/swarm}"

if [ -f "$HERE/install.sh" ] && [ -f "$HERE/app/main.py" ] && [ "$HERE" != "$TARGET" ]; then
  mkdir -p "$TARGET"
  tar -C "$HERE" \
    --exclude venv --exclude .git --exclude .env --exclude data \
    --exclude swarm.log --exclude swarm.pid --exclude __pycache__ \
    -cf - . | tar -C "$TARGET" -xf -
  sh "$TARGET/install.sh"
elif [ -f "$HERE/install.sh" ] && [ -f "$HERE/app/main.py" ]; then
  sh "$HERE/install.sh"
else
  curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
fi

if [ -t 0 ]; then
  printf '\nPress Enter to close. '
  read x || true
fi
