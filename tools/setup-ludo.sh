#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
command -v node
command -v npm
command -v ffmpeg
node -e 'if(Number(process.versions.node.split(".")[0])<24)throw Error("Node 24+ diperlukan")'
export NODE_USE_ENV_PROXY=1
npm --prefix "$repo/desktop" ci --cache "$repo/.cache/npm"
(cd "$repo/desktop" && node node_modules/electron/install.js)
npm --prefix "$repo/desktop" test
