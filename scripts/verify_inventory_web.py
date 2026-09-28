#!/usr/bin/env python3
"""Verify audited product identities and collect sourced facts with Google Search grounding."""

from __future__ import annotations

import argparse
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "generation" / "verified_inventory.json"
OUTPUT_PATH = ROOT / "generation" / "web_verified_inventory.json"
MODEL = "gemini-3.8-flash"

SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["confirmed", "corrected", "unverified"]},
        "brand": {"type": "string"},
        "model": {"type": "string"},
        "name": {"type": "string"},
        "variant": {"type": "string"},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "features": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "source_url": {"type": "string"},
                },
                "required": ["label", "value", "source_url"],
            },
        },
        "source_urls": {"type": "array", "items": {"type": "string"}},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "verdict",
        "brand",
        "model",
        "name",
        "variant",
        "confidence",
        "features",
        "source_urls",
        "notes",
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


def prompt_for(product: dict[str, Any]) -> str:
    evidence = "\n".join(f"- {value}" for value in product.get("readable_evidence", [])) or "- none"
    issues = "\n".join(f"- {value}" for value in product.get("issues", [])) or "- none"
    return f"""Verify this Turkish retail product using Google Search.

Visual audit candidate:
- Brand: {product['brand']}
- Model: {product['model']}
- Name: {product['name']}
- Variant: {product['variant']}
- Visual confidence: {product['identity_confidence']}

Text actually readable in the source photographs:
{evidence}

Visual-audit issues:
{issues}

Search for the exact product. Prefer the manufacturer, then reputable Turkish retailers or comparison sites. Never substitute a similarly named model. Correct the candidate only when exact model evidence supports the correction. If an exact model cannot be confirmed, use verdict unverified and keep the visually read identity unchanged.

Return at most five concise, sale-relevant features. Every feature must be supported by the exact source_url supplied for that feature; omit anything not verifiable. Do not infer wattage, capacity, accessory count, materials, dimensions, or warranty. source_urls must list only pages actually used.
"""


def grounded_urls(response: Any) -> list[str]:
    urls: list[str] = []
    for candidate in getattr(response, "candidates", []) or []:
        metadata = getattr(candidate, "grounding_metadata", None)
        for chunk in getattr(metadata, "grounding_chunks", []) or []:
            web = getattr(chunk, "web", None)
            uri = getattr(web, "uri", None)
            if isinstance(uri, str) and uri not in urls:
                urls.append(uri)
    return urls


def verify_one(product: dict[str, Any], client: Any, types: Any) -> dict[str, Any]:
    response = client.models.generate_content(
        model=MODEL,
        contents=prompt_for(product),
        config=types.GenerateContentConfig(
            temperature=0.1,
            tools=[types.Tool(google_search=types.GoogleSearch())],
            response_mime_type="application/json",
            response_schema=SCHEMA,
        ),
    )
    result = json.loads(response.text)
    result["grounding_urls"] = grounded_urls(response)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--limit", type=int)
    args = parser.parse_args()
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY eksik")
    from google import genai
    from google.genai import types

    client = genai.Client()
    products = json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))["products"]
    if OUTPUT_PATH.is_file():
        state = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    else:
        state = {"products": {}, "errors": {}}
    pending = [product for product in products if product["folder"] not in state["products"]]
    if args.limit is not None:
        pending = pending[: args.limit]
    print(f"Web dogrulama: {len(pending)} bekleyen")

    def attempt(product: dict[str, Any]) -> tuple[str, dict[str, Any] | None, str | None]:
        last_error = ""
        for retry in range(3):
            try:
                return product["folder"], verify_one(product, client, types), None
            except Exception as exc:
                last_error = str(exc)
                if retry < 2:
                    time.sleep(2 ** retry)
        return product["folder"], None, last_error

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    completed = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(attempt, product): product for product in pending}
        for future in as_completed(futures):
            slug, result, error = future.result()
            completed += 1
            if result is not None:
                state["products"][slug] = result
                state["errors"].pop(slug, None)
                print(f"[{completed}/{len(pending)}] {result['verdict'].upper()} {slug}", flush=True)
            else:
                state["errors"][slug] = error
                print(f"[{completed}/{len(pending)}] HATA {slug}: {error}", flush=True)
            OUTPUT_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kaydedildi: {OUTPUT_PATH.relative_to(ROOT)} | Basarili: {len(state['products'])} | Hata: {len(state['errors'])}")


if __name__ == "__main__":
    main()
