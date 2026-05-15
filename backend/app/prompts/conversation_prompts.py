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

INTENT_CLASSIFICATION_PROMPT = """Önceki sohbet bağlamı (eski → yeni):
{history_text}

Kullanıcının son mesajı: "{message}"

ÇOK ÖNEMLİ BAĞLAM KURALLARI:
1. Eğer önceki asistan mesajlarında "[Önerilen ürünler: ...]" varsa, bu bir ÜRÜN ARAMA bağlamıdır.
   Kullanıcının son mesajı kısa bir düzeltme/ek bilgi gibi görünüyorsa (örn: "ben erkeğim",
   "ben kadınım", "daha ucuz", "başka", "siyah olsun", "42 numara", "beğenmedim") bunu
   PRODUCT_SEARCH olarak işaretle ve extracted_query'i önceki arama sorgusu + yeni bilgiyi
   birleştirerek üret.
   Örnek: önceki "kadın pantolon" + son mesaj "ben erkeğim" → extracted_query: "erkek pantolon"
2. "teşekkür ederim", "sağ ol" gibi mesajlarda intent CHITCHAT olur. ASLA jenerik "nasıl
   yardımcı olabilirim?" deme — eğer önceki bağlamda ürün önerildiyse, ürünler hakkında
   bağlamlı yanıt ver: "Rica ederim! Beğendiğin oldu mu? Detayını sorabilirsin."
3. Geçmişte ürün önerildiyse ve kullanıcı yeni bir ürün adı söylemiyorsa, intent büyük
   ihtimalle PRODUCT_SEARCH'tür (refinement). CHITCHAT'e koşma.

JSON formatında yanıt ver (BAŞKA HİÇBİR ŞEY YAZMA):
{{
  "intent": "PRODUCT_SEARCH|COMPARISON|BUDGET_QUERY|COMPLAINT|GREETING|CHITCHAT",
  "confidence": 0.0-1.0 arası float,
  "reply": "CHITCHAT/GREETING/COMPLAINT/BUDGET_QUERY ise kısa samimi yanıt (bağlamı dikkate al!); PRODUCT_SEARCH/COMPARISON ise null",
  "comparison_products": ["ürün1", "ürün2"] veya [],
  "extracted_query": "PRODUCT_SEARCH/COMPARISON ise temizlenmiş arama sorgusu, diğerleri için null"
}}

Örnekler:
- "merhaba" → intent: GREETING, confidence: 0.99
- "teşekkürler" (ürün bağlamı YOK) → intent: CHITCHAT, reply: "Rica ederim! 😊", confidence: 0.98
- "teşekkürler" (önceki: [Önerilen ürünler: X, Y, Z]) → intent: CHITCHAT,
  reply: "Rica ederim! Beğendiğin oldu mu? Detayını sormak istediğin bir ürün varsa söyle.", confidence: 0.95
- "ben erkeğim" (önceki: kadın pantolon önerilmiş) → intent: PRODUCT_SEARCH,
  extracted_query: "erkek pantolon", reply: null, confidence: 0.9
- "daha ucuz olsun" (önceki: laptop önerilmiş) → intent: PRODUCT_SEARCH,
  extracted_query: "ucuz laptop", reply: null, confidence: 0.9
- "iPhone 15 mi Galaxy S24 mü alsam" → intent: COMPARISON, confidence: 0.95
- "bütçem yeterli mi?" → intent: BUDGET_QUERY, confidence: 0.9
- "laptop arıyorum 10000 TL" → intent: PRODUCT_SEARCH, confidence: 0.97
- "bu öneri berbat" → intent: COMPLAINT, confidence: 0.88"""

# ── Hızlı Yanıtlar (LLM çağırmadan) ────────────────────────────────────────
QUICK_REPLIES = {
    "selamlama": [
        "Selam! Bugün ne arıyoruz? 🛍️",
        "Hey! Hoş geldin, anlat bakalım.",
        "Selam! Sana nasıl yardımcı olabilirim?",
        "Selam dostum! Hayırlı bir şey mi var?",
        "Merhaba! Bütçene uygun harika ürünler bulmaya hazırım.",
    ],
    "tesekkur": [
        "Ne demek, kolay gelsin! 😊",
        "Rica ederim! İhtiyacın olursa yine buradayım.",
        "Bir şey değil! Aradığın başka bir şey olursa söyle yeter.",
    ],
    "evet": [
        "Harika! Devam edelim 😊",
        "Anladım, ilerleyelim!",
        "Süper, hemen bakıyorum.",
    ],
    "hayir": [
        "Tamam, farklı bir şeye bakalım mı?",
        "Anladım! Başka nasıl yardımcı olabilirim?",
    ],
    "guzel": [
        "Ne güzel! 😊 Başka bir şey ister misin?",
        "Sevindim! Sorun olursa buradayım.",
    ],
}

# ── Budget Query Yanıt ────────────────────────────────────────────────────
BUDGET_QUERY_PROMPT = """Kullanıcının bütçe durumu:
{budget_info}

Kullanıcı soruyor: "{message}"

Sıcak, samimi bir arkadaş gibi yanıt ver. 2-3 cümle yeterli.

KURALLLAR:
- "spendable_after_savings", "spending_type", "risk_score" gibi teknik terimler KULLANMA
- Sayıları doğal dilde ver: "10.000 TL harcanabilir alanın var" gibi
- "Sağlıklı", "Zorlanıyor", "Kritik" yerine doğal ifadeler kullan
- Sonunda açık uçlu bir soru sor (opsiyonel)

ÖRNEK YANIT TARZI:
"Şu an iyi durumdasın! Bu ay yaklaşık 10.000 TL'lik bir alanın var ve gider oranın da düşük — bütçen sağlıklı. Bir şey almak mı düşünüyorsun?"

SADECE düz metin döndür, JSON değil."""

# ── Şikayet Yanıt ────────────────────────────────────────────────────────
COMPLAINT_REPLY_PROMPT = """Kullanıcı şikayet ediyor: "{message}"

Empati kur, kısa ve samimi özür dile, farklı bir arama veya yardım teklif et.
SADECE düz metin döndür, JSON değil."""
