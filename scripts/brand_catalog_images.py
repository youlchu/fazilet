#!/usr/bin/env python3
"""Add the approved logo to catalog outputs, never to the original past_* photos."""

from __future__ import annotations

import argparse
from pathlib import Path

from image_branding import brand_file


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="Image files to brand in place")
    args = parser.parse_args()
    for raw_path in args.paths:
        path = raw_path if raw_path.is_absolute() else ROOT / raw_path
        if not path.name.startswith("product_"):
            raise SystemExit(f"Kaynak fotograf degistirilemez: {path}")
        brand_file(path)
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
