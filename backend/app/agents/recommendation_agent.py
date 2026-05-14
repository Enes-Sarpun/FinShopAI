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
Sen bir kişisel finans ve alışveriş danışmanısın.
Kullanıcının finansal profili ve bulunan ürünlere göre en iyi öneriyi yap.

Kullanıcı Profili:
- Harcama tipi: {spending_type}
- Risk skoru: {risk_score}/10 (yüksek = riskli harcayıcı)
- Impulsif harcama: {impulsive_score}/10 (yüksek = dürtüsel)
- Tasarruf skoru: {saving_score}/10 (yüksek = çok tasarruf ediyor)
- Araştırma skoru: {research_score}/10 (yüksek = çok araştırıyor)
- Bütçe durumu: {budget_status}
- Harcanabilir bütçe: {spendable} TL

Kullanıcı İsteği: "{message}"{gift_context_text}

Önerilen Ürünler:
{products_text}

Kullanıcı profiline göre kişiselleştirilmiş bir öneri yap.
- Impulsif skoru yüksekse: "fiyat/performans araştırın" vurgusu yap
- Tasarruf skoru yüksekse: ekonomik seçeneği öne çıkar
- Risk skoru yüksekse: dikkatli ol uyarısı ver
- Bütçe etiketleri: affordable (bütçe içinde), tight (sınırda), over_budget (bütçe dışı)

Aşağıdaki JSON formatında yanıt ver:
{{
    "top_pick": {{
        "product_name": "en iyi seçenek ürün adı",
        "reason": "neden bu ürünü öneriyorsun (2-3 cümle, kullanıcının finansal profiline göre kişiselleştirilmiş)",
        "value_score": 1-10 arası değer puanı,
        "personality_fit": "bu ürünün kullanıcının profiline neden uyduğu (1 cümle)"
    }},
    "summary": "tüm önerileri özetleyen 1-2 cümle mesaj",
    "financial_advice": "bu alışverişle ilgili kısa finansal tavsiye (spending_type'a göre kişiselleştirilmiş)",
    "ranking": ["1. sıra ürün adı", "2. sıra ürün adı", "3. sıra ürün adı"],
    "budget_warning": true veya false (ürün bütçeyi zorluyor mu)
}}

SADECE JSON DÖNDÜR.
"""

COMPARISON_PROMPT = """
Sen bir ürün karşılaştırma uzmanısın. Kullanıcı iki veya daha fazla ürünü karşılaştırmak istiyor.

Kullanıcı Profili:
- Harcama tipi: {spending_type}
- Bütçe durumu: {budget_status}
- Harcanabilir bütçe: {spendable} TL

Kullanıcı Sorusu: "{message}"{gift_context_text}
Karşılaştırılacak Ürünler: {comparison_products}

Bulunan Ürünler:
{products_text}

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

        return {
            "mode": "recommendation",
            "spending_type": spending_type,
            "budget_status": budget_status,
            "occasion": occasion,
            "recipient": recipient,
            "top_pick": llm_result.get("top_pick"),
            "summary": llm_result.get(
                "summary",
                f"{spending_type.capitalize()} profili için öneriler hazırlandı.",
            ),
            "financial_advice": llm_result.get("financial_advice", ""),
            "budget_warning": llm_result.get("budget_warning", False),
            "top_products": ranked_products,
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
