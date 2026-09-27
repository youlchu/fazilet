from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent / "contact_sheets"
OUT.mkdir(parents=True, exist_ok=True)

files = sorted(ROOT.glob("*.jpg"), key=lambda path: path.name)
font = ImageFont.load_default(size=18)
cols, rows = 5, 5
cell_w, cell_h = 360, 300
image_h = 260

for sheet_index, start in enumerate(range(0, len(files), cols * rows), start=1):
    batch = files[start : start + cols * rows]
    sheet = Image.new("RGB", (cols * cell_w, rows * cell_h), "white")
    draw = ImageDraw.Draw(sheet)
    for offset, path in enumerate(batch):
        row, col = divmod(offset, cols)
        x, y = col * cell_w, row * cell_h
        try:
            with Image.open(path) as source:
                source = ImageOps.exif_transpose(source).convert("RGB")
                thumb = ImageOps.contain(source, (cell_w - 12, image_h - 8))
            px = x + (cell_w - thumb.width) // 2
            py = y + (image_h - thumb.height) // 2
            sheet.paste(thumb, (px, py))
        except Exception as exc:
            draw.text((x + 8, y + 80), f"AÇILAMADI: {exc}", fill="red", font=font)
        label = path.name.split("-")[0]
        draw.rectangle((x, y + image_h, x + cell_w, y + cell_h), fill="#f2f2f2")
        draw.text((x + 8, y + image_h + 8), label, fill="black", font=font)
        draw.rectangle((x, y, x + cell_w - 1, y + cell_h - 1), outline="#777")
    first = batch[0].name.split("-")[0]
    last = batch[-1].name.split("-")[0]
    sheet.save(OUT / f"sheet_{sheet_index:02d}_{first}_{last}.jpg", quality=92)

print(f"{len(files)} görsel için {sheet_index} temas sayfası oluşturuldu: {OUT}")
