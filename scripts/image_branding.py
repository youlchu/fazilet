#!/usr/bin/env python3
"""Apply the Fazilet Ceyiz signature to generated catalog images."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / "assets" / "branding" / "fazilet-ceyiz-logo.png"


def _load_logo(width: int) -> Image.Image:
    if not LOGO_PATH.is_file():
        raise FileNotFoundError(f"Logo bulunamadi: {LOGO_PATH}")
    with Image.open(LOGO_PATH) as source:
        logo = source.convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"Logo tamamen seffaf: {LOGO_PATH}")
    logo = logo.crop(bbox)
    height = max(1, round(logo.height * width / logo.width))
    return logo.resize((width, height), Image.Resampling.LANCZOS)


def add_logo(image: Image.Image) -> Image.Image:
    """Return an RGB copy with a small top-right logo plate."""
    canvas = image.convert("RGBA")
    unit = min(canvas.size)
    logo = _load_logo(max(96, round(unit * 0.1595)))
    padding = max(7, round(unit * 0.0112))
    margin_right = max(18, round(unit * 0.0439))
    margin_top = max(18, round(unit * 0.0383))
    plate_size = (logo.width + padding * 2, logo.height + padding * 2)
    x0 = canvas.width - margin_right - plate_size[0]
    y0 = margin_top
    radius = plate_size[1] // 2

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0 + 2, y0 + 6, x0 + plate_size[0] + 2, y0 + plate_size[1] + 6),
        radius=radius,
        fill=(20, 24, 32, 34),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(max(5, round(unit * 0.009))))
    canvas.alpha_composite(shadow)

    plate = Image.new("RGBA", plate_size, (0, 0, 0, 0))
    ImageDraw.Draw(plate).rounded_rectangle(
        (0, 0, plate_size[0] - 1, plate_size[1] - 1),
        radius=radius,
        fill=(255, 255, 255, 232),
        outline=(224, 190, 185, 170),
        width=max(1, round(unit * 0.0016)),
    )
    plate.alpha_composite(logo, (padding, padding))
    canvas.alpha_composite(plate, (x0, y0))
    return canvas.convert("RGB")


def brand_file(path: Path, *, output: Path | None = None) -> Path:
    """Brand one image and save it, preserving PNG/JPEG from the destination suffix."""
    destination = output or path
    with Image.open(path) as source:
        branded = add_logo(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.suffix.lower() in {".jpg", ".jpeg"}:
        branded.save(destination, "JPEG", quality=95, optimize=True)
    else:
        branded.save(destination, "PNG", optimize=True)
    return destination
