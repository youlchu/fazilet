#!/usr/bin/env python3
"""Audit product identities in new_images before any catalog generation."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_ROOT = ROOT / "new_images"
GENERATION_ROOT = ROOT / "generation"
MODEL = "gemini-3.8-flash"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}

PRODUCT_SCHEMA = {
    "type": "object",
    "properties": {
        "suggested_folder": {"type": "string"},
        "matches_current_folder": {"type": "boolean"},
        "products": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "brand": {"type": "string"},
                    "model": {"type": "string"},
                    "name": {"type": "string"},
                    "variant": {"type": "string"},
                    "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
                    "is_primary_subject": {"type": "boolean"},
                    "readable_evidence": {"type": "array", "items": {"type": "string"}},
                    "reference_files": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "brand",
                    "model",
                    "name",
                    "variant",
                    "confidence",
                    "is_primary_subject",
                    "readable_evidence",
                    "reference_files",
                ],
            },
        },
        "issues": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["suggested_folder", "matches_current_folder", "products", "issues"],
}

PROMPT = """You are auditing retail product photographs before e-commerce image generation.

The current folder name is only a fallible prior: {slug}

Inspect every supplied image closely. Identify each DISTINCT sellable product for which the brand and model or product-line identity are actually readable. Do not trust the folder name when it conflicts with the pixels. Deduplicate the same product shown in several photos. A shelf photo may contain several different products: list them separately. A deliberate retail bundle may stay one product only when the packaging or photo clearly presents it as one bundle.

