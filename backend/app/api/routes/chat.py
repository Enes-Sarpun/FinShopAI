import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address
from app.agents.orchestrator import run_orchestrator
from app.agents.conversation_agent import ConversationAgent
from app.agents.security_agent import SecurityAgent
from app.services.supabase_service import SupabaseService
from app.services.llm_service import LLMService
from app.core.security import get_current_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ChatRequest(BaseModel):
    message: str


@router.post("")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]

    try:
        db = SupabaseService()
        llm = LLMService()

        # ── Güvenlik kontrolü ─────────────────────────────────────────
        security_agent = SecurityAgent(llm=llm, db=db)
        sec_result = await security_agent.execute({
            "action_type": "check_content",
            "content": body.message,
            "user_id": user_id,
            "content_type": "message",
        })
        if not sec_result.get("is_safe", True):
            action = sec_result.get("action", "block")
            if action in ("block", "ban"):
                raise HTTPException(
                    status_code=400,
                    detail=sec_result.get("reason") or "Mesajınız güvenlik kontrolünden geçemedi.",
                )
            # warn: devam et ama temizlenmiş içeriği kullan
            if sec_result.get("clean_content"):
                body = ChatRequest(message=sec_result["clean_content"])

        history = await db.get_chat_history(user_id, limit=6)

        conv_agent = ConversationAgent(llm=llm, db=db)
        conv_result = await conv_agent.execute({
            "message": body.message,
            "chat_history": history,
        })

        # Kullanıcı mesajını kaydet
        user_record = await db.save_chat({
            "user_id": user_id,
            "message": body.message,
            "role": "user",
            "agent_used": "conversation_agent",
            "metadata": {"is_product_request": conv_result["is_product_request"]}
        })
        user_msg_id = user_record.get("id") if user_record else None

        # ── SOHBET MODU ──────────────────────────────────────────
        if not conv_result["is_product_request"]:
            reply = conv_result.get("reply") or "Başka bir konuda yardımcı olabilir miyim?"

            await db.save_chat({
                "user_id": user_id,
                "message": reply,
                "role": "assistant",
                "agent_used": "conversation_agent",
                "metadata": {
                    "type": "text",
                    "user_msg_id": user_msg_id,
                }
            })

            return {
                "message": body.message,
                "reply": reply,
                "is_product_request": False,
                "user_msg_id": user_msg_id,
                "steps_completed": ["conversation"],
                "products": [],
                "recommendation": None,
                "budget_status": None,
                "affordability_message": None,
                "error": None,
            }

        # ── ÜRÜN ARAMA MODU ──────────────────────────────────────
        result = await run_orchestrator(user_id=user_id, message=body.message)

        budget_data = result.get("budget_status")
        affordability_message = None
        if result.get("recommendation"):
            if budget_data == "healthy":
                affordability_message = "Bütçen bu alışveriş için uygun görünüyor."
            elif budget_data == "warning":
                affordability_message = "Bu alışveriş bütçeni zorlayabilir, dikkatli ol."
            elif budget_data == "critical":
                affordability_message = "Bütçen kritik seviyede, bu alışverişi ertelemeyi düşün."

        # Asistan cevabını (ürün + öneri) JSON olarak kaydet
        assistant_payload = {
            "affordability_message": affordability_message,
            "summary": result.get("recommendation", {}).get("summary") if result.get("recommendation") else None,
            "financial_advice": result.get("recommendation", {}).get("financial_advice") if result.get("recommendation") else None,
            "top_pick": result.get("recommendation", {}).get("top_pick") if result.get("recommendation") else None,
            "products": result.get("products", []),
            "budget_status": budget_data,
        }

        await db.save_chat({
            "user_id": user_id,
            "message": f"[{len(result.get('products', []))} ürün bulundu]",
            "role": "assistant",
            "agent_used": "orchestrator",
            "metadata": {
                "type": "products",
                "user_msg_id": user_msg_id,
                "payload": assistant_payload,
                "product_count": len(result.get("products", [])),
                "budget_status": budget_data,
            }
        })

        return {
            **result,
            "is_product_request": True,
            "user_msg_id": user_msg_id,
            "affordability_message": affordability_message,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100)
):
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


@router.delete("/history")
async def delete_chat_history(current_user: dict = Depends(get_current_user)):
    """Kullanıcının tüm sohbet geçmişini siler."""
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        await db.delete_chat_history(user_id)
        return {"success": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/thread/{user_msg_id}")
async def get_thread(
    user_msg_id: str,
    current_user: dict = Depends(get_current_user)
):
    """
    Belirli bir kullanıcı mesajına ait sohbet thread'ini döner.
    Kullanıcı mesajı + asistan cevabını birlikte getirir.
    """
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        thread = await db.get_chat_thread(user_id=user_id, user_msg_id=user_msg_id)
        return {"thread": thread}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
