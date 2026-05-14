"""
Chat API Route — Geliştirilmiş Sürüm
========================================
Değişiklikler:
  - ConversationAgent'ın yeni intent çıktısı (intent, is_comparison, comparison_products, extracted_query) kullanılıyor
  - Orchestrator'a intent parametreleri geçiliyor
  - /api/chat/suggest endpoint'i eklendi (öneri chips için)
  - intent ve confidence response'a eklendi
  - BUDGET_QUERY intent'i özel olarak ele alındı
"""

import json
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.agents.orchestrator import run_orchestrator
from app.agents.conversation_agent import ConversationAgent
from app.agents.budget_agent import BudgetAgent
from app.services.supabase_service import SupabaseService
from app.services.llm_service import LLMService
from app.core.security import get_current_user

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


class ChatRequest(BaseModel):
    message: str


# ── Sohbet önerisi için hazır sorular ─────────────────────────────────────
_SUGGESTION_POOL = [
    "Anneme 1500 TL hediye öner",
    "En iyi kablosuz kulaklık hangisi?",
    "5000 TL bütçeyle laptop tavsiye et",
    "iPhone 15 mi Galaxy S24 mü?",
    "Uygun fiyatlı oyun mouse öner",
    "Bütçem bu alışveriş için yeterli mi?",
    "10000 TL altı gaming bilgisayar",
    "Sevgilime romantik hediye öner",
]


