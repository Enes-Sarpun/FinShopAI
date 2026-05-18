import json

from fastapi import APIRouter, Depends, HTTPException, status
from app.models.personality import PersonalitySubmitRequest, PersonalityResponse, QuestionsResponse
from app.agents.personality_agent import PersonalityAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter()


def _row_to_response(row: dict) -> dict:
    """personality_profiles row'unu PersonalityResponse şemasına çevirir."""
    raw_llm = row.get("llm_analysis") or {}
    if isinstance(raw_llm, str):
        try:
            raw_llm = json.loads(raw_llm)
        except (json.JSONDecodeError, ValueError):
            # Bazı eski kayıtlar Python repr formatında (tek tırnaklı) saklanmış olabilir.
            try:
                import ast
                raw_llm = ast.literal_eval(raw_llm)
                if not isinstance(raw_llm, dict):
                    raw_llm = {}
            except (ValueError, SyntaxError):
                raw_llm = {}

    return {
        "profile_id": row.get("id") or row.get("profile_id") or "",
        "spending_type": row.get("spending_type") or raw_llm.get("spending_type") or "dengeli",
        "rule_score": row.get("rule_score") or raw_llm.get("rule_score") or 0,
        "risk_score": row.get("risk_score") or raw_llm.get("risk_score") or 0,
        "impulsive_score": row.get("impulsive_score") or raw_llm.get("impulsive_score") or 0,
        "saving_score": row.get("saving_score") or raw_llm.get("saving_score") or 0,
        "research_score": row.get("research_score") or raw_llm.get("research_score") or 0,
        "strengths": row.get("strengths") or raw_llm.get("strengths") or [],
        "weaknesses": row.get("weaknesses") or raw_llm.get("weaknesses") or [],
        "recommendations": row.get("recommendations") or raw_llm.get("recommendations") or "",
        "personality_summary": (
            row.get("personality_summary")
            or raw_llm.get("personality_summary")
            or ""
        ),
    }


def get_agent() -> PersonalityAgent:
    return PersonalityAgent(llm=LLMService(), db=SupabaseService())


@router.get("/questions", response_model=QuestionsResponse)
async def get_questions():
    """Karakter analizi sorularını döner."""
    agent = get_agent()
    questions = agent.get_questions()
    return {"questions": questions, "total": len(questions)}


@router.post("/submit", response_model=PersonalityResponse)
async def submit_answers(
    body: PersonalitySubmitRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    10 sorunun cevaplarını alır, LLM analizi yapar, profili kaydeder.
    Authorization: Bearer <token> header gereklidir.
    """
    if len(body.answers) != 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="10 sorunun tamamı cevaplanmalı",
        )

    valid_keys = {str(i) for i in range(1, 11)}
    if not valid_keys.issubset(body.answers.keys()):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Eksik sorular: {valid_keys - body.answers.keys()}",
        )

    agent = get_agent()
    try:
        result = await agent.execute({
            "user_id": current_user["sub"],
            "answers": body.answers,
        })
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))

    return result


@router.get("/history")
async def get_personality_history(current_user: dict = Depends(get_current_user)):
    """Kullanıcının tüm karakter testi geçmişini döner (en yeniden eskiye)."""
    user_id = current_user["sub"]
    db = SupabaseService()
    history = await db.get_personality_history(user_id)
    return {
        "user_id": user_id,
        "count": len(history),
        "history": history
    }


@router.get("/{user_id}", response_model=PersonalityResponse)
async def get_personality(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Kullanıcının en son karakter profilini getirir."""
    if current_user["sub"] != user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Erişim reddedildi")

    db = SupabaseService()
    profile = await db.get_personality(user_id)
    if not profile:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profil bulunamadı")

    return _row_to_response(profile)
