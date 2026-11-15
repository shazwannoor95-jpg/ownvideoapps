#!/usr/bin/env bash
set -euo pipefail
repo="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
node -e 'if(Number(process.versions.node.split(".")[0])<24)throw Error("Node 24+ diperlukan")'
npm --prefix "$repo/browser-control" ci --cache "$repo/.cache/npm"
"$repo/browser-control/node_modules/.bin/chrome-devtools-mcp" --version
