from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService

RECOMMENDATION_PROMPT = """
Sen bir kişisel finans ve alışveriş danışmanısın.
Kullanıcının finansal profili ve bulunan ürünlere göre en iyi öneriyi yap.

Kullanıcı Profili:
- Harcama tipi: {spending_type}
- Risk skoru: {risk_score}/10
- Tasarruf skoru: {saving_score}/10
- Bütçe durumu: {budget_status}
- Harcanabilir bütçe: {spendable} TL

Kullanıcı İsteği: "{message}"

Önerilen Ürünler:
{products_text}

Aşağıdaki JSON formatında yanıt ver:
{{
    "top_pick": {{
        "product_name": "en iyi seçenek ürün adı",
        "reason": "neden bu ürünü öneriyorsun (2-3 cümle, kullanıcının finansal profiline göre)",
        "value_score": 1-10 arası değer puanı
    }},
    "summary": "tüm önerileri özetleyen 1-2 cümle mesaj",
    "financial_advice": "bu alışverişle ilgili kısa finansal tavsiye (kullanıcının spending_type'ına göre kişiselleştirilmiş)",
    "ranking": ["1. sıra ürün adı", "2. sıra ürün adı", "3. sıra ürün adı"]
}}

SADECE JSON DÖNDÜR.
"""


class RecommendationAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="recommendation_agent", llm=llm, db=db)

    async def execute(self, input_data: dict) -> dict:
        message = input_data.get("message", "")
        personality = input_data.get("personality") or {}
        budget = input_data.get("budget") or {}
        products = input_data.get("products") or []

        self.logger.info(f"Öneri üretiliyor | ürün_sayısı={len(products)}")

        if not products:
            return self._empty_result("Önerilecek ürün bulunamadı.")

        # Finansal metrikler
        spending_type = personality.get("spending_type", "dengeli")
        risk_score = personality.get("risk_score", 5)
        saving_score = personality.get("saving_score", 5)
        budget_status = budget.get("status", "unknown")
        financial_metrics = budget.get("financial_metrics", {})
        spendable = financial_metrics.get("spendable_after_savings", 0) or 0

        # Ürünleri metin formatına dök
        products_text = self._format_products(products)

        # LLM ile öneri üret
        try:
            prompt = RECOMMENDATION_PROMPT.format(
                spending_type=spending_type,
                risk_score=risk_score,
                saving_score=saving_score,
                budget_status=budget_status,
                spendable=f"{spendable:,.0f}",
                message=message,
                products_text=products_text
            )
            llm_result = await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri hatası: {e}")
            llm_result = {}

        # Ürünleri review analizine göre sırala (rating + review sentiment)
        ranked_products = self._rank_products(products, llm_result.get("ranking", []))

        return {
            "spending_type": spending_type,
            "budget_status": budget_status,
            "top_pick": llm_result.get("top_pick"),
            "summary": llm_result.get("summary", f"{spending_type.capitalize()} profili için öneriler hazırlandı."),
            "financial_advice": llm_result.get("financial_advice", ""),
            "top_products": ranked_products,
        }

    def _format_products(self, products: list) -> str:
        lines = []
        for i, p in enumerate(products[:5], 1):
            review = p.get("review_analysis", {})
            analysis = review.get("analysis", {})
            sentiment = analysis.get("overall_sentiment", "")
            rating = p.get("rating", 0)
            lines.append(
                f"{i}. {p.get('name', '')} | "
                f"Fiyat: {p.get('price', 0):,.0f} TL | "
                f"Satıcı: {p.get('seller', '')} | "
                f"Rating: {rating}/5 | "
                f"Yorum duygusu: {sentiment or 'bilinmiyor'}"
            )
        return "\n".join(lines)

    def _rank_products(self, products: list, llm_ranking: list) -> list:
        if llm_ranking:
            # LLM sıralamasına göre dizle
            name_to_product = {p.get("name", ""): p for p in products}
            ranked = []
            for name in llm_ranking:
                # Tam eşleşme veya kısmi eşleşme
                match = name_to_product.get(name)
                if not match:
                    match = next(
                        (p for p in products if name.lower() in p.get("name", "").lower()),
                        None
                    )
                if match and match not in ranked:
                    ranked.append(match)
            # Eşleşmeyen ürünleri sona ekle
            for p in products:
                if p not in ranked:
                    ranked.append(p)
            return ranked[:3]

        # LLM sıralaması yoksa rating'e göre sırala
        return sorted(products, key=lambda p: p.get("rating", 0), reverse=True)[:3]

    def _empty_result(self, message: str) -> dict:
        return {
            "spending_type": "dengeli",
            "budget_status": "unknown",
            "top_pick": None,
            "summary": message,
            "financial_advice": "",
            "top_products": [],
        }
