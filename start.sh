#!/bin/sh
set -eu
cd "$(dirname "$0")"
PYTHON_BIN="$(command -v python3.12 || command -v python3)"
if ! "$PYTHON_BIN" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  echo "Python 3.11 or newer is required. On macOS, install it with: brew install python@3.12" >&2
  exit 1
fi
if [ -x .venv/bin/python ] && ! .venv/bin/python -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
  rm -rf .venv
fi
if [ ! -x .venv/bin/yt-dlp ]; then
  "$PYTHON_BIN" -m venv .venv
fi
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install --upgrade --pre 'yt-dlp[default]'
if command -v node >/dev/null 2>&1; then
  echo "JavaScript runtime available: $(node --version)"
fi
if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "ffmpeg is required to create MP3 files. Install it with: brew install ffmpeg" >&2
  exit 1
fi
exec .venv/bin/python server.py
