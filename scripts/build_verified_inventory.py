#!/usr/bin/env python3
"""Build a canonical, deduplicated product inventory from the visual identity audit."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = ROOT / "generation" / "identity_audit_sync.json"
OUTPUT_PATH = ROOT / "generation" / "verified_inventory.json"
INPUT_ROOT = ROOT / "new_images"


def ascii_text(value: str) -> str:
    replacements = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")
    value = value.translate(replacements)
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", ascii_text(value).casefold())


def slugify(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", "-", ascii_text(value).casefold()).strip("-")
    return value[:120].rstrip("-")


def product_key(product: dict[str, Any]) -> tuple[str, str, str]:
    identity = normalized(product.get("model", "")) or normalized(product.get("name", ""))
    return normalized(product.get("brand", "")), identity, normalized(product.get("variant", ""))


def selected_products(audit: dict[str, Any]) -> list[dict[str, Any]]:
    products = audit.get("products", [])
    primary = [
        product
        for product in products
        if product.get("is_primary_subject") and product.get("confidence") != "low"
    ]
    if primary:
        return primary
    # Shelf/group photos intentionally have no single primary product. Keep only readable identities.
    return [product for product in products if product.get("confidence") in {"high", "medium"}]


def main() -> None:
    state = json.loads(AUDIT_PATH.read_text(encoding="utf-8"))
    audits = state["audits"]
    groups: dict[tuple[str, str, str], list[tuple[str, dict[str, Any], dict[str, Any]]]] = defaultdict(list)
    for source_folder, audit in sorted(audits.items()):
        for product in selected_products(audit):
            groups[product_key(product)].append((source_folder, product, audit))

    used_slugs: set[str] = set()
    inventory: list[dict[str, Any]] = []
    for _, occurrences in sorted(groups.items(), key=lambda item: item[0]):
        best_folder, best, _ = max(
            occurrences,
            key=lambda item: (
                item[1].get("confidence") == "high",
                bool(item[1].get("model")),
                len(item[1].get("readable_evidence", [])),
            ),
        )
        title_parts = [best.get("brand", ""), best.get("model", "")]
        if best.get("variant"):
            title_parts.append(best["variant"])
        if not best.get("model"):
            title_parts.append(best.get("name", ""))
        base_slug = slugify(" ".join(part for part in title_parts if part)) or slugify(best_folder)
        slug = base_slug
        suffix = 2
        while slug in used_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        used_slugs.add(slug)

        sources: list[str] = []
        evidence: list[str] = []
        issues: list[str] = []
        source_folders: list[str] = []
        confidence = "high"
        for source_folder, product, audit in occurrences:
            source_folders.append(source_folder)
            if product.get("confidence") != "high":
                confidence = "medium"
            for filename in product.get("reference_files", []):
                path = INPUT_ROOT / source_folder / filename
                if path.is_file():
                    relative = str(path.relative_to(ROOT))
                    if relative not in sources:
                        sources.append(relative)
            for value in product.get("readable_evidence", []):
                if value not in evidence:
                    evidence.append(value)
            for value in audit.get("issues", []):
                if value not in issues:
                    issues.append(value)

        inventory.append(
            {
                "folder": slug,
                "brand": best.get("brand", ""),
                "model": best.get("model", ""),
                "name": best.get("name", ""),
                "variant": best.get("variant", ""),
                "identity_confidence": confidence,
                "source_folders": sorted(set(source_folders)),
                "source_images": sources,
                "readable_evidence": evidence,
                "issues": issues,
                "status": "identity-audited",
            }
        )

    OUTPUT_PATH.write_text(
        json.dumps({"schema_version": 1, "products": inventory}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Kaydedildi: {OUTPUT_PATH.relative_to(ROOT)}")
    print(f"Kaynak klasor: {len(audits)} | Tekil urun: {len(inventory)}")
    print(f"Yuksek guven: {sum(p['identity_confidence'] == 'high' for p in inventory)}")
    print(f"Orta guven: {sum(p['identity_confidence'] == 'medium' for p in inventory)}")
    print(f"Referanssiz: {sum(not p['source_images'] for p in inventory)}")


if __name__ == "__main__":
    main()
