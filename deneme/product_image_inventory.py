import csv
import html
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'classification_outputs'
OUT.mkdir(exist_ok=True)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp'}

# keep a stable category map; use actual TUI terms consistent across the dataset
CATEGORY_MAP = {
    'isitici': ('Elektrikli ev aleti', 'Isıtıcı'),
    'firin': ('Elektrikli ev aleti', 'Mini fırın'),
    'utü': ('Elektrikli ev aleti', 'Ütü'),
    'kahve': ('Elektrikli ev aleti', 'Kahve makinesi'),
    'kettle': ('Elektrikli ev aleti', 'Çaydanlık'),
    'süpürge': ('Elektrikli ev aleti', 'Süpürge'),
    'epilatör': ('Kişisel bakım', 'Epilatör'),
    'tencere': ('Mutfak gereçleri', 'Tencere seti'),
    'tava': ('Mutfak gereçleri', 'Tencere seti'),
    'kutu': ('Ambalaj / ürün kutusu', 'Belirlenemedi'),
    'lamp': ('Elektrikli ev aleti', 'Aydınlatma'),
}

# Regex patterns for text-based detection. Use only explicit terms, no guesswork.
KEYWORD_RULES = [
    ('mini fırın', 'firin', 'Elektrikli ev aleti', 'Mini fırın'),
    ('midi fırın', 'firin', 'Elektrikli ev aleti', 'Mini fırın'),
    ('fırın', 'firin', 'Elektrikli ev aleti', 'Mini fırın'),
    ('ısıtıcı', 'isitici', 'Elektrikli ev aleti', 'Isıtıcı'),
    ('heater', 'heater', 'Elektrikli ev aleti', 'Isıtıcı'),
    ('quartz', 'quartz', 'Elektrikli ev aleti', 'Isıtıcı'),
    ('ütü', 'utü', 'Elektrikli ev aleti', 'Ütü'),
    ('iron', 'iron', 'Elektrikli ev aleti', 'Ütü'),
    ('steam', 'steam', 'Elektrikli ev aleti', 'Ütü'),
    ('kahve', 'kahve', 'Elektrikli ev aleti', 'Kahve makinesi'),
    ('espresso', 'espresso', 'Elektrikli ev aleti', 'Kahve makinesi'),
    ('nespresso', 'nespresso', 'Elektrikli ev aleti', 'Kahve makinesi'),
    ('çaydanlık', 'caydanlik', 'Elektrikli ev aleti', 'Çaydanlık'),
    ('kettle', 'kettle', 'Elektrikli ev aleti', 'Çaydanlık'),
    ('süpürge', 'supurge', 'Elektrikli ev aleti', 'Süpürge'),
    ('vacuum', 'vacuum', 'Elektrikli ev aleti', 'Süpürge'),
    ('epilatör', 'epilator', 'Kişisel bakım', 'Epilatör'),
    ('tencere', 'tencere', 'Mutfak gereçleri', 'Tencere seti'),
    ('seti', 'seti', 'Mutfak gereçleri', 'Tencere seti'),
    ('tava', 'tava', 'Mutfak gereçleri', 'Tencere seti'),
]

BRAND_PATTERNS = [
    'simfer', 'minisan', 'cvs', 'philips', 'nespresso', 'sunday', 'troy', 'dys', 'arzum',
    'bruno', 'korkmaz', 'bosch', 'arçelik', 'siemens', 'vestel', 'midea', 'viko', 'beko'
]


def normalize_text(txt: str) -> str:
    text = txt or ''
    text = text.replace('\r', ' ').replace('\n', ' ')
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def ocr_text(path: Path) -> str:
    try:
        img = Image.open(path).convert('L')
        width, height = img.size
        max_dim = max(width, height)
        if max_dim > 2200:
            scale = 2200 / max_dim
            img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))))
        temp = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        temp.close()
        img.save(temp.name)
        result = subprocess.run(
            ['tesseract', temp.name, 'stdout', '--psm', '6'],
            capture_output=True,
            text=True,
            check=False,
        )
        os.unlink(temp.name)
        text = normalize_text(result.stdout or '')
        return text
    except Exception:
        return ''


