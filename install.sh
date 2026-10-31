#!/bin/sh
# Swarm Detection - one-click installer (Linux, macOS, Android/Termux, WSL).
#   curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh
# Env:  SWARM_HOME (default ~/swarm)  SWARM_PORT (default 8000)  GEMINI_API_KEY
#       SWARM_REMOTE=1  public https link via Cloudflare tunnel (login still required)
#       SWARM_HTTPS=1   local self-signed https (lets phones use their camera over LAN)
#       SWARM_NO_START=1 (install only)   SWARM_NO_SERVICE=1 (no autostart service)   SWARM_NO_ICON=1
# Flag: --uninstall   stop + remove service/launcher/icons (keeps $SWARM_HOME and .env)
set -eu

REPO="coden607/swarm"
BRANCH="main"
SWARM_HOME="${SWARM_HOME:-$HOME/swarm}"
PORT="${SWARM_PORT:-8000}"

log() { printf '\033[32m[+]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[!]\033[0m %s\n' "$*" >&2; }
die() { printf '\033[31m[-]\033[0m %s\n' "$*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"
TERMUX=0
if [ -n "${TERMUX_VERSION:-}" ] || [ -d /data/data/com.termux ]; then TERMUX=1; fi
ISH=0   # iSH (Alpine on iPhone): uses apk-provided opencv/numpy, background start, no service
if { [ -e /proc/ish ] || [ "${SWARM_FORCE_ISH:-0}" = 1 ]; } && command -v apk >/dev/null 2>&1; then ISH=1; fi
KALI=0
if [ -f /etc/os-release ] && grep -q '^ID=kali$' /etc/os-release; then KALI=1; fi
if [ "${SWARM_FORCE_KALI:-0}" = 1 ]; then KALI=1; fi
if [ "$KALI" = 1 ]; then log "Kali Linux: installing into a virtualenv (system Python is externally managed)"; fi
SUDO=""
if [ "$(id -u)" -ne 0 ] && have sudo; then SUDO="sudo"; fi

BIN_DIR="$HOME/.local/bin"
UNIT="$HOME/.config/systemd/user/swarm.service"
PLIST="$HOME/Library/LaunchAgents/com.coden607.swarm.plist"
APPS_DIR="$HOME/.local/share/applications"
MAC_APP="$HOME/Applications/Swarm Detection.app"

desktop_dir() {
  d="$(xdg-user-dir DESKTOP 2>/dev/null || true)"
  [ -n "$d" ] && [ -d "$d" ] && { echo "$d"; return; }
  [ -d "$HOME/Desktop" ] && echo "$HOME/Desktop"
  return 0
}

# ---------------------------------------------------------------- uninstall
if [ "${1:-}" = "--uninstall" ]; then
  log "Stopping and removing service/launcher/icons (keeping $SWARM_HOME)"
  if have systemctl && [ -f "$UNIT" ]; then
    systemctl --user disable --now swarm 2>/dev/null || true
    rm -f "$UNIT"
  fi
  if [ -f "$PLIST" ]; then launchctl unload "$PLIST" 2>/dev/null || true; rm -f "$PLIST"; fi
  if [ -f "$SWARM_HOME/swarm.pid" ]; then kill "$(cat "$SWARM_HOME/swarm.pid")" 2>/dev/null || true; rm -f "$SWARM_HOME/swarm.pid"; fi
  rm -f "$BIN_DIR/swarm" "$BIN_DIR/swarm-open" "$APPS_DIR/swarm.desktop" "$HOME/.shortcuts/Swarm" "$HOME/.termux/boot/swarm"
  D="$(desktop_dir || true)"
  [ -n "$D" ] && rm -f "$D/Swarm Detection.desktop" "$D/Swarm Detection.app"
  rm -rf "$MAC_APP"
  log "Done. Delete $SWARM_HOME yourself to remove code, venv and .env."
  exit 0
fi

# ---------------------------------------------------------------- 1. source
SELF_DIR=""
case "$0" in
  */*) SELF_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd || true)" ;;
esac
if [ -n "$SELF_DIR" ] && [ -f "$SELF_DIR/app/main.py" ]; then
  SWARM_HOME="$SELF_DIR"
  log "Using local checkout: $SWARM_HOME"
elif [ -f "$SWARM_HOME/app/main.py" ]; then
  log "Updating $SWARM_HOME"
  if [ -d "$SWARM_HOME/.git" ] && have git; then git -C "$SWARM_HOME" pull --ff-only || warn "git pull failed; using existing files"; fi
else
  log "Downloading Swarm to $SWARM_HOME"
  mkdir -p "$SWARM_HOME"
  if have git; then
    git clone --depth 1 --branch "$BRANCH" "https://github.com/$REPO" "$SWARM_HOME"
  elif have curl && have tar; then
    curl -fsSL "https://codeload.github.com/$REPO/tar.gz/refs/heads/$BRANCH" | tar -xz --strip-components=1 -C "$SWARM_HOME"
  else
    die "Need git, or curl + tar, to download Swarm."
  fi
fi
cd "$SWARM_HOME"

# ---------------------------------------------------------------- 2. python
find_python() {
  for p in python3 python; do
    if have "$p" && "$p" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 9) else 1)' 2>/dev/null; then
      echo "$p"; return 0
    fi
  done
  return 1
}

termux_upgrade() {
  # Partial upgrades break Termux (e.g. new curl + old openssl); always upgrade everything first.
  log "Termux: upgrading packages (avoids mismatched libraries)"
  pkg upgrade -y -o Dpkg::Options::=--force-confold || warn "pkg upgrade failed; continuing"
}

install_python() {
  log "Installing Python 3 (may ask for your password)"
  if [ "$TERMUX" = 1 ]; then termux_upgrade; pkg install -y python
  elif [ "$ISH" = 1 ]; then apk add python3 py3-pip
  elif have apt-get; then $SUDO apt-get update -y && $SUDO apt-get install -y python3 python3-venv python3-pip
  elif have dnf; then $SUDO dnf install -y python3 python3-pip
  elif have pacman; then $SUDO pacman -Sy --noconfirm python python-pip
  elif have apk; then $SUDO apk add python3 py3-pip
  elif have zypper; then $SUDO zypper install -y python3 python3-pip
  elif have brew; then brew install python
  else die "Install Python 3.9+ from https://www.python.org/downloads/ and re-run."
  fi
}

PY="$(find_python || true)"
if [ -z "$PY" ]; then install_python; PY="$(find_python || true)"; fi
[ -n "$PY" ] || die "Python 3.9+ not found after install attempt."

if ! "$PY" -c 'import venv, ensurepip' 2>/dev/null; then
  if [ "$KALI" = 1 ] && [ -n "$SUDO" ] && ! $SUDO -n true 2>/dev/null; then
    die "Kali needs a virtualenv. Run: sudo apt install python3-venv python3-pip python3-full"
  fi
  if have apt-get; then $SUDO apt-get install -y python3-venv python3-pip; else die "Python venv module missing."; fi
fi

# ---------------------------------------------------------------- 3. venv + deps
REQ="requirements.txt"
VENV_ARGS=""
PIP_EXTRA=""
if [ "$ISH" = 1 ]; then
  log "iSH: installing opencv + numpy via apk (slow emulated CPU: expect low frame rates)"
  apk add py3-opencv py3-numpy py3-pip || warn "apk opencv install failed"
  VENV_ARGS="--system-site-packages"
  grep -vE '^(opencv|numpy|pywebpush|audioop)' requirements.txt > .requirements.termux || true
  REQ=".requirements.termux"
elif [ "$TERMUX" = 1 ]; then
  termux_upgrade
  log "Termux: installing opencv + numpy via pkg"
  pkg install -y x11-repo >/dev/null 2>&1 || true   # opencv-python lives in the x11 repo
  pkg install -y python-numpy || warn "pkg numpy install failed"
  pkg install -y opencv-python || pkg install -y python-opencv-python || warn "pkg opencv install failed (people detection needs it)"
  pkg install -y binutils libxml2 libxslt dbus >/dev/null 2>&1 || true   # dbus: Termux opencv pulls Qt, which needs libdbus-1.so
  VENV_ARGS="--system-site-packages"
  PIP_EXTRA="--prefer-binary --extra-index-url https://termux-user-repository.github.io/pypi/"   # prebuilt Android wheels (pydantic-core etc.)
  # core only; optional extras are installed best-effort below (uvicorn[standard] needs Rust: use plain uvicorn)
  grep -E '^(fastapi|uvicorn|python-dotenv|pyjwt)' requirements.txt | sed 's/\[standard\]//' > .requirements.termux || true
  REQ=".requirements.termux"
fi

if [ ! -x venv/bin/python ]; then
  log "Creating virtualenv"
  # shellcheck disable=SC2086
  "$PY" -m venv $VENV_ARGS venv
fi
log "Installing Python dependencies (first run takes a few minutes)"
venv/bin/python -m pip install -q --upgrade pip
# shellcheck disable=SC2086
if ! venv/bin/python -m pip install -q $PIP_EXTRA -r "$REQ"; then
  if [ "$TERMUX" = 1 ]; then
    warn "No prebuilt wheel for some packages; building from source with Rust (about 10 minutes, keep Termux open)"
    pkg install -y rust binutils
    venv/bin/python -m pip install -q $PIP_EXTRA -r "$REQ" || die "Python packages failed to install. Send the lines above to support."
  else
    die "Python packages failed to install."
  fi
fi
if [ "$TERMUX" = 1 ]; then
  for p in pywebpush onvif-zeep pydub audioop-lts google-generativeai; do
    # shellcheck disable=SC2086
    venv/bin/python -m pip install -q $PIP_EXTRA "$p" >/dev/null 2>&1 || warn "optional package $p not installed (the app still works)"
  done
elif [ "$ISH" = 1 ]; then venv/bin/python -m pip install -q pywebpush >/dev/null 2>&1 || warn "phone push alerts unavailable on this device (pywebpush failed to build)"; fi
venv/bin/python -m pip install -q qrcode >/dev/null 2>&1 || true   # optional, for QR output
if ! CVERR="$(venv/bin/python -c "import cv2" 2>&1)"; then
  if [ "$TERMUX" = 1 ]; then pkg install -y dbus >/dev/null 2>&1 || true; fi
  CVERR="$(venv/bin/python -c "import cv2" 2>&1)" || die "OpenCV does not load: $(printf '%s' "$CVERR" | tail -n 1)"
fi
if ! venv/bin/python -c "import cv2,sys; sys.exit(0 if hasattr(cv2,'HOGDescriptor') else 1)" 2>/dev/null; then
  log "OpenCV $(venv/bin/python -c 'import cv2;print(cv2.__version__)' 2>/dev/null) has no HOG: downloading the neural-net person model (3.6 MB)"
  venv/bin/python -c "from app.detector import ensure_model; ensure_model()" || warn "person model download failed; it will retry when a camera starts"
fi

LAN_IP="$(venv/bin/python -c "import socket; s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM); s.connect(('10.255.255.255', 1)); print(s.getsockname()[0])" 2>/dev/null || echo 127.0.0.1)"

# ---------------------------------------------------------------- 4. optional https / remote tunnel
SCHEME="http"
SSL_FLAGS=""
if [ "${SWARM_HTTPS:-0}" = 1 ]; then
  if have openssl; then
    mkdir -p data
    if [ ! -f data/cert.pem ]; then
      openssl req -x509 -newkey rsa:2048 -nodes -days 3650 -keyout data/key.pem -out data/cert.pem \
        -subj "/CN=swarm" -addext "subjectAltName=DNS:localhost,IP:$LAN_IP,IP:127.0.0.1" >/dev/null 2>&1 || warn "certificate generation failed"
    fi
    if [ -f data/cert.pem ]; then
      SCHEME="https"
      SSL_FLAGS="--ssl-keyfile $SWARM_HOME/data/key.pem --ssl-certfile $SWARM_HOME/data/cert.pem"
    fi
  else
    warn "SWARM_HTTPS=1 needs openssl; continuing with http"
  fi
fi

REMOTE=0
if [ "${SWARM_REMOTE:-0}" = 1 ]; then
  CFARCH=""
  case "$(uname -m)" in
    x86_64|amd64) CFARCH=amd64 ;; aarch64|arm64) CFARCH=arm64 ;; armv7*|armv8l) CFARCH=arm ;;
  esac
  mkdir -p bin
  if [ ! -x bin/cloudflared ]; then
    if [ "$OS" = Linux ] && [ "$TERMUX" = 0 ] && [ -n "$CFARCH" ] && have curl; then
      log "Downloading cloudflared (public https tunnel)"
      curl -fsSL "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-$CFARCH" -o bin/cloudflared && chmod +x bin/cloudflared || warn "cloudflared download failed"
    elif [ "$OS" = Darwin ] && have brew; then
      brew install cloudflared && ln -sf "$(command -v cloudflared)" bin/cloudflared || warn "brew install cloudflared failed"
    elif [ "$TERMUX" = 1 ]; then
      pkg install -y cloudflared && ln -sf "$(command -v cloudflared)" bin/cloudflared || warn "pkg install cloudflared failed"
    else
      warn "Unsupported platform for automatic cloudflared; install it manually and re-run."
    fi
  fi
  if [ -x bin/cloudflared ]; then REMOTE=1; fi
fi

# ---------------------------------------------------------------- 5. config
rand() { venv/bin/python -c 'import secrets; print(secrets.token_urlsafe(16))'; }
NEW_PASS=""
if [ ! -f .env ]; then
  log "Creating .env"
  KEY="${GEMINI_API_KEY:-}"
  if [ -z "$KEY" ]; then
    printf 'Gemini API key (optional, https://aistudio.google.com/apikey - Enter to skip; works offline without it) : ' >&2
    KEY="$(sh -c 'read -r k </dev/tty && printf %s "$k"' 2>/dev/null || true)"
    echo >&2
  fi
  NEW_PASS="$(rand)"
  ( umask 077
    {
      echo "JWT_SECRET=$(rand)$(rand)"
      echo "ADMIN_USER=admin"
      echo "ADMIN_PASS=$NEW_PASS"
      echo "GEMINI_API_KEY=$KEY"
      echo "# Optional alerts:"
      echo "# EMAIL_SMTP_SERVER="
      echo "# EMAIL_SMTP_PORT=587"
      echo "# EMAIL_SMTP_USER="
      echo "# EMAIL_SMTP_PASS="
      echo "# EMAIL_FROM="
      echo "# ONVIF_USER=admin"
      echo "# ONVIF_PASS="
    } > .env )
else
  log "Keeping existing .env"
fi
# remote flag is re-evaluated on every install
grep -v '^SWARM_REMOTE=' .env > .env.tmp || true
[ "$REMOTE" = 1 ] && echo "SWARM_REMOTE=1" >> .env.tmp
( umask 077; cat .env.tmp > .env ); rm -f .env.tmp

# ---------------------------------------------------------------- 6. launcher + open helper
mkdir -p "$BIN_DIR"
cat > "$SWARM_HOME/swarm" <<EOF
#!/bin/sh
cd "$SWARM_HOME" || exit 1
export SWARM_PORT="\${SWARM_PORT:-$PORT}" SWARM_SCHEME="$SCHEME"
exec "$SWARM_HOME/venv/bin/python" -m uvicorn app.main:app --host 0.0.0.0 --port "\$SWARM_PORT" $SSL_FLAGS
EOF
chmod +x "$SWARM_HOME/swarm"
ln -sf "$SWARM_HOME/swarm" "$BIN_DIR/swarm"

{
  printf '#!/bin/sh\nSWARM_HOME="%s"\nURL="%s://localhost:%s"\nPLIST="%s"\n' "$SWARM_HOME" "$SCHEME" "$PORT" "$PLIST"
  cat <<'EOF'
up() { "$SWARM_HOME/venv/bin/python" -c 'import ssl,sys,urllib.request as u;u.urlopen(sys.argv[1]+"/health",timeout=2,context=ssl._create_unverified_context())' "$URL" >/dev/null 2>&1; }
if ! up; then
  if command -v systemctl >/dev/null 2>&1 && systemctl --user cat swarm >/dev/null 2>&1; then systemctl --user start swarm
  elif [ -f "$PLIST" ]; then launchctl load "$PLIST" 2>/dev/null || true
  else (cd "$SWARM_HOME" && nohup "$SWARM_HOME/swarm" >> swarm.log 2>&1 &); fi
  i=0; while [ "$i" -lt 40 ] && ! up; do i=$((i + 1)); sleep 1; done
fi
for b in google-chrome google-chrome-stable chromium chromium-browser microsoft-edge brave-browser; do
  if command -v "$b" >/dev/null 2>&1; then exec "$b" --app="$URL"; fi
done
if [ -d "/Applications/Google Chrome.app" ]; then exec open -na "Google Chrome" --args --app="$URL"; fi
if command -v termux-open-url >/dev/null 2>&1; then exec termux-open-url "$URL"; fi
if command -v xdg-open >/dev/null 2>&1; then exec xdg-open "$URL"; fi
exec open "$URL"
EOF
} > "$SWARM_HOME/swarm-open"
chmod +x "$SWARM_HOME/swarm-open"
ln -sf "$SWARM_HOME/swarm-open" "$BIN_DIR/swarm-open"

# ---------------------------------------------------------------- 7. desktop / home-screen icon
if [ "${SWARM_NO_ICON:-0}" != 1 ]; then
  ICON="$SWARM_HOME/ui/icon-512.png"
  if [ "$TERMUX" = 1 ]; then
    mkdir -p "$HOME/.shortcuts" "$HOME/.termux/boot"
    printf '#!/bin/sh\nexec "%s/swarm-open"\n' "$SWARM_HOME" > "$HOME/.shortcuts/Swarm"
    printf '#!/bin/sh\ntermux-wake-lock\nexec "%s/swarm"\n' "$SWARM_HOME" > "$HOME/.termux/boot/swarm"
    chmod +x "$HOME/.shortcuts/Swarm" "$HOME/.termux/boot/swarm"
    log "Termux: shortcut 'Swarm' created (Termux:Widget). For a launcher icon open the URL in Chrome -> menu -> Install app."
  elif [ "$OS" = "Linux" ]; then
    mkdir -p "$APPS_DIR"
    cat > "$APPS_DIR/swarm.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Swarm Detection
Comment=Camera swarm detection dashboard
Exec=$SWARM_HOME/swarm-open
Icon=$ICON
Terminal=false
Categories=Utility;Network;Security;
EOF
    chmod +x "$APPS_DIR/swarm.desktop"
    D="$(desktop_dir || true)"
    if [ -n "$D" ]; then
      cp "$APPS_DIR/swarm.desktop" "$D/Swarm Detection.desktop"
      chmod +x "$D/Swarm Detection.desktop"
      gio set "$D/Swarm Detection.desktop" metadata::trusted true 2>/dev/null || true
    fi
    if [ "$KALI" = 1 ] && [ -n "$D" ] && [ -f "$SWARM_HOME/Install-Kali.sh" ]; then
      cat > "$D/Install Swarm on Kali.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Install Swarm on Kali
Comment=Install or update Swarm Detection, then open it
Exec=x-terminal-emulator -e sh "$SWARM_HOME/Install-Kali.sh"
Icon=$ICON
Terminal=false
Categories=Utility;Network;Security;
StartupNotify=true
EOF
      chmod +x "$D/Install Swarm on Kali.desktop"
      gio set "$D/Install Swarm on Kali.desktop" metadata::trusted true 2>/dev/null || true
    fi
    have update-desktop-database && update-desktop-database "$APPS_DIR" 2>/dev/null || true
    log "Icon added to your app menu${D:+ and Desktop}"
  elif [ "$OS" = "Darwin" ]; then
    mkdir -p "$MAC_APP/Contents/MacOS" "$MAC_APP/Contents/Resources"
    printf '#!/bin/sh\nexec "%s/swarm-open"\n' "$SWARM_HOME" > "$MAC_APP/Contents/MacOS/SwarmDetection"
    chmod +x "$MAC_APP/Contents/MacOS/SwarmDetection"
    cat > "$MAC_APP/Contents/Info.plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleExecutable</key><string>SwarmDetection</string>
<key>CFBundleIdentifier</key><string>com.coden607.swarm.app</string>
<key>CFBundleName</key><string>Swarm Detection</string>
<key>CFBundleIconFile</key><string>icon</string>
<key>CFBundlePackageType</key><string>APPL</string>
</dict></plist>
EOF
    if have sips && have iconutil; then
      IS="$(mktemp -d)/icon.iconset"; mkdir -p "$IS"
      for s in 16 32 128 256 512; do sips -z $s $s "$ICON" --out "$IS/icon_${s}x${s}.png" >/dev/null 2>&1 || true; done
      iconutil -c icns "$IS" -o "$MAC_APP/Contents/Resources/icon.icns" 2>/dev/null || true
    fi
    [ -d "$HOME/Desktop" ] && ln -sfn "$MAC_APP" "$HOME/Desktop/Swarm Detection.app"
    log "Icon added: ~/Applications/Swarm Detection.app (and Desktop)"
  fi
fi

# ---------------------------------------------------------------- 8. start
if [ "${SWARM_NO_START:-0}" = 1 ]; then
  log "Installed. Start with: $SWARM_HOME/swarm"
  exit 0
fi

start_background() {
  if [ -f swarm.pid ] && kill -0 "$(cat swarm.pid)" 2>/dev/null; then kill "$(cat swarm.pid)" 2>/dev/null || true; sleep 1; fi
  nohup "$SWARM_HOME/swarm" > swarm.log 2>&1 &
  echo $! > swarm.pid
  log "Started in background (log: $SWARM_HOME/swarm.log). Re-run 'swarm' after a reboot."
}

if [ "${SWARM_NO_SERVICE:-0}" = 1 ] || [ "$TERMUX" = 1 ] || [ "$ISH" = 1 ]; then
  start_background
elif [ "$OS" = "Linux" ] && have systemctl && systemctl --user show-environment >/dev/null 2>&1; then
  mkdir -p "$(dirname "$UNIT")"
  cat > "$UNIT" <<EOF
[Unit]
Description=Swarm Detection Service
After=network-online.target

[Service]
ExecStart=$SWARM_HOME/swarm
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
EOF
  systemctl --user daemon-reload
  systemctl --user enable swarm >/dev/null 2>&1 || true
  systemctl --user restart swarm
  $SUDO loginctl enable-linger "$(id -un)" 2>/dev/null || warn "Could not enable lingering; service starts at login, not boot."
  log "systemd user service 'swarm' enabled (restarts on failure)"
elif [ "$OS" = "Darwin" ]; then
  mkdir -p "$(dirname "$PLIST")"
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>Label</key><string>com.coden607.swarm</string>
<key>ProgramArguments</key><array><string>$SWARM_HOME/swarm</string></array>
<key>RunAtLoad</key><true/><key>KeepAlive</key><true/>
<key>StandardOutPath</key><string>$SWARM_HOME/swarm.log</string>
<key>StandardErrorPath</key><string>$SWARM_HOME/swarm.log</string>
</dict></plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  log "launchd agent loaded (restarts on failure)"
else
  start_background
fi

# ---------------------------------------------------------------- 9. verify + report
UP=0
i=0
WAIT=40; { [ "$TERMUX" = 1 ] || [ "$ISH" = 1 ]; } && WAIT=120   # phones start slower
while [ "$i" -lt "$WAIT" ]; do
  if venv/bin/python -c "import ssl,urllib.request as u; u.urlopen('$SCHEME://127.0.0.1:$PORT/health', timeout=2, context=ssl._create_unverified_context())" 2>/dev/null; then UP=1; break; fi
  i=$((i + 1)); sleep 1
done

URL="$SCHEME://$LAN_IP:$PORT"
if [ "$UP" = 1 ]; then
  log "Swarm is running: $URL   (this device: $SCHEME://localhost:$PORT)"
  PASS_NOW="$(grep '^ADMIN_PASS=' .env 2>/dev/null | cut -d= -f2-)"
  PAIR="$URL"; [ -n "$PASS_NOW" ] && PAIR="$URL/#key=$PASS_NOW"
  echo; echo "  Scan with your phone camera: opens Swarm already signed in (same Wi-Fi)"
  venv/bin/python -c "import qrcode,sys; q=qrcode.QRCode(border=1); q.add_data(sys.argv[1]); q.print_ascii(invert=True)" "$PAIR" 2>/dev/null || true
  [ "$PAIR" != "$URL" ] && echo "  Phone link: $PAIR"
  if [ -n "$NEW_PASS" ]; then
    echo
    echo "  Login:    admin"
    echo "  Password: $NEW_PASS      (saved in $SWARM_HOME/.env)"
  fi
  if [ "$REMOTE" = 1 ]; then
    echo
    echo "  Remote link (anywhere, login required) appears in the app within ~20 s, or:  grep trycloudflare $SWARM_HOME/data/tunnel.log"
  fi
  echo
  echo "  Phones: open the URL, then Share / menu -> Add to Home Screen (or 'Install app')."
  echo "  Works offline on your local network; the app also caches the last alerts if the server is unreachable."
  echo "  Make sure port $PORT is allowed through your firewall."
  if [ "${SWARM_NO_OPEN:-0}" != 1 ] && { [ "$OS" = Darwin ] || [ "$TERMUX" = 1 ] || [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; }; then
    log "Opening the dashboard..."
    nohup "$SWARM_HOME/swarm-open" >/dev/null 2>&1 &
  fi
else
  die "Installed but the server did not answer on port $PORT. Check $SWARM_HOME/swarm.log (or: journalctl --user -u swarm)."
fi