@router.post("")
@limiter.limit("10/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    current_user: dict = Depends(get_current_user),
):
    user_id = current_user["sub"]

    try:
        db = SupabaseService()
        llm = LLMService()

        # Sohbet geçmişini al
        history = await db.get_chat_history(user_id, limit=8)

        # ── ConversationAgent: intent tespiti ────────────────────────────
        # BUDGET_QUERY için bütçe bilgisini önceden çekiyoruz
        budget_info = None
        conv_agent = ConversationAgent(llm=llm, db=db)
        conv_result = await conv_agent.execute({
            "message": body.message,
            "chat_history": history,
            "budget_info": budget_info,
        })

        intent = conv_result["intent"]
        confidence = conv_result["confidence"]
        is_product_request = conv_result["is_product_request"]
        is_comparison = conv_result["is_comparison"]
        comparison_products = conv_result["comparison_products"]
        extracted_query = conv_result["extracted_query"]

        # ── Kullanıcı mesajını kaydet ─────────────────────────────────────
        user_record = await db.save_chat({
            "user_id": user_id,
            "message": body.message,
            "role": "user",
            "agent_used": "conversation_agent",
            "metadata": {
                "intent": intent,
                "confidence": confidence,
                "is_product_request": is_product_request,
            },
        })
        user_msg_id = user_record.get("id") if user_record else None

        # ── BUDGET_QUERY özel akışı ───────────────────────────────────────
        if intent == "BUDGET_QUERY":
            reply = conv_result.get("reply") or "Bütçe bilgilerinize bakıyorum..."

            # Bütçe bilgisini çekip yanıta ekle
            budget_context = None
            try:
                budget_agent = BudgetAgent(llm=llm, db=db)
                budget_data = await budget_agent.execute({
                    "action": "analyze",
                    "user_id": user_id,
                })
                if budget_data.get("success"):
                    fm = budget_data.get("financial_metrics", {})
                    spendable = fm.get("spendable_after_savings", 0) or 0
                    status = budget_data.get("status", "unknown")
                    budget_context = {
                        "status": status,
                        "spendable": spendable,
                    }
                    if not conv_result.get("reply"):
                        status_text = {
                            "healthy": "sağlıklı",
                            "warning": "dikkat gerektiriyor",
                            "critical": "kritik",
                        }.get(status, "bilinmiyor")
                        reply = (
                            f"Bütçe durumunuz {status_text}. "
                            f"Harcanabilir bakiyeniz: {spendable:,.0f} TL 💰"
                        )
            except Exception:
                pass

            await db.save_chat({
                "user_id": user_id,
                "message": reply,
                "role": "assistant",
                "agent_used": "conversation_agent",
                "metadata": {
                    "type": "text",
                    "intent": "BUDGET_QUERY",
                    "user_msg_id": user_msg_id,
                    "budget_context": budget_context,
                },
            })

            return {
                "message": body.message,
                "reply": reply,
                "intent": intent,
                "confidence": confidence,
                "is_product_request": False,
                "user_msg_id": user_msg_id,
                "steps_completed": ["conversation", "budget_query"],
                "products": [],
                "recommendation": None,
                "budget_status": budget_context.get("status") if budget_context else None,
                "affordability_message": None,
                "error": None,
            }

        # ── SOHBET MODU (CHITCHAT, GREETING, COMPLAINT) ───────────────────
        if not is_product_request:
            reply = conv_result.get("reply") or "Başka bir konuda yardımcı olabilir miyim?"

            await db.save_chat({
                "user_id": user_id,
                "message": reply,
                "role": "assistant",
                "agent_used": "conversation_agent",
                "metadata": {
                    "type": "text",
                    "intent": intent,
                    "user_msg_id": user_msg_id,
                },
            })

            return {
                "message": body.message,
                "reply": reply,
                "intent": intent,
                "confidence": confidence,
                "is_product_request": False,
                "user_msg_id": user_msg_id,
                "steps_completed": ["conversation"],
                "products": [],
                "recommendation": None,
                "budget_status": None,
                "affordability_message": None,
                "error": None,
            }

        # ── ÜRÜN ARAMA MODU (PRODUCT_SEARCH veya COMPARISON) ─────────────
        result = await run_orchestrator(
            user_id=user_id,
            message=body.message,
            intent=intent,
            is_comparison=is_comparison,
            comparison_products=comparison_products,
            extracted_query=extracted_query,
        )

        budget_data = result.get("budget_status")
        affordability_message = None
        if result.get("recommendation"):
            if budget_data == "healthy":
                affordability_message = "Bütçen bu alışveriş için uygun görünüyor. ✅"
            elif budget_data == "warning":
                affordability_message = "⚠️ Bu alışveriş bütçeni zorlayabilir, dikkatli ol."
            elif budget_data == "critical":
                affordability_message = "🚨 Bütçen kritik seviyede, bu alışverişi ertelemeyi düşün."

        # Asistan cevabını kaydet
        assistant_payload = {
            "affordability_message": affordability_message,
            "summary": (
                result.get("recommendation", {}).get("summary")
                if result.get("recommendation") else None
            ),
            "financial_advice": (
                result.get("recommendation", {}).get("financial_advice")
                if result.get("recommendation") else None
            ),
            "top_pick": (
                result.get("recommendation", {}).get("top_pick")
                if result.get("recommendation") else None
            ),
            "products": result.get("products", []),
            "budget_status": budget_data,
            "is_comparison": is_comparison,
            "comparison_table": (
                result.get("recommendation", {}).get("comparison_table")
                if result.get("recommendation") else None
            ),
        }

        await db.save_chat({
            "user_id": user_id,
            "message": f"[{len(result.get('products', []))} ürün bulundu]",
            "role": "assistant",
            "agent_used": "orchestrator",
            "metadata": {
                "type": "products",
                "intent": intent,
                "is_comparison": is_comparison,
                "user_msg_id": user_msg_id,
                "payload": assistant_payload,
                "product_count": len(result.get("products", [])),
                "budget_status": budget_data,
            },
        })

        return {
            **result,
            "intent": intent,
            "confidence": confidence,
            "is_product_request": True,
            "user_msg_id": user_msg_id,
            "affordability_message": affordability_message,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history")
async def get_chat_history(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=20, ge=1, le=100),
):
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        history = await db.get_chat_history(user_id, limit=limit)
        return {"user_id": user_id, "count": len(history), "history": history}
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
    current_user: dict = Depends(get_current_user),
):
    """Belirli bir kullanıcı mesajına ait sohbet thread'ini döner."""
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        thread = await db.get_chat_thread(user_id=user_id, user_msg_id=user_msg_id)
        return {"thread": thread}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/suggest")
async def get_suggestions(current_user: dict = Depends(get_current_user)):
    """Frontend suggestion chips için hazır soru önerileri döner."""
    import random
    suggestions = random.sample(_SUGGESTION_POOL, min(4, len(_SUGGESTION_POOL)))
    return {"suggestions": suggestions}
