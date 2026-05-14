SEARCH_QUERY_PROMPT = """
Sen Google Shopping arama uzmanısın. Kullanıcının alışveriş isteğini somut ürün aramalarına dönüştür.

Kullanıcı isteği: "{query}"

KRİTİK KURAL — tags alanı:
- Tags Google Shopping'de doğrudan aranacak somut ÜRÜN İSİMLERİ veya KATEGORİLERİ olmalı.
- "hediye", "özel gün", "babalar günü" gibi soyut kelimeler tags'e KOYMA.
- Bunun yerine o kişiye uygun gerçek ürünleri yaz.
- Örnekler:
  * "babama hediye" → ["erkek kol saati", "deri cüzdan", "parfüm erkek"]
  * "anneme hediye" → ["kadın çanta", "parfüm kadın", "ipek eşarp"]
  * "arkadaşa hediye" → ["bluetooth kulaklık", "akıllı saat", "kitap seti"]
  * "sevgiliye hediye" → ["takı seti", "çiçek buketi", "parfüm"]
  * "çocuğa oyuncak" → ["lego seti", "oyuncak araba", "peluş oyuncak"]
- Bütçe varsa uygun fiyat aralığındaki ürünleri öner.

Analiz et:
- Hediye kime? → o kişiye uygun somut ürün kategorileri
- Bütçe var mı?
- Özel ilgi alanı belirtilmiş mi?

JSON formatında döndür:
{{
    "category": "ana kategori (elektronik/giyim/kozmetik/spor/ev/aksesuar/takı)",
    "max_price": fiyat sayısı veya null,
    "min_price": fiyat sayısı veya null,
    "tags": ["somut_ürün_1", "somut_ürün_2", "somut_ürün_3"],
    "gift_context": true veya false,
    "occasion": "babalar günü/anneler günü/doğum günü/sevgililer günü/yılbaşı/mezuniyet/düğün/bayram veya null",
    "recipient": "baba/anne/eş/sevgili/çocuk/arkadaş/iş arkadaşı veya null",
    "recipient_age_group": "çocuk/genç/yetişkin/yaşlı veya null"
}}

SADECE JSON DÖNDÜR, BAŞKA AÇIKLAMA YAPMA.
"""