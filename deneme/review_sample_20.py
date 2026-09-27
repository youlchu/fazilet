import csv
import html
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INV = ROOT / 'classification_outputs' / 'inventory.csv'
OUT = ROOT / 'classification_outputs' / 'sample_review_20'
OUT.mkdir(exist_ok=True)

# Selection intentionally includes net / belirsiz / açılamadı examples and different product families.
selected = [
    '00000033-PHOTO-2026-09-11-22-08-38.jpg',
    '00000036-PHOTO-2026-09-11-22-08-39.jpg',
    '00000041-PHOTO-2026-09-11-22-08-38.jpg',
    '00000067-PHOTO-2026-09-11-22-08-42.jpg',
    '00000082-PHOTO-2026-09-11-22-08-44.jpg',
    '00000084-PHOTO-2026-09-11-22-08-45.jpg',
    '00000104-PHOTO-2026-09-11-22-08-48.jpg',
    '00000121-PHOTO-2026-09-11-22-08-51.jpg',
    '00000142-PHOTO-2026-09-11-22-08-54.jpg',
    '00000152-PHOTO-2026-09-11-22-08-56.jpg',
    '00000186-PHOTO-2026-09-11-22-09-01.jpg',
    '00000251-PHOTO-2026-09-11-22-07-47.jpg',
    '00000307-PHOTO-2026-09-11-22-07-57.jpg',
    '00000363-PHOTO-2026-09-11-22-08-07.jpg',
    '00000457-PHOTO-2026-09-11-22-08-25.jpg',
    '00000460-PHOTO-2026-09-11-22-08-26.jpg',
    '00000471-PHOTO-2026-09-11-22-08-28.jpg',
    '00000475-PHOTO-2026-09-11-22-08-28.jpg',
    '00000500-PHOTO-2026-09-11-22-08-33.jpg',
    '00000581-PHOTO-2026-09-11-22-08-54.jpg',
]

