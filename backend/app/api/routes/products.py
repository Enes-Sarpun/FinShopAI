from fastapi import APIRouter, Depends
from app.agents.search_agent import SearchAgent
from app.agents.review_agent import ReviewAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter(tags=["products"])


@router.get("/search")
async def search_products(q: str, budget: float = None, current_user: dict = Depends(get_current_user)):
    llm = LLMService()
    db = SupabaseService()
    agent = SearchAgent(llm=llm, db=db)
    result = await agent.execute({
        "query": q,
        "budget": budget,
        "user_id": current_user["sub"]
    })
    return result


@router.get("/{product_id}")
async def get_product(product_id: str, current_user: dict = Depends(get_current_user)):
    db = SupabaseService()
    result = db.client.table("mock_products").select("*").eq("id", product_id).execute()
    return result.data[0] if result.data else {"error": "Ürün bulunamadı"}


@router.get("/{product_name}/reviews")
async def get_product_reviews(
    product_name: str,
    product_id: str = None,
    price: float = 0,
    seller: str = "",
    rating: float = 0,
    current_user: dict = Depends(get_current_user)
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
