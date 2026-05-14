"""
Search Agent — Geliştirilmiş Sürüm
=====================================
Değişiklikler:
  - Ürün deduplikasyonu (isim benzerliği > 80%)
  - Karşılaştırma modu desteği (is_comparison flag)
  - Daha fazla satıcı URL mapping
  - Fiyat parse iyileştirmesi (TL, ₺, virgül/nokta)
  - Senkron SerpAPI çağrısı hatasız asyncio.to_thread ile sarılı (zaten vardı)
"""

import asyncio
import urllib.parse
from difflib import SequenceMatcher

from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.config import settings
from serpapi import GoogleSearch
from app.prompts.search_prompts import SEARCH_QUERY_PROMPT
from app.prompts.review_prompts import REVIEW_ANALYSIS_PROMPT


def _similarity(a: str, b: str) -> float:
    """İki string arasındaki benzerlik oranı (0-1)."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _deduplicate(products: list, threshold: float = 0.80) -> list:
    """
    İsim benzerliği yüksek ürünleri çıkar.
    Daha düşük fiyatlı olanı (veya ilk geleni) tutar.
    """
    unique = []
    for p in products:
        name = p.get("name", "")
        is_dup = False
        for u in unique:
            if _similarity(name, u.get("name", "")) >= threshold:
                # Daha ucuz olanı tut
                if p.get("price", 0) < u.get("price", float("inf")):
                    unique.remove(u)
                    unique.append(p)
                is_dup = True
                break
        if not is_dup:
            unique.append(p)
    return unique


# Satıcı → URL mapping (genişletilmiş)
_SELLER_URL_MAP = {
    "trendyol": lambda q: f"https://www.trendyol.com/sr?q={q}",
    "amazon": lambda q: f"https://www.amazon.com.tr/s?k={q}",
    "hepsiburada": lambda q: f"https://www.hepsiburada.com/ara?q={q}",
    "mediamarkt": lambda q: f"https://www.mediamarkt.com.tr/tr/search.html?query={q}",
    "teknosa": lambda q: f"https://www.teknosa.com/arama/?text={q}",
    "vatanbilgisayar": lambda q: f"https://www.vatanbilgisayar.com/ara/?q={q}",
    "itopya": lambda q: f"https://www.itopya.com/arama.aspx?q={q}",
    "n11": lambda q: f"https://www.n11.com/arama?q={q}",
    "gittigidiyor": lambda q: f"https://www.gittigidiyor.com/arama?k={q}",
    "çiçeksepeti": lambda q: f"https://www.ciceksepeti.com/arama?term={q}",
    "morhipo": lambda q: f"https://www.morhipo.com/search?search={q}",
    "boyner": lambda q: f"https://www.boyner.com.tr/arama?searchTerm={q}",
    "lcwaikiki": lambda q: f"https://www.lcwaikiki.com/tr-TR/TR/search?q={q}",
    "zara": lambda q: f"https://www.zara.com/tr/tr/search?searchTerm={q}",
}


class SearchAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="search_agent", llm=llm, db=db)

    async def execute(self, input_data: dict) -> dict:
        query = input_data.get("query", "")
        budget = input_data.get("budget", None)
        user_id = input_data.get("user_id", None)
        is_comparison = input_data.get("is_comparison", False)
        comparison_products = input_data.get("comparison_products", [])

        self.logger.info(f"Arama başladı: {query} | comparison={is_comparison}")

        # 1. LLM ile sorguyu parse et
        llm_parse_ok = False
        parsed = {}
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

        # 2. Arama sorgusunu oluştur
        tags = parsed.get("tags", [])
        if tags:
            search_query = " ".join(tags)
        elif not llm_parse_ok:
            words = query.split()
            search_query = " ".join(words[:5]) if len(words) > 5 else query
        else:
            search_query = query

        self.logger.info(f"Search query: {search_query} | budget: {budget}")

        # 3. SerpAPI ile ürün çek
        products = await asyncio.to_thread(
            self._search_google_shopping_sync, search_query, budget
        )

        # Boş sonuçta ham sorgu ile tekrar dene
        if not products and tags and search_query != query:
            self.logger.info("Tag sorgusu boş, ham sorgu ile tekrar deneniyor")
            words = query.split()
            fallback = " ".join(words[:5]) if len(words) > 5 else query
            products = await asyncio.to_thread(
                self._search_google_shopping_sync, fallback, budget
            )

        # Karşılaştırma modunda: her ürün için ayrı arama yap
        if is_comparison and comparison_products and len(products) < 2:
            self.logger.info("Karşılaştırma modu: ayrı aramalar yapılıyor")
            all_products = []
            for cp in comparison_products[:3]:
                cp_products = await asyncio.to_thread(
                    self._search_google_shopping_sync, cp, budget
                )
                if cp_products:
                    all_products.append(cp_products[0])  # Her ürünün en iyisi
            if all_products:
                products = all_products

        # 4. Deduplikasyon
        before = len(products)
        products = _deduplicate(products)
        if before != len(products):
            self.logger.info(f"Deduplicated: {before} → {len(products)} ürün")

        # 5. İlk 3 ürün için LLM öneri nedeni üret
        for product in products[:3]:
            reason = await self._generate_reason(product)
            product["recommendation_reason"] = reason

        # 6. Supabase'e kaydet
        if user_id and products:
            await self._save_to_supabase(user_id, query, products)

        return {
            "query": query,
            "category": parsed.get("category", ""),
            "gift_context": parsed.get("gift_context", False),
            "is_comparison": is_comparison,
            "total_found": len(products),
            "products": products,
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
                "api_key": settings.SERPAPI_KEY,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            products = []
            for item in results.get("shopping_results", [])[:12]:
                price_raw = item.get("price", "0")
                price = self._parse_price(price_raw)

                if budget and price > budget:
                    continue

                serpapi_product_id = (
                    item.get("product_id")
                    or item.get("serpapi_product_api_properties", {}).get("product_id")
                )

                seller = item.get("source", "")
                name = item.get("title", "")

                products.append({
                    "name": name,
                    "price": price,
                    "seller": seller,
                    "rating": float(item.get("rating", 0) or 0),
                    "rating_count": int(item.get("reviews", 0) or 0),
                    "description": item.get("snippet", ""),
                    "url": self._generate_url(name, seller),
                    "image_url": item.get("thumbnail", ""),
                    "recommendation_reason": "",
                    "serpapi_product_id": serpapi_product_id,
                })

            return products

        except Exception as e:
            self.logger.error(f"SerpAPI hatası: {e}")
            return []

    @staticmethod
    def _parse_price(price_raw: str) -> float:
        """Fiyat string'ini float'a çevir. Türk formatı: 1.234,56 TL"""
        try:
            cleaned = (
                price_raw
                .replace("₺", "")
                .replace("TL", "")
                .replace("\xa0", "")
                .strip()
            )
            # Türk formatı: nokta binlik ayraç, virgül ondalık
            if "," in cleaned and "." in cleaned:
                # 1.234,56 → 1234.56
                cleaned = cleaned.replace(".", "").replace(",", ".")
            elif "," in cleaned:
                # 1234,56 → 1234.56
                cleaned = cleaned.replace(",", ".")
            else:
                # 1.234 → 1234
                if cleaned.count(".") == 1 and len(cleaned.split(".")[-1]) == 3:
                    cleaned = cleaned.replace(".", "")
            return float(cleaned)
        except Exception:
            return 0.0

    def _generate_url(self, product_name: str, seller: str) -> str:
        encoded = urllib.parse.quote(product_name)
        seller_lower = seller.lower()
        for key, url_fn in _SELLER_URL_MAP.items():
            if key in seller_lower:
                return url_fn(encoded)
        return f"https://www.google.com/search?q={encoded}+satın+al"

    async def _generate_reason(self, product: dict) -> str:
        try:
            prompt = REVIEW_ANALYSIS_PROMPT.format(
                product_name=product.get("name", ""),
                price=product.get("price", ""),
                source=product.get("seller", ""),
            )
            return await self.call_llm(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri nedeni hatası: {e}")
            price = product.get("price", 0)
            seller = product.get("seller", "")
            name = product.get("name", "")
            return (
                f"{name}, {seller} üzerinde {price:,.0f} TL fiyatıyla sunulmaktadır. "
                f"Bütçenize uygun bu ürün kaliteli bir seçenek olarak öne çıkmaktadır."
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