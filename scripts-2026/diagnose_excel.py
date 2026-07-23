#!/usr/bin/env python3
"""CLI wrapper for Sircom 2026 Excel structure diagnostics."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from sircom2026.excel_diagnostic import main

    raise SystemExit(main())
