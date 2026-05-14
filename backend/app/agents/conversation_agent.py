from app.agents.base_agent import BaseAgent

# ── System prompt ────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Sen FinShop AI'sın — kullanıcının kişisel finansal alışveriş asistanısın.

KİŞİLİĞİN:
- Samimi, sıcak ve arkadaş canlısısın; robot gibi değil, gerçek bir arkadaş gibi konuşursun
- Türkçe'de günlük dil kullan, resmi olmayan ama saygılı bir ton
- Mizahı seversin ama yerinde kullanırsın
- Yargılamadan, destekleyerek yaklaşırsın
- Kullanıcının adını biliyorsan kullan ("Enes, şöyle yapabilirsin...")

NASIL CEVAP VERMELİSİN:

1. SOHBET (selam, naber, teşekkür, vb.) ise:
   - Doğal, kısa ve sıcak yanıt ver
   - ÖNERİ SUNMA — sadece sohbet et
   - Gerekirse açık uçlu soru sor

2. DUYGUSAL İFADE varsa:
   - Önce duyguyu kabul et ("Anlıyorum, zor olabiliyor")
   - Sonra yavaşça yardım öner

3. ÜRÜN / ALIŞVERİŞ isteği ise:
   - is_product_request: true döndür

KAÇINMAN GEREKEN İFADELER:
- "Önerebileceğim başka bir şey var mı?" (her mesajda otomatik)
- "Size nasıl yardımcı olabilirim?" (selamlamaya otomatik tepki)
- Özellik listesi dökmek
- "Ben bir yapay zekayım, duygularım yok" — bunu ASLA söyleme

JSON cevap formatı:
{
  "is_product_request": true/false,
  "reply": "sohbetse veya duygusal ifadeyse kısa samimi yanıt"
}
"""

# ── Keyword tabanlı hızlı sınıflandırıcı ────────────────────────────────────
PRODUCT_KEYWORDS = [
    "öner", "arıyorum", "bul", "istiyorum", "almak", "satın", "hediye",
    "ucuz", "fiyat", "ürün", "laptop", "telefon", "bilgisayar", "kulaklık",
    "kamera", "tablet", "saat", "ayakkabı", "giysi", "giyim", "kitap", "oyun",
    "tl", "lira", "bütçe", "indirim", "kampanya", "sipariş", "alabil",
    "tavsiye", "öneri", "seçenek", "model", "marka", "fiyatı ne",
]

# Bunlar varsa kesinlikle sohbet — ürün isteği değil
SMALL_TALK_PATTERNS = [
    "selam", "merhaba", "naber", "nasılsın", "nasilsin", "ne haber",
    "teşekkür", "tesekkur", "sağol", "sagol", "eyvallah", "tamam", "ok",
    "görüşürüz", "gorusuruz", "iyi geceler", "iyi günler", "günaydın",
    "gunaydin", "iyi akşamlar", "bay bay", "hoşça kal",
    "kimsin", "ne yapabilirsin", "nasıl çalışıyorsun",
    "harika", "süper", "çok güzel", "anladım", "evet", "hayır",
    "peki", "tamamdır", "oldu", "biliyorum",
]

EMOTIONAL_PATTERNS = [
    "param yetmiyor", "borcum var", "para sıkıntısı", "hiç param",
    "para kalmadı", "zor durum", "sıkıntı", "üzgün", "moralim",
    "gereksiz harcıyorum", "israf", "pişman",
]


def _classify_intent(message: str) -> str:
    """
    Hızlı keyword tabanlı intent sınıflandırıcı.
    Dönüş değerleri: 'small_talk' | 'product' | 'emotional' | 'unknown'
    """
    lower = message.lower().strip()

    # Çok kısa tek kelime/harf — kesinlikle sohbet
    if len(lower) <= 3:
        return "small_talk"

    # Small talk — kısa mesaj + anahtar kelime
    if len(lower) < 50 and any(p in lower for p in SMALL_TALK_PATTERNS):
        return "small_talk"

    # Duygusal ifade
    if any(p in lower for p in EMOTIONAL_PATTERNS):
        return "emotional"

    # Ürün isteği
    if any(kw in lower for kw in PRODUCT_KEYWORDS):
        return "product"

    return "unknown"


class ConversationAgent(BaseAgent):
    def __init__(self, llm, db):
        super().__init__("conversation_agent", llm, db)

    async def execute(self, input_data: dict) -> dict:
        """
        input_data:
            message: str
            chat_history: list (opsiyonel, bağlam için)

        Returns:
            is_product_request: bool
            reply: str | None
        """
        message = input_data.get("message", "")
        history = input_data.get("chat_history", [])

        intent = _classify_intent(message)

        # ── Small talk — LLM'e geç ama ürün isteği değil ──────────────────
        if intent == "small_talk":
            try:
                history_text = self._format_history(history)
                prompt = f"""{history_text}Kullanıcı: "{message}"

Bu kesinlikle bir sohbet mesajı, ürün isteği değil. Samimi ve kısa yanıt ver.
JSON: {{"is_product_request": false, "reply": "yanıtın"}}"""
                result = await self.call_llm_json(prompt, system=SYSTEM_PROMPT)
                return {
                    "is_product_request": False,
                    "reply": result.get("reply") or "😊",
                }
            except Exception:
                return {"is_product_request": False, "reply": "😊"}

        # ── Duygusal ifade ─────────────────────────────────────────────────
        if intent == "emotional":
            try:
                history_text = self._format_history(history)
                prompt = f"""{history_text}Kullanıcı: "{message}"

Kullanıcı duygusal bir şey ifade etti. Önce empati kur, sonra hafifçe yardım öner.
JSON: {{"is_product_request": false, "reply": "empatik yanıtın"}}"""
                result = await self.call_llm_json(prompt, system=SYSTEM_PROMPT)
                return {
                    "is_product_request": False,
                    "reply": result.get("reply") or "Anlıyorum, zor olabiliyor. Birlikte bir bakalım mı?",
                }
            except Exception:
                return {
                    "is_product_request": False,
                    "reply": "Anlıyorum, zor olabiliyor. Birlikte bir bakalım mı?",
                }

        # ── Açık ürün isteği ──────────────────────────────────────────────
        if intent == "product":
            return {"is_product_request": True, "reply": None}

        # ── Belirsiz — LLM ile karar ver ──────────────────────────────────
        try:
            history_text = self._format_history(history)
            prompt = f"""{history_text}Kullanıcı: "{message}"

Bu mesaj ürün/alışveriş isteği mi, yoksa sohbet mi? Emin değilsen sohbet say.
JSON: {{"is_product_request": true/false, "reply": "sohbetse yanıtın, ürün isteğiyse null"}}"""
            result = await self.call_llm_json(prompt, system=SYSTEM_PROMPT)
            return {
                "is_product_request": result.get("is_product_request", False),
                "reply": result.get("reply"),
            }
        except Exception:
            # Fallback: belirsizde sohbet olarak davran
            return {
                "is_product_request": False,
                "reply": "Bir şey mi takıldı? Yardım etmemi istediğin bir konu var mı?",
            }

    def _format_history(self, history: list) -> str:
        """Son 4 mesajı prompt için formatlar."""
        if not history:
            return ""
        recent = history[-4:]
        lines = "\n".join(
            f"{'Kullanıcı' if h.get('role') == 'user' else 'Asistan'}: {h.get('message', '')}"
            for h in recent
        )
        return f"Önceki sohbet:\n{lines}\n\n"
