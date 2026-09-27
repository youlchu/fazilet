#!/usr/bin/env python3
"""Create a clean Aprilla box image while preserving the photographed print."""

from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_DIR = ROOT / "new_images" / "aprilla-ahc-5038-sac-sakal-kesme-makinesi"
SOURCE = PRODUCT_DIR / "past_aprilla-ahc-5038-sac-sakal-kesme-makinesi_00000189.jpg"
OUTPUT = PRODUCT_DIR / "product_box.jpg"


def main() -> None:
    source = Image.open(SOURCE).convert("RGB")

    # Coordinates follow the four photographed corners of the real box front:
    # upper-left, lower-left, lower-right, upper-right.
    face = source.transform(
        (620, 1580),
        Image.Transform.QUAD,
        (226, 262, 203, 1848, 758, 1840, 780, 260),
        resample=Image.Resampling.BICUBIC,
    )
    # Remove the narrow photographed background/hand strip beyond the box edge.
    face = face.crop((0, 0, 555, 1580))
    face = ImageEnhance.Brightness(face).enhance(1.08)
    face = ImageEnhance.Contrast(face).enhance(1.08)
    face = ImageEnhance.Color(face).enhance(1.05)
    face = face.filter(ImageFilter.UnsharpMask(radius=1.2, percent=115, threshold=3))
    face = face.resize((390, 960), Image.Resampling.LANCZOS)

    size = 1254
    canvas = Image.new("RGB", (size, size), (247, 247, 244))

    shadow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    shadow_draw.ellipse((315, 1065, 880, 1170), fill=(0, 0, 0, 55))
    shadow = shadow.filter(ImageFilter.GaussianBlur(28))
    canvas.paste(shadow, (0, 0), shadow)

    front_x, front_y = 432, 125
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle(
        (front_x - 3, front_y - 3, front_x + face.width + 3, front_y + face.height + 3),
        radius=5,
        fill=(93, 28, 37),
    )
    canvas.paste(face, (front_x, front_y))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(OUTPUT, "JPEG", quality=96, optimize=True)
    print(OUTPUT.relative_to(ROOT))


if __name__ == "__main__":
    main()
