#!/bin/bash
# Usage: ./release.sh <dev|preprod> [app|temporal-server] [pr-number]
set -euo pipefail
exec python3 "$(dirname "$0")/.github/scripts/release.py" "$@"
