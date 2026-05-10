from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.agents.orchestrator import run_orchestrator
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ChatRequest(BaseModel):
    message: str


@router.post("")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    """
    Ana chat endpoint'i.
    Kullanıcının mesajını alır, tüm agent'ları orchestrate eder, sonucu döner.

    Örnek:
    { "message": "Anneme 1500 TL hediye öner" }
    """
    user_id = current_user["sub"]

    try:
        result = await run_orchestrator(user_id=user_id, message=body.message)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    # Affordability mesajını sonuca ekle
    budget_data = result.get("budget_status")
    affordability_message = None
    if result.get("recommendation"):
        if budget_data == "healthy":
            affordability_message = "Bütçen bu alışveriş için uygun görünüyor."
        elif budget_data == "warning":
            affordability_message = "Bu alışveriş bütçeni zorlayabilir, dikkatli ol."
        elif budget_data == "critical":
            affordability_message = "Bütçen kritik seviyede, bu alışverişi ertelemeyi düşün."

    # Sohbet geçmişine kaydet
    try:
        db = SupabaseService()
        await db.save_chat({
            "user_id": user_id,
            "message": body.message,
            "role": "user",
            "agent_used": "orchestrator",
            "metadata": {
                "steps": result.get("steps_completed"),
                "product_count": len(result.get("products", [])),
                "budget_status": budget_data
            }
        })
    except Exception:
        pass

    return {**result, "affordability_message": affordability_message}


@router.get("/history")
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100)
):
    """
    Kullanıcının sohbet geçmişini döner.
    En yeni mesajlar önce gelir.
    """
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        history = await db.get_chat_history(user_id, limit=limit)
        return {
            "user_id": user_id,
            "count": len(history),
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
