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
    # Mevcut sohbete devam ediliyorsa, o sohbetin ID'si (conversation_id).
    # Yeni sohbet ise None gönderilir; backend ilk user mesajının id'sini
    # conversation_id olarak atar ve frontend'e response'ta döner.
    conversation_id: str | None = None


@router.post("")
@limiter.limit("10/minute")
async def chat(request: Request, body: ChatRequest, current_user: dict = Depends(get_current_user)):
    user_id = current_user["sub"]
    incoming_conversation_id = body.conversation_id

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
                body = ChatRequest(message=sec_result["clean_content"], conversation_id=incoming_conversation_id)

        # Mevcut konuşmaya ait geçmişi getir.
        # Yeni sohbette (conversation_id yok) boş başla — önceki sohbetlerin
        # bağlamı sızmasın (örn. eski ürün önerisinin "contextual reply" tetiklemesi).
        if incoming_conversation_id:
            history = await db.get_chat_history_by_conversation(
                user_id, incoming_conversation_id, limit=12
            )
        else:
            history = []

        conv_agent = ConversationAgent(llm=llm, db=db)
        conv_result = await conv_agent.execute({
            "message": body.message,
            "chat_history": history,
        })

        # Kullanıcı mesajını kaydet — conversation_id metadata'ya yazılır
        # Yeni sohbet ise (incoming_conversation_id None), bu mesajın kendi id'si
        # conversation_id olur. Mevcut sohbete devam ediliyorsa gelen ID kullanılır.
        user_metadata: dict = {"is_product_request": conv_result["is_product_request"]}
        if incoming_conversation_id:
            user_metadata["conversation_id"] = incoming_conversation_id

        user_record = await db.save_chat({
            "user_id": user_id,
            "message": body.message,
            "role": "user",
            "agent_used": "conversation_agent",
            "metadata": user_metadata,
        })
        user_msg_id = user_record.get("id") if user_record else None

        # Yeni sohbetse, conversation_id = ilk user mesajının id'si olur ve
        # metadata bu ID ile güncellenir (sidebar gruplaması için).
        conversation_id = incoming_conversation_id or user_msg_id
        if not incoming_conversation_id and user_msg_id:
            try:
                user_metadata["conversation_id"] = user_msg_id
                await db.update_chat_metadata(user_msg_id, user_id, user_metadata)
            except Exception as e:
                # metadata güncellemesi kritik değil; sidebar fallback'i yine
                # bu mesajı conversation starter olarak gösterir.
                pass

        # ── SOHBET MODU ──────────────────────────────────────────
        if not conv_result["is_product_request"]:
            # Fallback bağlam-duyarlı: önceki mesajlarda ürün önerildiyse jenerik
            # "Nasıl yardımcı olabilirim?" yerine ürünlerle ilgili açık soru sor.
            fallback_reply = "Başka bir konuda yardımcı olabilir miyim?"
            if any(
                (h.get("role") == "assistant"
                 and isinstance(h.get("metadata"), dict)
                 and h.get("metadata", {}).get("type") == "products")
                for h in (history or [])[:4]
            ):
                fallback_reply = (
                    "Önerdiğim ürünler hakkında ne düşünüyorsun? "
                    "Beğenmediğin bir şey varsa kriterleri (fiyat, renk, marka...) "
                    "söyle, yeniden bakayım."
                )
            reply = conv_result.get("reply") or fallback_reply

            await db.save_chat({
                "user_id": user_id,
                "message": reply,
                "role": "assistant",
                "agent_used": "conversation_agent",
                "metadata": {
                    "type": "text",
                    "user_msg_id": user_msg_id,
                    "conversation_id": conversation_id,
                }
            })

            return {
                "message": body.message,
                "reply": reply,
                "is_product_request": False,
                "user_msg_id": user_msg_id,
                "conversation_id": conversation_id,
                "steps_completed": ["conversation"],
                "products": [],
                "recommendation": None,
                "budget_status": None,
                "affordability_message": None,
                "error": None,
            }

        # ── ÜRÜN / INTENT MODU ────────────────────────────────────
        # ConversationAgent'ın LLM ile tespit ettiği bilgileri Orchestrator'a aktar
        result = await run_orchestrator(
            user_id=user_id,
            message=body.message,
            conv_intent=conv_result.get("intent"),
            extracted_query=conv_result.get("extracted_query"),
            is_comparison=conv_result.get("is_comparison", False),
            comparison_products=conv_result.get("comparison_products", []),
            chat_history=history,
        )

        intent      = result.get("intent", "product_search")
        budget_data = result.get("budget_status")

        # ── Watchlist action ─────────────────────────────────────
        if intent == "watchlist_action":
            wl = result.get("watchlist_result") or {}
            reply_text = wl.get("message") or "Takip listesi güncellendi."
            await db.save_chat({
                "user_id": user_id, "message": reply_text,
                "role": "assistant", "agent_used": "watchlist_agent",
                "metadata": {"type": "watchlist", "user_msg_id": user_msg_id,
                             "conversation_id": conversation_id,
                             "payload": wl},
            })
            return {
                "message": body.message, "reply": reply_text,
                "intent": intent, "is_product_request": False,
                "user_msg_id": user_msg_id,
                "conversation_id": conversation_id,
                "steps_completed": result.get("steps_completed", []),
                "timing": result.get("timing", {}),
                "products": [], "recommendation": None,
                "watchlist_result": wl, "error": result.get("error"),
            }

        # ── Budget query ─────────────────────────────────────────
        if intent == "budget_query":
            budget = result.get("budget_status")
            status_messages = {
                "healthy":  "Bütçen sağlıklı görünüyor, iyi gidiyorsun! 💚",
                "warning":  "Bütçen biraz zorlanıyor, dikkatli ol. ⚠️",
                "critical": "Bütçen kritik seviyede, harcamaları gözden geçir! 🔴",
            }
            reply_text = status_messages.get(budget, "Bütçe bilgine ulaşıldı.")
            await db.save_chat({
                "user_id": user_id, "message": reply_text,
                "role": "assistant", "agent_used": "budget_agent",
                "metadata": {"type": "budget", "user_msg_id": user_msg_id,
                             "conversation_id": conversation_id,
                             "budget_status": budget},
            })
            return {
                "message": body.message, "reply": reply_text,
                "intent": intent, "is_product_request": False,
                "user_msg_id": user_msg_id,
                "conversation_id": conversation_id,
                "steps_completed": result.get("steps_completed", []),
                "timing": result.get("timing", {}),
                "budget_status": budget, "products": [],
                "recommendation": None, "error": result.get("error"),
            }

        # ── Product search / quick_search ────────────────────────
        affordability_message = None
        if result.get("recommendation"):
            affordability_message = {
                "healthy":  "Bütçen bu alışveriş için uygun görünüyor.",
                "warning":  "Bu alışveriş bütçeni zorlayabilir, dikkatli ol.",
                "critical": "Bütçen kritik seviyede, bu alışverişi ertelemeyi düşün.",
            }.get(budget_data)

        over_budget_products = result.get("over_budget_products") or []
        budget_exceeded_warning = result.get("budget_exceeded_warning")
        rec = result.get("recommendation") or {}

        assistant_payload = {
            "affordability_message": affordability_message,
            "summary": rec.get("summary"),
            "financial_advice": rec.get("financial_advice"),
            "top_pick": rec.get("top_pick"),
            "products": result.get("products", []),
            "budget_status": budget_data,
            "over_budget_products": over_budget_products,
            "budget_exceeded_warning": budget_exceeded_warning,
        }

        product_count = len(result.get("products", []))
        msg_label = (
            f"[{product_count} alternatif + {len(over_budget_products)} bütçe üstü ürün]"
            if over_budget_products
            else f"[{product_count} ürün bulundu]"
        )

        await db.save_chat({
            "user_id": user_id,
            "message": msg_label,
            "role": "assistant", "agent_used": "orchestrator",
            "metadata": {
                "type": "products", "user_msg_id": user_msg_id,
                "conversation_id": conversation_id,
                "payload": assistant_payload,
                "product_count": product_count,
                "budget_status": budget_data,
                "budget_exceeded_warning": budget_exceeded_warning,
                "intent": intent,
                "timing": result.get("timing", {}),
            },
        })

        return {
            **result,
            "is_product_request": True,
            "user_msg_id": user_msg_id,
            "conversation_id": conversation_id,
            "affordability_message": affordability_message,
            "over_budget_products": over_budget_products,
            "budget_exceeded_warning": budget_exceeded_warning,
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


@router.get("/conversations")
async def get_conversations(
    current_user: dict = Depends(get_current_user),
    limit: int = Query(default=15, ge=1, le=50)
):
    """Sidebar için: Her oturumun ilk kullanıcı mesajını döner.
    30 dakikadan fazla ara olan mesajlar farklı sohbet sayılır.
    """
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        conversations = await db.get_conversation_starters(user_id, limit=limit)
        return {
            "user_id": user_id,
            "count": len(conversations),
            "history": conversations
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


@router.delete("/conversation/{conversation_id}")
async def delete_single_conversation(
    conversation_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Tek bir sohbeti siler.
    conversation_id: Sidebar'da listelenen sohbetin (ilk user mesajının) id'si.
    O session'a ait tüm mesajlar (kullanıcı + asistan) silinir.
    """
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        deleted = await db.delete_chat_session(user_id, conversation_id)
        if deleted == 0:
            raise HTTPException(status_code=404, detail="Sohbet bulunamadı")
        return {"success": True, "deleted_count": deleted}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class UpdateTitleRequest(BaseModel):
    title: str

@router.patch("/{chat_id}/title")
async def update_chat_title(
    chat_id: str,
    body: UpdateTitleRequest,
    current_user: dict = Depends(get_current_user)
):
    """Belirli bir sohbetin adını günceller."""
    user_id = current_user["sub"]
    try:
        db = SupabaseService()
        await db.update_chat_title(chat_id, user_id, body.title)
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
