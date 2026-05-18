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

    async def get_chat_history_by_conversation(
        self, user_id: str, conversation_id: str, limit: int = 20
    ) -> list:
        """Belirli bir konuşmaya ait mesajları döner (conversation_id filtreli)."""
        result = (
            self.client.table("chat_history")
            .select("*")
            .eq("user_id", user_id)
            .eq("metadata->>conversation_id", conversation_id)
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return result.data or []

    async def get_conversation_starters(self, user_id: str, limit: int = 15) -> list:
        """Her sohbetin ilk user mesajını döner.

        Önce mesajın metadata.conversation_id alanına bakar; bu alan yeni mesajlarda
        konuşmayı net biçimde gruplar. Metadata'sı olmayan eski mesajlar için
        zaman bazlı (30 dakika) fallback uygulanır.
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

        session_gap = timedelta(minutes=30)
        # Her conversation'ın ilk user mesajını saklayacağımız haritalar:
        first_by_conv: dict[str, dict] = {}
        # Eski (metadata'sı olmayan) mesajlar için zaman bazlı fallback grupları
        legacy_sessions: list[dict] = []
        last_legacy_time: datetime | None = None

        for msg in messages:
            ts = parse_ts(msg["created_at"])
            if ts is None:
                continue

            metadata = msg.get("metadata") or {}
            conv_id = metadata.get("conversation_id") if isinstance(metadata, dict) else None

            if conv_id:
                # Yeni format: doğrudan conversation_id ile grupla.
                if conv_id not in first_by_conv:
                    first_by_conv[conv_id] = msg
                # Bu mesaj fallback zincirini de bozabilir; legacy timeline'ı
                # sıfırla ki sonradan gelen eski (metadata'sız) mesajlar
                # bu yeni mesajla aynı 30-dk içinde diye birleşmesin.
                last_legacy_time = ts
            else:
                # Legacy: 30 dakika gap mantığı
                if last_legacy_time is None or (ts - last_legacy_time) > session_gap:
                    legacy_sessions.append(msg)
                last_legacy_time = ts

        # Her iki grubu birleştir, en yeni üstte olacak şekilde sırala
        combined = list(first_by_conv.values()) + legacy_sessions
        combined.sort(
            key=lambda m: parse_ts(m["created_at"]) or datetime.min,
            reverse=True,
        )
        return combined[:limit]

    async def delete_chat_history(self, user_id: str) -> None:
        self.client.table("chat_history").delete().eq("user_id", user_id).execute()

    async def delete_chat_session(self, user_id: str, first_msg_id: str) -> int:
        """Tek bir sohbeti (session) siler.
        first_msg_id: o session'ın ilk kullanıcı mesajının ID'si.
        get_session_messages ile aynı mantık (30 dk pencere) kullanılır,
        böylece sidebar'da gösterilen sohbet ile birebir aynı mesajlar silinir.
        Geriye silinen kayıt sayısı döner.
        """
        messages = await self.get_session_messages(user_id, first_msg_id)
        if not messages:
            return 0

        ids = [m["id"] for m in messages if m.get("id")]
        if not ids:
            return 0

        self.client.table("chat_history").delete().in_("id", ids).eq("user_id", user_id).execute()
        return len(ids)

    async def update_avatar(self, user_id: str, avatar_url: str | None) -> None:
        """Kullanıcının profil fotoğrafını günceller (base64 data URL veya None)."""
        self.client.table("profiles").update(
            {"avatar_url": avatar_url}
        ).eq("id", user_id).execute()

    async def update_chat_title(self, chat_id: str, user_id: str, title: str) -> None:
        """Sohbet başlığını metadata içinde günceller."""
        result = self.client.table("chat_history").select("metadata").eq("id", chat_id).eq("user_id", user_id).single().execute()
        if not result.data:
            return

        metadata = result.data.get("metadata") or {}
        metadata["title"] = title

        self.client.table("chat_history").update({"metadata": metadata}).eq("id", chat_id).eq("user_id", user_id).execute()

    async def update_chat_metadata(self, chat_id: str, user_id: str, metadata: dict) -> None:
        """Bir chat_history satırının metadata alanını tamamen değiştirir."""
        self.client.table("chat_history").update({"metadata": metadata}).eq("id", chat_id).eq("user_id", user_id).execute()

    async def get_chat_thread(self, user_id: str, user_msg_id: str) -> list:
        """Eski endpoint - geriye dönük uyumluluk için bırakıldı."""
        return await self.get_session_messages(user_id, user_msg_id)

    async def get_session_messages(self, user_id: str, first_msg_id: str) -> list:
        """Bir sohbete ait TÜM mesajları döner.

        Öncelik sırası:
          1. Eğer hedef mesajın metadata.conversation_id alanı varsa, aynı
             conversation_id'ye sahip tüm mesajlar (user + assistant) döner.
          2. Yoksa eski 30-dakikalık zaman penceresi mantığı uygulanır
             (geriye dönük uyumluluk).
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

        # Önce hedef mesajı kendisi sorgula — büyük tabloda tek satır lookup hızlıdır.
        target_resp = (
            self.client.table("chat_history")
            .select("*")
            .eq("id", first_msg_id)
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )
        target_rows = target_resp.data or []
        if not target_rows:
            return []
        target = target_rows[0]

        target_meta = target.get("metadata") or {}
        target_conv_id = target_meta.get("conversation_id") if isinstance(target_meta, dict) else None

        # ── 1) Yeni format: conversation_id eşleşmesi ──
        if target_conv_id:
            # Kullanıcının metadata.conversation_id'si target_conv_id olan veya
            # mesajın kendi id'si target_conv_id olan tüm satırları çek.
            # Supabase PostgREST JSON filter: metadata->>conversation_id=eq.<id>
            try:
                resp_meta = (
                    self.client.table("chat_history")
                    .select("*")
                    .eq("user_id", user_id)
                    .eq("metadata->>conversation_id", target_conv_id)
                    .order("created_at", desc=False)
                    .execute()
                )
                msgs_meta = resp_meta.data or []
            except Exception:
                msgs_meta = []

            # İlk user mesajı (conversation root) bazen metadata olmadan kayıt
            # edilmiş olabilir (özellikle migration öncesi). Onu da ekleyelim.
            ids_in_set = {m["id"] for m in msgs_meta}
            if target["id"] not in ids_in_set:
                msgs_meta.insert(0, target)

            # Kronolojik sırala
            msgs_meta.sort(key=lambda m: parse_ts(m["created_at"]) or datetime.min)
            return msgs_meta

        # ── 2) Legacy: 30-dakika zaman penceresi ──
        start_ts = parse_ts(target["created_at"])
        if start_ts is None:
            return [target]
        end_ts = start_ts + timedelta(minutes=30)

        all_msgs = (
            self.client.table("chat_history")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=False)
            .limit(500)
            .execute()
        )
        messages = all_msgs.data or []
        session_msgs = []
        for msg in messages:
            ts = parse_ts(msg["created_at"])
            if ts is None:
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
