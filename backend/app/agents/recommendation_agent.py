"""
Recommendation Agent — Geliştirilmiş Sürüm v2
=============================================
Değişiklikler:
  - Tüm personality skorları kullanılıyor (impulsive, research, saving)
  - Karşılaştırma modu eklendi (COMPARISON intent)
  - review_analysis.overall_sentiment → review_analysis.analysis.sentiment_score okunuyor
  - Hibrit value_score hesaplama (rating + sentiment + budget fit) Python tarafında
  - Affordability tagging: affordable / tight / over_budget
  - pros / cons / review_summary inject (ürün çıktısına ekleniyor)
  - Gift context parametreleri: occasion, recipient
  - Gelişmiş fallback: LLM başarısız olursa hibrit skora göre sıralama
"""

from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService

RECOMMENDATION_PROMPT = """
Sen kullanıcının kişisel alışveriş arkadaşısın. Samimi, sıcak, kısa konuş.

Kullanıcı İsteği: "{message}"{gift_context_text}

Önerilen Ürünler:
{products_text}

Gizli bağlam (kullanıcıya GÖSTERME, sadece karar almak için kullan):
- Harcama eğilimi: {spending_type}
- Tasarruf odaklı mı: {saving_score}/10
- Dürtüsel mi: {impulsive_score}/10
- Bütçe durumu: {budget_status}
- Harcanabilir: {spendable} TL

KULLANICIYA SUNULAN METİNDE ASLA YAZILMAYACAKLAR:
✗ "Profilinize göre ayarlandı", "Savruk/Tasarrufçu/Dengeli profil"
✗ "Affordability skoru", "Value score", "Sentiment skoru"
✗ "Sistem analiz etti", "Pipeline çalıştı", "Bütçe hesaplandı"
✗ "spending_type", "impulsive_score" gibi teknik terimler
✗ İngilizce teknik kelimeler

YALNIZCA ŞU TARZDA YAZ:
✓ "Bütçene tam uyuyor" / "Biraz zorlar ama değer"
✓ "Yorumları çok güzel" / "Kullananlar memnun"
✓ "Fiyat-performansı şahane"
✓ Samimi, arkadaşça Türkçe

Aşağıdaki JSON formatında yanıt ver:
{{
    "top_pick": {{
        "product_name": "en iyi seçenek ürün adı (listeden seç, uydurma)",
        "reason": "neden bu ürünü öneriyorsun — samimi 1-2 cümle, teknik terim YOK",
        "value_score": 1-10 arası değer puanı,
        "personality_fit": "bu ürün sana uygun çünkü... (1 cümle, samimi)"
    }},
    "summary": "1-2 cümle, arkadaşça özet",
    "financial_advice": "bütçeye göre samimi 1 cümle tavsiye (teknik terim YOK)",
    "ranking": ["1. sıra ürün adı", "2. sıra ürün adı", "3. sıra ürün adı"],
    "budget_warning": true veya false
}}

SADECE JSON DÖNDÜR.
"""

COMPARISON_PROMPT = """
Sen kullanıcının alışveriş arkadaşısın. İki ürünü karşılaştırıyor.

Kullanıcı Sorusu: "{message}"{gift_context_text}
Karşılaştırılacak Ürünler: {comparison_products}

Gizli bağlam (kullanıcıya GÖSTERME):
- Harcama eğilimi: {spending_type}
- Bütçe: {budget_status} / {spendable} TL

Bulunan Ürünler:
{products_text}

KURAL: Samimi, kısa konuş. Teknik terim (skor, profil, pipeline) YAZMA.

Kapsamlı bir karşılaştırma yap:

{{
    "comparison_table": [
        {{
            "product_name": "ürün adı",
            "price": fiyat,
            "pros": ["artı 1", "artı 2"],
            "cons": ["eksi 1"],
            "best_for": "bu ürün kime uyar",
            "score": 1-10
        }}
    ],
    "winner": "kazanan ürün adı",
    "winner_reason": "neden bu ürün daha iyi (2-3 cümle)",
    "budget_recommendation": "bütçeye göre öneri",
    "summary": "karşılaştırma özeti (2 cümle)",
    "ranking": ["1. sıra", "2. sıra"]
}}

SADECE JSON DÖNDÜR.
"""


