#!/usr/bin/env python3
"""Generate reviewable product-image candidates with the Gemini image API.

The script never modifies source images and never overwrites an existing output
unless --force is explicitly supplied. It supports synchronous pilot runs and
lower-cost asynchronous Batch API jobs.
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT = ROOT / "generation" / "prompt.txt"
SUPPORTED_SUFFIXES = {".jpg", ".jpeg", ".png", ".webp"}


def load_dotenv(path: Path) -> None:
    """Load simple KEY=VALUE entries without adding another dependency."""
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_path(name: str, fallback: str) -> Path:
    raw = os.getenv(name, fallback)
    path = Path(raw).expanduser()
    return path if path.is_absolute() else ROOT / path


@dataclass(frozen=True)
class ProductJob:
    slug: str
    source_images: tuple[Path, ...]
    output_path: Path


def discover_jobs(input_dir: Path, output_dir: Path) -> list[ProductJob]:
    jobs: list[ProductJob] = []
    if not input_dir.is_dir():
        raise SystemExit(f"Girdi klasoru bulunamadi: {input_dir}")

    for product_dir in sorted(path for path in input_dir.iterdir() if path.is_dir()):
        images = tuple(
            sorted(
                path
                for path in product_dir.iterdir()
                if path.is_file() and path.suffix.lower() in SUPPORTED_SUFFIXES
            )
        )
        if images:
            jobs.append(
                ProductJob(
                    slug=product_dir.name,
                    source_images=images,
                    output_path=output_dir / product_dir.name / "product_hero.png",
                )
            )
    return jobs


def select_jobs(
    jobs: list[ProductJob],
    *,
    only: str | None,
    limit: int | None,
    force: bool,
) -> list[ProductJob]:
    if only:
        jobs = [job for job in jobs if job.slug == only]
        if not jobs:
            raise SystemExit(f"Urun klasoru bulunamadi: {only}")
    if not force:
        jobs = [job for job in jobs if not job.output_path.exists()]
    if limit is not None:
        jobs = jobs[:limit]
    return jobs


def product_title(slug: str) -> str:
    return slug.replace("-", " ")


def prompt_for(job: ProductJob, template: str) -> str:
    return template.replace("{product_name}", product_title(job.slug))


def mime_type(path: Path) -> str:
    guessed, _ = mimetypes.guess_type(path.name)
    return guessed or "image/jpeg"


def import_sdk() -> tuple[Any, Any]:
    try:
        from google import genai
        from google.genai import types
    except ImportError as exc:
        raise SystemExit(
            "Google SDK kurulu degil. Calistirin: python3 -m pip install -r requirements.txt"
        ) from exc
    return genai, types


def require_key() -> None:
    if not os.getenv("GEMINI_API_KEY"):
        raise SystemExit(
            "GEMINI_API_KEY eksik. .env.example dosyasini .env olarak kopyalayip anahtari ekleyin."
        )


def image_parts(job: ProductJob, types: Any, max_references: int) -> list[Any]:
    selected = job.source_images[:max_references]
    return [
        types.Part.from_bytes(data=path.read_bytes(), mime_type=mime_type(path))
        for path in selected
    ]


def extract_sync_image(response: Any) -> bytes:
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
    raise RuntimeError("API yanitinda gorsel bulunamadi")


def write_event(state_file: Path, event: dict[str, Any]) -> None:
    state_file.parent.mkdir(parents=True, exist_ok=True)
    with state_file.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def run_sync(args: argparse.Namespace, jobs: list[ProductJob], template: str) -> None:
    require_key()
    genai, types = import_sdk()
    client = genai.Client()
    state_file = ROOT / "generation" / "results.jsonl"

    for index, job in enumerate(jobs, start=1):
        print(f"[{index}/{len(jobs)}] {job.slug}", flush=True)
        started = datetime.now(timezone.utc).isoformat()
        try:
            contents = [
                types.Part.from_text(text=prompt_for(job, template)),
                *image_parts(job, types, args.max_references),
            ]
            response = client.models.generate_content(
                model=args.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_modalities=["IMAGE"],
                    image_config=types.ImageConfig(
                        aspect_ratio=args.aspect_ratio,
                        image_size=args.image_size,
                    ),
                ),
            )
            image = extract_sync_image(response)
            job.output_path.parent.mkdir(parents=True, exist_ok=True)
            job.output_path.write_bytes(image)
            write_event(
                state_file,
                {
                    "time": started,
                    "status": "success",
                    "mode": "sync",
                    "model": args.model,
                    "product": job.slug,
                    "sources": [str(path.relative_to(ROOT)) for path in job.source_images],
                    "output": str(job.output_path.relative_to(ROOT)),
                },
            )
        except Exception as exc:  # Continue so one bad item does not waste the run.
            print(f"  HATA: {exc}", file=sys.stderr, flush=True)
            write_event(
                state_file,
                {
                    "time": started,
                    "status": "error",
                    "mode": "sync",
                    "model": args.model,
                    "product": job.slug,
                    "error": str(exc),
                },
            )
        if args.delay and index != len(jobs):
            time.sleep(args.delay)


def batch_request(job: ProductJob, template: str, args: argparse.Namespace) -> dict[str, Any]:
    parts: list[dict[str, Any]] = [{"text": prompt_for(job, template)}]
    for path in job.source_images[: args.max_references]:
        parts.append(
            {
                "inlineData": {
                    "mimeType": mime_type(path),
                    "data": base64.b64encode(path.read_bytes()).decode("ascii"),
                }
            }
        )
    return {
        "key": job.slug,
        "request": {
            "contents": [{"role": "user", "parts": parts}],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
                "imageConfig": {
                    "aspectRatio": args.aspect_ratio,
                    "imageSize": args.image_size,
                },
            },
        },
    }


def submit_batch(args: argparse.Namespace, jobs: list[ProductJob], template: str) -> None:
    require_key()
    genai, types = import_sdk()
    client = genai.Client()
    generation_dir = ROOT / "generation"
    generation_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    request_file = generation_dir / f"batch_{timestamp}_requests.jsonl"

    with request_file.open("w", encoding="utf-8") as handle:
        for job in jobs:
            handle.write(json.dumps(batch_request(job, template, args)) + "\n")

    uploaded = client.files.upload(
        file=str(request_file),
        config=types.UploadFileConfig(
            display_name=f"fazilet-product-images-{timestamp}", mime_type="jsonl"
        ),
    )
    batch_job = client.batches.create(
        model=args.model,
        src={"file_name": uploaded.name},
        config={"display_name": f"fazilet-product-images-{timestamp}"},
    )
    record = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "name": batch_job.name,
        "model": args.model,
        "request_file": str(request_file.relative_to(ROOT)),
        "uploaded_file": uploaded.name,
        "products": [job.slug for job in jobs],
    }
    job_file = generation_dir / "latest_batch.json"
    job_file.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Batch gonderildi: {batch_job.name}")
    print(f"Durum/sonuc icin: python3 scripts/generate_product_images.py batch-fetch")


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


def fetch_batch(args: argparse.Namespace, output_dir: Path) -> None:
    require_key()
    genai, _ = import_sdk()
    client = genai.Client()
    job_file = ROOT / "generation" / "latest_batch.json"
    if not job_file.exists():
        raise SystemExit("generation/latest_batch.json bulunamadi; once batch-submit calistirin.")
    record = json.loads(job_file.read_text(encoding="utf-8"))
    job = client.batches.get(name=record["name"])
    state = getattr(getattr(job, "state", None), "name", str(getattr(job, "state", "UNKNOWN")))
    print(f"Batch durumu: {state}")
    if state != "JOB_STATE_SUCCEEDED":
        return

    destination = getattr(job, "dest", None)
    result_name = getattr(destination, "file_name", None)
    if not result_name:
        raise SystemExit("Tamamlanan batch icin sonuc dosyasi bulunamadi.")
    raw = client.files.download(file=result_name)
    result_file = ROOT / "generation" / "latest_batch_results.jsonl"
    result_file.write_bytes(raw)

    saved = 0
    for line in raw.decode("utf-8").splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        slug = item.get("key")
        image = find_image_data(item)
        if not slug or image is None:
            print(f"Sonuc atlandi (anahtar/gorsel yok): {slug or '?'}", file=sys.stderr)
            continue
        output = output_dir / slug / "product_hero.png"
        if output.exists() and not args.force:
            print(f"Mevcut, atlandi: {output.relative_to(ROOT)}")
            continue
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(image)
        saved += 1
    print(f"Kaydedilen aday gorsel: {saved}")


def write_review(output_dir: Path) -> Path:
    cards: list[str] = []
    for output in sorted(output_dir.glob("*/product_hero.png")):
        slug = output.parent.name
        source_dir = env_path("PRODUCT_INPUT_DIR", "new_images") / slug
        sources = sorted(
            path for path in source_dir.glob("*") if path.suffix.lower() in SUPPORTED_SUFFIXES
        )
        source_html = "".join(
            f'<img src="../{path.relative_to(ROOT).as_posix()}" alt="reference">' for path in sources
        )
        cards.append(
            f'<section><h2>{slug}</h2><div class="images">{source_html}'
            f'<img class="generated" src="../{output.relative_to(ROOT).as_posix()}" alt="generated">'
            "</div></section>"
        )
    html = f"""<!doctype html>
