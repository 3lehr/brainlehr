#!/usr/bin/env python3
"""Repository shortcut for `brainlehr-boundary`."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kern"))
from project_boundary_cli import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
