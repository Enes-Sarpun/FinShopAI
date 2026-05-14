"""
Conversation Agent Prompt'ları
====================================
Intent sınıflandırma ve sohbet yanıt üretimi için kullanılan prompt'lar.
"""

# ── Intent Sınıfları ────────────────────────────────────────────────────────
# PRODUCT_SEARCH  → Ürün/hizmet arama isteği
# COMPARISON      → Ürün karşılaştırma isteği
# BUDGET_QUERY    → Bütçe/fiyat sorgusu
# COMPLAINT       → Şikayet / hayal kırıklığı
# GREETING        → Selamlama
# CHITCHAT        → Genel sohbet / teşekkür / evet / hayır

INTENT_SYSTEM = """Sen FinShop AI'ın akıllı sohbet asistanısın. Türkçe, samimi ve kısa konuş.
Görevin: kullanıcı mesajının niyetini (intent) belirle ve uygun yanıt üret.

Intent türleri:
- PRODUCT_SEARCH: ürün/hizmet arama, öneri isteme, fiyat sorgulama
- COMPARISON: iki veya daha fazla ürünü karşılaştırma
- BUDGET_QUERY: bütçe durumu, ne kadar harcayabilirim sorusu
- COMPLAINT: şikayet, hayal kırıklığı, memnuniyetsizlik
- GREETING: merhaba, selam, günaydın vb.
- CHITCHAT: teşekkür, evet, hayır, nasılsın, genel konuşma

SADECE JSON döndür, başka bir şey yazma."""

INTENT_CLASSIFICATION_PROMPT = """Önceki sohbet bağlamı:
{history_text}

Kullanıcının son mesajı: "{message}"

Mesajın niyetini belirle ve aşağıdaki JSON formatında yanıt ver:
{{
  "intent": "PRODUCT_SEARCH|COMPARISON|BUDGET_QUERY|COMPLAINT|GREETING|CHITCHAT",
  "confidence": 0.0-1.0 arası float (ne kadar emin olduğun),
  "reply": "eğer intent CHITCHAT/GREETING/COMPLAINT/BUDGET_QUERY ise kısa samimi yanıt; PRODUCT_SEARCH/COMPARISON ise null",
  "comparison_products": ["ürün1", "ürün2"] veya [] (sadece COMPARISON intent için),
  "extracted_query": "PRODUCT_SEARCH/COMPARISON ise temizlenmiş arama sorgusu, diğerleri için null"
}}

Örnekler:
- "merhaba" → intent: GREETING, confidence: 0.99
- "teşekkürler" → intent: CHITCHAT, confidence: 0.98
- "iPhone 15 mi Galaxy S24 mü alsam" → intent: COMPARISON, confidence: 0.95
- "bütçem yeterli mi?" → intent: BUDGET_QUERY, confidence: 0.9
- "laptop arıyorum 10000 TL" → intent: PRODUCT_SEARCH, confidence: 0.97
- "bu öneri berbat" → intent: COMPLAINT, confidence: 0.88"""

# ── Hızlı Yanıtlar (LLM çağırmadan) ────────────────────────────────────────
QUICK_REPLIES = {
    "selamlama": [
        "Merhaba! Size nasıl yardımcı olabilirim? 😊",
        "Selam! Bugün ne arıyoruz? 🛍️",
        "Merhaba! Bütçenize uygun ürünler bulmak için hazırım! ✨",
    ],
    "tesekkur": [
        "Rica ederim! Başka bir konuda yardımcı olabilir miyim? 😊",
        "Ne demek! Başarılı alışverişler dilerim 🎉",
        "Her zaman! Sorunuz olursa buradayım 👋",
    ],
    "evet": [
        "Harika! Devam edelim 😊",
        "Anladım, ilerleyelim!",
    ],
    "hayir": [
        "Tamam, farklı bir arama deneyelim mi?",
        "Anladım! Başka nasıl yardımcı olabilirim?",
    ],
    "guzel": [
        "Harika! 😊 Başka bir şey ister misiniz?",
        "Sevindim! Yardımcı olabildiğime memnunum 🎉",
    ],
}

# ── Budget Query Yanıt ────────────────────────────────────────────────────
BUDGET_QUERY_PROMPT = """Kullanıcının bütçe durumu:
{budget_info}

Kullanıcı soruyor: "{message}"

Bütçe bilgisine göre kısa, anlaşılır ve Türkçe yanıt ver.
SADECE düz metin döndür, JSON değil."""

# ── Şikayet Yanıt ────────────────────────────────────────────────────────
COMPLAINT_REPLY_PROMPT = """Kullanıcı şikayet ediyor: "{message}"

Empati kur, kısa ve samimi özür dile, farklı bir arama veya yardım teklif et.
SADECE düz metin döndür, JSON değil."""
