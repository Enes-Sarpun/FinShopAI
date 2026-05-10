from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from app.agents.orchestrator import run_orchestrator
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@router.post("")
async def chat(body: ChatRequest, current_user: dict = Depends(get_current_user)):
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

    # Sohbet geçmişine kaydet
    try:
        db = SupabaseService()
        await db.save_chat({
            "user_id": user_id,
            "message": body.message,
            "role": "user",
            "agent_used": "orchestrator",
            "metadata": {"steps": result.get("steps_completed")}
        })
    except Exception:
        pass

    return result
