#!/usr/bin/env python3
"""Build a complete category index from products/product_manifest.json."""

from __future__ import annotations

import json
import re
import unicodedata
from collections import OrderedDict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "products" / "product_manifest.json"
OUTPUT_PATH = ROOT / "products" / "product_categories.json"

CATEGORIES = OrderedDict(
    (
        ("supurgeler", "Süpürgeler"),
        ("buharli_temizlik_ve_yikama", "Buharlı Temizlik ve Yıkama Makineleri"),
        ("utuler", "Ütüler"),
        ("cay_kahve_ve_su_isiticilar", "Çay, Kahve ve Su Isıtıcıları"),
        ("firin_airfryer_ve_izgaralar", "Fırın, Airfryer ve Izgaralar"),
        ("blender_ve_mutfak_hazirlik", "Blender ve Mutfak Hazırlık"),
        ("tencere_ve_sofra", "Tencere, Çaydanlık ve Sofra"),
        ("iklimlendirme_ve_isitma", "İklimlendirme ve Isıtma"),
        ("sac_sakal_bakimi", "Saç ve Sakal Bakımı"),
        ("epilasyon_ve_masaj", "Epilasyon ve Masaj"),
        ("ses_sistemleri", "Ses Sistemleri"),
        ("su_sebilleri", "Su Sebilleri"),
        ("ev_tekstili", "Ev Tekstili"),
        ("urun_aksesuarlari", "Ürün Aksesuarları"),
    )
)

MANUAL = {
    "cvs-dn-5481": "utuler",
    "cvs-dn-7518-9in1-erkek-bakim-seti": "sac_sakal_bakimi",
    "fakir-be6020-3200-w": "utuler",
    "fakir-bl-3048": "supurgeler",
    "falez-serafit": "tencere_ve_sofra",
    "falez-serafit-24-cm": "tencere_ve_sofra",
    "fantom-dc-3000": "supurgeler",
    "fantom-p-1250": "supurgeler",
    "goldmaster-gm-7171": "sac_sakal_bakimi",
    "goldmaster-gm-8184": "sac_sakal_bakimi",
    "korkmaz-a1817-rosagold": "blender_ve_mutfak_hazirlik",
    "korkmaz-elektro-set": "blender_ve_mutfak_hazirlik",
    "leader-fm304-s": "urun_aksesuarlari",
    "leader-lt-56": "sac_sakal_bakimi",
    "mehtap-orkide-plus": "tencere_ve_sofra",
    "philips-azur-7500-series-3200-w-dst7510": "utuler",
    "pirantech-ks-103": "sac_sakal_bakimi",
    "powertec-tr-3500": "sac_sakal_bakimi",
    "simfer-sk-6704-siyah": "firin_airfryer_ve_izgaralar",
    "tefal-fv8042": "utuler",
    "tefal-fv8042-2900w-50g-min-270g-boost": "utuler",
    "tefal-fv9e50e0": "utuler",
    "tefal-ultimate-pure": "utuler",
    "tefal-ultragliss-anti-calc-plus-2800-w-260-g": "utuler",
}


def normalized(value: str) -> str:
    value = value.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def contains(text: str, *terms: str) -> bool:
    return any(normalized(term) in text for term in terms)


def classify(product: dict[str, object]) -> str:
    folder = str(product["folder"])
    if folder in MANUAL:
        return MANUAL[folder]

    text = normalized(
        " ".join(
            str(product.get(field) or "")
            for field in ("folder", "brand", "model", "name", "variant")
        )
    )

    if contains(text, "su sebili", "water dispenser"):
        return "su_sebilleri"
    if contains(text, "nevresim", "pike", "battaniye"):
        return "ev_tekstili"
    if contains(text, "hoparlor", "ses sistemi", "speaker", "ev sinema"):
        return "ses_sistemleri"
    if contains(text, "utu", "steam iron", "iron"):
        return "utuler"
    if contains(text, "buharli temiz", "steam cleaner", "spot cleaner", "hali yikama", "buharli mop"):
        return "buharli_temizlik_ve_yikama"
    if contains(text, "supurge", "vacuum"):
        return "supurgeler"
    if contains(text, "epilasyon", "epilator", "ipl", "masaj"):
        return "epilasyon_ve_masaj"
    if contains(
        text,
        "sac kurutma",
        "sac sekillendir",
        "sac duzlestir",
        "sac kesme",
        "sakal",
        "tiras",
        "trimmer",
        "groom",
        "straightener",
        "hair styling",
        "haar styling",
        "multihaarschneideset",
        "windstraight",
        "windshape",
    ):
        return "sac_sakal_bakimi"
    if contains(text, "vantilator", "fan", "air cooler", "hava sogutucu", "isitici", "climator"):
        return "iklimlendirme_ve_isitma"
    if contains(text, "firin", "oven", "air fryer", "airfryer", "fritoz", "grill", "tost"):
        return "firin_airfryer_ve_izgaralar"
    if contains(text, "blender", "mutfak robotu", "el blenderi", "electro set", "elektro set"):
        return "blender_ve_mutfak_hazirlik"
    if contains(
        text,
        "tencere",
        "cookware",
        "ceyiz seti",
        "cezve",
        "caydanlik",
        "yemek takimi",
        "guvec set",
    ):
        return "tencere_ve_sofra"
    if contains(text, "cay makinesi", "tea maker", "tea machine", "kahve", "espresso", "kettle", "su isitici"):
        return "cay_kahve_ve_su_isiticilar"

    raise ValueError(f"Kategori belirlenemedi: {folder}")


def main() -> None:
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    products = manifest["products"]
    grouped = {category_id: [] for category_id in CATEGORIES}
    seen: set[str] = set()

    for product in products:
        folder = str(product["folder"])
        if folder in seen:
            raise ValueError(f"Manifestte yinelenen ürün: {folder}")
        seen.add(folder)
        grouped[classify(product)].append(folder)

    categories = []
    for category_id, name in CATEGORIES.items():
        folders = sorted(grouped[category_id])
        categories.append(
            {
                "id": category_id,
                "name": name,
                "product_count": len(folders),
                "products": folders,
            }
        )

    indexed = sum(category["product_count"] for category in categories)
    if indexed != len(products):
        raise ValueError(f"Kategori sayımı uyuşmuyor: {indexed} / {len(products)}")

    output = {
        "schema_version": 1,
        "source": "product_manifest.json",
        "product_count": len(products),
        "category_count": len(categories),
        "categories": categories,
    }
    OUTPUT_PATH.write_text(
        json.dumps(output, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{len(products)} ürün, {len(categories)} kategori -> {OUTPUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
