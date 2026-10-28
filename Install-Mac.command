#!/bin/sh
cd "$(dirname "$0")" || exit 1
if [ -f install.sh ]; then sh ./install.sh; else curl -fsSL https://raw.githubusercontent.com/coden607/swarm/main/install.sh | sh; fi
printf '\nPress Enter to close'; read x
