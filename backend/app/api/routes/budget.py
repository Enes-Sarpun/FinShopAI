# app/api/routes/budget.py

"""
Budget Routes - API Endpoint'leri
===================================

POST /api/budget/create              - Bütçe oluştur ve analiz et
GET  /api/budget/{user_id}           - Bütçeyi getir
GET  /api/budget/{user_id}/analysis  - Bütçe analizi getir
POST /api/budget/expense             - Harcama ekle
POST /api/budget/affordability       - Uygunluk kontrol et
"""

from fastapi import APIRouter, HTTPException
from app.agents.budget_agent import BudgetAgent
from app.services.supabase_service import SupabaseService
from app.services.llm_service import LLMService
from app.models.budget import (
    BudgetCreateRequest,
    ExpenseRequest,
    AffordabilityRequest
)

router = APIRouter(tags=["budget"])


def get_agent():
    """Budget Agent oluştur"""
    llm = LLMService()
    db = SupabaseService()
    return BudgetAgent(llm, db)


# ==================== ENDPOINT'LER ====================

@router.post("/create")
async def create_budget(request: BudgetCreateRequest):
    """
    Bütçe oluştur ve analiz et.

    Kullanıcıdan gelir, gider ve tasarruf bilgilerini alır.
    Supabase'e kaydeder, Personality verisiyle analiz yapar.

    Örnek Request:
    {
        "user_id": "uuid",
        "income_data": {
            "salary": 8000,
            "extra_income": 1000
        },
        "expense_data": {
            "rent": 2500,
            "electricity": 300,
            "water": 100,
            "gas": 200,
            "internet": 150,
            "phone": 100,
            "loan_payment": 500,
            "insurance": 200,
            "groceries": 1000,
            "transportation": 500,
            "health": 200,
            "education": 300,
            "entertainment": 200,
            "clothing": 100
        },
        "savings_data": {
            "savings_goal": 1000,
            "savings_purpose": "Tatil"
        }
    }
    """

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
async def get_budget(user_id: str):
    """
    Kullanıcının bütçesini getir.

    Supabase'den ham bütçe verisini döner.
    """

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
async def get_budget_analysis(user_id: str):
    """
    Kullanıcının bütçe analizini getir.

    Personality verisiyle birlikte analiz yapar.
    Spending type'a göre kişiselleştirilmiş tavsiyeler döner.
    """

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
async def add_expense(request: ExpenseRequest):
    """
    Harcama ekle.

    Gerçekleşen harcamayı Supabase'e kaydeder.

    Örnek Request:
    {
        "user_id": "uuid",
        "category": "Gıda",
        "amount": 500,
        "description": "Market alışverişi"
    }

    Geçerli Kategoriler:
    Gıda, Ulaşım, Sağlık, Eğitim, Eğlence, Giyim, Diğer
    """

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


@router.post("/affordability")
async def check_affordability(request: AffordabilityRequest):
    """
    Harcama uygunluğunu kontrol et.

    Kullanıcının belirli tutarı harcayıp harcayamayacağını kontrol eder.
    Personality verisiyle kişiselleştirilmiş tavsiye verir.

    Örnek Request:
    {
        "user_id": "uuid",
        "amount": 1500
    }
    """

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