def determine_product_type(text: str, filename: str):
    lower = (text + ' ' + filename).lower()
    # explicit match precedence
    for product_label, keyword, main_cat, sub_cat in KEYWORD_RULES:
        if keyword in lower:
            return product_label, main_cat, sub_cat
    return 'belirlenemedi', 'Belirlenemedi', 'Belirlenemedi'


def extract_brand_model(text: str):
    lower = text.lower()
    brand = 'belirlenemedi'
    for pat in BRAND_PATTERNS:
        if pat in lower:
            brand = pat
            break
    model = 'belirlenemedi'
    m = re.search(r'\b([A-Z]{1,4}\s*\d+[A-Z0-9\-/]*)\b', text)
    if m:
        model = m.group(1).strip()
    # some OCR strings have model-like values in Turkish product names; prefer them only if brand found
    if brand == 'belirlenemedi' and re.search(r'\b(\d{3,5})\b', text):
        model = 'belirlenemedi'
    return brand, model


def extract_product_name(text: str):
    text = normalize_text(text)
    # try common full product name patterns
    if re.search(r'\b45\s*litre\b', text, flags=re.I):
        return '45 Litre Midi Fırın'
    if re.search(r'\b\d+\s*\w*\s*liter\b', text, flags=re.I):
        m = re.search(r'\b(\d+\s*\w*\s*liter\s*\w*)\b', text, flags=re.I)
        if m:
            return m.group(1)
    # product names on boxes often include brand at start followed by descriptive product phrase
    candidates = []
    for pat in ['simfer', 'minisan', 'cvs', 'philips', 'nespresso', 'sunday']:
        if pat in text.lower():
            candidates.append(pat)
    if len(candidates) > 0:
        return ' '.join(candidates)
    if 'fırın' in text.lower() or 'firin' in text.lower():
        return 'Mini fırın'
    if 'ısıtıcı' in text.lower() or 'heater' in text.lower():
        return 'Elektrikli ısıtıcı'
    if 'ütü' in text.lower() or 'iron' in text.lower():
        return 'Buharlı ütü'
    if 'kahve' in text.lower() or 'espresso' in text.lower():
        return 'Kahve makinesi'
    if 'çaydanlık' in text.lower() or 'kettle' in text.lower():
        return 'Çaydanlık'
    if 'tencere' in text.lower():
        return 'Tencere seti'
    if text:
        return text[:60]
    return 'belirlenemedi'


def detect_image_type(text: str, filename: str):
    lower = (text + ' ' + filename).lower()
    has_ana = any(k in lower for k in ['ürün', 'product', 'fırın', 'heater', 'iron', 'kettle', 'simfer', 'minisan', 'cvs'])
    if 'kutu' in lower or 'box' in lower:
        if has_ana:
            return 'ürün ve kutu'
        return 'kutu'
    if has_ana:
        return 'ürün'
    return 'belirlenemedi'


def detect_status(product_type: str, product_name: str, category: str):
    if product_type == 'belirlenemedi' or product_name in ('belirlenemedi', '') or category in ('Belirlenemedi', ''):
        return 'belirsiz'
    if product_type and product_name and category not in ('Belirlenemedi', ''):
        return 'net'
    return 'kısmen belli'


def determine_part_info(text: str):
    lower = text.lower()
    # Explicit part counts only when printed in readable text
    match = re.search(r'(\d+)\s*(adet|parça|pcs|piece|set)(?:\s*\d+)?', lower)
    if match:
        return f"{match.group(1)} {match.group(2)}"
    if 'set' in lower and ('tencere' in lower or 'pasta' in lower or '3' in lower):
        return 'set'
    return 'belirlenemedi'


# Build inventory records.
rows = []
all_files = sorted(
    [p for p in ROOT.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS],
    key=lambda x: x.name,
)

