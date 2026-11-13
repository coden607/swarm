#!/usr/bin/env sh
# Local opt-in GitHub MCP (STDIO). Does not configure a client automatically.
# Token must already be exported in the invoking shell and is never echoed.
set -eu
if [ -z "${GITHUB_PERSONAL_ACCESS_TOKEN:-}" ]; then
  printf '%s\n' 'Missing GITHUB_PERSONAL_ACCESS_TOKEN in local environment' >&2
  exit 2
fi
if ! command -v docker >/dev/null 2>&1; then
  printf '%s\n' 'Docker is required for this optional local MCP launcher' >&2
  exit 3
fi
exec docker run -i --rm \
  -e GITHUB_PERSONAL_ACCESS_TOKEN \
  -e GITHUB_READ_ONLY=1 \
  -e GITHUB_TOOLSETS=repos,pull_requests,actions \
  ghcr.io/github/github-mcp-server
