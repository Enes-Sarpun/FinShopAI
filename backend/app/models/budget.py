# app/models/budget.py

"""
Budget Models - Veri Yapıları
==============================

Kullanıcıdan gelecek verilerin şeklini tanımlar.
FastAPI bu modelleri kullanarak veriyi otomatik doğrular.

Modeller:
- IncomeData: Gelir bilgileri
- ExpenseData: Gider bilgileri
- SavingsData: Tasarruf bilgileri
- BudgetCreateRequest: Bütçe oluşturma isteği
- ExpenseRequest: Harcama ekleme isteği
- AffordabilityRequest: Uygunluk kontrolü isteği
"""

from pydantic import BaseModel, Field, validator
from typing import Optional


# ==================== GELİR MODELİ ====================

class IncomeData(BaseModel):
    """
    Kullanıcının gelir bilgileri.
    
    Örnek:
    {
        "salary": 8000,
        "extra_income": 1000
    }
    """
    
    salary: float = Field(
        ...,                        # Zorunlu alan
        gt=0,                       # 0'dan büyük olmalı
        description="Aylık maaş (TRY)"
    )
    
    extra_income: Optional[float] = Field(
        default=0,
        ge=0,                       # 0 veya daha büyük
        description="Ek gelir (TRY)"
    )


# ==================== GİDER MODELİ ====================

class ExpenseData(BaseModel):
    """
    Kullanıcının gider bilgileri.
    Tüm alanlar opsiyonel, default 0.
    
    Örnek:
    {
        "rent": 2500,
        "electricity": 300,
        "groceries": 1000
    }
    """
    
    # --- Sabit Giderler ---
    rent: Optional[float] = Field(default=0, ge=0, description="Kira")
    electricity: Optional[float] = Field(default=0, ge=0, description="Elektrik faturası")
    water: Optional[float] = Field(default=0, ge=0, description="Su faturası")
    gas: Optional[float] = Field(default=0, ge=0, description="Doğalgaz faturası")
    internet: Optional[float] = Field(default=0, ge=0, description="İnternet faturası")
    phone: Optional[float] = Field(default=0, ge=0, description="Telefon faturası")
    loan_payment: Optional[float] = Field(default=0, ge=0, description="Kredi ödemesi")
    insurance: Optional[float] = Field(default=0, ge=0, description="Sigorta")
    other_fixed: Optional[float] = Field(default=0, ge=0, description="Diğer sabit giderler")
    
    # --- Değişken Giderler (Aylık Ortalama) ---
    groceries: Optional[float] = Field(default=0, ge=0, description="Market / Gıda")
    transportation: Optional[float] = Field(default=0, ge=0, description="Ulaşım")
    health: Optional[float] = Field(default=0, ge=0, description="Sağlık")
    education: Optional[float] = Field(default=0, ge=0, description="Eğitim")
    entertainment: Optional[float] = Field(default=0, ge=0, description="Eğlence")
    clothing: Optional[float] = Field(default=0, ge=0, description="Giyim")
    other_variable: Optional[float] = Field(default=0, ge=0, description="Diğer değişken giderler")


# ==================== TASARRUF MODELİ ====================

class SavingsData(BaseModel):
    """
    Kullanıcının tasarruf bilgileri.
    
    Örnek:
    {
        "savings_goal": 1000,
        "savings_purpose": "Tatil"
    }
    """
    
    savings_goal: Optional[float] = Field(
        default=0,
        ge=0,
        description="Aylık tasarruf hedefi (TRY)"
    )
    
    savings_purpose: Optional[str] = Field(
        default="",
        max_length=200,
        description="Tasarruf amacı (tatil, araba, ev vb.)"
    )


# ==================== İSTEK MODELLERİ ====================

class BudgetCreateRequest(BaseModel):
    """
    Bütçe oluşturma isteği.
    
    POST /api/budget/create endpoint'ine gönderilir.
    
    Örnek:
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
            "groceries": 1000
        },
        "savings_data": {
            "savings_goal": 1000,
            "savings_purpose": "Tatil"
        }
    }
    """
    
    user_id: str = Field(..., description="Kullanıcı ID (UUID)")
    income_data: IncomeData
    expense_data: ExpenseData
    savings_data: Optional[SavingsData] = SavingsData()
    
    @validator("user_id")
    def user_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id boş olamaz")
        return v


# İngilizce slug → kanonik form
VALID_EXPENSE_CATEGORIES = {
    "groceries", "transport", "health", "education",
    "entertainment", "clothing", "bills", "other",
}

# Geriye dönük: eski Türkçe isimleri slug'a çevir
LEGACY_EXPENSE_CATEGORY_MAP = {
    "Gıda": "groceries",
    "Ulaşım": "transport",
    "Sağlık": "health",
    "Eğitim": "education",
    "Eğlence": "entertainment",
    "Giyim": "clothing",
    "Diğer": "other",
}


class ExpenseRequest(BaseModel):
    """
    Harcama ekleme isteği.

    POST /api/budget/expense endpoint'ine gönderilir.

    Örnek:
    {
        "user_id": "uuid",
        "category": "groceries",
        "amount": 500,
        "description": "Market alışverişi"
    }

    Geçerli kategori slug'ları:
    groceries, transport, health, education,
    entertainment, clothing, bills, other
    (Eski TR isimler de geriye dönük uyumluluk için kabul edilir.)
    """

    user_id: str = Field(..., description="Kullanıcı ID")

    category: str = Field(
        ...,
        description="Harcama kategorisi (slug)"
    )

    amount: float = Field(
        ...,
        gt=0,
        description="Harcama tutarı (TRY)"
    )

    description: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Açıklama"
    )

    @validator("category")
    def category_must_be_valid(cls, v):
        if not v:
            raise ValueError("Kategori zorunludur")
        # Eski TR isimleri kabul et, slug'a çevir
        if v in LEGACY_EXPENSE_CATEGORY_MAP:
            return LEGACY_EXPENSE_CATEGORY_MAP[v]
        slug = v.strip().lower()
        if slug not in VALID_EXPENSE_CATEGORIES:
            raise ValueError(
                f"Geçersiz kategori. Geçerli kategoriler: {', '.join(sorted(VALID_EXPENSE_CATEGORIES))}"
            )
        return slug


class AffordabilityRequest(BaseModel):
    """
    Uygunluk kontrolü isteği.
    
    POST /api/budget/affordability endpoint'ine gönderilir.
    
    Örnek:
    {
        "user_id": "uuid",
        "amount": 1500
    }
    """
    
    user_id: str = Field(..., description="Kullanıcı ID")
    
    amount: float = Field(
        ...,
        gt=0,
        description="Kontrol edilecek tutar (TRY)"
    )


# ==================== YANIT MODELLERİ ====================

class BudgetResponse(BaseModel):
    """
    Bütçe yanıt modeli.
    API'den dönen veri yapısı.
    """
    
    success: bool
    budget_id: Optional[str] = None
    message: str


class AnalysisResponse(BaseModel):
    """
    Analiz yanıt modeli.
    """
    
    success: bool
    user_id: str
    spending_type: str
    status: str
    message: str