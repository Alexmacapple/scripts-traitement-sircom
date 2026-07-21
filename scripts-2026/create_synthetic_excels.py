#!/usr/bin/env python3
"""CLI wrapper for Sircom 2026 synthetic Excel fixture generation."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sircom2026.synthetic_excels import main


if __name__ == "__main__":
    raise SystemExit(main())

