from supabase import create_client, Client
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("supabase_service")

_client: Client = None


def get_supabase() -> Client:
    global _client
    if _client is None:
        _client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
        logger.info("Supabase client initialized")
    return _client


class SupabaseService:
    def __init__(self):
        self.client = get_supabase()

    async def get_profile(self, user_id: str) -> dict | None:
        result = self.client.table("profiles").select("*").eq("id", user_id).single().execute()
        return result.data

    async def upsert_profile(self, data: dict) -> dict:
        result = self.client.table("profiles").upsert(data).execute()
        return result.data[0]

    async def get_personality(self, user_id: str) -> dict | None:
        result = (
            self.client.table("personality_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def save_personality(self, data: dict) -> dict:
        result = self.client.table("personality_profiles").insert(data).execute()
        return result.data[0]

    async def get_budget(self, user_id: str) -> dict | None:
        result = (
            self.client.table("budgets")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def upsert_budget(self, data: dict) -> dict:
        result = self.client.table("budgets").upsert(data).execute()
        return result.data[0]

    async def add_expense(self, data: dict) -> dict:
        result = self.client.table("expenses").insert(data).execute()
        return result.data[0]

    async def get_recent_expenses(self, user_id: str, limit: int = 10) -> list:
        """Kullanıcının en son eklediği harcamaları döner."""
        result = (
            self.client.table("expenses")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_current_month_expense_total(self, user_id: str) -> float:
        """Bu ay (UTC) eklenen harcamaların toplamını döner."""
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
        result = (
            self.client.table("expenses")
            .select("amount")
            .eq("user_id", user_id)
            .gte("created_at", month_start)
            .execute()
        )
        rows = result.data or []
        return float(sum((r.get("amount") or 0) for r in rows))

    async def get_expense(self, user_id: str, expense_id: str) -> dict | None:
        """Tek bir harcama kaydını döner (sahiplik kontrolü için)."""
        result = (
            self.client.table("expenses")
            .select("*")
            .eq("id", expense_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        return result.data[0] if result.data else None

    async def delete_expense(self, user_id: str, expense_id: str) -> None:
        """Bir harcama kaydını siler (sahiplik doğrulamasıyla)."""
        self.client.table("expenses").delete().eq(
            "id", expense_id
        ).eq("user_id", user_id).execute()

    async def save_chat(self, data: dict) -> dict:
        result = self.client.table("chat_history").insert(data).execute()
        return result.data[0]

    async def search_products(self, query: str = None, category: str = None, max_price: float = None) -> list:
        q = self.client.table("mock_products").select("*")
        if category:
            q = q.eq("category", category)
        if max_price:
            q = q.lte("price", max_price)
        result = q.execute()
        return result.data

    async def get_product(self, product_id: str) -> dict | None:
        result = self.client.table("mock_products").select("*").eq("id", product_id).single().execute()
        return result.data

    async def get_reviews(self, product_id: str) -> list:
        result = self.client.table("mock_reviews").select("*").eq("product_id", product_id).execute()
        return result.data

    async def save_recommendation(self, data: dict) -> dict:
        result = self.client.table("product_recommendations").insert(data).execute()
        return result.data[0]

    async def get_chat_history(self, user_id: str, limit: int = 20) -> list:
        result = (
            self.client.table("chat_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_conversation_starters(self, user_id: str, limit: int = 15) -> list:
        """Her sohbetin ilk user mesajını döner (session bazlı gruplama).
        Mesajlar arasında 30 dakikadan fazla boşluk varsa yeni sohbet sayılır.
        """
        from datetime import datetime, timedelta

        def parse_ts(ts_raw: str) -> datetime | None:
            try:
                ts_str = ts_raw.replace("Z", "+00:00").replace(" ", "T")
                if ts_str.endswith("+00"):
                    ts_str = ts_str[:-3] + "+00:00"
                return datetime.fromisoformat(ts_str)
            except Exception:
                return None

        # En son 200 user mesajını çek (yeterli veri için)
        result = (
            self.client.table("chat_history")
            .select("id, message, created_at, role, metadata")
            .eq("user_id", user_id)
            .eq("role", "user")
            .order("created_at", desc=False)  # eskiden yeniye sırala
            .limit(200)
            .execute()
        )
        messages = result.data or []
        if not messages:
            return []

        # Zaman bazlı oturum gruplama (30 dakika eşiği)
        session_gap = timedelta(minutes=30)
        sessions: list[dict] = []  # her session'ın ilk mesajı
        last_time: datetime | None = None

        for msg in messages:
            ts = parse_ts(msg["created_at"])
            if ts is None:
                continue  # parse edilemeyen mesajı atla

            if last_time is None or (ts - last_time) > session_gap:
                # Yeni oturum başladı, bu mesajı kaydet
                sessions.append(msg)

            last_time = ts

        # En yeni oturumlar üstte olsun, limit uygula
        sessions.reverse()
        return sessions[:limit]

    async def delete_chat_history(self, user_id: str) -> None:
        self.client.table("chat_history").delete().eq("user_id", user_id).execute()

    async def update_chat_title(self, chat_id: str, user_id: str, title: str) -> None:
        """Sohbet başlığını metadata içinde günceller."""
        result = self.client.table("chat_history").select("metadata").eq("id", chat_id).eq("user_id", user_id).single().execute()
        if not result.data:
            return
        
        metadata = result.data.get("metadata") or {}
        metadata["title"] = title
        
        self.client.table("chat_history").update({"metadata": metadata}).eq("id", chat_id).eq("user_id", user_id).execute()

    async def get_chat_thread(self, user_id: str, user_msg_id: str) -> list:
        """Eski endpoint - geriye dönük uyumluluk için bırakıldı."""
        return await self.get_session_messages(user_id, user_msg_id)

    async def get_session_messages(self, user_id: str, first_msg_id: str) -> list:
        """Bir session'daki TÜM mesajları döner.
        first_msg_id: o session'ın ilk kullanıcı mesajının ID'si.
        O mesajın zamanından başlayarak 30 dakika içindeki tüm mesajları getirir.
        Timestamp karşılaştırması Supabase'de değil Python'da yapılır (format uyumsuzluğunu önler).
        """
        from datetime import datetime, timedelta

        # Önce tüm kullanıcı mesajlarını kronolojik olarak çek
        all_msgs = (
            self.client.table("chat_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )
        messages = all_msgs.data or []
        if not messages:
            return []

        # Hedef mesajı bul ve başlangıç zamanını al
        start_ts: datetime | None = None
        for msg in messages:
            if msg["id"] == first_msg_id:
                try:
                    ts_str = msg["created_at"].replace("Z", "+00:00").replace(" ", "T")
                    # +00 → +00:00 normalize et (bazı Supabase sürümleri kısa format döner)
                    if ts_str.endswith("+00"):
                        ts_str = ts_str[:-3] + "+00:00"
                    start_ts = datetime.fromisoformat(ts_str)
                except Exception:
                    pass
                break

        if start_ts is None:
            return []

        end_ts = start_ts + timedelta(minutes=30)

        # Python'da filtrele: [start_ts, end_ts] aralığındaki mesajlar
        session_msgs = []
        for msg in messages:
            try:
                ts_str = msg["created_at"].replace("Z", "+00:00").replace(" ", "T")
                if ts_str.endswith("+00"):
                    ts_str = ts_str[:-3] + "+00:00"
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                continue
            if start_ts <= ts <= end_ts:
                session_msgs.append(msg)

        return session_msgs


    async def get_personality_history(self, user_id: str) -> list:
        result = (
            self.client.table("personality_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    # ── Watchlist ────────────────────────────────────────────────────────────

    async def get_watchlist(self, user_id: str) -> list:
        """Kullanıcının aktif takip listesini döner."""
        result = (
            self.client.table("watchlist")
            .select("*")
            .eq("user_id", user_id)
            .eq("is_active", True)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []

    async def add_to_watchlist(self, data: dict) -> dict:
        """Takip listesine yeni ürün ekler."""
        result = self.client.table("watchlist").insert(data).execute()
        return result.data[0]

    async def update_watchlist_item(self, watchlist_id: str, data: dict) -> None:
        """Takip listesi kaydını günceller (fiyat, tarih vb.)."""
        self.client.table("watchlist").update(data).eq("id", watchlist_id).execute()

    async def deactivate_watchlist_item(self, user_id: str, watchlist_id: str) -> None:
        """Takip listesi kaydını soft-delete yapar (is_active=False)."""
        self.client.table("watchlist").update({"is_active": False}).eq(
            "id", watchlist_id
        ).eq("user_id", user_id).execute()

    # ── Notifications ────────────────────────────────────────────────────────

    async def create_notification(self, data: dict) -> dict:
        """Yeni bildirim kaydı oluşturur."""
        result = self.client.table("notifications").insert(data).execute()
        return result.data[0]

    async def get_notifications(
        self, user_id: str, limit: int = 20, unread_only: bool = False
    ) -> list:
        """Kullanıcının bildirimlerini döner."""
        q = (
            self.client.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if unread_only:
            q = q.eq("is_read", False)
        result = q.execute()
        return result.data or []

    async def mark_notification_read(self, user_id: str, notification_id: str) -> None:
        """Bir bildirimi okundu yapar."""
        self.client.table("notifications").update({"is_read": True}).eq(
            "id", notification_id
        ).eq("user_id", user_id).execute()

    async def mark_all_notifications_read(self, user_id: str) -> None:
        """Kullanıcının tüm bildirimlerini okundu yapar."""
        self.client.table("notifications").update({"is_read": True}).eq(
            "user_id", user_id
        ).eq("is_read", False).execute()

    async def get_unread_notification_count(self, user_id: str) -> int:
        """Okunmamış bildirim sayısını döner."""
        result = (
            self.client.table("notifications")
            .select("id", count="exact")
            .eq("user_id", user_id)
            .eq("is_read", False)
            .execute()
        )
        return result.count or 0