Never invent a model number, wattage, capacity, feature, or variant. Preserve punctuation and digits exactly as printed. Put uncertain or partially hidden readings at medium/low confidence and explain the ambiguity in issues. Set is_primary_subject true only when the product is deliberately centered or clearly the intended subject, not merely a background box. reference_files must contain only the supplied file labels that support that product. suggested_folder must be a lowercase ASCII hyphenated folder name for the primary product; leave it empty when there is no single primary product.
"""


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


def import_sdk() -> tuple[Any, Any]:
    from google import genai
    from google.genai import types

    return genai, types


def image_paths(folder: Path) -> list[Path]:
    return sorted(
        path
        for path in folder.glob("past_*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
    )


def mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/jpeg"


def request_for(folder: Path) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"text": PROMPT.format(slug=folder.name)}]
    for path in image_paths(folder):
        parts.append({"text": f"REFERENCE FILE: {path.name}"})
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime_type(path),
                    "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            }
        )
    return {
        "key": folder.name,
        "request": {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "temperature": 0.1,
                "responseMimeType": "application/json",
                "responseSchema": PRODUCT_SCHEMA,
            },
        },
    }


def submit() -> None:
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY eksik")
    genai, types = import_sdk()
    client = genai.Client()
    folders = sorted(path for path in INPUT_ROOT.iterdir() if path.is_dir() and image_paths(path))
    GENERATION_ROOT.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    request_file = GENERATION_ROOT / f"identity_audit_{timestamp}_requests.jsonl"
    with request_file.open("w", encoding="utf-8") as handle:
        for folder in folders:
            handle.write(json.dumps(request_for(folder), ensure_ascii=False) + "\n")

    uploaded = client.files.upload(
        file=str(request_file),
        config=types.UploadFileConfig(
            display_name=f"fazilet-identity-audit-{timestamp}", mime_type="jsonl"
        ),
    )
    job = client.batches.create(
        model=MODEL,
        src={"file_name": uploaded.name},
        config={"display_name": f"fazilet-identity-audit-{timestamp}"},
    )
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": job.name,
        "model": MODEL,
        "request_file": str(request_file.relative_to(ROOT)),
        "uploaded_file": uploaded.name,
        "folders": len(folders),
        "images": sum(len(image_paths(folder)) for folder in folders),
    }
    job_file = GENERATION_ROOT / "latest_identity_audit.json"
    job_file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kimlik denetimi gonderildi: {job.name}")
    print(f"Klasor: {record['folders']} | Referans: {record['images']} | Model: {MODEL}")


def find_text(value: Any) -> str | None:
    if isinstance(value, dict):
        text = value.get("text")
        if isinstance(text, str) and text.lstrip().startswith(("{", "[")):
            return text
        for nested in value.values():
            found = find_text(nested)
            if found is not None:
                return found
    elif isinstance(value, list):
        for nested in value:
            found = find_text(nested)
            if found is not None:
                return found
    return None


def fetch() -> None:
    load_dotenv()
    genai, _ = import_sdk()
    client = genai.Client()
    job_file = GENERATION_ROOT / "latest_identity_audit.json"
    if not job_file.is_file():
        raise SystemExit("Kimlik denetimi kaydi yok; once submit calistirin")
    record = json.loads(job_file.read_text(encoding="utf-8"))
    job = client.batches.get(name=record["name"])
    state = getattr(getattr(job, "state", None), "name", str(getattr(job, "state", "UNKNOWN")))
    print(f"Batch durumu: {state}")
    stats = getattr(job, "batch_stats", None)
    if stats is not None:
        total = getattr(stats, "request_count", None)
        successful = getattr(stats, "successful_request_count", None)
        failed = getattr(stats, "failed_request_count", None)
        pending = getattr(stats, "pending_request_count", None)
        print(f"Istek: {total} | Basarili: {successful} | Hatali: {failed} | Bekleyen: {pending}")
    if state != "JOB_STATE_SUCCEEDED":
        return
    destination = getattr(job, "dest", None)
    result_name = getattr(destination, "file_name", None)
    if not result_name:
        raise SystemExit("Tamamlanan denetimin sonuc dosyasi bulunamadi")
    raw = client.files.download(file=result_name)
    raw_path = GENERATION_ROOT / "identity_audit_results.jsonl"
    raw_path.write_bytes(raw)
    audits: dict[str, Any] = {}
    errors: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        key = item.get("key", "")
        text = find_text(item)
        if not key or text is None:
            errors[key or f"unknown-{len(errors) + 1}"] = "JSON yaniti bulunamadi"
            continue
        try:
            audits[key] = json.loads(text)
        except json.JSONDecodeError as exc:
            errors[key] = str(exc)
    output = GENERATION_ROOT / "identity_audit.json"
    output.write_text(
        json.dumps({"audits": audits, "errors": errors}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Kaydedildi: {output.relative_to(ROOT)} | Basarili: {len(audits)} | Hata: {len(errors)}")


def run_one(folder: Path, client: Any, types: Any) -> dict[str, Any]:
    contents: list[Any] = [PROMPT.format(slug=folder.name)]
    for path in image_paths(folder):
        contents.append(f"REFERENCE FILE: {path.name}")
        contents.append(types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type(path)))
    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(
            temperature=0.1,
            response_mime_type="application/json",
            response_schema=PRODUCT_SCHEMA,
        ),
    )
    return json.loads(response.text)


def run_sync(skip_first: int, workers: int) -> None:
    load_dotenv()
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit("GEMINI_API_KEY eksik")
    genai, types = import_sdk()
    client = genai.Client()
    folders = sorted(path for path in INPUT_ROOT.iterdir() if path.is_dir() and image_paths(path))
    folders = folders[skip_first:]
    output = GENERATION_ROOT / "identity_audit_sync.json"
    if output.is_file():
        state = json.loads(output.read_text(encoding="utf-8"))
    else:
        state = {"audits": {}, "errors": {}}
    pending = [folder for folder in folders if folder.name not in state["audits"]]
    print(f"Senkron denetim: {len(pending)} bekleyen / {len(folders)} hedef")

    def attempt(folder: Path) -> tuple[str, dict[str, Any] | None, str | None]:
        last_error = ""
        for retry in range(3):
            try:
                return folder.name, run_one(folder, client, types), None
            except Exception as exc:  # Individual failures must not discard the full audit.
                last_error = str(exc)
                if retry < 2:
                    time.sleep(2 ** retry)
        return folder.name, None, last_error

    GENERATION_ROOT.mkdir(parents=True, exist_ok=True)
    completed = 0
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(attempt, folder): folder for folder in pending}
        for future in as_completed(futures):
            slug, audit, error = future.result()
            completed += 1
            if audit is not None:
                state["audits"][slug] = audit
                state["errors"].pop(slug, None)
                count = len(audit.get("products", []))
                print(f"[{completed}/{len(pending)}] OK {slug}: {count} urun", flush=True)
            else:
                state["errors"][slug] = error
                print(f"[{completed}/{len(pending)}] HATA {slug}: {error}", flush=True)
            output.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Kaydedildi: {output.relative_to(ROOT)} | Basarili: {len(state['audits'])} | Hata: {len(state['errors'])}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("submit", "fetch", "run"))
    parser.add_argument("--skip-first", type=int, default=5)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if args.command == "submit":
        submit()
    elif args.command == "fetch":
        fetch()
    else:
        run_sync(args.skip_first, args.workers)


if __name__ == "__main__":
    main()
