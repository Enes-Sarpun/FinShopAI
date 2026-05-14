"""
Conversation Agent — Geliştirilmiş Sürüm
Intent-aware conversation management:
  - PRODUCT_SEARCH  → Orchestrator'a yönlendir
  - COMPARISON      → Karşılaştırma modunda orchestrator
  - BUDGET_QUERY    → Bütçe bilgisini getir ve yanıtla
  - COMPLAINT       → Empati + yeniden deneme teklifi
  - GREETING        → Hızlı selamlama (LLM çağrısı yok)
  - CHITCHAT        → Hızlı yanıt veya kısa LLM çağrısı

execute() çıktısı:
  intent:            str (yukarıdaki sınıflardan biri)
  confidence:        float (0-1)
  is_product_request: bool (PRODUCT_SEARCH veya COMPARISON → True)
  is_comparison:     bool
  comparison_products: list[str]  (ürün isimleri, COMPARISON ise dolu)
  extracted_query:   str | None   (temizlenmiş arama sorgusu)
  reply:             str | None   (sohbet yanıtı; ürün isteğinde None)
"""

import time
import random
from app.agents.base_agent import BaseAgent
from app.prompts.conversation_prompts import (
    INTENT_SYSTEM,
    INTENT_CLASSIFICATION_PROMPT,
    QUICK_REPLIES,
    BUDGET_QUERY_PROMPT,
    COMPLAINT_REPLY_PROMPT,
)

# ── Ürün anahtar kelimeleri (hızlı kontrol için) ───────────────────────────
PRODUCT_KEYWORDS = [
    "öner", "arıyorum", "bul", "istiyorum", "almak", "satın", "hediye",
    "ucuz", "fiyat", "ürün", "laptop", "telefon", "bilgisayar", "kulaklık",
    "kamera", "tablet", "saat", "ayakkabı", "giysi", "kitap", "oyun",
    "tl", "lira", "bütçe", "indirim", "kampanya", "sipariş", "iade",
    "monitor", "klavye", "mouse", "mikrodalga", "çamaşır", "bulaşık",
    "tv", "televizyon", "koltuk", "masa", "sandalye", "yastık", "battaniye",
    "parfüm", "kozmetik", "makyaj", "bisiklet", "spor", "koşu", "fitness",
    "çanta", "cüzdan", "gözlük", "bileklik", "kolye", "yüzük",
]

