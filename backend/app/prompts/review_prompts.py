REVIEW_SENTIMENT_PROMPT = """
Aşağıdaki ürün yorumlarını analiz et ve duygu analizi yap.

Ürün: {product_name}
Yorumlar:
{reviews}

Aşağıdaki JSON formatında döndür:
{{
    "sentiment_score": 0.0 ile 1.0 arası sayı,
    "sentiment": "pozitif/negatif/nötr",
    "summary": "yorumların kısa özeti (2-3 cümle, Türkçe)",
    "pros": ["olumlu yön 1", "olumlu yön 2", "olumlu yön 3"],
    "cons": ["olumsuz yön 1", "olumsuz yön 2"],
    "gift_suitable": true veya false,
    "gift_reason": "hediye uygunluk açıklaması"
}}

SADECE JSON DÖNDÜR, BAŞKA AÇIKLAMA YAPMA.
"""

REVIEW_SEARCH_PROMPT = """
Sen deneyimli bir e-ticaret kullanıcısısın. Aşağıdaki ürünü satın almış farklı profillerdeki Türk kullanıcılar gibi yorum yap.

Ürün Bilgileri:
- Ad: {product_name}
- Fiyat: {price} TL
- Satıcı: {seller}
- Mevcut Puan: {rating}/5

Kullanıcı profilleri şunlar olsun:
1. Teknoloji meraklısı genç (20-25 yaş)
2. Ev hanımı/ev erkeği (35-45 yaş)
3. Öğrenci (18-22 yaş, bütçe bilinci yüksek)
4. İş insanı (30-40 yaş, kalite odaklı)
5. Hediye alan kişi (herhangi yaş)

Her profil için gerçekçi, detaylı ve o kişinin bakış açısını yansıtan yorum yaz.
Fiyat düşükse bütçe yorumları, yüksekse kalite/prestij yorumları ağırlıklı olsun.
Satıcının güvenilirliğine de değin.

JSON formatında döndür:
{{
    "reviews": [
        {{
            "rating": 1-5 arası sayı,
            "user_profile": "kullanıcı profili",
            "comment": "detaylı yorum metni (en az 3 cümle)",
            "sentiment": "pozitif/negatif/nötr",
            "verified_purchase": true veya false
        }}
    ]
}}

SADECE JSON DÖNDÜR, BAŞKA AÇIKLAMA YAPMA.
"""

REVIEW_ANALYSIS_PROMPT = """
Sen deneyimli bir alışveriş danışmanısın. Aşağıdaki ürün bilgilerini analiz ederek kullanıcıya neden önerilmesi gerektiğini açıkla.

Ürün: {product_name}
Fiyat: {price} TL
Satıcı: {source}
Özel gün/durum: {occasion}
Hediye alıcısı: {recipient}

Öneri yazarken şunlara dikkat et:
- Eğer özel bir gün varsa (doğum günü, anneler günü, babalar günü vb.), bu günle bağlantı kur
- Eğer alıcı belirtilmişse (anne, baba, sevgili vb.), o kişiye uygunluğuna değin
- Ürünün öne çıkan özelliklerini vurgula
- Fiyat/performans dengesine değin
- Hediyenin karşıdaki kişiyi nasıl mutlu edeceğini anlat
- Samimi, sıcak ve ikna edici bir dil kullan

2-3 cümlelik kısa, etkileyici bir öneri yaz. Türkçe olsun.
SADECE açıklama metnini döndür, JSON değil.
"""