from fastapi import APIRouter, Depends
from pydantic import BaseModel
from app.agents.security_agent import SecurityAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter(tags=["security"])


class ContentCheckRequest(BaseModel):
    content: str
    content_type: str = "message"


class ReviewCheckRequest(BaseModel):
    content: str
    rating: int = 3
    review_count: int = 0


class RateLimitRequest(BaseModel):
    action_count: int
    action_type_detail: str = "request"
    ip_address: str = "unknown"


def _make_agent() -> SecurityAgent:
    return SecurityAgent(llm=LLMService(), db=SupabaseService())


@router.post("/check")
async def check_content(
    body: ContentCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    return await _make_agent().execute({
        "action_type": "check_content",
        "content": body.content,
        "user_id": user_id,
        "content_type": body.content_type,
    })


@router.post("/check-review")
async def check_review(
    body: ReviewCheckRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    return await _make_agent().execute({
        "action_type": "check_review",
        "content": body.content,
        "user_id": user_id,
        "rating": body.rating,
        "review_count": body.review_count,
    })


@router.post("/check-rate-limit")
async def check_rate_limit(
    body: RateLimitRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]
    return await _make_agent().execute({
        "action_type": "check_rate_limit",
        "user_id": user_id,
        "action_count": body.action_count,
        "action_type_detail": body.action_type_detail,
        "ip_address": body.ip_address,
    })
