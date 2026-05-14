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

    async def delete_chat_history(self, user_id: str) -> None:
        self.client.table("chat_history").delete().eq("user_id", user_id).execute()

    async def get_chat_thread(self, user_id: str, user_msg_id: str) -> list:
        """Bir kullanıcı mesajı ve ona ait asistan cevabını döner."""
        # Önce kullanıcı mesajını çek
        user_msg = (
            self.client.table("chat_history")
            .select("*")
            .eq("id", user_msg_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        if not user_msg.data:
            return []

        # Asistan cevabını metadata.user_msg_id ile bul
        # Supabase JSON filter: metadata->user_msg_id = user_msg_id
        assistant_msg = (
            self.client.table("chat_history")
            .select("*")
            .eq("user_id", user_id)
            .eq("role", "assistant")
            .filter("metadata->>user_msg_id", "eq", user_msg_id)
            .limit(1)
            .execute()
        )

        result = list(user_msg.data)
        if assistant_msg.data:
            result.extend(assistant_msg.data)
        return result

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
