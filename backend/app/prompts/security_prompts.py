CONTENT_MODERATION_PROMPT = """
Sen bir içerik moderasyon uzmanısın. Aşağıdaki metni analiz et.

Metin: "{content}"
Kullanıcı ID: {user_id}
İçerik Tipi: {content_type}

Aşağıdaki kurallara göre değerlendir:
1. Küfür, hakaret, argo içeriyor mu?
2. Nefret söylemi var mı?
3. Spam veya reklam içeriyor mu?
4. Kişisel bilgi (telefon, adres, TC kimlik) paylaşılıyor mu?
5. Tehdit veya taciz var mı?
6. Sahte yorum veya manipülasyon var mı?
7. XSS veya injection saldırısı girişimi var mı?

JSON formatında döndür:
{{
    "is_safe": true veya false,
    "risk_level": "low/medium/high/critical",
    "violations": ["ihlal1", "ihlal2"],
    "action": "allow/warn/block/ban",
    "clean_content": "temizlenmiş metin veya null",
    "reason": "karar açıklaması",
    "is_spam": true veya false,
    "is_fake_review": true veya false,
    "has_personal_info": true veya false,
    "has_injection": true veya false
}}

SADECE JSON DÖNDÜR.
"""

BANNED_WORDS_CHECK_PROMPT = """
Aşağıdaki metinde Türkçe küfür, hakaret, argo veya uygunsuz kelimeler var mı?

Metin: "{content}"

JSON formatında döndür:
{{
    "has_banned_words": true veya false,
    "found_words": ["kelime1", "kelime2"],
    "censored_content": "yıldızlanmış hali",
    "severity": "low/medium/high"
}}

SADECE JSON DÖNDÜR.
"""

FAKE_REVIEW_DETECTION_PROMPT = """
Aşağıdaki yorumu analiz et ve sahte/manipüle edilmiş olup olmadığını tespit et.

Yorum: "{content}"
Kullanıcının daha önce attığı yorum sayısı: {review_count}
Puan: {rating}

Sahte yorum belirtileri:
- Aşırı genel ve klişe ifadeler
- Ürünle alakasız içerik
- Çok kısa veya anlamsız metin
- Rakip ürünlere saldırı
- Aşırı övgü veya aşırı yergi

JSON formatında döndür:
{{
    "is_fake": true veya false,
    "confidence": 0.0 ile 1.0 arası,
    "reasons": ["sebep1", "sebep2"],
    "action": "allow/flag/remove"
}}

SADECE JSON DÖNDÜR.
"""

RATE_LIMIT_PROMPT = """
Kullanıcının davranışını analiz et ve şüpheli aktivite var mı tespit et.

Kullanıcı ID: {user_id}
Son 1 saatteki işlem sayısı: {action_count}
İşlem tipi: {action_type}
IP adresi: {ip_address}

JSON formatında döndür:
{{
    "is_suspicious": true veya false,
    "risk_level": "low/medium/high/critical",
    "action": "allow/throttle/block/ban",
    "reason": "açıklama"
}}

SADECE JSON DÖNDÜR.
"""