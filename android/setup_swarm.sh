#!/bin/sh
# Android (Termux) entry point - delegates to the main installer.
set -eu
pkg upgrade -y -o Dpkg::Options::=--force-confold
pkg install -y curl git
exec sh -c "$(curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh)"
