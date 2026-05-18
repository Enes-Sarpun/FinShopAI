"""
Search Agent — v4 (Paralel Manus + SerpAPI)
=====================================
Değişiklikler:
  - Ürün deduplikasyonu (isim benzerliği > 80%)
  - Karşılaştırma modu desteği (is_comparison flag)
  - Daha fazla satıcı URL mapping
  - Fiyat parse iyileştirmesi (TL, ₺, virgül/nokta)
  - Senkron SerpAPI çağrısı hatasız asyncio.to_thread ile sarılı
  v4:
  - ENABLE_MANUS=true ise Manus + SerpAPI paralel çalışır
  - Sonuçlar birleştirilir, duplikatlar temizlenir
  - Manus veya SerpAPI down olsa bile diğeri devam eder
"""

import asyncio
import random
import re
import urllib.parse
from difflib import SequenceMatcher

from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.config import settings
from serpapi import GoogleSearch
from app.prompts.search_prompts import SEARCH_QUERY_PROMPT
from app.prompts.review_prompts import REVIEW_ANALYSIS_PROMPT


def infer_budget_from_context(
    user_budget: dict = None,
    recipient: str = None,
    occasion: str = None,
    personality: dict = None,
) -> dict:
    """
    Kullanıcı fiyat belirtmediyse akıllı bütçe tahmini yapar.
    Returns: { "min": float, "max": float, "auto_inferred": True }
    """
    CATEGORY_RANGES = {
        ("anne", None):              (300, 1500),
        ("anne", "doğum_günü"):      (400, 2000),
        ("anne", "anneler_günü"):    (350, 1500),
        ("anne", "yılbaşı"):         (400, 1800),
        ("baba", None):              (400, 2000),
        ("baba", "doğum_günü"):      (500, 2500),
        ("baba", "babalar_günü"):    (400, 1800),
        ("sevgili", None):           (500, 3000),
        ("sevgili", "sevgililer_günü"): (600, 2500),
        ("sevgili", "doğum_günü"):   (800, 3500),
        ("sevgili", "yılbaşı"):      (700, 3000),
        ("arkadaş", None):           (200, 800),
        ("arkadaş", "doğum_günü"):   (300, 1000),
        ("öğretmen", None):          (150, 600),
        (None, None):                (200, 1500),
    }

    r = (recipient or "").lower()
    o = (occasion or "").lower().replace(" ", "_")

    range_min, range_max = 200, 1500
    for key in [(r, o), (r, None), (None, None)]:
        if key in CATEGORY_RANGES:
            range_min, range_max = CATEGORY_RANGES[key]
            break

    if user_budget:
        # user_budget financial_metrics dict'i olabilir (spendable_after_savings içerir)
        spendable = (
            user_budget.get("spendable_after_savings")
            or user_budget.get("spendable")
            or 0
        )
        if spendable > 0:
            max_safe = spendable * 0.20
            range_max = min(range_max, max_safe)
            range_min = min(range_min, range_max * 0.4)

    if personality:
        if personality.get("saving_score", 5) >= 7:
            range_max *= 0.7
            range_min *= 0.8
        elif personality.get("impulsive_score", 5) >= 7:
            range_max *= 0.85

    return {"min": round(max(range_min, 50)), "max": round(range_max), "auto_inferred": True}


_CATEGORY_QUERIES = {
    "mücevher":      {"anne": "kadın gümüş kolye", "sevgili": "kadın gümüş bileklik", None: "gümüş takı"},
    "kişisel_bakım": {"anne": "kadın parfüm seti", "baba": "erkek parfüm", "sevgili": "parfüm hediye seti", None: "parfüm seti"},
    "premium_yaşam": {None: "premium çikolata hediye kutu"},
    "ev_dekorasyon": {None: "el yapımı seramik vazo"},
    "teknoloji":     {None: "bluetooth kulaklık"},
    "hobi":          {"baba": "erkek kol saati", None: "hediye seti"},
}


