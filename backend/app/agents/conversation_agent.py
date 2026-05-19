import time
import json
import random
from app.agents.base_agent import BaseAgent
from app.prompts.conversation_prompts import (
    CONVERSATION_SYSTEM_PROMPT,
    INTENT_SYSTEM,
    INTENT_CLASSIFICATION_PROMPT,
    QUICK_REPLIES,
    BUDGET_QUERY_PROMPT,
    COMPLAINT_REPLY_PROMPT,
)

GREETING_WORDS = {
    "merhaba", "selam", "günaydın", "iyi günler", "iyi akşamlar",
    "hey", "hi", "hello",
}

HOWRU_WORDS = {"naber", "nasılsın", "nasıl gidiyor", "ne haber", "iyi misin"}
HOWRU_REPLIES = [
    "İyiyim, teşekkürler! 😊 Sen nasılsın? Bugün ne arıyoruz?",
    "Gayet iyiyim! Sağ ol. Sana nasıl yardımcı olabilirim? 🛍️",
    "Çok iyiyim, teşekkürler! Bugün bir şeyler mi arıyoruz?",
]

BUDGET_KEYWORDS = [
    "bütçem", "bütçemi", "bütçemde", "bütçeme", "bütçemle",
    "bütçem ne", "bütçem var", "bütçem kaç", "bütçem nedir",
    "ne kadar bütçe", "bütçem ne kadar", "bütçe durumum", "bütçe bilgi",
    "bütçeye bak", "bütçeyi göster", "bütçeyi görebilir",
    "param var mı", "param yeter mi", "param ne kadar", "ne kadar param",
    "param kaç", "param nedir", "paramı göster", "param kaldı mı",
    "harcayabilir miyim", "ne kadar harcadım", "bu ay ne harcadım",
    "harcama durumum", "mali durum", "finansal durum",
    "gelir", "maaşım", "aylık gelir",
    "ne kadar kaldı", "kalan param", "kalan bütçe",
]

PRODUCT_KEYWORDS = [
    "öner", "arıyorum", "bul", "istiyorum", "almak", "satın", "hediye",
    "ucuz", "fiyat", "ürün", "laptop", "telefon", "bilgisayar", "kulaklık",
    "tablet", "saat", "ayakkabı", "tv", "televizyon", "parfüm",
    "iphone", "samsung", "xiaomi", "apple", "nasıl olur", "ne olur",
    "peki", "ya", "başka", "farklı", "alternatif",
]

def _coerce_metadata(meta) -> dict:
    if isinstance(meta, dict):
        return meta
    if isinstance(meta, str) and meta.strip():
        try:
            parsed = json.loads(meta)
            return parsed if isinstance(parsed, dict) else {}
        except (ValueError, TypeError):
            return {}
    return {}


GENDER_MALE_HINTS = {"erkeğim", "erkek", "bay", "oğlan", "adamım"}
GENDER_FEMALE_HINTS = {"kadınım", "kadın", "bayan", "kız", "hanımım"}


def _tokenize(message: str) -> set[str]:
    import re
    return set(re.findall(r"[a-zçğıöşüâîû]+", message.lower()))


def _has_gender_hint(message: str) -> str | None:
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


def _get_greeting_reply(message: str) -> str:
    return random.choice(QUICK_REPLIES["selamlama"])