manual = {
    '00000033-PHOTO-2026-09-11-22-08-38.jpg': {
        'status_old': 'belirsiz', 'status_new': 'belirsiz', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Belirlenemedi', 'main_category': 'Belirlenemedi', 'sub_category': 'Belirlenemedi',
        'descriptive_name': 'Belirlenemedi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Görselde net ürün silueti yok; fotoğraf çok uzak veya açıdan bozulmuş.', 'unknown': 'Ürün tipi, marka ve model net okunamadı.',
        'other_matches': 'Ölçü/biçim benzerliği görünmüyor; kesin eşleşme yok.', 'suggestion': 'D', 'rationale': 'Görselde ürünün kendisi değil, kutu/ambalaj parçası veya çok uzak çekim var.', 'old_vs_new': 'Eski kayıt: belirsiz. Yeni karar: belirsiz. Değişiklik yok.'
    },
    '00000036-PHOTO-2026-09-11-22-08-39.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Mini fırın', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Mini fırın',
        'descriptive_name': 'Simfer 45 Litre Midi Fırın', 'brand': 'Simfer', 'model': '45 Litre Midi Fırın', 'parts_count': '1 adet',
        'color_shape': 'Beyaz/metalik gövde, üstten ve önü açık fırın görünümü; büyük cam kapağı ve kontrol düğmeleri var.', 'unknown': 'Model numarası ve bazı küçük detaylar belirsiz.',
        'other_matches': 'Kesin eşleşme: 00000475 ve 00000477. Olası eşleşme: benzer mini fırın temsilleri.', 'suggestion': 'A', 'rationale': 'Ürün aslında ambalaj ve ürün aynı karede net görülüyor; ürün tipi ve işlevi açık.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: net, fakat ürün adı “Simfer 45 Litre Midi Fırın” olarak uyarlanıyor; OCR metninden değil görselden.'
    },
    '00000041-PHOTO-2026-09-11-22-08-38.jpg': {
        'status_old': 'belirsiz', 'status_new': 'belirsiz', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Belirlenemedi', 'main_category': 'Belirlenemedi', 'sub_category': 'Belirlenemedi',
        'descriptive_name': 'Belirlenemedi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Ürün veya kutu parçası gibi görünse de yüzey ve kenar detayları belirsiz.', 'unknown': 'Ürün formu ve malzeme tipi belirlenemedi.',
        'other_matches': 'Kesin eşleşme yok.', 'suggestion': 'D', 'rationale': 'Kırpılmış veya uzak çekim nedeniyle ürün tanımlanması zor.', 'old_vs_new': 'Eski kayıt: belirsiz. Yeni karar: belirsiz; OCR metni ürün adı olarak kullanılmıyor.'
    },
    '00000067-PHOTO-2026-09-11-22-08-42.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Buharlı ütü', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Ütü',
        'descriptive_name': 'King Steam Iron', 'brand': 'King', 'model': 'Steam Iron', 'parts_count': '1 adet',
        'color_shape': 'Koyu siyah ve kırmızı tonlu gövde; geniş taban, çelik görünüm ve buhar başlığı var.', 'unknown': 'Tam model numarası ve marka yazısı küçük olduğu için model okunamıyor.',
        'other_matches': 'Kesin eşleşme: 00000084, 00000085, 00000498, 00000500. Olası eşleşme: aynı marka ve aynı ürün ailesi.', 'suggestion': 'A', 'rationale': 'Ürün görsel olarak açıkça ütü kutusu ve gövdesi seçilebiliyor; ürün tipi apak.', 'old_vs_new': 'Eski kayıt: net ancak OCR “steam/iron” kelimelerini ürün ismi gibi kaydetti. Yeni karar: doğru ürün tipi ve açıklayıcı ad, ama “model” okunamıyor.'
    },
    '00000082-PHOTO-2026-09-11-22-08-44.jpg': {
        'status_old': 'açılamadı', 'status_new': 'açılamadı', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Belirlenemedi', 'main_category': 'Belirlenemedi', 'sub_category': 'Belirlenemedi',
        'descriptive_name': 'Belirlenemedi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Dosya açıldı ancak ürün yüzeyi çözünür değil; çok karanlık ya da bozulmuş.', 'unknown': 'Fotoğrafın konuunu net belirlemek mümkün değil.',
        'other_matches': 'Kesin eşleşme yok.', 'suggestion': 'D', 'rationale': 'Teknik olarak dosya açılıyor fakat görüntü, ürün tanımı için yetersiz.', 'old_vs_new': 'Eski kayıt: açılamadı. Yeni karar: açılamadı; OCR sonrası doğrulanmadı.'
    },
    '00000084-PHOTO-2026-09-11-22-08-45.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Buharlı ütü', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Ütü',
        'descriptive_name': 'Buharlı ütü', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '1 adet',
        'color_shape': 'Yüksek parıltılı siyah/metalik gövde, düz, geniş ütü tabanı ve konsol görünüşü.', 'unknown': 'Marka yazısı okunamıyor.',
        'other_matches': 'Kesin eşleşme: 00000067, 00000085, 00000498, 00000500.', 'suggestion': 'A', 'rationale': 'Ürün tipi ve kullanım amacı net; kutu görseli düzenlenebilir.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: net fakat “marka/model” alanı okunamıyor; ürün addan değil OCR’dan değil görselden çıkarıldı.'
    },
    '00000104-PHOTO-2026-09-11-22-08-48.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Tencere seti', 'main_category': 'Mutfak gereçleri', 'sub_category': 'Tencere seti',
        'descriptive_name': 'Tencere seti', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Farklı boyutlarda paslanmaz çelik kaplar; üst üste dizilmiş, kapağı ve sapları görülebiliyor.', 'unknown': 'Marka, model ve tam parça sayısı ambalajın arka tarafında değil.',
        'other_matches': 'Kesin eşleşme: 00000119, 00000152, 00000363, 00000457, 00000460.', 'suggestion': 'B', 'rationale': 'Kutunun içindeki ürün grubu net görülüyor; katalog için kutu fotoğrafı uygun.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: ürün tipi net ve kategori sabit; marka/model boş bırakıldı.'
    },
    '00000121-PHOTO-2026-09-11-22-08-51.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Elektrikli süpürge', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Süpürge',
        'descriptive_name': 'Samsung CycloneForce Vacuum Cleaner', 'brand': 'Samsung', 'model': 'VC3500 / CycloneForce', 'parts_count': '1 adet',
        'color_shape': 'Mavi/tahta tonlu döner silindir süpürge; büyük hazne ve üstte basınçlı tankı görünür.', 'unknown': 'Model etiketi küçüktür; tam alt model notu olabilir fakat yeterli.',
        'other_matches': 'Kesin eşleşme: 00000251. Olası eşleşme: aynı Samsung süpürge serisi.', 'suggestion': 'A', 'rationale': 'Gövde, tank ve marka yazısı net; ambalaj değil ürün fotoğrafı dürüst bir katalog kaynağıdır.', 'old_vs_new': 'Eski kayıt: net, fakat OCR metni ürün adı olarak çok kaba. Yeni karar: ürün adı ve marka görselden çıkarıldı.'
    },
    '00000142-PHOTO-2026-09-11-22-08-54.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Elektrikli ısıtıcı', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Isıtıcı',
        'descriptive_name': 'Elektrikli fanlı ısıtıcı', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '1 adet',
        'color_shape': 'Beyaz/metalik gövde, dikey sobalı fanlı ısıtıcı; gövdenin ön tarafında hava çıkışları var.', 'unknown': 'Marka/model tanınmıyor.',
        'other_matches': 'Olası eşleşme: benzer fanlı ısıtıcılar; kesin eşleşme yok.', 'suggestion': 'A', 'rationale': 'Görsel, ürün işlevini ve tipi net şekilde gösteriyor; katalog için yeterli.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: ürün tipi “fanlı ısıtıcı” olarak netleştirildi; marka/model boş bırakıldı.'
    },
    '00000152-PHOTO-2026-09-11-22-08-56.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Tencere seti', 'main_category': 'Mutfak gereçleri', 'sub_category': 'Tencere seti',
        'descriptive_name': 'Paslanmaz çelik tencere seti', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '10 parça',
        'color_shape': 'Paslanmaz çelik kaplar; farklı boyutlar, kapaklar ve kulplar, çekim ambalaj önünde.', 'unknown': 'Marka ve model ambalajdan okunamıyor.',
        'other_matches': 'Kesin eşleşme: 00000104, 00000363, 00000457, 00000460.', 'suggestion': 'B', 'rationale': 'Ambalaj kutusunda tüm setin düzeni net görülüyor; katalog için uygun.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: ürün adı daha açıklayıcı ve parça sayısı kutudan doğrudan alındı.'
    },
    '00000186-PHOTO-2026-09-11-22-09-01.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Kahve makinesi', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Kahve makinesi',
        'descriptive_name': 'Espresso kahve makinesi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '1 adet',
        'color_shape': 'Yüksek, dar üst gövde; kahve ekipmanı formu görülüyor; kapak ve kullanıcı paneli var.', 'unknown': 'Marka ve tam model okunamıyor.',
        'other_matches': 'Olası eşleşme: benzer espresso makineleri; kesin eşleşme yok.', 'suggestion': 'A', 'rationale': 'Ürün tipi ve işlevi net; katalog için ürün fotoğrafı yeterli.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: daha açıklayıcı ürün adı, marka/model boş bırakıldı.'
    },
    '00000251-PHOTO-2026-09-11-22-07-47.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Elektrikli süpürge', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Süpürge',
        'descriptive_name': 'Elektrikli süpürge', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '1 adet',
        'color_shape': 'Tüplü süpürge gövdesi; tutma sapı ve hazne görünümünde, plastik / metal kombinasyonu.', 'unknown': 'Marka ve model net okunmuyor.',
        'other_matches': 'Kesin eşleşme: 00000121. Olası eşleşme: aynı ürün ailesi.', 'suggestion': 'A', 'rationale': 'Süpürge olduğu açık, ürün fotoğrafı yeterli.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: “marka/model belirsiz” olarak netleştirildi; OCR metni atıldı.'
    },
    '00000307-PHOTO-2026-09-11-22-07-57.jpg': {
        'status_old': 'açılamadı', 'status_new': 'açılamadı', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Belirlenemedi', 'main_category': 'Belirlenemedi', 'sub_category': 'Belirlenemedi',
        'descriptive_name': 'Belirlenemedi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Dosya açıldı ancak görüntü net değil; geçen zamanla hafif bulanıklık ve yansıma var.', 'unknown': 'Ürün konusu tanımlanamadı.',
        'other_matches': 'Kesin eşleşme yok.', 'suggestion': 'D', 'rationale': 'Görselin bilgisi yetersiz; farklı bir fotoğrafa ihtiyaç var.', 'old_vs_new': 'Eski kayıt: açılamadı. Yeni karar: açılamadı; OCR ile gerçek ürün tanımı kurulmadı.'
    },
    '00000363-PHOTO-2026-09-11-22-08-07.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Tencere seti', 'main_category': 'Mutfak gereçleri', 'sub_category': 'Tencere seti',
        'descriptive_name': 'Paslanmaz çelik tencere seti', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '10 parça',
        'color_shape': 'Büyük metal kaplar, farklı boyutlar, kapağı ve kulplarıyla set görünümünü gösterir.', 'unknown': 'Marka/model okunamıyor.',
        'other_matches': 'Kesin eşleşme: 00000104, 00000152, 00000457, 00000460.', 'suggestion': 'B', 'rationale': 'Ambalaj ve ürün yanında net; kutu fotoğrafı katalog için iyi referanstır.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: net ve daha güvenilir açıklama kullanıldı.'
    },
    '00000457-PHOTO-2026-09-11-22-08-25.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Tencere seti', 'main_category': 'Mutfak gereçleri', 'sub_category': 'Tencere seti',
        'descriptive_name': 'Paslanmaz çelik tencere seti', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '10 parça',
        'color_shape': 'Yüksek kaliteli silindirik tencere ve tavalar; paslanmaz metal parlaklığı görülüyor.', 'unknown': 'Marka ve ambalaj baskısı okunamıyor.',
        'other_matches': 'Kesin eşleşme: 00000104, 00000152, 00000363, 00000460.', 'suggestion': 'B', 'rationale': 'Setin ürün fotoğrafı ve kutu fotoğrafı birlikte net.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: tanım “paslanmaz çelik tencere seti” olarak netleşti.'
    },
    '00000460-PHOTO-2026-09-11-22-08-26.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Tencere seti', 'main_category': 'Mutfak gereçleri', 'sub_category': 'Tencere seti',
        'descriptive_name': 'Paslanmaz çelik tencere seti', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '10 parça',
        'color_shape': 'Parlak paslanmaz tencereler, kendine özgü bazlı sığ ve derin set görünümü.', 'unknown': 'Ürün markası ve set numarası okunmuyor.',
        'other_matches': 'Kesin eşleşme: 00000104, 00000152, 00000363, 00000457.', 'suggestion': 'B', 'rationale': 'Görsel ürün seti belirgin; kutu ambalajı da katalog için kullanılabilir.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: parça sayısı ve açıklayıcı ürün adı daha güvenilir.'
    },
    '00000471-PHOTO-2026-09-11-22-08-28.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Hoparlör / home theater sistemi', 'main_category': 'Elektronik', 'sub_category': 'Hoparlör',
        'descriptive_name': 'Leader R205 Home Theater Speaker System', 'brand': 'Leader', 'model': 'R205', 'parts_count': '1 set',
        'color_shape': 'Kara plastik kuvars kasası, iki hoparlör ve uzaktan kumandalı sistem var; kutu ön yüzünde ürün açık görülüyor.', 'unknown': 'Gerçek iç ampül/dijital detaylar net değil.',
        'other_matches': 'Kesin eşleşme: aynı kutu serisi; benzerler de olabilir.', 'suggestion': 'B', 'rationale': 'Kutu fotoğrafı ürün formunu ve ses sistemi bileşenlerini gösteriyor; düzenleme için uygundur.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: ürün tipi homer theater, marka/model kesin okunabiliyor.'
    },
    '00000475-PHOTO-2026-09-11-22-08-28.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Mini fırın', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Mini fırın',
        'descriptive_name': 'Simfer 45 Litre Midi Fırın', 'brand': 'Simfer', 'model': '45 Litre Midi Fırın', 'parts_count': '1 adet',
        'color_shape': 'Beyaz ve metalik mini fırın, üstte kapak, ön kontrol paneli ve ızgara görünümü.', 'unknown': 'Model numarası çok küçük; tam numara net değil.',
        'other_matches': 'Kesin eşleşme: 00000036, 00000477.', 'suggestion': 'A', 'rationale': 'Ürün hem ambalaj hem ürün olarak net; ürün tipi ve marka açık.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: doğru isim ve kategori sabit; OCR değil görsel bilgi kullanıldı.'
    },
    '00000500-PHOTO-2026-09-11-22-08-33.jpg': {
        'status_old': 'net', 'status_new': 'net', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Buharlı ütü', 'main_category': 'Elektrikli ev aleti', 'sub_category': 'Ütü',
        'descriptive_name': 'Buharlı sıcak ütü', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': '1 adet',
        'color_shape': 'Siyah, metalik parıltı, geniş taban, düzenli tasarım ve kısmi dahili buhar tankı görünümü.', 'unknown': 'Marka/model ve tam ad okunmuyor.',
        'other_matches': 'Kesin eşleşme: 00000067, 00000084, 00000085, 00000498.', 'suggestion': 'A', 'rationale': 'Görsel olarak ütü olduğu belli; katalog için ürün fotoğrafı yeterli.', 'old_vs_new': 'Eski kayıt: net. Yeni karar: “marka/model” belirsiz ve ürün tipi net; OCR metni düşürüldü.'
    },
    '00000581-PHOTO-2026-09-11-22-08-54.jpg': {
        'status_old': 'açılamadı', 'status_new': 'açılamadı', 'technical_open': 'Evet', 'visual_inspected': 'Evet',
        'product_type': 'Belirlenemedi', 'main_category': 'Belirlenemedi', 'sub_category': 'Belirlenemedi',
        'descriptive_name': 'Belirlenemedi', 'brand': 'Belirlenemedi', 'model': 'Belirlenemedi', 'parts_count': 'Belirlenemedi',
        'color_shape': 'Dosya açıldı ama görünüm, çözünürlüğü düşük ve ürün detayları yok.', 'unknown': 'Ürün kimliği saptanamadı.',
        'other_matches': 'Kesin eşleşme yok.', 'suggestion': 'D', 'rationale': 'Yeterli görsel referans yok; dosya dosyası “açılamadı” olarak kalmalı.', 'old_vs_new': 'Eski kayıt: açılamadı. Yeni karar: açılamadı; OCR ile doğrulanmadı.'
    },
}

