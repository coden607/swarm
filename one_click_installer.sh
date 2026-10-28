#!/usr/bin/env bash
# -------------------------------------------------
# Swarm Detection – Downloadable One‑Click Installer
# -------------------------------------------------
# This script performs a completely automated setup:
#   • Installs Docker, Docker‑Compose, Node, Yarn, qrencode
#   • Builds the UI and Docker image
#   • Creates a systemd service that restarts on failure
#   • Detects the host IP, updates installer.html placeholder, and prints a QR‑code
#   • Writes the reachable URL to .env for the FastAPI app
#
set -euo pipefail

log() { echo -e "\e[32m[+] $*\e[0m"; }
err() { echo -e "\e[31m[-] $*\e[0m" >&2; }

# ---------- 0️⃣ Determine repo root (where this script lives) ----------
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$REPO_ROOT"

# ---------- 1️⃣ Install system dependencies ----------
log "Updating package index…"
sudo apt-get update -y

log "Installing Docker & Docker‑Compose…"
if ! command -v docker >/dev/null; then
  sudo apt-get install -y ca-certificates curl gnupg lsb-release
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
  sudo apt-get update -y
  sudo apt-get install -y docker-ce docker-ce-cli containerd.io
fi

log "Ensuring Docker daemon is running…"
sudo systemctl enable --now docker

log "Installing Docker‑Compose…"
if ! command -v docker-compose >/dev/null; then
  sudo curl -L "https://github.com/docker/compose/releases/download/v2.28.0/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
  sudo chmod +x /usr/local/bin/docker-compose
fi

log "Installing Node.js (LTS) and Yarn…"
if ! command -v node >/dev/null; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi
if ! command -v yarn >/dev/null; then
  sudo npm install -g yarn
fi

log "Installing QR‑code generator…"
if ! command -v qrencode >/dev/null; then
  sudo apt-get install -y qrencode
fi

# ---------- 2️⃣ Build UI ----------
log "Installing UI dependencies…"
pushd ui >/dev/null
yarn install --silent
yarn build   # produces ./dist
popd >/dev/null

# ---------- 3️⃣ Build Docker image & start container ----------
log "Building Docker image…"
docker build -t swarm:latest .

log "Starting container via docker‑compose…"
docker-compose up -d --remove-orphans

# ---------- 4️⃣ Create systemd service ----------
SERVICE_FILE="/etc/systemd/system/swarm.service"
log "Creating systemd service at $SERVICE_FILE"
sudo bash -c "cat > $SERVICE_FILE <<'EOF'
[Unit]
Description=Swarm Detection Service
After=network.target docker.service
Requires=docker.service

[Service]
Restart=always
RestartSec=10
ExecStart=/usr/bin/docker run --rm -p 8000:8000 swarm:latest
ExecStop=/usr/bin/docker stop \$(docker ps -q --filter ancestor=swarm:latest)

[Install]
WantedBy=multi-user.target
EOF"

sudo systemctl daemon-reload
sudo systemctl enable --now swarm.service

# ---------- 5️⃣ Detect host IP and update installer.html ----------
HOST_IP=$(hostname -I | awk '{print $1}')
UI_URL="http://${HOST_IP}:8000"
log "Detected host IP: $HOST_IP"

# Update installer.html placeholder (line containing YOUR_HOST_IP) if present
HTML_FILE="installer.html"
if grep -q "YOUR_HOST_IP" "$HTML_FILE"; then
  sed -i "s|http://YOUR_HOST_IP:8000|${UI_URL}|g" "$HTML_FILE"
  log "Updated $HTML_FILE with reachable URL."
fi

# Write the URL into .env for FastAPI (optional, for JWT config etc.)
ENV_FILE=".env"
if [ ! -f "$ENV_FILE" ]; then
  touch "$ENV_FILE"
fi
# Ensure HOST_URL variable is present/updated
if grep -q "^HOST_URL=" "$ENV_FILE"; then
  sed -i "s|^HOST_URL=.*|HOST_URL=${UI_URL}|" "$ENV_FILE"
else
  echo "HOST_URL=${UI_URL}" >> "$ENV_FILE"
fi
log "Wrote HOST_URL to $ENV_FILE"

# ---------- 6️⃣ QR‑code for mobile access ----------
log "Generating QR‑code for $UI_URL"
qrencode -t ANSIUTF8 "$UI_URL"

log "✅ One‑click installer finished! Open $UI_URL on any device."
log "On iOS, open the URL in Safari → Share → ‘Add to Home Screen’ for a native‑like app."
