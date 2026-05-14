from fastapi import APIRouter, Request
from app.agents.security_agent import SecurityAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService

router = APIRouter(tags=["security"])

@router.post("/api/security/check")
async def check_content(
    content: str,
    user_id: str = "anonymous",
    content_type: str = "message"
):
    llm = LLMService()
    db = SupabaseService()
    agent = SecurityAgent(llm=llm, db=db)
    return await agent.execute({
        "action_type": "check_content",
        "content": content,
        "user_id": user_id,
        "content_type": content_type
    })

@router.post("/api/security/check-review")
async def check_review(
    content: str,
    user_id: str = "anonymous",
    rating: int = 3,
    review_count: int = 0
):
    llm = LLMService()
    db = SupabaseService()
    agent = SecurityAgent(llm=llm, db=db)
    return await agent.execute({
        "action_type": "check_review",
        "content": content,
        "user_id": user_id,
        "rating": rating,
        "review_count": review_count
    })

@router.post("/api/security/check-rate-limit")
async def check_rate_limit(
    user_id: str,
    action_count: int,
    action_type_detail: str = "request",
    ip_address: str = "unknown"
):
    llm = LLMService()
    db = SupabaseService()
    agent = SecurityAgent(llm=llm, db=db)
    return await agent.execute({
        "action_type": "check_rate_limit",
        "user_id": user_id,
        "action_count": action_count,
        "action_type_detail": action_type_detail,
        "ip_address": ip_address
    })