<html lang="tr"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Üretilen ürün görselleri</title>
<style>
body{{font:14px system-ui;margin:24px;background:#f4f4f4}}section{{background:white;padding:16px;margin:16px 0;border-radius:12px}}
h2{{font-size:16px}}.images{{display:flex;gap:12px;overflow:auto;align-items:center}}img{{max-width:260px;max-height:260px;object-fit:contain}}
.generated{{border:4px solid #1677ff}}
</style><h1>Ürün görseli adayları</h1><p>Mavi çerçeveli görsel API çıktısıdır.</p>{''.join(cards)}</html>"""
    review = ROOT / "generation" / "review.html"
    review.parent.mkdir(parents=True, exist_ok=True)
    review.write_text(html, encoding="utf-8")
    return review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    def shared(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--input", type=Path)
        subparser.add_argument("--output", type=Path)
        subparser.add_argument("--model", default=os.getenv("GEMINI_IMAGE_MODEL", "gemini-3.1-flash-lite-image"))
        subparser.add_argument("--image-size", default=os.getenv("GEMINI_IMAGE_SIZE", "1K"))
        subparser.add_argument("--aspect-ratio", default=os.getenv("GEMINI_ASPECT_RATIO", "1:1"))
        subparser.add_argument("--prompt", type=Path, default=DEFAULT_PROMPT)
        subparser.add_argument("--only", help="Yalnizca bu urun klasorunu isle")
        subparser.add_argument("--limit", type=int)
        subparser.add_argument("--max-references", type=int, default=3)
        subparser.add_argument("--force", action="store_true")

    plan = subparsers.add_parser("plan", help="Ucret olusturmadan is listesini goster")
    shared(plan)
    run = subparsers.add_parser("run", help="Senkron pilot uretim yap")
    shared(run)
    run.add_argument("--delay", type=float, default=1.0, help="Istekler arasi saniye")
    submit = subparsers.add_parser("batch-submit", help="Ucuz toplu isi gonder")
    shared(submit)
    fetch = subparsers.add_parser("batch-fetch", help="Son batch durumunu kontrol et ve sonucu indir")
    fetch.add_argument("--output", type=Path)
    fetch.add_argument("--force", action="store_true")
    review = subparsers.add_parser("review", help="Adaylar icin HTML kontrol sayfasi olustur")
    review.add_argument("--output", type=Path)
    return parser


def resolve_cli_path(value: Path | None, env_name: str, fallback: str) -> Path:
    if value is None:
        return env_path(env_name, fallback)
    return value if value.is_absolute() else ROOT / value


def main() -> None:
    load_dotenv(ROOT / ".env")
    parser = build_parser()
    args = parser.parse_args()
    output_dir = resolve_cli_path(getattr(args, "output", None), "PRODUCT_OUTPUT_DIR", "generated_candidates")

    if args.command == "batch-fetch":
        fetch_batch(args, output_dir)
        return
    if args.command == "review":
        review = write_review(output_dir)
        print(review)
        return

    input_dir = resolve_cli_path(args.input, "PRODUCT_INPUT_DIR", "new_images")
    template = args.prompt.read_text(encoding="utf-8")
    jobs = select_jobs(
        discover_jobs(input_dir, output_dir),
        only=args.only,
        limit=args.limit,
        force=args.force,
    )
    if not jobs:
        print("Islenecek yeni urun yok.")
        return

    if args.command == "plan":
        for job in jobs:
            print(f"{job.slug}: {len(job.source_images)} referans -> {job.output_path.relative_to(ROOT)}")
        print(f"Toplam: {len(jobs)} urun")
    elif args.command == "run":
        run_sync(args, jobs, template)
    elif args.command == "batch-submit":
        submit_batch(args, jobs, template)


if __name__ == "__main__":
    main()

