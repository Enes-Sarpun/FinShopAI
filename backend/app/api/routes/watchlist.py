"""
Watchlist (Takip Listesi) API Routes  (v2)
==========================================
Endpoint'ler:
  GET    /api/watchlist/                          → Kullanıcının takip listesi
  POST   /api/watchlist/                          → Ürün ekle
  DELETE /api/watchlist/{watchlist_id}            → Ürün çıkar
  PATCH  /api/watchlist/{watchlist_id}/threshold  → Alarm eşiğini güncelle  [v2]
  POST   /api/watchlist/check                     → Fiyatları manuel tetikle
  GET    /api/watchlist/{watchlist_id}/history    → Fiyat geçmişi           [v2]
  GET    /api/watchlist/notifications             → Kullanıcı bildirimleri
  PATCH  /api/watchlist/notifications/{id}/read   → Bildirimi okundu işaretle
  PATCH  /api/watchlist/notifications/read-all    → Tüm bildirimleri okundu
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional

from app.agents.watchlist_agent import WatchlistAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger("watchlist_route")


# ── Pydantic Modeller ────────────────────────────────────────────────────────

class AddToWatchlistRequest(BaseModel):
    name: str = Field(..., min_length=1, description="Ürün adı")
    price: float = Field(..., ge=0, description="Referans fiyat (TL)")
    url: Optional[str] = Field(None, description="Ürün linki")
    image_url: Optional[str] = Field(None, description="Ürün görseli")
    seller: Optional[str] = Field(None, description="Satıcı")
    search_query: Optional[str] = Field(None, description="Fiyat takibi için arama terimi")
    # [v2] Per-ürün özel alarm eşiği — belirtilmezse agent varsayılanı kullanır
    alert_threshold_pct: Optional[float] = Field(
        None, ge=0.5, le=90.0,
        description="Alarm için minimum indirim yüzdesi (varsayılan: %3)"
    )


# ── Dependency ───────────────────────────────────────────────────────────────

def _agent() -> WatchlistAgent:
    return WatchlistAgent(llm=LLMService(), db=SupabaseService())


# ── Endpoint'ler ─────────────────────────────────────────────────────────────

@router.get("/", summary="Takip listesini getir")
async def get_watchlist(current_user: dict = Depends(get_current_user)):
    """Kullanıcının aktif takip listesini döner."""
    user_id = current_user["sub"]
    agent = _agent()
    result = await agent.execute({"user_id": user_id, "mode": "list"})
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error", "Bilinmeyen hata"))
    return result


@router.post("/", summary="Ürünü takip listesine ekle", status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    body: AddToWatchlistRequest,
    current_user: dict = Depends(get_current_user),
):
    """Yıldızlanan ürünü takip listesine ekler."""
    user_id = current_user["sub"]
    agent = _agent()
    result = await agent.execute({
        "user_id": user_id,
        "mode": "add",
        "product": body.model_dump(),
    })
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.delete("/{watchlist_id}", summary="Ürünü takip listesinden çıkar")
async def remove_from_watchlist(
    watchlist_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Belirtilen takip listesi kaydını devre dışı bırakır (soft delete)."""
    user_id = current_user["sub"]
    agent = _agent()
    result = await agent.execute({
        "user_id": user_id,
        "mode": "remove",
        "watchlist_id": watchlist_id,
    })
    if not result.get("success"):
        raise HTTPException(status_code=400, detail=result.get("error"))
    return result


@router.post("/check", summary="Fiyatları şimdi kontrol et")
async def check_prices(current_user: dict = Depends(get_current_user)):
    """
    Takip listesindeki tüm ürünleri PARALEL olarak SerpAPI'den kontrol eder.
    İndirim tespit edilirse (per-ürün eşiğe göre) bildirim oluşturulur.
    """
    user_id = current_user["sub"]
    agent = _agent()
    result = await agent.execute({"user_id": user_id, "mode": "check"})
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/{watchlist_id}/history", summary="Fiyat geçmişini getir")  # [v2]
async def get_price_history(
    watchlist_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Belirtilen takip listesi ürününün kaydedilmiş fiyat geçmişini ve
    7 günlük trend etiketini döner.
    """
    user_id = current_user["sub"]
    agent = _agent()
    result = await agent.execute({
        "user_id": user_id,
        "mode": "history",
        "watchlist_id": watchlist_id,
    })
    if not result.get("success"):
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.patch("/{watchlist_id}/threshold", summary="Alarm eşiğini güncelle")  # [v2]
async def update_alert_threshold(
    watchlist_id: str,
    threshold_pct: float,
    current_user: dict = Depends(get_current_user),
):
    """Belirtilen ürün için alarm tetiklenme eşiğini günceller."""
    if not (0.5 <= threshold_pct <= 90.0):
        raise HTTPException(status_code=422, detail="Eşik %0.5 ile %90 arasında olmalı")
    user_id = current_user["sub"]
    db = SupabaseService()
    try:
        db.client.table("watchlist").update({"alert_threshold_pct": threshold_pct}).eq(
            "id", watchlist_id
        ).eq("user_id", user_id).execute()
        return {
            "success": True,
            "message": f"Alarm eşiği %{threshold_pct} olarak güncellendi.",
        }
    except Exception as e:
        logger.error(f"Eşik güncelleme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/notifications", summary="Kullanıcı bildirimlerini getir")
async def get_notifications(
    limit: int = 20,
    unread_only: bool = False,
    current_user: dict = Depends(get_current_user),
):
    """Kullanıcının fiyat düşüş bildirimlerini döner."""
    user_id = current_user["sub"]
    db = SupabaseService()
    try:
        q = (
            db.client.table("notifications")
            .select("*")
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(limit)
        )
        if unread_only:
            q = q.eq("is_read", False)

        result = q.execute()
        items = result.data or []

        unread_count = sum(1 for n in items if not n.get("is_read"))
        return {
            "success": True,
            "count": len(items),
            "unread_count": unread_count,
            "notifications": items,
        }
    except Exception as e:
        logger.error(f"Bildirim getirme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/read-all", summary="Tüm bildirimleri okundu işaretle")
async def mark_all_notifications_read(current_user: dict = Depends(get_current_user)):
    """Kullanıcının tüm okunmamış bildirimlerini okundu yapar."""
    user_id = current_user["sub"]
    db = SupabaseService()
    try:
        db.client.table("notifications").update({"is_read": True}).eq(
            "user_id", user_id
        ).eq("is_read", False).execute()
        return {"success": True, "message": "Tüm bildirimler okundu olarak işaretlendi."}
    except Exception as e:
        logger.error(f"Toplu bildirim güncelleme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/notifications/{notification_id}/read", summary="Bildirimi okundu işaretle")
async def mark_notification_read(
    notification_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Belirtilen bildirimi okundu olarak işaretler."""
    user_id = current_user["sub"]
    db = SupabaseService()
    try:
        db.client.table("notifications").update({"is_read": True}).eq(
            "id", notification_id
        ).eq("user_id", user_id).execute()
        return {"success": True, "message": "Bildirim okundu olarak işaretlendi."}
    except Exception as e:
        logger.error(f"Bildirim güncelleme hatası: {e}")
        raise HTTPException(status_code=500, detail=str(e))
