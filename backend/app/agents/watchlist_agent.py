"""
WatchlistAgent — Yıldızlı Ürün Takip Ajanı  (v2)
==================================================
İYİLEŞTİRMELER (v1 → v2):
  1. Eşzamanlı fiyat kontrolü  — asyncio.Semaphore ile paralel SerpAPI çağrısı
  2. Bildirim spam koruması    — son bildirimden bu yana cooldown süresi dolmadıysa atla
  3. Per-ürün alarm eşiği      — watchlist'teki her ürün için özel alert_threshold_pct
  4. SerpAPI retry + backoff   — başarısız istekte 3 denemeye kadar üstel bekleme
  5. Fiyat geçmişi kaydı       — price_history tablosuna her kontrol sonucu yazılır
  6. Trend özeti               — sonuç dict'e 7 günlük fiyat trendi eklenir

Çalışma akışı:
  execute({"user_id": ..., "mode": "check"})   → paralel fiyat kontrolü
  execute({"user_id": ..., "mode": "add",    "product": {...}})
  execute({"user_id": ..., "mode": "remove", "watchlist_id": "..."})
  execute({"user_id": ..., "mode": "list"})
  execute({"user_id": ..., "mode": "history", "watchlist_id": "..."})  ← YENİ
"""

import asyncio
import time
from datetime import datetime, timezone, timedelta
from typing import Optional

from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.config import settings


# ── Sabitler ─────────────────────────────────────────────────────────────────

# Kaç ürün aynı anda SerpAPI'ye gönderilsin?
CONCURRENCY_LIMIT = 3

# Aynı ürün için minimum bildirim aralığı (saat)
NOTIFICATION_COOLDOWN_HOURS = 24

# SerpAPI retry ayarları
SERPAPI_MAX_RETRIES = 3
SERPAPI_BACKOFF_BASE = 1.5  # saniye (1.5 → 2.25 → 3.375)


# ── LLM prompt: fiyat alarm metni ───────────────────────────────────────────
PRICE_DROP_ANALYSIS_PROMPT = """
Bir ürün fiyat analizi yapıyorsun.

Ürün: {product_name}
Referans fiyat: {old_price} TL
Güncel fiyat: {new_price} TL
İndirim oranı: %{discount_pct:.1f}
Fiyat trendi: {trend_label}

Kullanıcıya gösterilecek kısa, samimi ve motive edici bir bildirim metni yaz (max 2 cümle).
Türkçe yaz. Emoji kullanabilirsin. Trend varsa bunu da değerlendir.
Sadece bildirim metnini yaz, başka açıklama ekleme.
"""


