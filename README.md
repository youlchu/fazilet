# Fazilet ürün görselleri

Bu depo mağazada çekilmiş ürün referanslarını düzenlemek, ürün kimliklerini doğrulamak ve Gemini Nano Banana API ile incelenebilir katalog görseli adayları üretmek için kullanılır.

## Klasörler

- `new_images/`: Ürün adına göre ayrılmış özgün referans görselleri. Bu klasörde yalnızca ürün klasörleri ve görseller bulunur.
- `_okunamayanlar/`: Henüz güvenilir şekilde sınıflandırılamayan özgün fotoğraflar.
- `generated_candidates/`: API ile üretilen, insan kontrolü bekleyen görseller. Git'e eklenmez.
- `products/`: Onaylanmış örnek katalog ürünleri ve görselleri.
- `generation/`: İstem şablonu ve yerel işlem kayıtları.
- `scripts/`: API ve kontrol araçları.

## Hızlı başlangıç

Ayrıntılı hesap, API anahtarı ve faturalandırma adımları için [KURULUM.md](docs/KURULUM.md) dosyasını okuyun.

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

Önce ücretsiz plan görünümü:

```bash
python3 scripts/generate_product_images.py plan --limit 10
```

Tek ürünle ücretli pilot:

```bash
python3 scripts/generate_product_images.py run \
  --only evia-holiday-ea-4603-1100-w-seyahat-utusu
```

En ucuz toplu üretim:

```bash
python3 scripts/generate_product_images.py batch-submit --limit 10
python3 scripts/generate_product_images.py batch-fetch
python3 scripts/generate_product_images.py review
```

`run` ve `batch-submit` gerçek API çağrısı yapar ve ücret oluşturabilir. Script kaynak görsellere dokunmaz ve `--force` verilmedikçe mevcut aday çıktının üzerine yazmaz.

