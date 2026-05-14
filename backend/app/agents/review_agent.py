"""
Review Agent — Geliştirilmiş Sürüm
=====================================
Değişiklikler:
  - overall_sentiment alanı düzeltildi (sentiment_score + sentiment ikisi de döndürülüyor)
  - Yapay zeka analizi metadata'da işaretleniyor
"""

from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.prompts.review_prompts import REVIEW_SENTIMENT_PROMPT, REVIEW_SEARCH_PROMPT


class ReviewAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="review_agent", llm=llm, db=db)

    async def execute(self, input_data: dict) -> dict:
        product_name = input_data.get("product_name", "")
        product_id = input_data.get("product_id", None)
        price = input_data.get("price", 0)
        seller = input_data.get("seller", "")
        rating = input_data.get("rating", 0)

        self.logger.info(f"Yorum analizi başladı: {product_name}")

        # 1. Yorumları getir (cache veya LLM üret)
        reviews, is_ai_generated = await self._get_reviews(
            product_id, product_name, price, seller, rating
        )

        # 2. LLM ile duygu analizi yap
        analysis = await self._analyze_sentiment(product_name, reviews)

        # 3. overall_sentiment uyumluluk — eski kod bunu arıyor
        if "sentiment" in analysis and "overall_sentiment" not in analysis:
            analysis["overall_sentiment"] = analysis["sentiment"]

        # 4. Supabase'e kaydet (sadece gerçek yorum varsa)
        if product_id and not is_ai_generated:
            await self._save_reviews(product_id, reviews)

        return {
            "product_name": product_name,
            "price": price,
            "seller": seller,
            "review_count": len(reviews),
            "reviews": reviews,
            "analysis": analysis,
            "ai_generated": is_ai_generated,  # Şeffaflık için
        }

    async def _get_reviews(
        self, product_id: str, product_name: str, price: float, seller: str, rating: float
    ) -> tuple[list, bool]:
        """(reviews, is_ai_generated) döndürür."""
        # 1. Supabase cache'de ara
        if product_id:
            try:
                result = (
                    self.db.client
                    .table("mock_reviews")
                    .select("*")
                    .eq("product_id", product_id)
                    .execute()
                )
                if result.data:
                    self.logger.info(
                        f"Supabase cache'den {len(result.data)} yorum bulundu"
                    )
                    return result.data, False
            except Exception as e:
                self.logger.error(f"DB yorum hatası: {e}")

        # 2. LLM ile ürüne özgü yorum üret (yapay zeka)
        reviews = await self._generate_reviews(product_name, price, seller, rating)
        return reviews, True

    async def _generate_reviews(
        self,
        product_name: str,
        price: float = 0,
        seller: str = "",
        rating: float = 0,
    ) -> list:
        try:
            prompt = REVIEW_SEARCH_PROMPT.format(
                product_name=product_name,
                price=price,
                seller=seller,
                rating=rating,
            )
            result = await self.call_llm_json(prompt)
            return result.get("reviews", [])
        except Exception as e:
            self.logger.error(f"Yorum üretme hatası: {e}")
            return []

    async def _analyze_sentiment(self, product_name: str, reviews: list) -> dict:
        try:
            reviews_text = "\n".join([
                f"- ({r.get('rating', '?')}/5) "
                f"[{r.get('user_profile', 'Kullanıcı')}] "
                f"{r.get('comment', '')}"
                for r in reviews
            ])
            prompt = REVIEW_SENTIMENT_PROMPT.format(
                product_name=product_name,
                reviews=reviews_text,
            )
            result = await self.call_llm_json(prompt)
            # overall_sentiment normalize et
            if "sentiment" in result:
                result["overall_sentiment"] = result["sentiment"]
            return result
        except Exception as e:
            self.logger.error(f"Duygu analizi hatası: {e}")
            return {
                "sentiment_score": 0.5,
                "sentiment": "nötr",
                "overall_sentiment": "nötr",
                "summary": "Analiz yapılamadı.",
                "pros": [],
                "cons": [],
            }

    async def _save_reviews(self, product_id: str, reviews: list):
        try:
            rows = [
                {
                    "product_id": product_id,
                    "rating": r.get("rating"),
                    "comment": r.get("comment"),
                    "sentiment": r.get("sentiment"),
                }
                for r in reviews
            ]
            self.db.client.table("mock_reviews").insert(rows).execute()
            self.logger.info(f"{len(rows)} yorum Supabase'e kaydedildi")
        except Exception as e:
            self.logger.error(f"Yorum kayıt hatası: {e}")