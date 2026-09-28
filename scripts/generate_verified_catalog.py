#!/usr/bin/env python3
"""Generate verified hero, packaging and information images directly under products/."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

from image_branding import add_logo, brand_file


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_ROOT = ROOT / "products"
INVENTORY_PATH = ROOT / "generation" / "verified_inventory.json"
WEB_PATH = ROOT / "generation" / "web_verified_inventory.json"
FINAL_PATH = ROOT / "generation" / "final_verified_inventory.json"
STATE_PATH = ROOT / "generation" / "verified_generation_results.jsonl"
MODEL = "gemini-3.1-flash-image"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"


def load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def ascii_text(value: str) -> str:
    value = value.translate(str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU"))
    return unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", ascii_text(value).casefold()).strip("-")[:120].rstrip("-")


def normalized(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", ascii_text(value).casefold())


def identity_key(product: dict[str, Any]) -> tuple[str, str, str]:
    return (
        normalized(product.get("brand", "")),
        normalized(product.get("model", "")) or normalized(product.get("name", "")),
        normalized(product.get("variant", "")),
    )


def existing_identity_folders() -> dict[tuple[str, str], str]:
    manifest = json.loads((PRODUCTS_ROOT / "product_manifest.json").read_text(encoding="utf-8"))
    result: dict[tuple[str, str], str] = {}
    for product in manifest["products"]:
        if product.get("model"):
            result[(normalized(product.get("brand", "")), normalized(product["model"]))] = product["folder"]
    return result


def prepare() -> list[dict[str, Any]]:
    audited = {p["folder"]: p for p in json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))["products"]}
    verified = json.loads(WEB_PATH.read_text(encoding="utf-8"))["products"]
    existing = existing_identity_folders()
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = {}
    for audit_slug, web in verified.items():
        audit = audited[audit_slug]
        combined = {
            **audit,
            "brand": web["brand"] or audit["brand"],
            "model": web["model"] or audit["model"],
            "name": web["name"] or audit["name"],
            "variant": web["variant"] or audit["variant"],
            "web_verdict": web["verdict"],
            "web_confidence": web["confidence"],
            "features": web["features"] if web["verdict"] != "unverified" else [],
            "source_urls": web["source_urls"],
            "verification_notes": web["notes"],
        }
        groups.setdefault(identity_key(combined), []).append(combined)

    used: set[str] = set()
    final: list[dict[str, Any]] = []
    for products in groups.values():
        best = max(products, key=lambda p: (p["web_verdict"] != "unverified", p["web_confidence"] == "high"))
        existing_folder = existing.get((normalized(best["brand"]), normalized(best["model"])))
        title_identity = best["model"] or best["name"]
        base = existing_folder or slugify(" ".join(x for x in (best["brand"], title_identity, best["variant"]) if x))
        folder = base
        counter = 2
        while folder in used:
            folder = f"{base}-{counter}"
            counter += 1
        used.add(folder)
        sources: list[str] = []
        evidence: list[str] = []
        source_urls: list[str] = []
        features: list[dict[str, str]] = []
        for product in products:
            for key, target in (("source_images", sources), ("readable_evidence", evidence), ("source_urls", source_urls)):
                for value in product.get(key, []):
                    if value not in target:
                        target.append(value)
            for feature in product.get("features", []):
                pair = (feature.get("label", ""), feature.get("value", ""))
                if pair != ("", "") and all((f.get("label"), f.get("value")) != pair for f in features):
                    features.append(feature)
        best = {**best, "folder": folder, "source_images": sources, "readable_evidence": evidence, "source_urls": source_urls, "features": features[:5]}
        final.append(best)

    final.sort(key=lambda p: p["folder"])
    FINAL_PATH.write_text(json.dumps({"schema_version": 1, "products": final}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    for product in final:
        target = PRODUCTS_ROOT / product["folder"]
        target.mkdir(parents=True, exist_ok=True)
        for source_text in product["source_images"]:
            source = ROOT / source_text
            destination = target / source.name
            if not destination.exists():
                shutil.copy2(source, destination)
        (target / "product_info.json").write_text(json.dumps(product, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Hazirlandi: {len(final)} tekil urun -> {FINAL_PATH.relative_to(ROOT)}")
    return final


def load_products() -> list[dict[str, Any]]:
    if not FINAL_PATH.is_file():
        return prepare()
    return json.loads(FINAL_PATH.read_text(encoding="utf-8"))["products"]


def mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/jpeg"


def extract_image(response: Any) -> bytes:
    for candidate in getattr(response, "candidates", []) or []:
        content = getattr(candidate, "content", None)
        for part in getattr(content, "parts", []) or []:
            inline = getattr(part, "inline_data", None)
            if inline is not None and str(getattr(inline, "mime_type", "")).startswith("image/"):
                data = getattr(inline, "data", None)
                if isinstance(data, bytes):
                    return data
                if isinstance(data, str):
                    return base64.b64decode(data)
    raise RuntimeError("API yanitinda gorsel yok")


def identity_text(product: dict[str, Any]) -> str:
    return " | ".join(x for x in (product["brand"], product["model"], product["name"], product["variant"]) if x)


def image_prompt(product: dict[str, Any], kind: str) -> str:
    evidence = "; ".join(product.get("readable_evidence", [])[:8])
    if kind == "hero":
        request = "Create a photorealistic clean studio hero image of the physical product itself, removed from its retail box."
        constraints = "Show one exact product set only, centered on seamless white, full object visible, soft realistic shadow. No packaging, people, hands, price labels, text, watermark or invented accessories."
    else:
        request = "Create a photorealistic clean studio catalog photograph of the exact CLOSED retail packaging shown in the references."
        constraints = "Preserve the real carton geometry, colors, printed product image, brand and model. Do not redesign it or invent claims. Show one closed undamaged box on seamless light gray, full box visible. No loose product, people, price labels or watermark."
    return f"""{request}

