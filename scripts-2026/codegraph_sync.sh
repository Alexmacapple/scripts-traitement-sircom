#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"

if ! command -v codegraph >/dev/null 2>&1; then
  echo "codegraph: command not found" >&2
  echo "Install CodeGraph before running this helper." >&2
  exit 127
fi

if [ ! -d "$ROOT/.codegraph" ]; then
  echo "Initializing CodeGraph index for $ROOT"
  codegraph init "$ROOT"
else
  echo "Syncing CodeGraph index for $ROOT"
  codegraph sync "$ROOT"
fi

codegraph status "$ROOT"
