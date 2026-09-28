#!/usr/bin/env python3
"""Build a local visual index for reviewing every catalog product."""

from __future__ import annotations

import html
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "product_manifest.json"
OUTPUT = ROOT / "catalog_review.html"


def first_reference(folder: Path) -> str:
    references = sorted(folder.glob("past_*"))
    return references[0].name if references else ""


def main() -> None:
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    cards = []
    for item in data["products"]:
        folder_name = item["folder"]
        folder = ROOT / folder_name
        reference = first_reference(folder)
        title = " ".join(
            value for value in (item.get("brand"), item.get("model"), item.get("name")) if value
        )
        source = item.get("source")
        source_html = (
            f'<a href="{html.escape(source, quote=True)}" target="_blank" rel="noreferrer">Kaynağı aç</a>'
            if source
            else "Ambalajdan doğrulandı"
        )
        ref_html = (
            f'<figure><img src="{folder_name}/{html.escape(reference, quote=True)}" '
            f'alt="Eski referans"><figcaption>past_ referans</figcaption></figure>'
            if reference
            else '<figure class="missing"><figcaption>Referans yok</figcaption></figure>'
        )
        info_html = (
            f'<figure><img src="{folder_name}/product_info.png" alt="Ürün bilgi kartı">'
            '<figcaption>product_info.png</figcaption></figure>'
            if (folder / "product_info.png").is_file()
            else '<figure class="missing"><figcaption>Bilgi kartı henüz yok</figcaption></figure>'
        )
        cards.append(
            f"""
            <article class="card">
              <header>
                <div>
                  <h2>{html.escape(title)}</h2>
                  <code>{html.escape(folder_name)}</code>
                </div>
                <span class="confidence">{html.escape(item.get('identity_confidence', ''))}</span>
              </header>
              <div class="images">
                {ref_html}
                <figure><img src="{folder_name}/product_hero.png" alt="Temiz ürün"><figcaption>product_hero.png</figcaption></figure>
                <figure><img src="{folder_name}/product_box.png" alt="Kutulu ürün"><figcaption>product_box.png</figcaption></figure>
                {info_html}
              </div>
              <footer>{source_html}</footer>
            </article>
            """
        )

    document = f"""<!doctype html>
<html lang="tr">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Ürün katalog görsel kontrolü</title>
  <style>
    :root {{ color-scheme: light; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; background: #f3f5f7; color: #18212b; }}
    .page {{ width: min(1540px, 96vw); margin: 32px auto 64px; }}
    .summary {{ display: flex; gap: 14px; align-items: baseline; margin-bottom: 24px; }}
    .summary h1 {{ margin: 0; font-size: clamp(24px, 3vw, 40px); }}
    .summary span {{ color: #647180; }}
    .grid {{ display: grid; gap: 22px; }}
    .card {{ background: white; border: 1px solid #dce2e8; border-radius: 16px; padding: 18px; box-shadow: 0 8px 26px #27384a10; }}
    header {{ display: flex; justify-content: space-between; gap: 18px; margin-bottom: 15px; }}
    h2 {{ margin: 0 0 7px; font-size: 19px; }}
    code {{ color: #647180; font-size: 12px; }}
    .confidence {{ align-self: flex-start; padding: 5px 9px; border-radius: 999px; background: #eaf3ee; color: #276246; font-size: 12px; }}
    .images {{ display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 14px; }}
    figure {{ margin: 0; min-width: 0; }}
    img {{ width: 100%; aspect-ratio: 1; object-fit: contain; display: block; border-radius: 10px; background: #f7f8fa; border: 1px solid #e7ebef; }}
    figcaption {{ margin-top: 7px; color: #566575; font-size: 12px; }}
    footer {{ margin-top: 14px; font-size: 13px; }}
    a {{ color: #1769aa; }}
    @media (max-width: 760px) {{ .images {{ grid-template-columns: 1fr; }} header {{ flex-direction: column; }} }}
  </style>
</head>
<body>
  <main class="page">
    <div class="summary"><h1>Ürün katalog görsel kontrolü</h1><span>{len(cards)} ürün · referans / temiz / kutulu / bilgi</span></div>
    <section class="grid">{''.join(cards)}</section>
  </main>
</body>
</html>
"""
    OUTPUT.write_text(document, encoding="utf-8")
    print(OUTPUT)


if __name__ == "__main__":
    main()
