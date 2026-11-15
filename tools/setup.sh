#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
command -v python3
command -v ffmpeg
command -v ffprobe
python3 -m venv "$repo/.venv"
"$repo/.venv/bin/python" -m pip install -r "$repo/requirements-lock.txt"
"$repo/.venv/bin/python" -m pip check