def _build_query_from_category(category: str, recipient: str = None) -> str:
    cat = _CATEGORY_QUERIES.get(category, {})
    return cat.get(recipient) or cat.get(None) or category.replace("_", " ")


_SPECIFIC_BRANDS = {
    "iphone", "samsung", "galaxy", "xiaomi", "huawei", "oppo", "realme",
    "oneplus", "sony", "motorola", "nokia", "asus", "lenovo", "hp", "dell",
    "acer", "msi", "macbook", "ipad", "airpods", "dyson", "casio", "seiko",
}
_SPECIFIC_MODEL_RE = re.compile(
    r"\b(iphone\s*\d+|galaxy\s*[a-z]?\d+|redmi|poco|mi\s*\d+|macbook|ipad|airpods)\b",
    re.IGNORECASE,
)
_STOP_SUFFIXES = (
    " almak istiyorum", " almak istiyorum.", " satın almak istiyorum",
    " öner", " önerir misin", " arıyorum", " bakıyorum",
    " istiyorum", " almayı düşünüyorum", " tavsiye et",
)


def _detect_specific_product(query: str) -> bool:
    """LLM olmadan kural tabanlı spesifik ürün/marka tespiti."""
    lower = query.lower()
    if _SPECIFIC_MODEL_RE.search(lower):
        return True
    return any(brand in lower for brand in _SPECIFIC_BRANDS)


def _clean_query_fallback(query: str) -> str:
    """
    LLM parse başarısız olduğunda ham sorgudan temiz arama sorgusu çıkar.
    Fiil/yardımcı kelimeler kırpılır, renk + ürün adı korunur.
    Örn: "pembe iPhone 16 almak istiyorum" → "pembe iPhone 16"
    """
    text = query.strip()
    lower = text.lower()
    for suffix in _STOP_SUFFIXES:
        if lower.endswith(suffix):
            text = text[: len(text) - len(suffix)].strip()
            lower = text.lower()
            break
    words = text.split()
    return " ".join(words[:6]) if len(words) > 6 else text


