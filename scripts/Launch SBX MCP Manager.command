#!/bin/zsh
set -e
cd "${0:A:h}/.."
export PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:$HOME/.local/bin:$PATH"
if command -v python3 >/dev/null 2>&1; then
  PY="$(command -v python3)"
else
  echo 'Python 3 is required (brew install python).'
  read '?Press Enter to close...'
  exit 1
fi
if ! command -v sbx >/dev/null 2>&1; then
  echo 'Warning: sbx not found. Install Docker Desktop and check your PATH.'
fi
echo 'Starting SBX MCP Manager. Keep Terminal open; press Ctrl+C to stop.'
exec "$PY" "$PWD/src/server.py"
