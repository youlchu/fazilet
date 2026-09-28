#!/usr/bin/env python3
"""Create accurate, consistent Turkish product-information cards locally."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
IMAGE_ROOT = ROOT / "new_images"
FONT_REGULAR = "/System/Library/Fonts/Supplemental/Arial.ttf"
FONT_BOLD = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
LOGO_PATH = ROOT / "assets" / "branding" / "fazilet-ceyiz-logo.png"
# The logo stays a discreet watermark-like signature in the top-right corner.
LOGO_WIDTH = 200
LOGO_TOP = 48
LOGO_RIGHT_MARGIN = 55
LOGO_PADDING = 14
LOGO_PLATE_ALPHA = 232

PRODUCTS = {
    "akdeniz-zumrut-soft-siraz-bakalit-kulp-orta-boy-caydanlik": {
        "brand": "AKDENİZ",
        "title": "ZÜMRÜT SOFT ŞİRAZ",
        "subtitle": "Bakalit Kulp • Orta Boy Çaydanlık",
        "accent": (126, 34, 66),
        "features": [
            "304 kalite paslanmaz çelik",
            "Kendinden süzgeçli tasarım",
            "3 kat kapsül taban",
            "Özenle parlatılmış dış yüzey",
        ],
    },
    "aksu-t11-ken-fry-2-2-l-1600-w-beyaz-fritoz": {
        "brand": "AKSU",
        "title": "KEN FRY T11",
        "subtitle": "2,2 L • 1600 W • Beyaz Fritöz",
        "accent": (213, 65, 45),
        "features": [
            "2,2 litre geniş iç hacim",
            "1600 W güç",
            "Ayarlanabilir ısı kontrolü",
            "Koku filtresi ve emniyet kilidi",
            "Asansörlü sepet sistemi",
        ],
    },
    "altus-al-606-sg-st-sr-toz-torbasiz-supurge": {
        "brand": "ALTUS",
        "title": "AL 606 SERİSİ",
        "subtitle": "SG • ST • SR Torbasız Süpürge",
        "accent": (194, 21, 105),
        "features": [
            "Siklonik torbasız teknoloji",
            "2,5 L geniş toz haznesi",
            "HEPA 12 filtre",
            "Üç farklı renk seçeneği",
        ],
    },
    "aprilla-ahc-5038-sac-sakal-kesme-makinesi": {
        "brand": "APRILLA",
        "title": "AHC-5038",
        "subtitle": "Şarjlı Saç ve Sakal Kesme Makinesi",
        "accent": (139, 41, 52),
        "features": [
            "Kablolu ve kablosuz kullanım",
            "2 saatte hızlı şarj",
            "45 dakika çalışma süresi",
            "Yeni nesil USB Type-C",
            "1,5 / 2 / 3 / 4 mm taraklar",
        ],
    },
    "arnica-lotus-trend-et14000-toz-torbali-elektrikli-supurge": {
        "brand": "ARNICA",
        "title": "LOTUS TREND ET14000",
        "subtitle": "Toz Torbalı Elektrikli Süpürge",
        "accent": (28, 68, 115),
        "features": [
            "899 W yüksek motor gücü",
            "4,5 L toz torbası",
            "Elektronik emiş gücü ayarı",
            "Yıkanabilir HEPA 13 filtre",
            "Toz torbası doluluk göstergesi",
        ],
    },
}


def font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def mix(a: tuple[int, int, int], b: tuple[int, int, int], amount: float) -> tuple[int, int, int]:
    return tuple(round(x * (1 - amount) + y * amount) for x, y in zip(a, b))


def wrap(draw: ImageDraw.ImageDraw, text: str, face: ImageFont.FreeTypeFont, width: int) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
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


def rounded_image(source: Image.Image, size: tuple[int, int], radius: int) -> Image.Image:
    fitted = ImageOps.contain(source.convert("RGB"), size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, "white")
    x = (size[0] - fitted.width) // 2
    y = (size[1] - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, size[0], size[1]), radius=radius, fill=255)
    canvas.putalpha(mask)
    return canvas


def load_logo(width: int) -> Image.Image:
    """Return the branding logo trimmed to its visible pixels at the requested width."""
    if not LOGO_PATH.is_file():
        raise FileNotFoundError(f"Branding logo not found: {LOGO_PATH}")
    logo = Image.open(LOGO_PATH).convert("RGBA")
    bbox = logo.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"Branding logo is fully transparent: {LOGO_PATH}")
    logo = logo.crop(bbox)
    height = max(1, round(logo.height * width / logo.width))
    return logo.resize((width, height), Image.Resampling.LANCZOS)


def paste_logo(canvas: Image.Image, accent: tuple[int, int, int]) -> None:
    """Overlay the small logo on a rounded plate in the top-right corner of a card."""
    logo = load_logo(LOGO_WIDTH)
    plate_size = (logo.width + LOGO_PADDING * 2, logo.height + LOGO_PADDING * 2)
    x0 = canvas.width - LOGO_RIGHT_MARGIN - plate_size[0]
    y0 = LOGO_TOP
    radius = plate_size[1] // 2

    plate = Image.new("RGBA", plate_size, (0, 0, 0, 0))
    plate_draw = ImageDraw.Draw(plate)
    plate_draw.rounded_rectangle(
        (0, 0, plate_size[0] - 1, plate_size[1] - 1),
        radius=radius,
        fill=(255, 255, 255, LOGO_PLATE_ALPHA),
        outline=mix(accent, (255, 255, 255), 0.68) + (150,),
        width=2,
    )
    plate.alpha_composite(logo, (LOGO_PADDING, LOGO_PADDING))

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle(
        (x0 + 2, y0 + 7, x0 + plate_size[0] + 2, y0 + plate_size[1] + 7),
        radius=radius,
        fill=(20, 24, 32, 30),
    )
    canvas.paste(shadow, (0, 0), shadow.filter(ImageFilter.GaussianBlur(11)))
    canvas.paste(plate, (x0, y0), plate)


def create_card(slug: str, spec: dict[str, object]) -> Path:
    width = height = 1254
    accent = spec["accent"]
    assert isinstance(accent, tuple)

    canvas = Image.new("RGB", (width, height))
    pixels = canvas.load()
    pale = mix(accent, (255, 255, 255), 0.92)
    for y in range(height):
        ratio = y / (height - 1)
        row = mix((255, 255, 255), pale, ratio)
        for x in range(width):
            pixels[x, y] = row

    draw = ImageDraw.Draw(canvas)
    draw.ellipse((900, -250, 1420, 270), fill=mix(accent, (255, 255, 255), 0.87))
    draw.ellipse((-240, 1000, 240, 1480), fill=mix(accent, (255, 255, 255), 0.9))
    draw.rounded_rectangle((55, 48, 245, 100), radius=26, fill=accent)
    draw.text((150, 74), "ÜRÜN BİLGİSİ", font=font(22, bold=True), fill="white", anchor="mm")

    draw.text((55, 135), str(spec["brand"]), font=font(30, bold=True), fill=accent)
    draw.text((55, 177), str(spec["title"]), font=font(62, bold=True), fill=(25, 29, 38))
    draw.text((58, 252), str(spec["subtitle"]), font=font(27), fill=(76, 82, 94))
    draw.line((55, 305, 1199, 305), fill=mix(accent, (255, 255, 255), 0.65), width=3)

    paste_logo(canvas, accent)

    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.rounded_rectangle((57, 354, 704, 1166), radius=42, fill=(20, 24, 32, 42))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    canvas.paste(shadow, (0, 0), shadow)

    hero_path = IMAGE_ROOT / slug / "product_hero.jpg"
    hero = rounded_image(Image.open(hero_path), (630, 795), 38)
    canvas.paste(hero, (55, 342), hero)

    draw = ImageDraw.Draw(canvas)
    features = list(spec["features"])
    card_x1, card_x2 = 735, 1199
    top, gap = 350, 18
    available = 790
    card_h = (available - gap * (len(features) - 1)) // len(features)
    body = font(26, bold=True)
    for index, feature in enumerate(features, start=1):
        y1 = top + (index - 1) * (card_h + gap)
        y2 = y1 + card_h
        draw.rounded_rectangle((card_x1, y1, card_x2, y2), radius=26, fill=(255, 255, 255), outline=mix(accent, (255, 255, 255), 0.72), width=2)
        circle_x = card_x1 + 52
        circle_y = (y1 + y2) // 2
        draw.ellipse((circle_x - 28, circle_y - 28, circle_x + 28, circle_y + 28), fill=accent)
        draw.text((circle_x, circle_y + 1), f"{index:02d}", font=font(19, bold=True), fill="white", anchor="mm")
        lines = wrap(draw, str(feature), body, card_x2 - card_x1 - 125)
        line_height = 34
        text_y = circle_y - (len(lines) * line_height) // 2
        for line in lines:
            draw.text((card_x1 + 98, text_y), line, font=body, fill=(36, 40, 49))
            text_y += line_height

    draw.text((1199, 1193), "DOĞRULANMIŞ ÜRÜN ÖZELLİKLERİ", font=font(17, bold=True), fill=mix(accent, (90, 90, 100), 0.45), anchor="ra")

    output = IMAGE_ROOT / slug / "product_info.jpg"
    canvas.save(output, "JPEG", quality=95, optimize=True)
    return output


def main() -> None:
    for slug, spec in PRODUCTS.items():
        output = create_card(slug, spec)
        print(output.relative_to(ROOT))


if __name__ == "__main__":
    main()