import random as _random


def _compute_personality_weights(personality: dict) -> dict:
    weights = {"budget_fit": 0.30, "rating": 0.20, "reviews": 0.20, "value": 0.15, "detail": 0.15}
    saving      = personality.get("saving_score", 5)
    research    = personality.get("research_score", 5)
    impulsive   = personality.get("impulsive_score", 5)

    if saving >= 7:
        weights = {"budget_fit": 0.45, "value": 0.25, "rating": 0.15, "reviews": 0.10, "detail": 0.05}
    elif research >= 7:
        weights = {"reviews": 0.30, "detail": 0.25, "rating": 0.20, "budget_fit": 0.15, "value": 0.10}
    elif impulsive >= 7:
        weights = {"rating": 0.35, "budget_fit": 0.25, "value": 0.20, "reviews": 0.15, "detail": 0.05}
    return weights


def _compute_personalized_score(product: dict, weights: dict) -> tuple[float, list]:
    factors = []

    affordability = product.get("affordability_tag", "tight")
    if affordability == "affordable":
        budget_score = 10.0
        factors.append({"name": "bütçe_uyumu", "label": "bütçene tam uyuyor", "w": weights["budget_fit"]})
    elif affordability == "tight":
        budget_score = 5.0
        factors.append({"name": "bütçe_uyumu", "label": "bütçenin sınırında", "w": weights["budget_fit"] * 0.5})
    else:
        budget_score = 0.0

    rating = float(product.get("rating") or 0)
    rating_score = (rating / 5.0) * 10.0
    if rating >= 4.5:
        factors.append({"name": "yüksek_puan", "label": f"puanı {rating}/5", "w": weights["rating"]})

    sentiment = float((product.get("review_analysis") or {}).get("analysis", {}).get("sentiment_score") or 5)
    if sentiment >= 7:
        factors.append({"name": "iyi_yorumlar", "label": "yorumları çok güzel", "w": weights["reviews"]})

    value_score = float(product.get("value_score") or 5)
    if value_score >= 7:
        factors.append({"name": "fiyat_performans", "label": "fiyat-performansı şahane", "w": weights["value"]})

    pros = len((product.get("review_analysis") or {}).get("analysis", {}).get("pros") or [])
    detail_score = min(10.0, pros * 2.5)
    if pros >= 3:
        factors.append({"name": "detaylı", "label": "özellikleri zengin", "w": weights["detail"]})

    total = (
        budget_score * weights["budget_fit"] +
        rating_score * weights["rating"] +
        sentiment   * weights["reviews"] +
        value_score * weights["value"] +
        detail_score * weights["detail"]
    )
    return total, factors


