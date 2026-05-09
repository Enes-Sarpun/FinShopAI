from fastapi import APIRouter, Depends, HTTPException, status
from app.models.personality import PersonalitySubmitRequest, PersonalityResponse, QuestionsResponse
from app.agents.personality_agent import PersonalityAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.security import get_current_user

router = APIRouter()


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

    return profile
