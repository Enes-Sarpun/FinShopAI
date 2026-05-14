"""
Recommendation Agent — Geliştirilmiş Sürüm
=============================================
Değişiklikler:
  - Tüm personality skorları kullanılıyor (impulsive, research, saving)
  - Karşılaştırma modu eklendi (COMPARISON intent)
  - review_analysis.overall_sentiment → review_analysis.analysis.sentiment_score okunuyor
  - value_score hesaplama daha güçlü
  - Kişilik-ürün uyum skoru
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

Kullanıcı İsteği: "{message}"

Önerilen Ürünler:
{products_text}

Kullanıcı profiline göre kişiselleştirilmiş bir öneri yap.
- Impulsif skoru yüksekse: "fiyat/performans araştırın" vurgusu yap
- Tasarruf skoru yüksekse: ekonomik seçeneği öne çıkar
- Risk skoru yüksekse: dikkatli ol uyarısı ver

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

Kullanıcı Sorusu: "{message}"
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

        self.logger.info(
            f"Öneri üretiliyor | intent={intent} | ürün_sayısı={len(products)}"
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

        products_text = self._format_products(products)

        # Karşılaştırma modu
        if is_comparison and comparison_products:
            return await self._comparison_mode(
                message=message,
                comparison_products=comparison_products,
                products=products,
                products_text=products_text,
                spending_type=spending_type,
                budget_status=budget_status,
                spendable=spendable,
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
            )
            llm_result = await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri hatası: {e}")
            llm_result = {}

        ranked_products = self._rank_products(products, llm_result.get("ranking", []))

        return {
            "mode": "recommendation",
            "spending_type": spending_type,
            "budget_status": budget_status,
            "top_pick": llm_result.get("top_pick"),
            "summary": llm_result.get(
                "summary",
                f"{spending_type.capitalize()} profili için öneriler hazırlandı."
            ),
            "financial_advice": llm_result.get("financial_advice", ""),
            "budget_warning": llm_result.get("budget_warning", False),
            "top_products": ranked_products,
        }

    async def _comparison_mode(
        self,
        message: str,
        comparison_products: list,
        products: list,
        products_text: str,
        spending_type: str,
        budget_status: str,
        spendable: float,
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
            } if llm_result.get("winner") else None,
            "summary": llm_result.get("summary", "Karşılaştırma tamamlandı."),
            "financial_advice": llm_result.get("budget_recommendation", ""),
            "budget_warning": False,
            "top_products": ranked_products,
        }

    def _format_products(self, products: list) -> str:
        lines = []
        for i, p in enumerate(products[:5], 1):
            review = p.get("review_analysis", {})
            analysis = review.get("analysis", {})
            # sentiment_score veya overall_sentiment — her ikisini de dene
            sentiment = (
                analysis.get("sentiment")
                or analysis.get("overall_sentiment")
                or "bilinmiyor"
            )
            sentiment_score = analysis.get("sentiment_score", "?")
            rating = p.get("rating", 0)
            lines.append(
                f"{i}. {p.get('name', '')} | "
                f"Fiyat: {p.get('price', 0):,.0f} TL | "
                f"Satıcı: {p.get('seller', '')} | "
                f"Rating: {rating}/5 | "
                f"Duygu: {sentiment} ({sentiment_score})"
            )
        return "\n".join(lines)

    def _rank_products(self, products: list, llm_ranking: list) -> list:
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

        return sorted(products, key=lambda p: p.get("rating", 0), reverse=True)[:3]

    def _empty_result(self, message: str) -> dict:
        return {
            "mode": "recommendation",
            "spending_type": "dengeli",
            "budget_status": "unknown",
            "top_pick": None,
            "summary": message,
            "financial_advice": "",
            "budget_warning": False,
            "top_products": [],
        }
