#!/bin/sh
# Android (Termux) entry point - delegates to the main installer.
set -eu
pkg update -y && pkg install -y curl git
exec sh -c "$(curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh)"
