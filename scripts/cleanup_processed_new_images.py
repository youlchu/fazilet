#!/usr/bin/env python3
"""Move fully preserved new_images folders out of the input queue into a recoverable archive."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "new_images"
PRODUCTS_ROOT = ROOT / "products"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--destination", type=Path, required=True)
    parser.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    destination = args.destination.expanduser().resolve()

    preserved_names = {path.name for path in PRODUCTS_ROOT.glob("*/past_*") if path.is_file()}
    eligible: list[Path] = []
    blocked: list[tuple[Path, list[str]]] = []
    for folder in sorted(path for path in INPUT_ROOT.iterdir() if path.is_dir()):
        references = sorted(path.name for path in folder.glob("past_*") if path.is_file())
        missing = [name for name in references if name not in preserved_names]
        if missing or not references:
            blocked.append((folder, missing or ["past_ referansi yok"]))
        else:
            eligible.append(folder)

    print(f"Tasınabilir: {len(eligible)} | Korunacak: {len(blocked)}")
    for folder, missing in blocked:
        print(f"KORU {folder.name}: {', '.join(missing)}")
    if not args.execute:
        print("Dry-run: hiçbir dosya taşınmadı")
        return

    destination.mkdir(parents=True, exist_ok=True)
    for folder in eligible:
        target = destination / folder.name
        if target.exists():
            raise SystemExit(f"Hedef zaten var; işlem durduruldu: {target}")
    for folder in eligible:
        shutil.move(str(folder), str(destination / folder.name))
    print(f"Taşındı: {len(eligible)} klasör -> {destination}")


if __name__ == "__main__":
    main()
