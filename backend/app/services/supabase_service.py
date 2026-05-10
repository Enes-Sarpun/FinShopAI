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

    async def get_personality_history(self, user_id: str) -> list:
        result = (
            self.client.table("personality_profiles")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .execute()
        )
        return result.data or []