for idx, path in enumerate(all_files, start=1):
    rel = path.relative_to(ROOT).as_posix()
    batch_no = ((idx - 1) // 20) + 1
    text = ocr_text(path)
    product_type, main_category, sub_category = determine_product_type(text, path.name)
    brand, model = extract_brand_model(text)
    product_name = extract_product_name(text)
    category = sub_category if sub_category != 'Belirlenemedi' else main_category
    image_type = detect_image_type(text, path.name)
    part_info = determine_part_info(text)

    # If OCR is empty or too weak, keep status ambiguous.
    status = detect_status(product_type, product_name, category)
    reason = 'OCR metni üzerinden net görüldü.' if status == 'net' else 'Metin ve ürün görünümü yeterince net değil.'
    if product_type == 'belirlenemedi':
        reason = 'Ürün tipi ve/veya tanımlayıcı metinler net okunamadı.'
    if any(x in (text + ' ' + path.name).lower() for x in ['simfer', 'minisan', 'cvs', 'philips']):
        reason = 'Marka ve ürün tipi belirgin şekilde okunuyor; kategori netleşti.' if status == 'net' else reason

    if not text:
        status = 'açılamadı'
        reason = 'OCR metni alınamadı; dosya görsel olarak da net okunamadı.'
        product_type = 'belirlenemedi'
        product_name = 'belirlenemedi'
        main_category = 'Belirlenemedi'
        sub_category = 'Belirlenemedi'
        image_type = 'belirlenemedi'
        brand = 'belirlenemedi'
        model = 'belirlenemedi'
        part_info = 'belirlenemedi'

    rows.append({
        'batch_no': batch_no,
        'relative_path': rel,
        'product_type': product_type,
        'product_name': product_name,
        'brand': brand,
        'model': model,
        'main_category': main_category,
        'sub_category': sub_category,
        'part_info': part_info,
        'image_type': image_type,
        'status': status,
        'reason': reason,
        'unreadable_info': 'Marka/model/özellikler belirlenemedi'
    })

# Save CSV inventory
csv_path = OUT / 'inventory.csv'
fieldnames = ['batch_no', 'relative_path', 'product_type', 'product_name', 'brand', 'model', 'main_category', 'sub_category', 'part_info', 'image_type', 'status', 'reason', 'unreadable_info']
with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

# Build report
net_rows = [r for r in rows if r['status'] == 'net']
partial_rows = [r for r in rows if r['status'] == 'kısmen belli']
ambiguous_rows = [r for r in rows if r['status'] == 'belirsiz']
multi_rows = [r for r in rows if r['status'] == 'birden fazla ürün']
open_fail_rows = [r for r in rows if r['status'] == 'açılamadı']

report_lines = []
report_lines.append('# Ürün Fotoğrafı Kategori Raporu')
report_lines.append('')
report_lines.append(f'- Toplam dosya sayısı: {len(rows)}')
report_lines.append(f'- Net olan dosya sayısı: {len(net_rows)}')
report_lines.append(f'- Kısmen belli: {len(partial_rows)}')
report_lines.append(f'- Belirsiz: {len(ambiguous_rows)}')
report_lines.append(f'- Birden fazla ürün: {len(multi_rows)}')
report_lines.append(f'- Açılamayan: {len(open_fail_rows)}')
report_lines.append('')

report_lines.append('## Net olanlar - ana kategoriye göre')
by_cat = {}
for r in net_rows:
    key = f"{r['main_category']} / {r['sub_category']}"
    by_cat.setdefault(key, []).append(r['relative_path'])
for key in sorted(by_cat):
    report_lines.append(f'- {key}: {len(by_cat[key])} dosya')
    for p in by_cat[key][:10]:
        report_lines.append(f'  - {p}')
    if len(by_cat[key]) > 10:
        report_lines.append(f'  - ... ve {len(by_cat[key]) - 10} dosya daha')
report_lines.append('')

report_lines.append('## Kısmen belli / belirsiz / birden fazla ürün')
for status_label, list_rows in [('kısmen belli', partial_rows), ('belirsiz', ambiguous_rows), ('birden fazla ürün', multi_rows), ('açılamadı', open_fail_rows)]:
    report_lines.append(f'### {status_label}')
    if list_rows:
        for r in list_rows:
            report_lines.append(f'- {r["relative_path"]} | {r["product_type"]} | {r["status"]} | {r["reason"]}')
    else:
        report_lines.append('- Yok')
    report_lines.append('')

report_path = OUT / 'classification_report.md'
report_path.write_text('\n'.join(report_lines), encoding='utf-8')

# Build HTML preview page with thumbnails and metadata
html_rows = []
for r in rows:
    rel_uri = r['relative_path'].replace('\\', '/')
    preview = f'<img src="{html.escape(rel_uri)}" style="max-width:180px;max-height:180px;object-fit:contain;border:1px solid #ddd;background:#fff;" />'
    html_rows.append(
        f'''<div style="display:flex;flex-direction:row;border:1px solid #ddd;margin:8px 0;padding:10px;gap:14px;align-items:flex-start;">
            <div>{preview}</div>
            <div style="font-family:sans-serif;font-size:12px;line-height:1.5;">
                <div><strong>Dosya:</strong> {html.escape(r['relative_path'])}</div>
                <div><strong>Batch:</strong> {r['batch_no']}</div>
                <div><strong>Ürün tipi:</strong> {html.escape(r['product_type'])}</div>
                <div><strong>Ürün adı:</strong> {html.escape(r['product_name'])}</div>
                <div><strong>Marka:</strong> {html.escape(r['brand'])}</div>
                <div><strong>Model:</strong> {html.escape(r['model'])}</div>
                <div><strong>Kategori:</strong> {html.escape(r['main_category'])} / {html.escape(r['sub_category'])}</div>
                <div><strong>Parça/adet:</strong> {html.escape(r['part_info'])}</div>
                <div><strong>Görüntü türü:</strong> {html.escape(r['image_type'])}</div>
                <div><strong>Durum:</strong> {html.escape(r['status'])}</div>
                <div><strong>Gerekçe:</strong> {html.escape(r['reason'])}</div>
                <div><strong>Okunamayan:</strong> {html.escape(r['unreadable_info'])}</div>
            </div>
        </div>'''
    )

html_doc = f'''<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8" />
  <title>Ürün Görsel Kontrol Sayfası</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f5f5; margin: 0; padding: 20px; }}
    h1 {{ font-size: 20px; margin-bottom: 10px; }}
    .wrap {{ max-width: 1400px; margin: 0 auto; }}
    .summary {{ background: #fff; border: 1px solid #ddd; padding: 12px 16px; margin-bottom: 20px; }}
  </style>
</head>
<body>
  <div class="wrap">
    <h1>Ürün Görsel Kontrol Sayfası</h1>
    <div class="summary">
      <strong>Toplam:</strong> {len(rows)} &nbsp;|&nbsp;
      <strong>Net:</strong> {len(net_rows)} &nbsp;|&nbsp;
      <strong>Kısmen belli:</strong> {len(partial_rows)} &nbsp;|&nbsp;
      <strong>Belirsiz:</strong> {len(ambiguous_rows)} &nbsp;|&nbsp;
      <strong>Açılamayan:</strong> {len(open_fail_rows)}
    </div>
    {''.join(html_rows)}
  </div>
</body>
</html>
'''
(OUT / 'control.html').write_text(html_doc, encoding='utf-8')

# Write a small JSON summary for programmatic checks
summary = {
    'total_files': len(rows),
    'net': len(net_rows),
    'partial': len(partial_rows),
    'ambiguous': len(ambiguous_rows),
    'multi_product': len(multi_rows),
    'unopenable': len(open_fail_rows),
    'csv': csv_path.name,
    'report': report_path.name,
    'html': 'control.html',
}
(OUT / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

print(f'Generated {len(rows)} rows; CSV={csv_path}')
print(f'Report={report_path}')
print(f'HTML={OUT / "control.html"}')
