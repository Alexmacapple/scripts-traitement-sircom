#!/usr/bin/env python3
"""CLI wrapper for one Sircom 2026 local worker acquisition."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sircom2026.worker_runner import main


if __name__ == "__main__":
    raise SystemExit(main())