Verified identity: {identity_text(product)}
Readable visual evidence: {evidence or 'Use only the supplied reference pixels.'}

Treat every supplied image as a strict factual identity reference. Do not substitute a related model. Preserve exact shape, proportions, color, materials, controls and included components. If a shelf photo contains several products, isolate only the verified identity above.

CRITICAL IDENTITY RULE: The only permitted manufacturer brand is "{product['brand']}" and the only permitted model identity is "{product['model']}". Never draw a fictional logo, substitute brand, altered model code, pseudo-text or gibberish. If a tiny marking cannot be reproduced exactly from the reference, leave that tiny marking blank and visually neutral instead of inventing text. A wrong brand or model makes the result unusable.

{constraints}
Square 1:1 premium e-commerce photography. The Fazilet Ceyiz logo will be added later; do not draw any store logo.
"""


def generate_one(product: dict[str, Any], kind: str, client: Any, types: Any, force: bool) -> tuple[str, str]:
    output = PRODUCTS_ROOT / product["folder"] / f"product_{kind}.png"
    if output.exists() and not force:
        return product["folder"], "existing"
    parts: list[Any] = [types.Part.from_text(text=image_prompt(product, kind))]
    for source_text in product["source_images"][:4]:
        source = ROOT / source_text
        parts.append(types.Part.from_bytes(data=source.read_bytes(), mime_type=mime_type(source)))
    response = client.models.generate_content(
        model=MODEL,
        contents=parts,
        config=types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            image_config=types.ImageConfig(aspect_ratio="1:1", image_size="1K"),
        ),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(extract_image(response))
    brand_file(output)
    with STATE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"product": product["folder"], "kind": kind, "status": "success", "model": MODEL}, ensure_ascii=False) + "\n")
    return product["folder"], "generated"


def generate_images(kind: str, workers: int, force: bool, limit: int | None) -> None:
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY eksik")
    from google import genai
    from google.genai import types

    products = load_products()
    if limit is not None:
        products = products[:limit]
    pending = [p for p in products if force or not (PRODUCTS_ROOT / p["folder"] / f"product_{kind}.png").exists()]
    print(f"{kind}: {len(pending)} bekleyen / {len(products)} hedef")
    client = genai.Client()

    def attempt(product: dict[str, Any]) -> tuple[str, str]:
        last_error = ""
        for retry in range(3):
            try:
                return generate_one(product, kind, client, types, force)
            except Exception as exc:
                last_error = str(exc)
                if retry < 2:
                    time.sleep(2 ** retry)
        with STATE_PATH.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({"product": product["folder"], "kind": kind, "status": "error", "error": last_error}, ensure_ascii=False) + "\n")
        return product["folder"], f"error: {last_error}"

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(attempt, product) for product in pending]
        for index, future in enumerate(as_completed(futures), start=1):
            slug, status = future.result()
            print(f"[{index}/{len(pending)}] {status.upper()} {slug}", flush=True)


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if draw.textbbox((0, 0), candidate, font=face)[2] <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def info_features(product: dict[str, Any]) -> list[str]:
    features = [f"{f['label']}: {f['value']}" for f in product.get("features", []) if f.get("label") and f.get("value")]
    if features:
        return features[:5]
    return [value for value in product.get("readable_evidence", []) if value][:5] or ["Ürün kimliği görsel referanstan doğrulandı"]


def create_info(product: dict[str, Any], force: bool) -> None:
    output = PRODUCTS_ROOT / product["folder"] / "product_info.png"
    if output.exists() and not force:
        return
    hero_path = PRODUCTS_ROOT / product["folder"] / "product_hero.png"
    if not hero_path.is_file():
        return
    canvas = Image.new("RGB", (1254, 1254), (248, 247, 246))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((55, 48, 245, 100), radius=26, fill=(151, 50, 66))
    draw.text((150, 74), "ÜRÜN BİLGİSİ", font=font(22, True), fill="white", anchor="mm")
    draw.text((55, 135), product["brand"].upper(), font=font(30, True), fill=(151, 50, 66))
    title = " ".join(x for x in (product["model"], product["name"]) if x)
    title_lines = wrap(draw, title, font(50, True), 790)
    for i, line in enumerate(title_lines[:2]):
        draw.text((55, 178 + i * 57), line, font=font(50, True), fill=(25, 29, 38))
    draw.line((55, 310, 1199, 310), fill=(220, 190, 195), width=3)
    with Image.open(hero_path) as source:
        hero = ImageOps.contain(source.convert("RGB"), (630, 790), Image.Resampling.LANCZOS)
    hero_panel = Image.new("RGB", (630, 790), "white")
    hero_panel.paste(hero, ((630 - hero.width) // 2, (790 - hero.height) // 2))
    canvas.paste(hero_panel, (55, 350))
    features = info_features(product)
    top, gap = 350, 16
    card_h = (790 - gap * (len(features) - 1)) // len(features)
    body = font(24, True)
    for index, feature in enumerate(features, 1):
        y1 = top + (index - 1) * (card_h + gap)
        y2 = y1 + card_h
        draw.rounded_rectangle((735, y1, 1199, y2), radius=24, fill="white", outline=(228, 205, 209), width=2)
        draw.ellipse((755, (y1 + y2) // 2 - 26, 807, (y1 + y2) // 2 + 26), fill=(151, 50, 66))
        draw.text((781, (y1 + y2) // 2), f"{index:02d}", font=font(18, True), fill="white", anchor="mm")
        lines = wrap(draw, feature, body, 350)[:4]
        y = (y1 + y2) // 2 - len(lines) * 16
        for line in lines:
            draw.text((830, y), line, font=body, fill=(36, 40, 49))
            y += 32
    footer = "KAYNAKLI ÜRÜN ÖZELLİKLERİ" if product.get("features") else "GÖRSEL REFERANSTAN DOĞRULANDI"
    draw.text((1199, 1195), footer, font=font(16, True), fill=(110, 70, 78), anchor="ra")
    add_logo(canvas).save(output, "PNG", optimize=True)


def create_infos(force: bool) -> None:
    products = load_products()
    for index, product in enumerate(products, 1):
        create_info(product, force)
        print(f"[{index}/{len(products)}] {product['folder']}")


def batch_request(
    product: dict[str, Any], types: Any, *, kind: str = "box", extra_instruction: str = ""
) -> dict[str, Any]:
    prompt = image_prompt(product, kind)
    if extra_instruction:
        prompt += f"\n\nMANDATORY QA CORRECTION:\n{extra_instruction}\n"
    parts: list[dict[str, Any]] = [{"text": prompt}]
    for source_text in product["source_images"][:4]:
        source = ROOT / source_text
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime_type(source),
                    "data": base64.b64encode(source.read_bytes()).decode("ascii"),
                }
            }
        )
    return {
        "key": product["folder"],
        "request": {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {"aspectRatio": "1:1", "imageSize": "1K"},
            },
        },
    }


def submit_box_batch() -> None:
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY eksik")
    from google import genai
    from google.genai import types

    products = [
        product
        for product in load_products()
        if not (PRODUCTS_ROOT / product["folder"] / "product_box.png").exists()
    ]
    if not products:
        print("Eksik kutulu gorsel yok")
        return
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    request_file = ROOT / "generation" / f"verified_box_{timestamp}_requests.jsonl"
    with request_file.open("w", encoding="utf-8") as handle:
        for product in products:
            handle.write(json.dumps(batch_request(product, types), ensure_ascii=False) + "\n")
    client = genai.Client()
    uploaded = client.files.upload(
        file=str(request_file),
        config=types.UploadFileConfig(display_name=f"fazilet-verified-box-{timestamp}", mime_type="jsonl"),
    )
    job = client.batches.create(
        model=MODEL,
        src={"file_name": uploaded.name},
        config={"display_name": f"fazilet-verified-box-{timestamp}"},
    )
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": job.name,
        "model": MODEL,
        "request_file": str(request_file.relative_to(ROOT)),
        "uploaded_file": uploaded.name,
        "products": [product["folder"] for product in products],
    }
    path = ROOT / "generation" / "latest_verified_box_batch.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kutulu batch gonderildi: {job.name} | Urun: {len(products)}")


def submit_hero_retry_batch() -> None:
    load_dotenv()
    from google import genai
    from google.genai import types

    products = {product["folder"]: product for product in load_products()}
    qc = json.loads((ROOT / "generation" / "qc_hero.json").read_text(encoding="utf-8"))["results"]
    retry_slugs = [slug for slug, result in qc.items() if result["severity"] in {"major", "critical"}]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    request_file = ROOT / "generation" / f"verified_hero_retry_{timestamp}_requests.jsonl"
    with request_file.open("w", encoding="utf-8") as handle:
        for slug in retry_slugs:
            instruction = qc[slug]["retry_instruction"] or "; ".join(qc[slug]["issues"])
            handle.write(
                json.dumps(
                    batch_request(products[slug], types, kind="hero", extra_instruction=instruction),
                    ensure_ascii=False,
                )
                + "\n"
            )
    client = genai.Client()
    uploaded = client.files.upload(
        file=str(request_file),
        config=types.UploadFileConfig(display_name=f"fazilet-hero-retry-{timestamp}", mime_type="jsonl"),
    )
    job = client.batches.create(
        model=MODEL,
        src={"file_name": uploaded.name},
        config={"display_name": f"fazilet-hero-retry-{timestamp}"},
    )
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": job.name,
        "model": MODEL,
        "request_file": str(request_file.relative_to(ROOT)),
        "products": retry_slugs,
    }
    path = ROOT / "generation" / "latest_verified_hero_retry_batch.json"
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Hero tekrar batch gonderildi: {job.name} | Urun: {len(retry_slugs)}")


def find_image_data(value: Any) -> bytes | None:
    if isinstance(value, dict):
        mime = value.get("mimeType") or value.get("mime_type")
        data = value.get("data")
        if isinstance(mime, str) and mime.startswith("image/") and isinstance(data, str):
            return base64.b64decode(data)
        for nested in value.values():
            found = find_image_data(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_image_data(nested)
            if found is not None:
                return found
    return None


def fetch_box_batch() -> None:
    load_dotenv()
    from google import genai

    record_path = ROOT / "generation" / "latest_verified_box_batch.json"
    if not record_path.is_file():
        raise SystemExit("Kutulu batch kaydi yok")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    client = genai.Client()
    job = client.batches.get(name=record["name"])
    state = getattr(getattr(job, "state", None), "name", str(getattr(job, "state", "UNKNOWN")))
    print(f"Kutulu batch durumu: {state}")
    if state != "JOB_STATE_SUCCEEDED":
        return
    destination = getattr(job, "dest", None)
    result_name = getattr(destination, "file_name", None)
    if not result_name:
        raise SystemExit("Batch sonuc dosyasi yok")
    raw = client.files.download(file=result_name)
    (ROOT / "generation" / "verified_box_batch_results.jsonl").write_bytes(raw)
    saved = 0
    errors = 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        slug = item.get("key")
        image = find_image_data(item)
        if not slug or image is None:
            errors += 1
            continue
        output = PRODUCTS_ROOT / slug / "product_box.png"
        if output.exists():
            continue
        output.write_bytes(image)
        brand_file(output)
        saved += 1
    print(f"Kaydedilen: {saved} | Hatali/eksik: {errors}")


def fetch_hero_retry_batch() -> None:
    load_dotenv()
    from google import genai

    record_path = ROOT / "generation" / "latest_verified_hero_retry_batch.json"
    if not record_path.is_file():
        raise SystemExit("Hero tekrar batch kaydi yok")
    record = json.loads(record_path.read_text(encoding="utf-8"))
    client = genai.Client()
    job = client.batches.get(name=record["name"])
    state = getattr(getattr(job, "state", None), "name", str(getattr(job, "state", "UNKNOWN")))
    print(f"Hero tekrar batch durumu: {state}")
    if state != "JOB_STATE_SUCCEEDED":
        return
    destination = getattr(job, "dest", None)
    result_name = getattr(destination, "file_name", None)
    if not result_name:
        raise SystemExit("Hero tekrar sonuc dosyasi yok")
    raw = client.files.download(file=result_name)
    (ROOT / "generation" / "verified_hero_retry_results.jsonl").write_bytes(raw)
    saved = 0
    errors = 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        slug = item.get("key")
        image = find_image_data(item)
        if not slug or image is None:
            errors += 1
            continue
        output = PRODUCTS_ROOT / slug / "product_hero.png"
        output.write_bytes(image)
        brand_file(output)
        saved += 1
    print(f"Yenilenen hero: {saved} | Hatali/eksik: {errors}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "command",
        choices=(
            "prepare",
            "hero",
            "box",
            "info",
            "box-batch-submit",
            "box-batch-fetch",
            "hero-retry-batch-submit",
            "hero-retry-batch-fetch",
        ),
    )
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    if args.command == "prepare":
        prepare()
    elif args.command in {"hero", "box"}:
        generate_images(args.command, args.workers, args.force, args.limit)
    elif args.command == "info":
        create_infos(args.force)
    elif args.command == "box-batch-submit":
        submit_box_batch()
    elif args.command == "box-batch-fetch":
        fetch_box_batch()
    elif args.command == "hero-retry-batch-submit":
        submit_hero_retry_batch()
    else:
        fetch_hero_retry_batch()


if __name__ == "__main__":
    main()