def select_winner(products: list, personality: dict, user_budget: dict = None) -> dict | None:
    """
    Kişilik bazlı winner seçimi. LLM çağrısı yok — template-based, hızlı.
    Returns: { winner_index, reasoning_for_user, confidence, key_factors }
    """
    if not products:
        return None
    if len(products) == 1:
        p = products[0]
        tag = p.get("affordability_tag", "tight")
        if tag == "affordable":
            reason = f"**{p.get('name','')}** tek seçenek ve bütçene tam uyuyor."
        elif tag == "over_budget":
            reason = f"**{p.get('name','')}** bulunan tek seçenek ama biraz bütçeni zorlayabilir."
        else:
            reason = f"**{p.get('name','')}** sana en uygunu gibi duruyor."
        return {"winner_index": 0, "winner_product": p, "reasoning_for_user": reason,
                "confidence": "high", "key_factors": []}

    weights = _compute_personality_weights(personality)
    scored = []
    for idx, p in enumerate(products):
        total, factors = _compute_personalized_score(p, weights)
        scored.append({"index": idx, "product": p, "score": total, "factors": factors})

    scored.sort(key=lambda x: x["score"], reverse=True)
    winner = scored[0]
    score_gap = scored[0]["score"] - scored[1]["score"] if len(scored) > 1 else 99

    confidence = "high" if score_gap > 1.5 else ("medium" if score_gap > 0.7 else "low")

    # Samimi reasoning oluştur
    top_factors = sorted(winner["factors"], key=lambda f: f["w"], reverse=True)[:2]
    name = winner["product"].get("name", "Bu ürün")
    openings = [
        f"Sana **{name}**'i öneriyorum",
        f"Bence en uygunu **{name}**",
        f"**{name}** tam senin için",
        f"Eğer benim önerim olursa: **{name}**",
    ]
    opening = _random.choice(openings)

    if top_factors:
        labels = [f["label"] for f in top_factors]
        reason_part = f"çünkü {labels[0]}" + (f" ve {labels[1]}" if len(labels) > 1 else "")
    else:
        reason_part = "çünkü en dengeli seçenek"

    # Kişilik notu
    personality_note = ""
    if personality.get("saving_score", 5) >= 7:
        personality_note = " Dikkatli alışveriş yapıyorsun, bu seçim güvenli."
    elif personality.get("research_score", 5) >= 7:
        personality_note = " Detaylı araştırırsın, ürün sayfasını mutlaka incele."
    elif personality.get("impulsive_score", 5) >= 7:
        personality_note = " Ama bir gün düşünüp öyle al olur mu? 😄"

    closing_map = {"high": "Gözüm kapalı bunu öneririm.", "medium": "Diğerleri de fena değil ama bu öne çıkıyor.", "low": "Yakın bir yarış oldu ama bu küçük farkla önde."}
    closing = closing_map[confidence]

    reasoning = f"{opening} — {reason_part}.{personality_note} {closing}"

    return {
        "winner_index": winner["index"],
        "winner_product": winner["product"],
        "reasoning_for_user": reasoning,
        "confidence": confidence,
        "key_factors": [f["name"] for f in top_factors],
    }


class RecommendationAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="recommendation_agent", llm=llm, db=db)

    async def execute(self, input_data: dict) -> dict:
        message = input_data.get("message", "")
        intent = input_data.get("intent", "PRODUCT_SEARCH")
        is_comparison = input_data.get("is_comparison", False)
        comparison_products = input_data.get("comparison_products", [])
        personality = input_data.get("personality") or {}
        budget = input_data.get("budget") or {}
        products = input_data.get("products") or []

        # Gift context
        occasion = input_data.get("occasion") or ""
        recipient = input_data.get("recipient") or ""

        self.logger.info(
            f"Öneri üretiliyor | intent={intent} | ürün_sayısı={len(products)} "
            f"| occasion={occasion} | recipient={recipient}"
        )

        if not products:
            return self._empty_result("Önerilecek ürün bulunamadı.")

        # Finansal metrikler
        spending_type = personality.get("spending_type", "dengeli")
        risk_score = personality.get("risk_score", 5)
        impulsive_score = personality.get("impulsive_score", 5)
        saving_score = personality.get("saving_score", 5)
        research_score = personality.get("research_score", 5)
        budget_status = budget.get("status", "unknown")
        financial_metrics = budget.get("financial_metrics", {})
        spendable = financial_metrics.get("spendable_after_savings", 0) or 0

        # 1) Affordability tagging + review inject
        enriched_products = self._enrich_products(products, spendable)

        # 2) Hibrit value_score hesapla (Python tarafında)
        scored_products = self._compute_value_scores(enriched_products, spendable)

        products_text = self._format_products(scored_products)
        gift_context_text = self._format_gift_context(occasion, recipient)

        # Karşılaştırma modu
        if is_comparison and comparison_products:
            return await self._comparison_mode(
                message=message,
                comparison_products=comparison_products,
                products=scored_products,
                products_text=products_text,
                spending_type=spending_type,
                budget_status=budget_status,
                spendable=spendable,
                gift_context_text=gift_context_text,
            )

        # Normal öneri modu
        try:
            prompt = RECOMMENDATION_PROMPT.format(
                spending_type=spending_type,
                risk_score=risk_score,
                impulsive_score=impulsive_score,
                saving_score=saving_score,
                research_score=research_score,
                budget_status=budget_status,
                spendable=f"{spendable:,.0f}",
                message=message,
                products_text=products_text,
                gift_context_text=gift_context_text,
            )
            llm_result = await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri hatası: {e}")
            llm_result = {}

        ranked_products = self._rank_products(
            scored_products, llm_result.get("ranking", [])
        )

        # Winner seçimi (LLM çağrısı yok, template-based hızlı)
        winner_data = select_winner(ranked_products, personality, budget)
        if winner_data:
            wi = winner_data["winner_index"]
            if wi < len(ranked_products):
                ranked_products[wi]["is_recommended"] = True
                ranked_products[wi]["recommendation_reason"] = winner_data["reasoning_for_user"]

        # LLM summary yoksa sade fallback (teknik terim içermeyen)
        summary = llm_result.get("summary", "")
        if not summary or any(w in summary.lower() for w in ["profil", "spending_type", "affordability", "pipeline"]):
            summary = "Sana birkaç güzel seçenek buldum, bir göz at!"

        financial_advice = llm_result.get("financial_advice", "")
        if financial_advice and any(w in financial_advice.lower() for w in ["savruk", "profil", "spending", "affordability"]):
            financial_advice = ""

        return {
            "mode": "recommendation",
            "spending_type": spending_type,
            "budget_status": budget_status,
            "occasion": occasion,
            "recipient": recipient,
            "top_pick": llm_result.get("top_pick"),
            "summary": summary,
            "financial_advice": financial_advice,
            "budget_warning": llm_result.get("budget_warning", False),
            "top_products": ranked_products,
            "winner": winner_data,
        }

    # ------------------------------------------------------------------ #
    # Karşılaştırma modu                                                   #
    # ------------------------------------------------------------------ #

    async def _comparison_mode(
        self,
        message: str,
        comparison_products: list,
        products: list,
        products_text: str,
        spending_type: str,
        budget_status: str,
        spendable: float,
        gift_context_text: str,
    ) -> dict:
        """Karşılaştırma modu — ürünleri karşı karşıya değerlendir."""
        try:
            prompt = COMPARISON_PROMPT.format(
                spending_type=spending_type,
                budget_status=budget_status,
                spendable=f"{spendable:,.0f}",
                message=message,
                comparison_products=" vs ".join(comparison_products),
                products_text=products_text,
                gift_context_text=gift_context_text,
            )
            llm_result = await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"Comparison LLM hatası: {e}")
            llm_result = {}

        ranked_products = self._rank_products(products, llm_result.get("ranking", []))

        return {
            "mode": "comparison",
            "spending_type": spending_type,
            "budget_status": budget_status,
            "comparison_table": llm_result.get("comparison_table", []),
            "top_pick": {
                "product_name": llm_result.get("winner", ""),
                "reason": llm_result.get("winner_reason", ""),
                "value_score": 8,
                "personality_fit": llm_result.get("budget_recommendation", ""),
            }
            if llm_result.get("winner")
            else None,
            "summary": llm_result.get("summary", "Karşılaştırma tamamlandı."),
            "financial_advice": llm_result.get("budget_recommendation", ""),
            "budget_warning": False,
            "top_products": ranked_products,
        }

    # ------------------------------------------------------------------ #
    # Yardımcı metodlar                                                    #
    # ------------------------------------------------------------------ #

    def _enrich_products(self, products: list, spendable: float) -> list:
        """
        Her ürüne:
          - affordability_tag  : affordable | tight | over_budget
          - review_summary     : LLM'den gelen genel özet metni
          - pros               : inceleme artıları
          - cons               : inceleme eksileri
        alanları eklenir.
        """
        enriched = []
        for p in products:
            p = dict(p)  # kopya al, orijinali değiştirme

            # --- Affordability tagging ---
            price = p.get("price", 0) or 0
            if spendable <= 0:
                tag = "unknown"
            elif price <= spendable * 0.80:
                tag = "affordable"
            elif price <= spendable:
                tag = "tight"
            else:
                tag = "over_budget"
            p["affordability_tag"] = tag

            # --- Review detail inject ---
            review = p.get("review_analysis") or {}
            analysis = review.get("analysis") or {}

            p.setdefault("review_summary", analysis.get("summary") or review.get("summary") or "")
            p.setdefault("pros", analysis.get("pros") or review.get("pros") or [])
            p.setdefault("cons", analysis.get("cons") or review.get("cons") or [])

            enriched.append(p)
        return enriched

    def _compute_value_scores(self, products: list, spendable: float) -> list:
        """
        Hibrit value_score hesapla (0–10):
          - rating bileşeni      : rating/5 * 4  → max 4 puan
          - sentiment bileşeni   : sentiment_score/10 * 3 → max 3 puan
          - budget fit bileşeni  : affordable=3, tight=1.5, over_budget=0
        """
        for p in products:
            rating = float(p.get("rating") or 0)
            review = p.get("review_analysis") or {}
            analysis = review.get("analysis") or {}
            sentiment_score = float(
                analysis.get("sentiment_score")
                or analysis.get("overall_sentiment")
                or 5
            )
            affordability_tag = p.get("affordability_tag", "unknown")

            rating_component = (rating / 5.0) * 4.0
            sentiment_component = (sentiment_score / 10.0) * 3.0
            budget_component = {"affordable": 3.0, "tight": 1.5, "over_budget": 0.0}.get(
                affordability_tag, 1.5
            )

            raw = rating_component + sentiment_component + budget_component
            p["value_score"] = round(min(raw, 10.0), 2)
        return products

    def _format_gift_context(self, occasion: str, recipient: str) -> str:
        """Gift context varsa prompt'a ek satır oluştur."""
        parts = []
        if occasion:
            parts.append(f"Özel durum/hediye vesile: {occasion}")
        if recipient:
            parts.append(f"Hediye alınan kişi: {recipient}")
        if parts:
            return "\n" + "\n".join(parts)
        return ""

    def _format_products(self, products: list) -> str:
        lines = []
        for i, p in enumerate(products[:5], 1):
            review = p.get("review_analysis") or {}
            analysis = review.get("analysis") or {}
            sentiment = (
                analysis.get("sentiment")
                or analysis.get("overall_sentiment")
                or "bilinmiyor"
            )
            sentiment_score = analysis.get("sentiment_score", "?")
            rating = p.get("rating", 0)
            tag = p.get("affordability_tag", "")
            value_score = p.get("value_score", "?")
            pros = p.get("pros") or []
            cons = p.get("cons") or []
            review_summary = p.get("review_summary") or ""

            line = (
                f"{i}. {p.get('name', '')} | "
                f"Fiyat: {p.get('price', 0):,.0f} TL | "
                f"Satıcı: {p.get('seller', '')} | "
                f"Rating: {rating}/5 | "
                f"Duygu: {sentiment} ({sentiment_score}) | "
                f"Bütçe: {tag} | "
                f"ValueScore: {value_score}/10"
            )
            if review_summary:
                line += f"\n   Özet: {review_summary}"
            if pros:
                line += f"\n   Artılar: {', '.join(pros[:3])}"
            if cons:
                line += f"\n   Eksiler: {', '.join(cons[:2])}"
            lines.append(line)
        return "\n".join(lines)

    def _rank_products(self, products: list, llm_ranking: list) -> list:
        """
        LLM sıralaması varsa ona göre, yoksa hibrit value_score'a göre sırala.
        """
        if llm_ranking:
            name_to_product = {p.get("name", ""): p for p in products}
            ranked = []
            for name in llm_ranking:
                match = name_to_product.get(name)
                if not match:
                    match = next(
                        (p for p in products if name.lower() in p.get("name", "").lower()),
                        None,
                    )
                if match and match not in ranked:
                    ranked.append(match)
            for p in products:
                if p not in ranked:
                    ranked.append(p)
            return ranked[:3]

        # Gelişmiş fallback: hibrit value_score'a göre sırala
        return sorted(
            products,
            key=lambda p: (p.get("value_score") or 0),
            reverse=True,
        )[:3]

    def _empty_result(self, message: str) -> dict:
        return {
            "mode": "recommendation",
            "spending_type": "dengeli",
            "budget_status": "unknown",
            "occasion": "",
            "recipient": "",
            "top_pick": None,
            "summary": message,
            "financial_advice": "",
            "budget_warning": False,
            "top_products": [],
        }
