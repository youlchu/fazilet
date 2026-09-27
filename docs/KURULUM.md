# Nano Banana API kurulum rehberi

Bu proje Google Gemini API üzerinden Nano Banana görsel modellerini kullanır. ChatGPT veya Gemini aboneliği API kullanım ücretini karşılamaz; API faturalandırması ayrıdır.

## 1. Google hesabı ve AI Studio

1. Bir Google hesabıyla [Google AI Studio](https://aistudio.google.com/) adresini açın.
2. Hizmet şartları gösterilirse kabul edin.
3. Sol menüden **Get API key** bölümünü veya doğrudan [API Keys](https://aistudio.google.com/apikey) sayfasını açın.
4. **Create API key** seçeneğine basın.
5. Yeni veya mevcut bir Google Cloud projesi seçin. Bu proje için `fazilet-images` gibi anlaşılır bir ad kullanabilirsiniz.
6. Oluşturulan anahtarı kopyalayın. Anahtarı GitHub'a, ekran görüntüsüne veya mesaj içine koymayın.

## 2. Faturalandırma ve limit

1. [Google Cloud Console](https://console.cloud.google.com/) içinde AI Studio'da seçtiğiniz aynı projeyi açın.
2. **Billing** bölümünden projeye bir faturalandırma hesabı bağlayın.
3. **Billing > Budgets & alerts** bölümünde aylık bütçe uyarısı oluşturun. Başlangıç için 5 veya 10 USD uygun bir güvenlik sınırıdır.
4. Bütçe uyarısının harcamayı otomatik durdurmadığını unutmayın; yalnızca bildirim gönderir. Önce `--limit 1`, ardından `--limit 10` kullanın.
5. API anahtarının kısıtlar sayfasında mümkünse anahtarı yalnızca **Generative Language API / Gemini API** için sınırlandırın.

Güncel model fiyatlarını işlemden önce [Gemini API fiyatlandırma](https://ai.google.dev/gemini-api/docs/pricing) sayfasından kontrol edin. Batch API standart ücretin yüzde 50'sidir ve sonuçlanması 24 saate kadar sürebilir.

## 3. Yerel ortam

Terminalde depo klasörüne girin:

```bash
cd /Users/youlchu/Desktop/fazilet
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
cp .env.example .env
```

`.env` dosyasını bir metin düzenleyiciyle açın ve yalnızca aşağıdaki değeri doldurun:

```dotenv
GEMINI_API_KEY=buraya_google_ai_studio_anahtari
```

Diğer ayarların anlamı:

- `GEMINI_IMAGE_MODEL`: İlk denemelerde `gemini-3.1-flash-lite-image`; ayrıntısı bozulan zor ürünlerde `gemini-3.1-flash-image`.
- `PRODUCT_INPUT_DIR`: Kaynak görsellerin bulunduğu `new_images`.
- `PRODUCT_OUTPUT_DIR`: İncelenecek adayların yazıldığı `generated_candidates`.
- `GEMINI_IMAGE_SIZE`: En düşük maliyet için `1K`.
- `GEMINI_ASPECT_RATIO`: Katalog standardı için `1:1`.

Gerçek `.env` dosyası `.gitignore` içindedir ve GitHub'a gönderilmez. Repoda yalnızca boş açıklama şablonu olan `.env.example` bulunur.

## 4. Ücret oluşturmadan kontrol

```bash
python3 scripts/generate_product_images.py plan --limit 10
```

Bu komut yalnızca hangi ürünlerin işleneceğini listeler; API çağrısı veya ücret oluşturmaz.

## 5. Tek ürün pilotu

```bash
python3 scripts/generate_product_images.py run \
  --only evia-holiday-ea-4603-1100-w-seyahat-utusu
```

Çıktı şurada oluşur:

```text
generated_candidates/evia-holiday-ea-4603-1100-w-seyahat-utusu/product_hero.jpg
```

Kaynak fotoğraf değiştirilmez. Mevcut çıktı da `--force` verilmeden değiştirilmez.

## 6. On ürünlük kalite testi

```bash
python3 scripts/generate_product_images.py run --limit 10
python3 scripts/generate_product_images.py review
open generation/review.html
```

Kontrol sırasında ürünün rengi, düğmeleri, aksesuarları, model kodu, marka logosu ve kutu üzerindeki yazıları özgün fotoğrafla karşılaştırın.

## 7. En düşük maliyetli Batch üretimi

Önce küçük bir batch gönderin:

```bash
python3 scripts/generate_product_images.py batch-submit --limit 10
```

Bir süre sonra durumu kontrol edip tamamlanan sonuçları indirin:

```bash
python3 scripts/generate_product_images.py batch-fetch
python3 scripts/generate_product_images.py review
```

Test başarılıysa `--limit` vermeden kalan ürünleri gönderebilirsiniz:

```bash
python3 scripts/generate_product_images.py batch-submit
```

Batch sonuçları hemen hazır olmayabilir. Aynı batch'i tekrar göndermek yerine `batch-fetch` komutunu daha sonra yeniden çalıştırın.

## 8. Zor ürünleri yeniden üretme

Lite model ürün ayrıntısını değiştirmişse yalnızca o ürün için normal Nano Banana 2 kullanın:

```bash
python3 scripts/generate_product_images.py run \
  --model gemini-3.1-flash-image \
  --only URUN-KLASOR-ADI \
  --force
```

`--force` mevcut aday görseli değiştirir. Kaynak `past_*.jpg` dosyalarını yine değiştirmez.

## Güvenlik

- API anahtarını asla commit etmeyin veya GitHub'a yüklemeyin.
- Anahtar yanlışlıkla yayımlanırsa AI Studio'dan hemen iptal edip yenisini oluşturun.
- İlk çalıştırmalarda mutlaka `--limit 1` ve `--limit 10` kullanın.
- Yapay görselleri fiziksel ürünle karşılaştırmadan satış kataloğuna taşımayın.
- Ürün ve marka görsellerini kullanmak için gerekli haklara sahip olduğunuzdan emin olun.

Resmi belgeler: [görsel üretme](https://ai.google.dev/gemini-api/docs/image-generation), [Batch API](https://ai.google.dev/gemini-api/docs/batch-api), [fiyatlandırma](https://ai.google.dev/gemini-api/docs/pricing).