class WatchlistAgent(BaseAgent):
    """Takip listesi + fiyat alarm ajanı (v2)."""

    # Varsayılan global alarm eşiği — per-ürün override edilebilir
    DEFAULT_DISCOUNT_PCT: float = 3.0

    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="watchlist_agent", llm=llm, db=db)
        # Eşzamanlı SerpAPI çağrısı limiti
        self._semaphore = asyncio.Semaphore(CONCURRENCY_LIMIT)

    # ================================================================
    # Ana giriş noktası
    # ================================================================

    async def execute(self, input_data: dict) -> dict:
        mode = input_data.get("mode", "check")
        user_id = input_data.get("user_id")

        if not user_id:
            return {"success": False, "error": "user_id gerekli"}

        dispatch = {
            "add":     lambda: self._add_to_watchlist(user_id, input_data.get("product", {})),
            "remove":  lambda: self._remove_from_watchlist(user_id, input_data.get("watchlist_id")),
            "list":    lambda: self._get_watchlist(user_id),
            "check":   lambda: self._check_prices(user_id),
            "history": lambda: self._get_price_history(user_id, input_data.get("watchlist_id")),
        }

        handler = dispatch.get(mode)
        if handler is None:
            return {"success": False, "error": f"Bilinmeyen mod: {mode}"}

        return await handler()

    # ================================================================
    # MOD: Ürünü takip listesine ekle
    # ================================================================

    async def _add_to_watchlist(self, user_id: str, product: dict) -> dict:
        if not product.get("name"):
            return {"success": False, "error": "Ürün adı gerekli"}

        try:
            row = {
                "user_id": user_id,
                "product_name": product.get("name"),
                "product_url": product.get("url", ""),
                "image_url": product.get("image_url", ""),
                "seller": product.get("seller", ""),
                "reference_price": float(product.get("price", 0)),
                "current_price": float(product.get("price", 0)),
                "search_query": product.get("search_query") or product.get("name"),
                # İYİLEŞTİRME 3: per-ürün eşik — belirtilmezse global varsayılan
                "alert_threshold_pct": float(
                    product.get("alert_threshold_pct") or self.DEFAULT_DISCOUNT_PCT
                ),
                "is_active": True,
                "last_checked_at": datetime.now(timezone.utc).isoformat(),
                "last_notified_at": None,  # İYİLEŞTİRME 2: cooldown için
            }

            result = (
                self.db.client
                .table("watchlist")
                .insert(row)
                .execute()
            )

            inserted = result.data[0] if result.data else row
            self.logger.info(
                f"Ürün takip listesine eklendi: {product.get('name')} | user={user_id}"
            )
            return {
                "success": True,
                "message": f"'{product.get('name')}' takip listesine eklendi.",
                "watchlist_item": inserted,
            }

        except Exception as e:
            self.logger.error(f"Watchlist ekleme hatası: {e}")
            return {"success": False, "error": str(e)}

    # ================================================================
    # MOD: Ürünü takip listesinden çıkar
    # ================================================================

    async def _remove_from_watchlist(self, user_id: str, watchlist_id: Optional[str]) -> dict:
        if not watchlist_id:
            return {"success": False, "error": "watchlist_id gerekli"}

        try:
            self.db.client.table("watchlist").update({"is_active": False}).eq(
                "id", watchlist_id
            ).eq("user_id", user_id).execute()

            self.logger.info(f"Ürün takip listesinden çıkarıldı: id={watchlist_id}")
            return {"success": True, "message": "Ürün takip listesinden çıkarıldı."}

        except Exception as e:
            self.logger.error(f"Watchlist silme hatası: {e}")
            return {"success": False, "error": str(e)}

    # ================================================================
    # MOD: Takip listesini getir
    # ================================================================

    async def _get_watchlist(self, user_id: str) -> dict:
        try:
            result = (
                self.db.client
                .table("watchlist")
                .select("*")
                .eq("user_id", user_id)
                .eq("is_active", True)
                .order("created_at", desc=True)
                .execute()
            )
            items = result.data or []
            return {"success": True, "count": len(items), "watchlist": items}

        except Exception as e:
            self.logger.error(f"Watchlist getirme hatası: {e}")
            return {"success": False, "error": str(e), "watchlist": []}

    # ================================================================
    # MOD: Fiyat geçmişi getir  [YENİ — v2]
    # ================================================================

    async def _get_price_history(self, user_id: str, watchlist_id: Optional[str]) -> dict:
        """Bir ürünün son 30 günlük fiyat geçmişini döner."""
        if not watchlist_id:
            return {"success": False, "error": "watchlist_id gerekli"}

        try:
            result = (
                self.db.client
                .table("price_history")
                .select("*")
                .eq("watchlist_id", watchlist_id)
                .eq("user_id", user_id)
                .order("checked_at", desc=False)
                .limit(60)   # ~30 gün × 2 kontrol/gün
                .execute()
            )
            records = result.data or []

            # Trend hesapla
            trend = self._calculate_trend(records)

            return {
                "success": True,
                "watchlist_id": watchlist_id,
                "history": records,
                "trend": trend,
            }

        except Exception as e:
            self.logger.error(f"Fiyat geçmişi hatası: {e}")
            return {"success": False, "error": str(e), "history": []}

    # ================================================================
    # MOD: Fiyatları kontrol et — PARALEL  [İYİLEŞTİRME 1]
    # ================================================================

    async def _check_prices(self, user_id: str) -> dict:
        """
        Takip listesindeki tüm ürünleri PARALEL olarak kontrol eder.
        asyncio.Semaphore ile eşzamanlılık CONCURRENCY_LIMIT ile sınırlandırılır.
        """
        watchlist_result = await self._get_watchlist(user_id)
        items = watchlist_result.get("watchlist", [])

        if not items:
            return {
                "success": True,
                "message": "Takip listesi boş.",
                "checked": 0,
                "alerts_triggered": 0,
            }

        self.logger.info(
            f"Paralel fiyat kontrolü başladı | user={user_id} "
            f"| {len(items)} ürün | eşzamanlılık={CONCURRENCY_LIMIT}"
        )

        # Her ürün için bir coroutine oluştur, hepsini aynı anda başlat
        tasks = [
            self._check_single_product_guarded(user_id, item)
            for item in items
        ]
        outcomes = await asyncio.gather(*tasks, return_exceptions=False)

        alerts_triggered = sum(1 for o in outcomes if o.get("alert_sent"))

        self.logger.info(
            f"Paralel kontrol tamamlandı | checked={len(outcomes)} "
            f"| alerts={alerts_triggered}"
        )

        return {
            "success": True,
            "checked": len(outcomes),
            "alerts_triggered": alerts_triggered,
            "results": outcomes,
        }

    async def _check_single_product_guarded(self, user_id: str, item: dict) -> dict:
        """Semaphore ile korunan wrapper — eşzamanlılık limiti burada uygulanır."""
        async with self._semaphore:
            try:
                return await self._check_single_product(user_id, item)
            except Exception as e:
                self.logger.error(
                    f"Ürün kontrolü hatası [{item.get('product_name')}]: {e}"
                )
                return {
                    "watchlist_id": item.get("id"),
                    "product_name": item.get("product_name"),
                    "alert_sent": False,
                    "error": str(e),
                }

    # ================================================================
    # Tek ürün kontrol mantığı
    # ================================================================

    async def _check_single_product(self, user_id: str, item: dict) -> dict:
        product_name     = item.get("product_name", "")
        search_query     = item.get("search_query") or product_name
        reference_price  = float(item.get("reference_price") or 0)
        watchlist_id     = item.get("id")

        # İYİLEŞTİRME 3: per-ürün eşik
        threshold_pct = float(
            item.get("alert_threshold_pct") or self.DEFAULT_DISCOUNT_PCT
        )

        # İYİLEŞTİRME 4: retry destekli SerpAPI çağrısı
        current_price = await asyncio.to_thread(
            self._fetch_current_price_with_retry, search_query
        )

        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload: dict = {
            "last_checked_at": now_iso,
            "current_price": current_price,
        }

        outcome = {
            "watchlist_id": watchlist_id,
            "product_name": product_name,
            "reference_price": reference_price,
            "current_price": current_price,
            "alert_sent": False,
        }

        # İYİLEŞTİRME 5: Fiyat geçmişi kaydet (fiyat alınamasada yaz)
        if current_price is not None:
            await self._save_price_history(user_id, watchlist_id, current_price, now_iso)

        # İndirim kontrolü
        if current_price and reference_price and current_price < reference_price:
            discount_pct = ((reference_price - current_price) / reference_price) * 100

            if discount_pct >= threshold_pct:
                # İYİLEŞTİRME 2: Cooldown kontrolü
                if self._is_cooldown_active(item):
                    self.logger.info(
                        f"Cooldown aktif, bildirim atlandı: {product_name}"
                    )
                    outcome["skipped_cooldown"] = True
                else:
                    # İYİLEŞTİRME 5: Trend etiketi hesapla
                    trend_label = await self._get_trend_label(watchlist_id, user_id)

                    notification_text = await self._generate_alert_text(
                        product_name, reference_price, current_price,
                        discount_pct, trend_label
                    )

                    await self._create_notification(
                        user_id=user_id,
                        watchlist_id=watchlist_id,
                        product_name=product_name,
                        old_price=reference_price,
                        new_price=current_price,
                        discount_pct=discount_pct,
                        notification_text=notification_text,
                    )

                    update_payload["reference_price"] = current_price
                    update_payload["last_notified_at"] = now_iso  # cooldown saat damgası

                    outcome.update({
                        "alert_sent": True,
                        "discount_pct": round(discount_pct, 1),
                        "notification_text": notification_text,
                        "trend": trend_label,
                    })

                    self.logger.info(
                        f"Fiyat alarmı! {product_name} | "
                        f"{reference_price} → {current_price} TL "
                        f"| %{discount_pct:.1f} | trend={trend_label}"
                    )

        # Watchlist satırını güncelle
        try:
            self.db.client.table("watchlist").update(update_payload).eq(
                "id", watchlist_id
            ).execute()
        except Exception as e:
            self.logger.error(f"Watchlist güncelleme hatası: {e}")

        return outcome

    # ================================================================
    # İYİLEŞTİRME 2: Cooldown kontrol yardımcısı
    # ================================================================

    def _is_cooldown_active(self, item: dict) -> bool:
        """Son bildirimden bu yana NOTIFICATION_COOLDOWN_HOURS geçmediyse True döner."""
        last_notified_raw = item.get("last_notified_at")
        if not last_notified_raw:
            return False
        try:
            last_notified = datetime.fromisoformat(last_notified_raw.replace("Z", "+00:00"))
            elapsed = datetime.now(timezone.utc) - last_notified
            return elapsed < timedelta(hours=NOTIFICATION_COOLDOWN_HOURS)
        except Exception:
            return False

    # ================================================================
    # İYİLEŞTİRME 4: SerpAPI — retry + exponential backoff
    # ================================================================

    def _fetch_current_price_with_retry(self, query: str) -> Optional[float]:
        """
        Google Shopping'de ürünü arar. Hata durumunda SERPAPI_MAX_RETRIES
        kez üstel beklemeyle yeniden dener.
        """
        last_err: Exception = Exception("Bilinmeyen hata")

        for attempt in range(1, SERPAPI_MAX_RETRIES + 1):
            try:
                result = self._fetch_current_price_sync(query)
                if result is not None:
                    return result
                # None döndü ama exception yok — ürün bulunamadı, retry yapma
                return None
            except Exception as e:
                last_err = e
                wait = SERPAPI_BACKOFF_BASE ** attempt
                self.logger.warning(
                    f"SerpAPI deneme {attempt}/{SERPAPI_MAX_RETRIES} başarısız "
                    f"({e}). {wait:.1f}s bekleniyor."
                )
                time.sleep(wait)

        self.logger.error(f"SerpAPI {SERPAPI_MAX_RETRIES} denemede başarısız: {last_err}")
        return None

    def _fetch_current_price_sync(self, query: str) -> Optional[float]:
        """Google Shopping'de ürünü arar, en düşük fiyatı döner."""
        from serpapi import GoogleSearch

        params = {
            "q": query,
            "tbm": "shop",
            "gl": "tr",
            "hl": "tr",
            "num": "5",
            "api_key": settings.SERPAPI_KEY,
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        items = results.get("shopping_results", [])

        prices = [
            p for item in items[:5]
            if (p := self._parse_price(item.get("price", ""))) and p > 0
        ]
        return min(prices) if prices else None

    def _parse_price(self, price_raw: str) -> Optional[float]:
        """Türkçe/İngilizce formatlı fiyat string'ini float'a çevirir."""
        try:
            cleaned = (
                price_raw.replace("₺", "")
                .replace("TL", "")
                .replace("\xa0", "")
                .strip()
            )
            if not cleaned:
                return None

            if "," in cleaned and "." in cleaned:
                if cleaned.rindex(".") > cleaned.rindex(","):
                    return float(cleaned.replace(",", ""))
                else:
                    return float(cleaned.replace(".", "").replace(",", "."))
            elif "," in cleaned:
                return float(cleaned.replace(",", "."))
            else:
                parts = cleaned.split(".")
                if len(parts) == 2 and len(parts[1]) == 3:
                    return float(cleaned.replace(".", ""))
                return float(cleaned)
        except Exception:
            return None

    # ================================================================
    # İYİLEŞTİRME 5: Fiyat geçmişi yardımcıları
    # ================================================================

    async def _save_price_history(
        self, user_id: str, watchlist_id: str, price: float, checked_at: str
    ) -> None:
        """Her kontrolde price_history tablosuna yeni satır yazar."""
        try:
            self.db.client.table("price_history").insert({
                "user_id": user_id,
                "watchlist_id": watchlist_id,
                "price": price,
                "checked_at": checked_at,
            }).execute()
        except Exception as e:
            self.logger.error(f"price_history kayıt hatası: {e}")

    async def _get_trend_label(self, watchlist_id: str, user_id: str) -> str:
        """
        Son 7 günlük verilere bakarak fiyat eğilimini hesaplar.
        Dönüş: 'düşüyor' | 'yükseliyor' | 'sabit' | 'veri yok'
        """
        try:
            week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            result = (
                self.db.client
                .table("price_history")
                .select("price, checked_at")
                .eq("watchlist_id", watchlist_id)
                .eq("user_id", user_id)
                .gte("checked_at", week_ago)
                .order("checked_at", desc=False)
                .execute()
            )
            records = result.data or []
            return self._calculate_trend(records)
        except Exception:
            return "veri yok"

    def _calculate_trend(self, records: list) -> str:
        """
        Verilen fiyat kayıtlarının eğilimini hesaplar.
        İlk yarı ile ikinci yarının ortalamasını karşılaştırır.
        """
        prices = [float(r["price"]) for r in records if r.get("price")]

        if len(prices) < 3:
            return "veri yok"

        mid = len(prices) // 2
        first_half_avg = sum(prices[:mid]) / mid
        second_half_avg = sum(prices[mid:]) / (len(prices) - mid)

        change_pct = ((second_half_avg - first_half_avg) / first_half_avg) * 100

        if change_pct <= -2:
            return "düşüyor"
        elif change_pct >= 2:
            return "yükseliyor"
        else:
            return "sabit"

    # ================================================================
    # LLM — bildirim metni üretimi (trend aware)
    # ================================================================

    async def _generate_alert_text(
        self,
        product_name: str,
        old_price: float,
        new_price: float,
        discount_pct: float,
        trend_label: str = "veri yok",
    ) -> str:
        try:
            prompt = PRICE_DROP_ANALYSIS_PROMPT.format(
                product_name=product_name,
                old_price=old_price,
                new_price=new_price,
                discount_pct=discount_pct,
                trend_label=trend_label,
            )
            text = await self.call_llm(prompt)
            return text.strip()
        except Exception as e:
            self.logger.error(f"Bildirim metni üretme hatası: {e}")
            return (
                f"🎉 {product_name} fiyatı düştü! "
                f"{old_price:,.0f} TL → {new_price:,.0f} TL "
                f"(%{discount_pct:.0f} indirim)"
            )

    # ================================================================
    # Supabase — bildirim kaydı oluştur
    # ================================================================

    async def _create_notification(
        self,
        user_id: str,
        watchlist_id: str,
        product_name: str,
        old_price: float,
        new_price: float,
        discount_pct: float,
        notification_text: str,
    ) -> None:
        try:
            row = {
                "user_id": user_id,
                "type": "price_drop",
                "title": f"Fiyat Düştü: {product_name[:60]}",
                "message": notification_text,
                "metadata": {
                    "watchlist_id": watchlist_id,
                    "product_name": product_name,
                    "old_price": old_price,
                    "new_price": new_price,
                    "discount_pct": round(discount_pct, 1),
                },
                "is_read": False,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }

            self.db.client.table("notifications").insert(row).execute()
            self.logger.info(f"Bildirim oluşturuldu: {product_name}")

        except Exception as e:
            self.logger.error(f"Bildirim kayıt hatası: {e}")
