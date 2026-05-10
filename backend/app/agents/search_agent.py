import asyncio
from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.config import settings
from serpapi import GoogleSearch
import urllib.parse
from app.prompts.search_prompts import SEARCH_QUERY_PROMPT
from app.prompts.review_prompts import REVIEW_ANALYSIS_PROMPT


class SearchAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="search_agent", llm=llm, db=db)

    async def execute(self, input_data: dict) -> dict:
        query = input_data.get("query", "")
        budget = input_data.get("budget", None)
        user_id = input_data.get("user_id", None)

        self.logger.info(f"Arama başladı: {query}")

        # 1. LLM ile sorguyu parse et
        llm_parse_ok = False
        try:
            parsed = await self.call_llm_json(
                SEARCH_QUERY_PROMPT.format(query=query)
            )
            if not budget and parsed.get("max_price"):
                budget = parsed.get("max_price")
            self.logger.info(f"Parsed query: {parsed}")
            llm_parse_ok = True
        except Exception as e:
            self.logger.error(f"Sorgu parse hatası (LLM fallback aktif): {e}")
            parsed = {}

        # 2. Arama sorgusunu LLM'in ürettiği tag'lerden oluştur
        # LLM başarısız olduysa ham sorgudan anahtar kelime çıkar
        tags = parsed.get("tags", [])
        if tags:
            search_query = " ".join(tags)
        elif not llm_parse_ok:
            # LLM rate limit veya hata — ham sorgudan ilk 5 kelimeyi al
            words = query.split()
            search_query = " ".join(words[:5]) if len(words) > 5 else query
            self.logger.info(f"LLM fallback: kısaltılmış sorgu kullanılıyor")
        else:
            search_query = query
        self.logger.info(f"Search query: {search_query} | budget: {budget}")

        # 3. SerpAPI ile Google Shopping'den ürün çek (senkron → thread'de çalıştır)
        products = await asyncio.to_thread(self._search_google_shopping_sync, search_query, budget)

        # Sonuç boşsa ve LLM parse başarılıysa kısa tag'lerle tekrar dene
        if not products and tags and search_query != query:
            self.logger.info("Tag sorgusu sonuç vermedi, ham sorgu ile tekrar deneniyor")
            fallback_words = query.split()
            fallback_query = " ".join(fallback_words[:5]) if len(fallback_words) > 5 else query
            products = await asyncio.to_thread(self._search_google_shopping_sync, fallback_query, budget)

        # 4. Her ürün için LLM ile öneri nedeni üret
        for product in products[:3]:
            reason = await self._generate_reason(product)
            product["recommendation_reason"] = reason

        # 3. Supabase'e kaydet
        if user_id and products:
            await self._save_to_supabase(user_id, query, products)

        return {
            "query": query,
            "category": parsed.get("category", ""),
            "gift_context": parsed.get("gift_context", False),
            "total_found": len(products),
            "products": products
        }

    def _search_google_shopping_sync(self, query: str, budget: float = None) -> list:
        try:
            search_query = query
            if budget:
                search_query += f" {int(budget)} TL altı"

            params = {
                "q": search_query,
                "tbm": "shop",
                "gl": "tr",
                "hl": "tr",
                "api_key": settings.SERPAPI_KEY
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            products = []
            for item in results.get("shopping_results", [])[:10]:
                price_raw = item.get("price", "0")
                try:
                    price = float(
                        price_raw.replace("₺", "")
                        .replace("TL", "")
                        .replace(".", "")
                        .replace(",", ".")
                        .strip()
                    )
                except:
                    price = 0

                if budget and price > budget:
                    continue

                products.append({
                    "name": item.get("title", ""),
                    "price": price,
                    "seller": item.get("source", ""),
                    "rating": float(item.get("rating", 0)),
                    "description": item.get("snippet", ""),
                    "url": self._generate_url(item.get("title", ""), item.get("source", "")),
                    "image_url": item.get("thumbnail", ""),
                    "recommendation_reason": ""
                })

            return products

        except Exception as e:
            self.logger.error(f"SerpAPI hatası: {e}")
            return []

    def _generate_url(self, product_name: str, seller: str) -> str:
        encoded = urllib.parse.quote(product_name)
        seller_lower = seller.lower()

        if "trendyol" in seller_lower:
            return f"https://www.trendyol.com/sr?q={encoded}"
        elif "amazon" in seller_lower:
            return f"https://www.amazon.com.tr/s?k={encoded}"
        elif "hepsiburada" in seller_lower:
            return f"https://www.hepsiburada.com/ara?q={encoded}"
        elif "mediamarkt" in seller_lower:
            return f"https://www.mediamarkt.com.tr/tr/search.html?query={encoded}"
        elif "teknosa" in seller_lower:
            return f"https://www.teknosa.com/arama/?text={encoded}"
        else:
            return f"https://www.google.com/search?q={encoded}+sat%C4%B1n+al"

    async def _generate_reason(self, product: dict) -> str:
        try:
            prompt = REVIEW_ANALYSIS_PROMPT.format(
                product_name=product.get("name", ""),
                price=product.get("price", ""),
                source=product.get("seller", "")
            )
            return await self.call_llm(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri hatası: {e}")
            # LLM başarısız olduğunda fiyat bazlı statik fallback
            price = product.get("price", 0)
            seller = product.get("seller", "")
            name = product.get("name", "")
            return (
                f"{name}, {seller} üzerinde {price:,.0f} TL fiyatıyla sunulmaktadır. "
                f"Bütçenize uygun bu ürün, kaliteli bir seçenek olarak öne çıkmaktadır."
            )

    async def _save_to_supabase(self, user_id: str, query: str, products: list):
        try:
            rows = [
                {
                    "user_id": user_id,
                    "query": query,
                    "product_name": p.get("name"),
                    "price": p.get("price"),
                    "product_url": p.get("url"),
                    "recommendation_reason": p.get("recommendation_reason", ""),
                    "quality_score": int(p.get("rating", 0)),
                }
                for p in products
            ]
            self.db.client.table("product_recommendations").insert(rows).execute()
            self.logger.info(f"{len(rows)} ürün Supabase'e kaydedildi")
        except Exception as e:
            self.logger.error(f"Supabase kayıt hatası: {e}")