COMPARISON_KEYWORDS = [
    "mı alsam", "mi alsam", "karşılaştır", "farkı ne", "hangisi daha",
    "hangisini", "arasında", "vs ", " vs", "veya", "yoksa", "mı yoksa",
    "mi yoksa", "mu yoksa", "mü yoksa",
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

GREETING_WORDS = {
    "merhaba", "selam", "günaydın", "iyi günler", "iyi akşamlar",
    "hey", "hi", "hello", "naber", "nasılsın", "nasıl gidiyor",
}

CHITCHAT_WORDS = {
    "teşekkür", "teşekkürler", "sağol", "sağ ol", "tamam", "ok", "okay",
    "evet", "hayır", "güzel", "süper", "harika", "iyi", "kötü", "anladım",
    "peki", "tabi", "tabii", "neden", "niçin", "niye", "nasıl",
}


def _is_single_emoji(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) <= 3 and not stripped.isascii()


def _quick_intent(message: str) -> str | None:
    """
    LLM çağrısı yapmadan hızlı intent tespiti.
    Belirsiz durumlarda None döner → LLM'e gönderilir.
    """
    lower = message.lower().strip()

    if _is_single_emoji(message):
        return "CHITCHAT"

    # Karşılaştırma kontrolü (product keywords'ten önce)
    if any(kw in lower for kw in COMPARISON_KEYWORDS):
        return "COMPARISON"

    # Selamlama (kısa mesajlarda)
    if len(lower) <= 25 and any(lower.startswith(g) or lower == g for g in GREETING_WORDS):
        return "GREETING"

    # Chitchat (kısa + bilinen kelimeler)
    if len(lower) <= 20 and any(cw in lower for cw in CHITCHAT_WORDS):
        return "CHITCHAT"

    # Ürün arama
    if any(kw in lower for kw in PRODUCT_KEYWORDS):
        return "PRODUCT_SEARCH"

    # Uzun mesaj → LLM'e bırak
    return None


def _get_quick_reply(intent: str, message: str) -> str:
    """LLM çağırmadan anında yanıt üret."""
    lower = message.lower()

    if intent == "GREETING":
        return random.choice(QUICK_REPLIES["selamlama"])

    if intent == "CHITCHAT":
        if any(w in lower for w in ["teşekkür", "sağol", "sağ ol"]):
            return random.choice(QUICK_REPLIES["tesekkur"])
        if lower.strip() in {"evet", "e", "ok", "okay", "tabi", "tabii"}:
            return random.choice(QUICK_REPLIES["evet"])
        if lower.strip() in {"hayır", "h", "yok"}:
            return random.choice(QUICK_REPLIES["hayir"])
        if lower.strip() in {"güzel", "süper", "harika", "iyi"}:
            return random.choice(QUICK_REPLIES["guzel"])
        return "Anlıyorum 😊 Başka bir konuda yardımcı olabilir miyim?"

    return "Başka bir konuda yardımcı olabilir miyim?"
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
        Parametreler:
            message:      str
            chat_history: list (opsiyonel)
            budget_info:  dict (opsiyonel — BUDGET_QUERY için)

        Döndürür:
            intent, confidence, is_product_request, is_comparison,
            comparison_products, extracted_query, reply
        """
        t0 = time.monotonic()
        message = input_data.get("message", "").strip()
        history = input_data.get("chat_history", [])
        budget_info = input_data.get("budget_info")  # Opsiyonel

        if not message:
            return self._build_result("CHITCHAT", 1.0, "Ne sormak isterdiniz? 😊")

        # ── 1. Hızlı kural tabanlı intent tespiti ────────────────────────
        quick_intent = _quick_intent(message)

        if quick_intent in ("GREETING", "CHITCHAT"):
            reply = _get_quick_reply(quick_intent, message)
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(f"[conv] quick={quick_intent} | {elapsed:.0f}ms")
            return self._build_result(quick_intent, 0.95, reply)

        if quick_intent == "PRODUCT_SEARCH":
            # Ürün isteği kesin, LLM çağırma
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(f"[conv] quick=PRODUCT_SEARCH | {elapsed:.0f}ms")
            return self._build_result("PRODUCT_SEARCH", 0.9, None,
                                      extracted_query=message)

        # ── 2. LLM ile intent sınıflandırma ──────────────────────────────
        try:
            history_text = self._format_history(history, limit=8)
            prompt = INTENT_CLASSIFICATION_PROMPT.format(
                history_text=history_text or "(geçmiş yok)",
                message=message,
            )
            result = await self.call_llm_json(prompt, system=INTENT_SYSTEM)

            intent = result.get("intent", "CHITCHAT").upper()
            confidence = float(result.get("confidence", 0.5))
            reply = result.get("reply")
            comparison_products = result.get("comparison_products", [])
            extracted_query = result.get("extracted_query")

            # Güven düşükse CHITCHAT'e düşür
            if confidence < 0.45 and intent in ("PRODUCT_SEARCH", "COMPARISON"):
                intent = "CHITCHAT"
                reply = "Tam anlayamadım 😅 Ürün mü arıyorsunuz, yoksa başka bir konuda yardım mı istersiniz?"

        except Exception as e:
            self.logger.error(f"[conv] LLM error: {e}")
            # Fallback: keyword'e göre tahmin
            intent = "PRODUCT_SEARCH" if quick_intent == "PRODUCT_SEARCH" else "CHITCHAT"
            confidence = 0.6
            reply = None if intent == "PRODUCT_SEARCH" else "Anlıyorum! Nasıl yardımcı olabilirim?"
            comparison_products = []
            extracted_query = message if intent == "PRODUCT_SEARCH" else None

        # ── 3. BUDGET_QUERY özel işlemi ──────────────────────────────────
        if intent == "BUDGET_QUERY" and budget_info:
            try:
                budget_prompt = BUDGET_QUERY_PROMPT.format(
                    budget_info=str(budget_info),
                    message=message,
                )
                reply = await self.call_llm(budget_prompt)
            except Exception:
                reply = "Bütçe bilgilerinize şu an ulaşamıyorum. Daha sonra tekrar deneyin."

        # ── 4. COMPLAINT özel işlemi ──────────────────────────────────────
        if intent == "COMPLAINT":
            if not reply:
                try:
                    complaint_prompt = COMPLAINT_REPLY_PROMPT.format(message=message)
                    reply = await self.call_llm(complaint_prompt)
                except Exception:
                    reply = "Üzgünüm, yaşadığınız sorun için özür dilerim 🙏 Farklı bir arama yapmamı ister misiniz?"

        elapsed = (time.monotonic() - t0) * 1000
        self.logger.info(
            f"[conv] intent={intent} confidence={confidence:.2f} | {elapsed:.0f}ms"
        )

        return self._build_result(
            intent, confidence, reply,
            comparison_products=comparison_products,
            extracted_query=extracted_query,
        )

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def _format_history(self, history: list, limit: int = 8) -> str:
        if not history:
            return ""
        recent = history[-limit:]
        lines = []
        for h in recent:
            role = "Kullanıcı" if h.get("role") == "user" else "Asistan"
            msg = h.get("message", "")[:200]  # Çok uzun mesajları kırp
            lines.append(f"{role}: {msg}")
        return "\n".join(lines)

    def _build_result(
        self,
        intent: str,
        confidence: float,
        reply: str | None,
        *,
        comparison_products: list = None,
        extracted_query: str | None = None,
    ) -> dict:
        is_product = intent in ("PRODUCT_SEARCH", "COMPARISON")
        return {
            "intent": intent,
            "confidence": round(confidence, 3),
            "is_product_request": is_product,
            "is_comparison": intent == "COMPARISON",
            "comparison_products": comparison_products or [],
            "extracted_query": extracted_query,
            "reply": reply,
        }
