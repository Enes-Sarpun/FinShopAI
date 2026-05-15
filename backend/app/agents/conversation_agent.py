"""
Conversation Agent — v3 (Bağlam Farkındalığı)
Intent-aware conversation management with follow-up memory:
  - PRODUCT_SEARCH  → Orchestrator'a yönlendir
  - COMPARISON      → Karşılaştırma modunda orchestrator
  - BUDGET_QUERY    → Bütçe bilgisini getir ve yanıtla
  - COMPLAINT       → Empati + yeniden deneme teklifi
  - GREETING        → Hızlı selamlama (LLM çağrısı yok)
  - CHITCHAT        → Hızlı yanıt veya kısa LLM çağrısı
  - FOLLOW_UP       → Önceki ürün aramasını rafine et (v3)

v3 Değişiklikleri:
  - Sohbet bağlamı farkındalığı: önceki ürün önerileri hatırlanır
  - "Ben erkeğim" gibi takip mesajları önceki arama ile birleştirilir
  - "Teşekkürler" sonrası bağlamsal yanıt (ürün sonrası vs genel)
  - Enriched history: [N ürün bulundu] yerine gerçek ürün isimleri

execute() çıktısı:
  intent:            str (yukarıdaki sınıflardan biri)
  confidence:        float (0-1)
  is_product_request: bool (PRODUCT_SEARCH, COMPARISON veya FOLLOW_UP → True)
  is_comparison:     bool
  comparison_products: list[str]  (ürün isimleri, COMPARISON ise dolu)
  extracted_query:   str | None   (temizlenmiş arama sorgusu)
  reply:             str | None   (sohbet yanıtı; ürün isteğinde None)
"""

import time
import json
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

# ── v3: Takip mesajı anahtar kelimeleri ─────────────────────────────────────
REFINEMENT_KEYWORDS = [
    # Cinsiyet / kişi düzeltmeleri
    "erkeğim", "kadınım", "erkek", "kadın", "kız", "oğlan", "bay", "bayan",
    # Fiyat düzeltmeleri
    "daha ucuz", "daha pahalı", "daha uygun", "bütçem",
    # Tercih düzeltmeleri
    "başka", "farklı", "benzer", "alternatif", "başka bir",
    # Beğenmeme
    "beğenmedim", "olmaz", "istemem", "sevmedim", "hoşuma gitmedi",
    # Detay ekleme
    "ama ", "fakat", "ancak", "aslında",
    # Fiziksel özellikler
    "yaşında", "beden", "numara", "renk", "boyut",
    # Daha fazla bilgi
    "daha büyük", "daha küçük", "daha hafif", "daha kaliteli",
]

# ── v3: Ürün sonrası bağlamsal yanıtlar ─────────────────────────────────────
CONTEXTUAL_REPLIES = {
    "tesekkur": [
        "Rica ederim! 😊 Ürünlerden beğendiğin oldu mu?",
        "Ne demek! Beğendiğin bir şey varsa detay sorabilirssin.",
        "Rica ederim! Başka bir ürün aramamı ister misin?",
    ],
    "evet": [
        "Harika! Ürünlerden birini takip listene eklememi ister misin? ⭐",
        "Süper! Detayını görmek istediğin bir ürün var mı?",
    ],
    "hayir": [
        "Anladım! Farklı ürünler görmek ister misin? Ne tarz bir şey arıyorsun?",
        "Tamam! Başka kriterlere göre arayalım mı?",
    ],
    "guzel": [
        "Sevindim! 😊 Bir tanesini watchlist'e ekleyeyim mi?",
        "Güzel! Başka bir şey aramamı ister misin?",
    ],
}


def _is_single_emoji(text: str) -> bool:
    stripped = text.strip()
    return len(stripped) <= 3 and not stripped.isascii()


def _coerce_metadata(meta) -> dict:
    """
    Supabase'den gelen `metadata` çoğu zaman dict olur ama bazı
    sürücüler/durumlarda JSON string olarak dönebilir. Tek tip dict
    döndürmek için normalize ederiz.
    """
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str) and meta.strip():
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