class ConversationAgent(BaseAgent):
    def __init__(self, llm, db):
        super().__init__("conversation_agent", llm, db)

    async def execute(self, input_data: dict) -> dict:
        t0 = time.monotonic()
        message = input_data.get("message", "").strip()
        history = input_data.get("chat_history", [])
        budget_info = input_data.get("budget_info")
        user_id = input_data.get("user_id")

        if not message:
            return self._build_result("CHITCHAT", 1.0, "Ne sormak isterdiniz? 😊")

        import re as _re
        lower = message.lower().strip()
        # Noktalama temizlenmiş versiyon — keyword matching için
        lower_clean = _re.sub(r"\s+", " ", _re.sub(r"[^\w\s]", " ", lower)).strip()
        if len(lower_clean) <= 35 and any(lower_clean.startswith(g) or lower_clean == g for g in GREETING_WORDS):
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(f"[conv] quick=GREETING | {elapsed:.0f}ms")
            return self._build_result("GREETING", 0.99, _get_greeting_reply(message))

        if len(lower_clean) <= 40 and any(lower_clean.startswith(g) or lower_clean == g for g in HOWRU_WORDS):
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(f"[conv] quick=HOWRU | {elapsed:.0f}ms")
            return self._build_result("GREETING", 0.99, random.choice(HOWRU_REPLIES))

        if any(kw in lower_clean for kw in BUDGET_KEYWORDS):
            self.logger.info("[conv] quick=BUDGET_QUERY")
            reply = await self._handle_budget_query(message, budget_info, user_id)
            elapsed = (time.monotonic() - t0) * 1000
            self.logger.info(f"[conv] BUDGET_QUERY done | {elapsed:.0f}ms")
            return self._build_result("BUDGET_QUERY", 0.97, reply)

        product_context = self._get_product_context(history)
        has_recent_products = product_context is not None
        prev_query = (product_context or {}).get("user_query", "") or ""
        product_names = (product_context or {}).get("product_names", [])

        self.logger.info(
            f"[conv] llm_classify | has_products={has_recent_products} "
            f"prev_query='{prev_query[:40]}' history_len={len(history)}"
        )

        try:
            history_text = self._format_history(history, limit=8)
            context_block = ""
            if has_recent_products:
                names_str = ", ".join(product_names[:3]) if product_names else "—"
                context_block = (
                    f"\nÖnceki arama sorgusu: \"{prev_query}\"\n"
                    f"Önerilen ürünler: {names_str}"
                )
            # .format() yerine manuel replace — prev_query/product_names içinde
            # süslü parantez { } olursa format() KeyError fırlatır.
            prompt = (
                INTENT_CLASSIFICATION_PROMPT
                .replace("{history_text}", history_text or "(geçmiş yok)")
                .replace("{context_block}", context_block)
                .replace("{message}", message)
            )
            result = await self.call_llm_json(prompt, system=INTENT_SYSTEM)

            intent = result.get("intent", "CHITCHAT").upper()
            confidence = float(result.get("confidence", 0.5))
            reply = result.get("reply")
            comparison_products = result.get("comparison_products", [])
            extracted_query = result.get("extracted_query")

            if confidence < 0.45 and intent in ("PRODUCT_SEARCH", "COMPARISON"):
                intent = "CHITCHAT"
                reply = "Tam anlayamadım 😅 Ürün mü arıyorsun, yoksa başka bir konuda yardım mı istersin?"

            if (
                intent == "PRODUCT_SEARCH"
                and has_recent_products
                and prev_query
                and (not extracted_query or len(extracted_query.split()) <= 2)
            ):
                refined = self._build_refined_query(prev_query, message)
                self.logger.info(
                    f"[conv] thin query → refined '{extracted_query}' → '{refined}'"
                )
                extracted_query = refined

        except Exception as e:
            self.logger.error(f"[conv] LLM error: {e}")
            # Fallback: keyword varlığına göre tahmin
            has_product_kw = any(kw in lower_clean for kw in PRODUCT_KEYWORDS)
            intent = "PRODUCT_SEARCH" if has_product_kw else "CHITCHAT"
            confidence = 0.6
            reply = None if intent == "PRODUCT_SEARCH" else random.choice(QUICK_REPLIES.get("tesekkur", ["Ne demek! 😊"]))
            comparison_products = []
            extracted_query = message if intent == "PRODUCT_SEARCH" else None

        if intent == "BUDGET_QUERY" and not reply:
            reply = await self._handle_budget_query(message, budget_info, user_id)

        if intent == "COMPLAINT":
            if not reply:
                try:
                    complaint_prompt = COMPLAINT_REPLY_PROMPT.format(message=message)
                    reply = await self.call_llm(complaint_prompt, system=CONVERSATION_SYSTEM_PROMPT)
                except Exception:
                    reply = "Üzgünüm, yaşadığın sorun için özür dilerim 🙏 Farklı bir arama deneyelim mi?"

        elapsed = (time.monotonic() - t0) * 1000
        self.logger.info(
            f"[conv] intent={intent} confidence={confidence:.2f} | {elapsed:.0f}ms"
        )

        return self._build_result(
            intent, confidence, reply,
            comparison_products=comparison_products,
            extracted_query=extracted_query,
        )

    async def _handle_budget_query(self, message: str, budget_info: dict | None, user_id: str | None = None) -> str:
        if not budget_info and user_id:
            try:
                from app.agents.budget_agent import BudgetAgent
                result = await BudgetAgent(llm=self.llm, db=self.db).execute(
                    {"action": "analyze", "user_id": user_id}
                )
                budget_info = result.get("financial_metrics")
                self.logger.info(f"[conv] budget_info fetched in handler: {bool(budget_info)}")
            except Exception as e:
                self.logger.error(f"[conv] BudgetAgent çağrısı başarısız: {e}")

        if not budget_info:
            return (
                "Bütçe bilgilerine ulaşamadım. "
                "Bütçe Ayarları sayfasından gelir ve giderlerini girersen sana detaylı analiz yapabilirim."
            )

        try:
            b = budget_info if isinstance(budget_info, dict) else {}
            budget_summary = (
                f"Aylık gelir: {b.get('total_income', '?')} TL\n"
                f"Sabit giderler: {b.get('fixed_expenses', '?')} TL\n"
                f"Tasarruf hedefi: {b.get('savings_goal', 0)} TL\n"
                f"Harcanabilir (tasarruf sonrası): {b.get('spendable_after_savings', '?')} TL\n"
                f"Bu ay harcanan: {b.get('current_month_spending', 0)} TL\n"
                f"Kalan harcanabilir: {b.get('remaining_spendable', '?')} TL"
            )
            prompt = BUDGET_QUERY_PROMPT.format(
                budget_info=budget_summary,
                message=message,
            )
            return await self.call_llm(prompt, system=CONVERSATION_SYSTEM_PROMPT)
        except Exception:
            return "Bütçe bilgilerine şu an ulaşamıyorum, birazdan tekrar dener misin?"

    def _get_product_context(self, history: list) -> dict | None:
        if not history:
            return None

        for i, h in enumerate(history[:8]):
            if h.get("role") != "assistant":
                continue
            meta = _coerce_metadata(h.get("metadata"))
            if meta.get("type") != "products":
                continue

            user_query = ""
            user_msg_id = meta.get("user_msg_id")
            for older in history[i + 1:i + 6]:
                if older.get("role") != "user":
                    continue
                if user_msg_id and older.get("id") == user_msg_id:
                    user_query = older.get("message", "") or ""
                    break
                if not user_query:
                    user_query = older.get("message", "") or ""
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

    def _strip_product_search_prefixes(self, query: str) -> str:
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
        prev_core = self._strip_product_search_prefixes(prev_query) or prev_query or ""
        lower = new_message.lower()

        gender = _has_gender_hint(new_message)
        if gender == "male":
            return f"erkek {prev_core}".strip()
        if gender == "female":
            return f"kadın {prev_core}".strip()

        if "daha ucuz" in lower or "daha uygun" in lower:
            return f"{prev_core} uygun fiyatlı".strip()
        if "daha pahalı" in lower or "daha kaliteli" in lower:
            return f"{prev_core} premium kaliteli".strip()

        if any(w in lower for w in ["başka", "farklı", "alternatif", "beğenmedim"]):
            return f"{prev_core} alternatif".strip()

        return f"{prev_core} {new_message}".strip()

    def _format_history(self, history: list, limit: int = 8) -> str:
        if not history:
            return ""
        # history DB'den DESC (en yeni ilk) gelir; LLM'e kronolojik (eski → yeni) gönderilir.
        chronological = list(reversed(history))
        recent = chronological[-limit:]
        lines = []
        for h in recent:
            role = "Kullanıcı" if h.get("role") == "user" else "Asistan"
            msg = h.get("message", "")

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
