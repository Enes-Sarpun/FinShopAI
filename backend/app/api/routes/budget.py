from fastapi import APIRouter, HTTPException, Depends
from app.agents.budget_agent import BudgetAgent
from app.services.supabase_service import SupabaseService
from app.services.llm_service import LLMService
from app.models.budget import (
    BudgetCreateRequest,
    ExpenseRequest,
    AffordabilityRequest,
)
from app.core.security import get_current_user

router = APIRouter(tags=["budget"])


def get_agent():
    llm = LLMService()
    db = SupabaseService()
    return BudgetAgent(llm, db)


@router.post("/create")
async def create_budget(request: BudgetCreateRequest, current_user: dict = Depends(get_current_user)):
    try:
        agent = get_agent()

        result = await agent.execute({
            "action": "save_and_analyze",
            "user_id": request.user_id,
            "income_data": request.income_data.model_dump(),
            "expense_data": request.expense_data.model_dump(),
            "savings_data": request.savings_data.model_dump()
        })

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Bütçe oluşturma hatası")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}")
async def get_budget(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        db = SupabaseService()
        budget = await db.get_budget(user_id)

        if not budget:
            raise HTTPException(
                status_code=404,
                detail="Bütçe bulunamadı"
            )

        return {
            "success": True,
            "data": budget,
            "message": "Bütçe başarıyla getirildi"
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/analysis")
async def get_budget_analysis(user_id: str, current_user: dict = Depends(get_current_user)):
    try:
        agent = get_agent()

        result = await agent.execute({
            "action": "analyze",
            "user_id": user_id
        })

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Analiz hatası")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expense")
async def add_expense(request: ExpenseRequest, current_user: dict = Depends(get_current_user)):
    try:
        agent = get_agent()

        result = await agent.execute({
            "action": "add_expense",
            "user_id": request.user_id,
            "category": request.category,
            "amount": request.amount,
            "description": request.description
        })

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Harcama ekleme hatası")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{user_id}/expenses")
async def list_expenses(
    user_id: str,
    limit: int = 10,
    current_user: dict = Depends(get_current_user),
):
    """
    Kullanıcının son harcamalarını listeler (en yeni önce).
    """
    if current_user.get("sub") != user_id:
        raise HTTPException(status_code=403, detail="Bu hesaba erişim yetkiniz yok")

    if limit < 1 or limit > 100:
        limit = 10

    try:
        db = SupabaseService()
        items = await db.get_recent_expenses(user_id, limit=limit)
        return {
            "success": True,
            "items": items,
            "count": len(items),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/expense/{expense_id}")
async def delete_expense(
    expense_id: str,
    current_user: dict = Depends(get_current_user),
):
    if not expense_id:
        raise HTTPException(status_code=400, detail="expense_id zorunludur")

    user_id = current_user.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Yetki gerekli")

    try:
        db = SupabaseService()
        existing = await db.get_expense(user_id, expense_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Harcama bulunamadı")

        await db.delete_expense(user_id, expense_id)
        return {"success": True, "message": "Harcama silindi"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/affordability")
async def check_affordability(request: AffordabilityRequest, current_user: dict = Depends(get_current_user)):
    try:
        agent = get_agent()

        result = await agent.execute({
            "action": "check_affordability",
            "user_id": request.user_id,
            "amount": request.amount
        })

        if not result["success"]:
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Uygunluk kontrolü hatası")
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))