# Cinsiyet / refinement ön-yakalama kalıpları
GENDER_MALE_HINTS = {"erkeğim", "erkek", "bay", "oğlan", "adamım"}
GENDER_FEMALE_HINTS = {"kadınım", "kadın", "bayan", "kız", "hanımım"}


def _tokenize(message: str) -> set[str]:
    """Mesajı küçük harfli kelime kümesine çevir (basit Türkçe-uyumlu)."""
    import re
    return set(re.findall(r"[a-zçğıöşüâîû]+", message.lower()))


def _has_gender_hint(message: str) -> str | None:
    """
    Mesajda kullanıcı kendi cinsiyetini belirtiyor mu? 'male'/'female'/None.
    Token-tabanlı + Türkçe iyelik eki ('-ım/-im/-um/-üm') toleransı:
      'bayan' → eşleşir,  'bayanım' → eşleşir,  'erkekçocuğu' → eşleşmez.
    """
    tokens = _tokenize(message)
    male_stems = {h for h in GENDER_MALE_HINTS}
    female_stems = {h for h in GENDER_FEMALE_HINTS}

    def _matches(tok: str, stems: set[str]) -> bool:
        if tok in stems:
            return True
        # Türkçe iyelik / -im eki: "bayan" + "ım" → "bayanım"
        for s in stems:
            if tok == s + "ım" or tok == s + "im" or tok == s + "um" or tok == s + "üm":
                return True
        return False

    for tok in tokens:
        if _matches(tok, male_stems):
            return "male"
        if _matches(tok, female_stems):
            return "female"
    return None


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

    # Teşekkür her uzunlukta CHITCHAT olarak yakalansın (önceden 20 char limiti
    # vardı; "çok teşekkür ederim yardımın için" gibi mesajlar LLM'e gidiyordu)
    if any(w in lower for w in ["teşekkür", "sağ ol", "sağol", "eyvallah"]):
        return "CHITCHAT"

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


