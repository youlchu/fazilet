# Ürün katalog çalışma alanı

Bu klasörde her gerçek ürün için ayrı bir klasör bulunur. Dosya standardı:

- `past_*`: mağazada çekilmiş özgün referans fotoğrafı; arşivlenir, katalogta doğrudan kullanılmaz.
- `product_hero.png`: kutusuz, temiz stüdyo ürün sunumu.
- `product_box.png`: ürünün kutulu katalog sunumu.
- `product_info.json`: doğrulanmış ürün kimliği, kaynaklar ve güven notları.

## Ürün kimliği kuralları

- Klasör adları küçük harf, ASCII ve tire ile yazılır.
- Model kodu doğrulanabiliyorsa klasör adına eklenir.
- Aynı fotoğrafta iki farklı ürün/model varsa ayrı klasörlere ayrılır.
- Görselde veya kaynaklarda doğrulanmayan teknik özellikler katalog görseline yazılmaz.
- Yapay üretim görselleri satış öncesinde fiziksel ürünle son kez karşılaştırılmalıdır.

## Mevcut kapsam

Toplam 17 ayrı ürün vardır. `classification_outputs` eski otomatik tarama çıktısıdır; ürün klasörü değildir. `catalog_outputs` önceki geçici üretim dizinidir; nihai görseller artık doğrudan ilgili ürün klasöründe tutulur.

Toplu görsel kontrol için `catalog_review.html` açılabilir. Manifest veya görseller değiştiğinde `python3 build_catalog_review.py` komutu sayfayı yeniden üretir.