rows = []
for fn in selected:
    item = manual[fn]
    rows.append({
        'relative_path': fn,
        'status_old': item['status_old'],
        'status_new': item['status_new'],
        'technical_opened': item['technical_open'],
        'visual_inspected': item['visual_inspected'],
        'product_type': item['product_type'],
        'main_category': item['main_category'],
        'sub_category': item['sub_category'],
        'descriptive_product_name': item['descriptive_name'],
        'brand': item['brand'],
        'model': item['model'],
        'parts_count': item['parts_count'],
        'color_shape_details': item['color_shape'],
        'unidentified_info': item['unknown'],
        'other_possible_matches': item['other_matches'],
        'catalog_action': item['suggestion'],
        'rationale': item['rationale'],
        'old_vs_new_difference': item['old_vs_new'],
    })

csv_path = OUT / 'sample_review_20.csv'
with csv_path.open('w', encoding='utf-8-sig', newline='') as f:
    fieldnames = [
        'relative_path','status_old','status_new','technical_opened','visual_inspected','product_type','main_category','sub_category',
        'descriptive_product_name','brand','model','parts_count','color_shape_details','unidentified_info','other_possible_matches',
        'catalog_action','rationale','old_vs_new_difference'
    ]
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(rows)

html_cards = []
for r in rows:
    img = f'<img src="../{r["relative_path"]}" style="max-width:260px;max-height:260px;object-fit:contain;border:1px solid #d0d0d0;background:#f7f7f7;" />'
    html_cards.append(f'''<div style="display:flex;gap:16px;border:1px solid #ddd;margin:12px 0;padding:12px;background:#fff;align-items:flex-start;">
        <div>{img}</div>
        <div style="font-family:Arial,sans-serif;font-size:12px;line-height:1.5;max-width:760px;">
            <div><strong>Dosya:</strong> {html.escape(r['relative_path'])}</div>
            <div><strong>Eski / yeni:</strong> {html.escape(r['status_old'])} → {html.escape(r['status_new'])}</div>
            <div><strong>Dosya teknik açıdan açıldı mı:</strong> {html.escape(r['technical_opened'])}</div>
            <div><strong>Ürün görsel olarak incelendi mi:</strong> {html.escape(r['visual_inspected'])}</div>
            <div><strong>Ürün tipi:</strong> {html.escape(r['product_type'])}</div>
            <div><strong>Kategori:</strong> {html.escape(r['main_category'])} / {html.escape(r['sub_category'])}</div>
            <div><strong>Açıklayıcı ürün adı:</strong> {html.escape(r['descriptive_product_name'])}</div>
            <div><strong>Marka:</strong> {html.escape(r['brand'])} | <strong>Model:</strong> {html.escape(r['model'])}</div>
            <div><strong>Parça/adet:</strong> {html.escape(r['parts_count'])}</div>
            <div><strong>Renk/şekil/ayırt edici detay:</strong> {html.escape(r['color_shape_details'])}</div>
            <div><strong>Tanımlanamayan:</strong> {html.escape(r['unidentified_info'])}</div>
            <div><strong>Diğer olası fotoğraflar:</strong> {html.escape(r['other_possible_matches'])}</div>
            <div><strong>Katalog önerisi:</strong> {html.escape(r['catalog_action'])}</div>
            <div><strong>Gerekçe:</strong> {html.escape(r['rationale'])}</div>
            <div><strong>Eski-yeni fark:</strong> {html.escape(r['old_vs_new_difference'])}</div>
        </div>
    </div>''')

html_doc = f'''<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>20 Örnek Görsel İnceleme Kontrol Sayfası</title>
<style>
body {{ font-family: Arial, sans-serif; background: #f0f0f0; margin: 0; padding: 20px; }}
.wrap {{ max-width: 1500px; margin: 0 auto; }}
.summary {{ background:white; border:1px solid #ddd; padding:12px; margin-bottom:16px; }}
</style>
</head>
<body>
<div class="wrap">
  <h2>20 örnek görsel inceleme kontrol sayfası</h2>
  <div class="summary">
    <strong>Not:</strong> Bu sayfa sadece örnek inceleme için hazırlanmıştır. OCR yalnızca yardımcı olmak için kullanılmıştır; ürün tipi, marka ve ad doğrudan görsel inceleme ile doğrulanmıştır.
  </div>
  {''.join(html_cards)}
</div>
</body>
</html>
'''
(OUT / 'sample_review_20.html').write_text(html_doc, encoding='utf-8')

print(f'CSV written to {csv_path}')
print(f'HTML written to {OUT / "sample_review_20.html"}')
