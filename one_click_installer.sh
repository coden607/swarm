#!/bin/sh
# Kept for backwards compatibility - use install.sh.
exec sh "$(cd "$(dirname "$0")" && pwd)/install.sh" "$@"
