#!/usr/bin/env python3
"""Visually compare generated catalog images with their source references."""

from __future__ import annotations

import argparse
import json
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PRODUCTS_ROOT = ROOT / "products"
INVENTORY_PATH = ROOT / "generation" / "final_verified_inventory.json"
MODEL = "gemini-3.8-flash"

SCHEMA = {
    "type": "object",
    "properties": {
        "pass": {"type": "boolean"},
        "severity": {"type": "string", "enum": ["none", "minor", "major", "critical"]},
        "identity_match": {"type": "boolean"},
        "product_type_match": {"type": "boolean"},
        "color_and_shape_match": {"type": "boolean"},
        "wrong_or_fictional_brand": {"type": "boolean"},
        "wrong_model_text": {"type": "boolean"},
        "issues": {"type": "array", "items": {"type": "string"}},
        "retry_instruction": {"type": "string"},
    },
    "required": [
        "pass",
        "severity",
        "identity_match",
        "product_type_match",
        "color_and_shape_match",
        "wrong_or_fictional_brand",
        "wrong_model_text",
        "issues",
        "retry_instruction",
    ],
}


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


def mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/png"


def qc_one(product: dict[str, Any], kind: str, client: Any, types: Any) -> dict[str, Any]:
    generated = PRODUCTS_ROOT / product["folder"] / f"product_{kind}.png"
    prompt = f"""Perform strict visual QA for an e-commerce catalog image.

Expected identity: {product['brand']} | {product['model']} | {product['name']} | {product['variant']}
The first image is the generated {kind} candidate. Remaining images are factual store references.

Compare product type, body geometry, major colors, controls, components/accessories, packaging identity and any clearly visible brand/model text. A different product, different model, fictional/substitute brand, major missing component, impossible geometry or wrong primary color is major/critical and must fail. Tiny generic pseudo-text that does not claim another brand/model may be minor. For a box image, the printed brand and model must be correct. Be conservative and factual; store references may be blurry or show the product printed on a box.
"""
    contents: list[Any] = [prompt, types.Part.from_bytes(data=generated.read_bytes(), mime_type=mime_type(generated))]
    for source_text in product["source_images"][:3]:
        source = ROOT / source_text
        contents.append(types.Part.from_bytes(data=source.read_bytes(), mime_type=mime_type(source)))
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=SCHEMA,
        ),
    )
    return json.loads(response.text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=("hero", "box"))
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--recheck-severe", action="store_true")
    args = parser.parse_args()
    load_dotenv()
    from google import genai
    from google.genai import types

    products = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))["products"]
    output = ROOT / "generation" / f"qc_{args.kind}.json"
    state = json.loads(output.read_text(encoding="utf-8")) if output.is_file() else {"results": {}, "errors": {}}
    if args.recheck_severe:
        severe = {
            slug
            for slug, result in state["results"].items()
            if result.get("severity") in {"major", "critical"}
        }
        for slug in severe:
            state["results"].pop(slug, None)
        print(f"Yeniden denetlenecek major/critical: {len(severe)}")
    pending = [
        product
        for product in products
        if product["folder"] not in state["results"]
        and (PRODUCTS_ROOT / product["folder"] / f"product_{args.kind}.png").is_file()
    ]
    client = genai.Client()
    print(f"QC {args.kind}: {len(pending)} bekleyen")

    def attempt(product: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
        last = ""
        for retry in range(3):
            try:
                return product["folder"], qc_one(product, args.kind, client, types), None
            except Exception as exc:
                last = str(exc)
                if retry < 2:
                    time.sleep(2 ** retry)
        return product["folder"], None, last

    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [pool.submit(attempt, product) for product in pending]
        for index, future in enumerate(as_completed(futures), 1):
            slug, result, error = future.result()
            if result is not None:
                state["results"][slug] = result
                state["errors"].pop(slug, None)
                print(f"[{index}/{len(pending)}] {result['severity'].upper()} {slug}", flush=True)
            else:
                state["errors"][slug] = error
                print(f"[{index}/{len(pending)}] HATA {slug}", flush=True)
            output.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kaydedildi: {output.relative_to(ROOT)} | Sonuc: {len(state['results'])} | Hata: {len(state['errors'])}")


if __name__ == "__main__":
    main()