def _get_contextual_reply(message: str) -> str:
    """Ürün önerisi sonrası bağlamsal yanıt üret."""
    lower = message.lower()
    if any(w in lower for w in ["teşekkür", "sağol", "sağ ol"]):
        return random.choice(CONTEXTUAL_REPLIES["tesekkur"])
    if lower.strip() in {"evet", "e", "ok", "okay", "tabi", "tabii"}:
        return random.choice(CONTEXTUAL_REPLIES["evet"])
    if lower.strip() in {"hayır", "h", "yok"}:
        return random.choice(CONTEXTUAL_REPLIES["hayir"])
    if lower.strip() in {"güzel", "süper", "harika", "iyi"}:
        return random.choice(CONTEXTUAL_REPLIES["guzel"])
    return random.choice(CONTEXTUAL_REPLIES["tesekkur"])


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

        # ── 0. Son ürün bağlamını kontrol et ──────────────────────────
        product_context = self._get_product_context(history)
        has_recent_products = product_context is not None
        self.logger.info(
            f"[conv] context_check | has_recent_products={has_recent_products} "
            f"history_len={len(history)} prev_query="
            f"'{(product_context or {}).get('user_query', '')}'"
        )

        # ── 0.5 Takip mesajı (FOLLOW-UP) ön-yakalama ─────────────────
        # Bu kontrol quick_intent'ten ÖNCE yapılır çünkü "ben erkeğim" gibi
        # mesajlar quick_intent'te None döner ama LLM bunları CHITCHAT olarak
        # işaretleyip "nasıl yardımcı olabilirim?" diyebiliyor. Ürün bağlamı
        # varsa direkt refinement olarak işle, LLM çağırma.
        if has_recent_products and self._is_refinement_message(message):
            prev_query = product_context.get("user_query", "") or ""
            refined_query = self._build_refined_query(prev_query, message)
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(
                f"[conv] FOLLOW_UP detected (pre-quick) | prev='{prev_query}' + "
                f"new='{message}' → refined='{refined_query}' | {elapsed:.0f}ms"
            )
            return self._build_result(
                "PRODUCT_SEARCH", 0.9, None,
                extracted_query=refined_query,
            )

        # ── 1. Hızlı kural tabanlı intent tespiti ────────────────────────
        quick_intent = _quick_intent(message)

        if quick_intent in ("GREETING", "CHITCHAT"):
            if has_recent_products:
                # Ürün önerisi sonrası bağlamsal yanıt ver
                # Örn: "Teşekkürler" → "Rica ederim! Ürünlerden beğendiğin oldu mu?"
                reply = _get_contextual_reply(message)
                elapsed = (time.monotonic() - t0) * 1000
                self.logger.info(
                    f"[conv] quick={quick_intent} + product_context → contextual reply | {elapsed:.0f}ms"
                )
                return self._build_result(quick_intent, 0.95, reply)
            else:
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

            # v3: LLM CHITCHAT dedi ama ürün bağlamı varsa → her zaman contextual reply ver
            # (LLM jenerik "nasıl yardımcı olabilirim?" dese bile bağlamlı yanıtla override)
            if intent in ("CHITCHAT", "GREETING") and has_recent_products:
                reply = _get_contextual_reply(message)
                self.logger.info(
                    f"[conv] llm={intent} but product_context → contextual reply override"
                )

            # v3: LLM PRODUCT_SEARCH dedi + ürün bağlamı + extracted_query çok kısa/eksik
            # → önceki sorguyla birleştir (örn: kullanıcı 'ben erkeğim' dedi, LLM bunu
            # PRODUCT_SEARCH olarak işaretledi ama query'i eksik üretti)
            if (
                intent == "PRODUCT_SEARCH"
                and has_recent_products
                and (not extracted_query or len(extracted_query.split()) <= 2)
            ):
                prev_query = product_context.get("user_query", "") or ""
                if prev_query:
                    refined = self._build_refined_query(prev_query, message)
                    self.logger.info(
                        f"[conv] llm=PRODUCT_SEARCH + thin query → refined "
                        f"'{extracted_query}' → '{refined}'"
                    )
                    extracted_query = refined

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

    # ── v3: Bağlam yardımcıları ──────────────────────────────────────────────

    def _get_product_context(self, history: list) -> dict | None:
        """
        Son ~8 mesajda ürün önerisi var mı kontrol et.
        Varsa: önceki kullanıcı sorgusu + ürün isimleri döner.

        History DESC sıralı gelir (en yeni ilk). En yeni asistan ürün
        mesajını bulup, onu tetikleyen kullanıcı sorgusunu eşleştiririz.
        """
        if not history:
            return None

        for i, h in enumerate(history[:8]):
            if h.get("role") != "assistant":
                continue
            meta = _coerce_metadata(h.get("metadata"))
            if meta.get("type") != "products":
                continue

            # Bu ürün önerisini tetikleyen kullanıcı mesajını bul
            user_query = ""
            user_msg_id = meta.get("user_msg_id")
            # Sonraki elemanlarda (daha eski) user mesajını ara
            for older in history[i + 1:i + 6]:
                if older.get("role") != "user":
                    continue
                # Önce id eşleşmesi (sağlam yol)
                if user_msg_id and older.get("id") == user_msg_id:
                    user_query = older.get("message", "") or ""
                    break
                # ID eşleşmezse, en yakın user mesajını fallback olarak al
                if not user_query:
                    user_query = older.get("message", "") or ""
                # ID yoksa direkt ilk user mesajıyla yetin
                if not user_msg_id:
                    break

            payload = meta.get("payload") or {}
            products = payload.get("products") or []
            product_names = [p.get("name", "")[:50] for p in products[:5]]

            return {
                "user_query": user_query,
                "product_names": product_names,
                "product_count": len(products),
            }
        return None

    def _is_refinement_message(self, message: str) -> bool:
        """Mesajın bir önceki ürün aramasını rafine eden bir takip mesajı olup olmadığını kontrol et."""
        lower = message.lower().strip()
        tokens = _tokenize(message)

        # Cinsiyet bildirimi → kesin refinement
        if _has_gender_hint(message):
            return True

        # Kelime-tabanlı refinement (substring değil, böylece 'erkek' 'erken'i yakalamaz)
        word_kws = {"başka", "farklı", "benzer", "alternatif", "beğenmedim",
                    "olmaz", "istemem", "sevmedim", "beden", "numara", "renk",
                    "boyut", "yaşında", "bütçem", "ucuz", "pahalı"}
        if tokens & word_kws:
            return True

        # Çok-kelimeli (substring uygun olan) refinement kalıpları
        phrase_kws = [
            "daha ucuz", "daha pahalı", "daha uygun", "daha kaliteli",
            "daha büyük", "daha küçük", "daha hafif", "hoşuma gitmedi",
            "başka bir", "ama ", "fakat", "ancak", "aslında",
        ]
        if any(p in lower for p in phrase_kws):
            return True

        # Kısa mesajlar + ürün bağlamı varsa muhtemelen follow-up
        # "Siyah olsun", "42 numara", "Samsung olmasın" gibi
        if len(lower) <= 60 and not any(kw in lower for kw in PRODUCT_KEYWORDS):
            word_count = len(lower.split())
            if word_count <= 8:
                return True

        return False

    def _strip_product_search_prefixes(self, query: str) -> str:
        """'pantolon öner', 'pantolon arıyorum' → 'pantolon' gibi sadeleştir."""
        if not query:
            return ""
        text = query.strip()
        # Sonu yumuşat: "öner / öneri / önerir misin / arıyorum" gibi yardımcı kelimeleri at
        suffixes = [
            " öner", " önerir misin", " önerir misiniz", " öneri", " önerisi",
            " arıyorum", " bakıyorum", " istiyorum", " almak istiyorum",
            " satın almak istiyorum", " bul", " bulur musun", " ister misin",
        ]
        lower = text.lower()
        for s in suffixes:
            if lower.endswith(s):
                text = text[: len(text) - len(s)].strip()
                lower = text.lower()
        return text or query.strip()

    def _build_refined_query(self, prev_query: str, new_message: str) -> str:
        """Önceki sorgu + yeni bağlamı birleştirerek rafine edilmiş sorgu oluştur."""
        prev_core = self._strip_product_search_prefixes(prev_query) or prev_query or ""
        lower = new_message.lower()

        # Cinsiyet düzeltmesi (token-bazlı, daha güvenli)
        gender = _has_gender_hint(new_message)
        if gender == "male":
            return f"erkek {prev_core}".strip()
        if gender == "female":
            return f"kadın {prev_core}".strip()

        # Fiyat düzeltmesi
        if "daha ucuz" in lower or "daha uygun" in lower:
            return f"{prev_core} uygun fiyatlı".strip()
        if "daha pahalı" in lower or "daha kaliteli" in lower:
            return f"{prev_core} premium kaliteli".strip()

        # Beğenmeme / alternatif
        if any(w in lower for w in ["başka", "farklı", "alternatif", "beğenmedim"]):
            return f"{prev_core} alternatif".strip()

        # Genel ek bilgi: önceki sorguya ek olarak ekle
        return f"{prev_core} {new_message}".strip()

    # ── Yardımcılar ──────────────────────────────────────────────────────────

    def _format_history(self, history: list, limit: int = 8) -> str:
        if not history:
            return ""
        # history DB'den DESC (en yeni ilk) gelir; LLM'e kronolojik sırayla
        # (eski → yeni) gönderiyoruz. Önce ters çevir, sonra son `limit`'i al.
        chronological = list(reversed(history))
        recent = chronological[-limit:]
        lines = []
        for h in recent:
            role = "Kullanıcı" if h.get("role") == "user" else "Asistan"
            msg = h.get("message", "")

            # v3: Ürün önerisi mesajlarını zenginleştir
            if h.get("role") == "assistant":
                meta = _coerce_metadata(h.get("metadata"))
                if meta.get("type") == "products":
                    payload = meta.get("payload") or {}
                    products = payload.get("products") or []
                    if products:
                        names = [p.get("name", "")[:40] for p in products[:3]]
                        msg = f"[Önerilen ürünler: {', '.join(names)}]"
                    else:
                        msg = "[Ürün araması yapıldı (sonuç bulunamadı)]"

            lines.append(f"{role}: {msg[:200]}")
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
