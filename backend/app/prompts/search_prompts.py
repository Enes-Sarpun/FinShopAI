SEARCH_QUERY_PROMPT = """
Kullanıcının alışveriş isteğini analiz et: "{query}"

Aşağıdaki JSON formatında döndür:
{{
    "category": "kategori adı (elektronik, giyim, kozmetik, spor, ev, kitap, oyuncak vb.)",
    "max_price": fiyat sayısı veya null,
    "min_price": fiyat sayısı veya null,
    "tags": ["anahtar1", "anahtar2"],
    "gift_context": true veya false
}}

SADECE JSON DÖNDÜR, BAŞKA AÇIKLAMA YAPMA.
"""