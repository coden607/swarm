#!/usr/bin/env bash
# =============================================================================
# Android one‑click Swarm installer (run inside Termux)
# =============================================================================
# This script is fetched by the one‑line command shown in the Android README.
# It performs the following steps inside a lightweight proot‑distro (Alpine) so
# that Docker can run without requiring a rooted Android device.
#
# Prerequisites (handled by the outer Termux command):
#   - termux-app installed (via F‑Droid)
#   - pkg, git, python, curl, wget, proot-distro available
#
# The script creates a distro called "docker-lite", installs Docker in rootless
# mode, pulls the Swarm repo, and runs the same install.sh you would use on a
# normal Linux host.
# =============================================================================
set -euo pipefail

# Helper for logging
log() { echo -e "\e[32m[ANDROID-SETUP]\e[0m $*"; }

# ---------------------------------------------------------------------------
# 1️⃣ Ensure we are inside a proot-distro (Alpine) where Docker can be installed.
# ---------------------------------------------------------------------------
if [ -z "${PROOT_DISTRO_NAME:-}" ]; then
  log "Not inside a proot-distro – creating 'docker-lite' Alpine instance."
  # Install a minimal Alpine distro (includes apk package manager)
  proot-distro install docker-lite || {
    log "Failed to install docker-lite distro"; exit 1;
  }
  # Re‑login to the new distro and re‑run this script inside it
  log "Re‑launching script inside docker-lite..."
  proot-distro login docker-lite -- bash -c "bash /data/data/com.termux/files/home/setup_swarm.sh"
  exit 0
fi

# ---------------------------------------------------------------------------
# 2️⃣ Inside the distro – update and install Docker (rootless) and dependencies.
# ---------------------------------------------------------------------------
log "Inside proot-distro: $PROOT_DISTRO_NAME"
apk update && apk upgrade
apk add curl git python3 py3-pip docker runc

# Enable Docker in rootless mode (no daemon needed for the simple use‑case)
log "Configuring rootless Docker"
# Docker daemon in rootless mode uses the user namespace; we start it manually.
export DOCKER_HOST="unix:///run/user/$(id -u)/docker.sock"
mkdir -p /run/user/$(id -u)

dockerd-rootless.sh &
# Wait for daemon socket
for i in {1..10}; do
  if [ -S "$DOCKER_HOST" ]; then break; fi
  sleep 1
done
if [ ! -S "$DOCKER_HOST" ]; then
  log "Docker daemon failed to start"; exit 1;
fi
log "Docker daemon ready"

# ---------------------------------------------------------------------------
# 3️⃣ Clone the Swarm repository (or extract if tarball already present).
# ---------------------------------------------------------------------------
SWARM_DIR="/root/swarm"
if [ -d "$SWARM_DIR" ]; then
  log "Swarm directory already exists – pulling latest changes"
  cd "$SWARM_DIR" && git pull --rebase
else
  log "Cloning Swarm repository"
  git clone https://github.com/your-org/swarm "$SWARM_DIR"
fi
cd "$SWARM_DIR"

# ---------------------------------------------------------------------------
# 4️⃣ Run the existing Linux installer (install.sh) inside the distro.
# ---------------------------------------------------------------------------
log "Running main install script"
chmod +x install.sh
./install.sh

# ---------------------------------------------------------------------------
# 5️⃣ Final output – print the local URL and QR‑code location.
# ---------------------------------------------------------------------------
HOST_IP="127.0.0.1"
log "Swarm UI available at http://$HOST_IP:8000"
log "A QR‑code image has been placed at /usr/share/pixmaps/swarm_qr.png"
log "You can open the URL in Chrome on this device and add it to the home screen."

exit 0