def _similarity(a: str, b: str) -> float:
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
        for idx, u in enumerate(unique):
            if _similarity(name, u.get("name", "")) >= threshold:
                if p.get("price", 0) < u.get("price", float("inf")):
                    unique[idx] = p
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
        occasion = input_data.get("occasion", "")
        recipient = input_data.get("recipient", "")

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

            # Hediye bağlamı varsa occasion/recipient güncelle
            if not occasion and parsed.get("occasion"):
                occasion = parsed["occasion"]
            if not recipient and parsed.get("recipient"):
                recipient = parsed["recipient"]
        except Exception as e:
            self.logger.error(f"Sorgu parse hatası (LLM fallback aktif): {e}")

        # 2. Arama sorgusunu oluştur
        tags = parsed.get("tags", [])
        recipient = recipient or parsed.get("recipient", "")
        occasion = occasion or parsed.get("occasion", "")
        gift_intent = parsed.get("gift_intent", False) or parsed.get("gift_context", False)
        inferred_categories = parsed.get("inferred_categories", [])
        previously_shown: list[str] = input_data.get("previously_shown") or []

        # Spesifik marka+model mi (iPhone 15) yoksa genel/kategori mi (bütçeme uygun iPhone)?
        is_specific_product = parsed.get("is_specific_product", False)
        # LLM parse başarısız olduysa kural tabanlı tespit
        if not llm_parse_ok:
            is_specific_product = _detect_specific_product(query)

        # Kullanıcı fiyat belirtmemişse → otomatik bütçe tahmini
        budget_was_inferred = False
        if not budget:
            user_budget_metrics = input_data.get("user_budget") or {}
            spendable = user_budget_metrics.get("spendable_after_savings") or 0

            # Spesifik ürün (iPhone 16, Samsung S24) → inferred budget uygulanmaz
            # Fiyatı önceden bilinemeyen ürünleri budget ile kesmek yanlış sonuç verir
            if is_specific_product:
                pass
            elif gift_intent and (recipient or occasion) and spendable > 0:
                inferred_bgt = infer_budget_from_context(
                    user_budget=user_budget_metrics,
                    recipient=recipient,
                    occasion=occasion,
                    personality=input_data.get("personality"),
                )
                budget = inferred_bgt["max"]
                budget_was_inferred = True
                self.logger.info(f"Hediye bütçe tahmini: {inferred_bgt}")
            elif spendable > 0:
                auto_max = min(max(spendable * 0.15, 200), 20000)
                budget = round(auto_max)
                budget_was_inferred = True
                self.logger.info(f"Genel bütçe tahmini: {budget} TL (spendable={spendable})")

        # Tag'ler varsa ilk tag'i kullan; LLM parse başarısızsa query'yi temizle
        if tags:
            search_query = tags[0]
        elif not llm_parse_ok:
            search_query = _clean_query_fallback(query)
        else:
            search_query = query

        self.logger.info(f"Search query: {search_query} | budget: {budget} | tags: {tags}")

        # 3. Ürün çek — ENABLE_MANUS=true ise paralel, yoksa sadece SerpAPI
        budget_range = None
        if budget:
            budget_range = {"min": 0, "max": float(budget)}
        over_budget_products: list = []
        budget_exceeded_warning: dict | None = None

        if settings.ENABLE_MANUS and self._is_user_in_manus_rollout(input_data.get("user_id")):
            # ── Paralel: Manus + SerpAPI aynı anda ──────────────────────────
            products = await self._parallel_search(search_query, budget, budget_range, parsed)
            self.logger.info(f"[search] paralel mod | {len(products)} ürün bulundu")
        else:
            # ── Legacy: Sadece SerpAPI ──────────────────────────────────────
            #
            # İKİ MOD:
            # A) Spesifik ürün (iPhone 15, Galaxy S24):
            #    → Bütçe filtresi olmadan ara, over_budget badge'i ile göster
            # B) Genel/kategori (bütçeme uygun iPhone, ucuz telefon):
            #    → Bütçe filtresiyle ara, boşsa kategori fallback

            if is_specific_product:
                # ── MOD A: Spesifik ürün — filtre yok, over_budget badge ────
                self.logger.info(f"[search] Spesifik ürün modu: {search_query}")
                raw = await asyncio.to_thread(
                    self._search_google_shopping_sync,
                    search_query, budget,
                    True,  # no_budget_filter
                    True,  # mark_over_budget
                )
                raw = [p for p in raw if not self._is_refurbished_or_grey_market(p)]
                products = raw[:5]
                # over_budget olarak işaretlenenleri ayır
                over_budget_products = [p for p in products if p.get("over_budget")]
                products = [p for p in products if not p.get("over_budget")]
                if over_budget_products and not products:
                    # Tamamı bütçeyi aşıyor
                    min_price = min(
                        (p["price"] for p in over_budget_products if p.get("price", 0) > 0),
                        default=0,
                    )
                    budget_exceeded_warning = {
                        "requested_query": search_query,
                        "min_found_price": round(min_price),
                        "user_budget": round(budget) if budget else 0,
                    }
                    self.logger.info(
                        f"[search] Spesifik ürün bütçeyi aşıyor | "
                        f"over_budget={len(over_budget_products)} | min={min_price} TL"
                    )
            else:
                # ── MOD B: Genel/kategori — bütçe filtresiyle ara ───────────
                products = await asyncio.to_thread(
                    self._search_google_shopping_sync, search_query, budget
                )
                products = [p for p in products if not self._is_refurbished_or_grey_market(p)]

                # Boş sonuçta kalan tag'leri sırayla dene
                if not products and len(tags) > 1:
                    for alt_tag in tags[1:]:
                        self.logger.info(f"Alternatif tag deneniyor: {alt_tag}")
                        raw = await asyncio.to_thread(
                            self._search_google_shopping_sync, alt_tag, budget
                        )
                        products = [p for p in raw if not self._is_refurbished_or_grey_market(p)]
                        if products:
                            break

                # Hâlâ boşsa ham sorguyu dene
                if not products and search_query != query:
                    words = query.split()
                    fallback_q = " ".join(words[:5]) if len(words) > 5 else query
                    raw = await asyncio.to_thread(
                        self._search_google_shopping_sync, fallback_q, budget
                    )
                    products = [p for p in raw if not self._is_refurbished_or_grey_market(p)]

                # inferred_categories fallback
                if not products and inferred_categories:
                    for cat in inferred_categories:
                        cat_query = _build_query_from_category(cat, recipient)
                        self.logger.info(f"Category fallback: {cat_query}")
                        raw = await asyncio.to_thread(
                            self._search_google_shopping_sync, cat_query, budget
                        )
                        products = [p for p in raw if not self._is_refurbished_or_grey_market(p)]
                        if products:
                            break

                # Son çare: hediye fallback
                if not products and (recipient or occasion):
                    fallback_query = self._get_gift_fallback(recipient, occasion, budget)
                    if fallback_query:
                        self.logger.info(f"Hediye fallback: {fallback_query}")
                        raw = await asyncio.to_thread(
                            self._search_google_shopping_sync, fallback_query, budget
                        )
                        products = [p for p in raw if not self._is_refurbished_or_grey_market(p)]

        # Daha önce gösterilen ürünleri filtrele (aynı sohbette tekrar gelmemesi için)
        if previously_shown:
            shown_cf = [s.casefold() for s in previously_shown]
            def _was_shown(p: dict) -> bool:
                name_cf = (p.get("name") or "").casefold()
                return any(_similarity(name_cf, s) >= 0.75 for s in shown_cf)
            before_filter = len(products)
            products = [p for p in products if not _was_shown(p)]
            if before_filter != len(products):
                self.logger.info(
                    f"[search] previously_shown filtre: {before_filter} → {len(products)} ürün"
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

        # 5. İlk 5 ürün için LLM öneri nedeni üret (BATCH — tek çağrı)
        top_products = products[:5]
        if top_products:
            reasons = await self._generate_reasons_batch(top_products, occasion, recipient)
            for i, product in enumerate(top_products):
                product["recommendation_reason"] = reasons.get(str(i + 1), "")

        # 6. Supabase'e kaydet
        if user_id and products:
            await self._save_to_supabase(user_id, query, products)

        return {
            "query": query,
            "category": parsed.get("category", ""),
            "gift_context": {
                "recipient": recipient,
                "occasion": occasion,
                "gift_intent": gift_intent,
                "budget_was_inferred": budget_was_inferred,
            },
            "is_comparison": is_comparison,
            "total_found": len(products),
            "products": products,
            "over_budget_products": over_budget_products,
            "budget_exceeded_warning": budget_exceeded_warning,
        }

    def _search_google_shopping_sync(
        self,
        query: str,
        budget: float = None,
        no_budget_filter: bool = False,
        mark_over_budget: bool = False,
    ) -> list:
        try:
            if not settings.SERPAPI_KEY:
                self.logger.error("SERPAPI_KEY boş — .env dosyasını kontrol et!")
                return []

            search_query = query

            params = {
                "engine": "google_shopping",
                "q": search_query,
                "gl": "tr",
                "hl": "tr",
                "api_key": settings.SERPAPI_KEY,
            }

            search = GoogleSearch(params)
            results = search.get_dict()

            self.logger.info(
                f"SerpAPI raw: query='{search_query}' "
                f"shopping_results={len(results.get('shopping_results', []))} "
                f"error={results.get('error', 'none')}"
            )

            products = []
            for item in results.get("shopping_results", [])[:12]:
                price_raw = item.get("price", "0")
                price = self._parse_price(price_raw)

                self.logger.debug(f"  item: {item.get('title','')[:40]} | price_raw={price_raw!r} | parsed={price}")

                # Fiyat parse edilemişse ve budget varsa filtrele
                # %20 tolerans: tahmini bütçede biraz esneklik ver
                if not no_budget_filter and budget and price > 0 and price > float(budget) * 1.20:
                    continue

                serpapi_product_id = (
                    item.get("product_id")
                    or item.get("serpapi_product_api_properties", {}).get("product_id")
                )

                seller = item.get("source", "")
                name = item.get("title", "")

                # SerpAPI gerçek URL'i varsa onu kullan, yoksa üret
                real_link = item.get("link") or item.get("product_link")
                product_url = real_link if real_link else self._generate_url(name, seller)

                product_entry = {
                    "name": name,
                    "price": price,
                    "seller": seller,
                    "rating": float(item.get("rating", 0) or 0),
                    "rating_count": int(item.get("reviews", 0) or 0),
                    "description": item.get("snippet", ""),
                    "url": product_url,
                    "image_url": item.get("thumbnail", ""),
                    "recommendation_reason": "",
                    "serpapi_product_id": serpapi_product_id,
                }
                if mark_over_budget and budget and price > float(budget) * 1.20:
                    product_entry["over_budget"] = True
                products.append(product_entry)

            return products

        except Exception as e:
            self.logger.error(f"SerpAPI hatası: {type(e).__name__}: {e}", exc_info=True)
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

    @staticmethod
    def _get_gift_fallback(recipient: str, occasion: str, budget: float = None) -> str:
        """
        recipient/occasion'a göre Google Shopping'de sonuç veren somut bir arama sorgusu döner.
        """
        r = (recipient or "").lower()
        o = (occasion or "").lower()

        # Alıcıya göre popüler hediye kategorileri
        recipient_map = {
            "baba":   ["erkek kol saati", "deri cüzdan erkek", "erkek parfüm"],
            "anne":   ["kadın çanta", "kadın parfüm", "altın kolye"],
            "eş":     ["takı seti", "parfüm", "çiçek aranjmanı"],
            "sevgili":["çiçek buketi", "takı kadın", "parfüm kadın"],
            "arkadaş":["bluetooth kulaklık", "kupa bardak kişiselleştirilmiş", "kitap seti"],
            "çocuk":  ["lego seti", "oyuncak araba", "peluş oyuncak"],
            "öğretmen":["kupa bardak", "çiçek", "ajanda seti"],
            "iş arkadaşı": ["kupa bardak", "çikolata kutusu", "ajanda"],
        }

        # Bütçeye göre seçim (yüksek bütçe → ilk seçenek, düşük bütçe → son seçenek)
        for key, options in recipient_map.items():
            if key in r:
                if budget and budget < 500:
                    return options[-1]
                return options[0]

        # Occasion'a göre generic fallback
        if "babalar" in o:
            return "erkek kol saati"
        if "anneler" in o:
            return "kadın çanta"
        if "doğum" in o:
            return "doğum günü hediyesi seti"
        if "sevgililer" in o:
            return "sevgiliye hediye seti"
        if "yılbaşı" in o or "noel" in o:
            return "yılbaşı hediye seti"
        if "mezuniyet" in o:
            return "mezuniyet hediyesi"

        return "hediye seti"

    async def _generate_reason(self, product: dict, occasion: str = "", recipient: str = "") -> str:
        try:
            prompt = REVIEW_ANALYSIS_PROMPT.format(
                product_name=product.get("name", ""),
                price=product.get("price", ""),
                source=product.get("seller", ""),
                occasion=occasion or "belirtilmedi",
                recipient=recipient or "belirtilmedi",
            )
            return await self.call_llm(prompt)
        except Exception as e:
            self.logger.error(f"LLM öneri hatası: {e}")
            return self._fallback_reason(product, occasion, recipient)

    async def _generate_reasons_batch(self, products: list, occasion: str = "", recipient: str = "") -> dict:
        """3 ürünü tek LLM çağrısında işle — batch prompting."""
        product_lines = []
        for i, p in enumerate(products, 1):
            product_lines.append(
                f"{i}. {p.get('name', '')} | Fiyat: {p.get('price', 0):,.0f} TL | "
                f"Satıcı: {p.get('seller', '')}"
            )

        prompt = (
            f"Aşağıdaki {len(products)} ürün için kısa birer öneri nedeni yaz.\n"
            f"Durum: {occasion or 'belirtilmedi'} | Kime: {recipient or 'belirtilmedi'}\n\n"
            + "\n".join(product_lines) + "\n\n"
            "JSON formatında yanıt ver:\n"
            '{"1": "ürün 1 öneri nedeni", "2": "ürün 2", "3": "ürün 3", "4": "ürün 4", "5": "ürün 5"}\n'
            "SADECE JSON DÖNDÜR."
        )

        try:
            result = await self.call_llm_json(prompt)
            return {str(k): str(v) for k, v in result.items()}
        except Exception as e:
            self.logger.error(f"Batch reason hatası: {e}")
            return {
                str(i + 1): self._fallback_reason(p, occasion, recipient)
                for i, p in enumerate(products)
            }

    @staticmethod
    def _fallback_reason(product: dict, occasion: str = "", recipient: str = "") -> str:
        price = product.get("price", 0)
        seller = product.get("seller", "")
        name = product.get("name", "")
        occasion_text = f"{occasion} için " if occasion else ""
        recipient_text = f"{recipient}'a " if recipient else ""
        return (
            f"{name}, {seller} üzerinde {price:,.0f} TL fiyatıyla sunulmaktadır. "
            f"{occasion_text}{recipient_text}bütçenize uygun kaliteli bir seçenek olarak öne çıkmaktadır."
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

    # ── FAZ 3: Paralel Manus + SerpAPI ──────────────────────────────────────

    def _is_user_in_manus_rollout(self, user_id: str | None) -> bool:
        """Her istek için rastgele seçim — MANUS_ROLLOUT_PERCENTAGE kadar şans."""
        pct = settings.MANUS_ROLLOUT_PERCENTAGE
        if pct >= 100:
            return True
        if pct <= 0:
            return False
        return random.randint(1, 100) <= pct

    async def _parallel_search(
        self,
        search_query: str,
        budget: float | None,
        budget_range: dict | None,
        parsed: dict,
    ) -> list:
        """Manus + SerpAPI paralel çalıştır, sonuçları birleştir."""
        from app.services.llm.factory import LLMFactory

        manus_client = LLMFactory.get_manus()

        manus_task = asyncio.create_task(
            self._safe_manus_search(manus_client, search_query, budget_range)
        )
        serpapi_task = asyncio.create_task(
            self._safe_serpapi_search(search_query, budget)
        )

        try:
            results = await asyncio.wait_for(
                asyncio.gather(manus_task, serpapi_task, return_exceptions=True),
                timeout=20,
            )
            manus_result, serpapi_result = results
        except asyncio.TimeoutError:
            self.logger.warning("[search] paralel arama timeout (20s)")
            manus_result = manus_task.result() if manus_task.done() else {"products": []}
            serpapi_result = serpapi_task.result() if serpapi_task.done() else {"products": []}
            for t in (manus_task, serpapi_task):
                if not t.done():
                    t.cancel()

        manus_products = (
            manus_result.get("products", []) if isinstance(manus_result, dict) else []
        )
        serpapi_products = (
            serpapi_result.get("products", []) if isinstance(serpapi_result, dict) else []
        )

        provider_log = []
        if manus_products:
            provider_log.append(f"manus={len(manus_products)}")
        if serpapi_products:
            provider_log.append(f"serpapi={len(serpapi_products)}")
        self.logger.info(f"[search] paralel sonuç | {', '.join(provider_log) or 'boş'}")

        merged = self._merge_results(manus_products, serpapi_products)

        # Manus da boşsa SerpAPI fallback zinciri
        if not merged:
            self.logger.info("[search] paralel sonuç boş, SerpAPI fallback zincirine geçiliyor")
            merged = await asyncio.to_thread(
                self._search_google_shopping_sync, search_query, budget
            )

        return merged

    async def _safe_manus_search(self, manus_client, query: str, budget_range: dict | None) -> dict:
        """Manus araması — hata fırlatmaz."""
        try:
            result = await manus_client.research_products(
                query=query,
                budget_range=budget_range,
                max_results=10,
            )
            if result.get("error"):
                self.logger.warning(f"[manus] error: {result['error']}")
                return {"products": []}
            # Manus ürünlerini ortak formata çevir
            normalized = []
            for p in result.get("products", []):
                normalized.append({
                    "name": p.get("name", ""),
                    "price": float(p.get("price") or 0),
                    "seller": p.get("source", "manus"),
                    "rating": float(p.get("rating") or 0),
                    "rating_count": int(p.get("review_count") or 0),
                    "description": p.get("description", ""),
                    "url": p.get("url", ""),
                    "image_url": p.get("image_url", ""),
                    "recommendation_reason": "",
                    "source_provider": "manus",
                })
            return {"products": normalized}
        except Exception as e:
            self.logger.warning(f"[manus] safe_search exception: {e}")
            return {"products": []}

    async def _safe_serpapi_search(self, query: str, budget: float | None) -> dict:
        """SerpAPI araması — hata fırlatmaz."""
        try:
            products = await asyncio.to_thread(
                self._search_google_shopping_sync, query, budget
            )
            for p in products:
                p["source_provider"] = "serpapi"
            return {"products": products}
        except Exception as e:
            self.logger.warning(f"[serpapi] safe_search exception: {e}")
            return {"products": []}

    def _merge_results(self, manus_products: list, serpapi_products: list) -> list:
        """
        İki kaynaktan gelen ürünleri birleştir.
        Manus öncelikli (daha zengin veri). SerpAPI tamamlayıcı.
        Benzer isimli ürünler tek seferde, en zengin veriyle gösterilir.
        """
        merged = []
        seen_names: set[str] = set()

        for product in manus_products:
            norm = self._normalize_product_name(product.get("name", ""))
            if norm and norm not in seen_names:
                merged.append(product)
                seen_names.add(norm)

        for product in serpapi_products:
            norm = self._normalize_product_name(product.get("name", ""))
            if norm and norm not in seen_names:
                merged.append(product)
                seen_names.add(norm)
            else:
                # Aynı ürün varsa daha ucuz fiyatı işaretle
                self._update_with_better_price(merged, norm, product)

        # Rating + fiyat skoruna göre sırala
        merged.sort(
            key=lambda p: (
                p.get("rating", 0),
                1 if p.get("source_provider") == "manus" else 0,
                -(p.get("price") or 999999),
            ),
            reverse=True,
        )
        return merged[:10]

    @staticmethod
    def _normalize_product_name(name: str) -> str:
        """Ürün isimlerini eşleştirme için normalize et."""
        if not name:
            return ""
        n = name.lower()
        n = re.sub(r"[^a-z0-9çğışöüâîû]", "", n)
        return n[:20]

    @staticmethod
    def _is_refurbished_or_grey_market(product: dict) -> bool:
        """
        Yenilenmiş, yurt dışı veya gray market ürünü mü?
        casefold() kullanılır — Türkçe İ/ı büyük/küçük harf dönüşümü
        Python str.lower() ile tam çalışmayabileceğinden casefold() daha güvenli.
        """
        _KEYWORDS = [
            "yenilenmiş", "yenilenmis", "refurbished", "renewed",
            "yurt dışı", "yurt disi", "gray market", "grey market",
            "ithal", "paralel ithalat", "outlet", "teşhir", "teshir",
            "açık kutu", "acik kutu", "open box",
            "kullanılmış", "kullanilmis", "ikinci el", "2. el",
            "- iyi", "- çok iyi", "- mükemmel",  # Trendyol yenilenmiş notasyonu
        ]
        name_cf = (product.get("name") or "").casefold()
        desc_cf = (product.get("description") or "").casefold()
        seller_cf = (product.get("seller") or "").casefold()
        text = name_cf + " " + desc_cf + " " + seller_cf
        return any(kw.casefold() in text for kw in _KEYWORDS)

    @staticmethod
    def _build_brand_alt_query(brand: str, original_query: str, inferred_categories: list) -> str:
        """
        Bütçeye uygun alternatif için arama sorgusu üret.
        Sadece marka adı yerine marka + kategori ipucu kullan.
        Örn: brand="iPhone", query="iPhone 16" → "iPhone ucuz modeller"
             brand="Apple", query="iPhone" → "Apple iPhone uygun fiyat"
             brand="Samsung", query="Samsung Galaxy S24" → "Samsung Galaxy uygun fiyat"
        """
        # Marka → kategori eşlemesi
        _BRAND_CATEGORY = {
            "iphone": "iPhone",
            "apple": "Apple iPhone",
            "samsung": "Samsung Galaxy",
            "xiaomi": "Xiaomi telefon",
            "huawei": "Huawei telefon",
            "dyson": "Dyson",
            "nike": "Nike",
            "adidas": "Adidas",
        }
        brand_lower = brand.lower()
        base = _BRAND_CATEGORY.get(brand_lower, brand)

        # inferred_categories'den kategori ipucu al
        cat_hint = ""
        if inferred_categories:
            cat_map = {
                "akıllı telefon": "telefon",
                "telefon": "telefon",
                "laptop": "laptop",
                "bilgisayar": "bilgisayar",
                "kulaklık": "kulaklık",
                "tablet": "tablet",
                "saat": "saat",
            }
            for cat in inferred_categories:
                mapped = cat_map.get(cat.lower())
                if mapped and mapped.lower() not in base.lower():
                    cat_hint = mapped
                    break

        if cat_hint:
            return f"{base} {cat_hint} uygun fiyat"
        return f"{base} uygun fiyat"

    @staticmethod
    def _extract_brand(query: str) -> str:
        """
        Arama sorgusundan marka adını çıkar.
        Örn: "iPhone 15" → "iPhone", "Samsung Galaxy S24" → "Samsung"
        """
        _KNOWN_BRANDS = [
            "apple", "iphone", "samsung", "xiaomi", "huawei", "oppo", "vivo",
            "realme", "oneplus", "sony", "lg", "motorola", "nokia", "asus",
            "lenovo", "hp", "dell", "acer", "msi", "dyson", "nike", "adidas",
            "puma", "zara", "h&m", "philips", "bosch", "siemens", "arçelik",
            "vestel", "beko", "grundig", "casio", "citizen", "seiko",
        ]
        lower = query.lower()
        for brand in _KNOWN_BRANDS:
            if brand in lower:
                # İlk kelimeyi de kontrol et (Samsung Galaxy → Samsung)
                words = query.split()
                if words and words[0].lower() == brand:
                    return words[0]
                return brand.capitalize()
        # Sorgunun ilk kelimesi büyük harfle başlıyorsa marka olabilir
        words = query.split()
        if words and words[0][0].isupper():
            return words[0]
        return ""

    @staticmethod
    def _update_with_better_price(merged: list, norm_name: str, new_product: dict):
        """Aynı ürün varsa daha ucuz fiyatı 'alternative_price' olarak işaretle."""
        for existing in merged:
            ex_norm = re.sub(r"[^a-z0-9çğışöüâîû]", "", existing.get("name", "").lower())[:20]
            if ex_norm == norm_name:
                ep = existing.get("price") or 0
                np_ = new_product.get("price") or 0
                if np_ > 0 and (ep == 0 or np_ < ep):
                    existing["alternative_price"] = {
                        "price": np_,
                        "source": new_product.get("seller", ""),
                        "url": new_product.get("url", ""),
                    }
                break