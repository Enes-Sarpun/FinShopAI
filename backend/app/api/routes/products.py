from fastapi import APIRouter
from app.agents.search_agent import SearchAgent
from app.agents.review_agent import ReviewAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService

router = APIRouter(tags=["products"])

@router.get("/search")
async def search_products(q: str, budget: float = None, user_id: str = None):
    llm = LLMService()
    db = SupabaseService()
    agent = SearchAgent(llm=llm, db=db)

    result = await agent.execute({
        "query": q,
        "budget": budget,
        "user_id": user_id
    })
    return result

@router.get("/{product_id}")
async def get_product(product_id: str):
    db = SupabaseService()
    result = db.client.table("mock_products") \
        .select("*") \
        .eq("id", product_id) \
        .execute()
    return result.data[0] if result.data else {"error": "Ürün bulunamadı"}

@router.get("/{product_name}/reviews")
async def get_product_reviews(
    product_name: str,
    product_id: str = None,
    price: float = 0,
    seller: str = "",
    rating: float = 0
):
    llm = LLMService()
    db = SupabaseService()
    agent = ReviewAgent(llm=llm, db=db)

    result = await agent.execute({
        "product_name": product_name,
        "product_id": product_id,
        "price": price,
        "seller": seller,
        "rating": rating
    })
    return result