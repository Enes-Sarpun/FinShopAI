from pydantic import BaseModel, Field, validator
from typing import Optional, Union


class IncomeData(BaseModel):
    salary: Union[float, int] = Field(..., gt=0, description="Aylık maaş (TRY)")
    extra_income: Optional[Union[float, int]] = Field(default=0, ge=0, description="Ek gelir (TRY)")


class ExpenseData(BaseModel):
    rent: Optional[Union[float, int]] = Field(default=0, ge=0, description="Kira")
    electricity: Optional[Union[float, int]] = Field(default=0, ge=0, description="Elektrik faturası")
    water: Optional[Union[float, int]] = Field(default=0, ge=0, description="Su faturası")
    gas: Optional[Union[float, int]] = Field(default=0, ge=0, description="Doğalgaz faturası")
    internet: Optional[Union[float, int]] = Field(default=0, ge=0, description="İnternet faturası")
    phone: Optional[Union[float, int]] = Field(default=0, ge=0, description="Telefon faturası")
    loan_payment: Optional[Union[float, int]] = Field(default=0, ge=0, description="Kredi ödemesi")
    insurance: Optional[Union[float, int]] = Field(default=0, ge=0, description="Sigorta")
    other_fixed: Optional[Union[float, int]] = Field(default=0, ge=0, description="Diğer sabit giderler")
    groceries: Optional[Union[float, int]] = Field(default=0, ge=0, description="Market / Gıda")
    transportation: Optional[Union[float, int]] = Field(default=0, ge=0, description="Ulaşım")
    health: Optional[Union[float, int]] = Field(default=0, ge=0, description="Sağlık")
    education: Optional[Union[float, int]] = Field(default=0, ge=0, description="Eğitim")
    entertainment: Optional[Union[float, int]] = Field(default=0, ge=0, description="Eğlence")
    clothing: Optional[Union[float, int]] = Field(default=0, ge=0, description="Giyim")
    other_variable: Optional[Union[float, int]] = Field(default=0, ge=0, description="Diğer değişken giderler")


class SavingsData(BaseModel):
    savings_goal: Optional[Union[float, int]] = Field(default=0, ge=0, description="Aylık tasarruf hedefi (TRY)")
    savings_purpose: Optional[str] = Field(default="", max_length=200, description="Tasarruf amacı")


class BudgetCreateRequest(BaseModel):
    user_id: str = Field(..., description="Kullanıcı ID (UUID)")
    income_data: IncomeData
    expense_data: ExpenseData
    savings_data: Optional[SavingsData] = SavingsData()

    @validator("user_id")
    def user_id_must_not_be_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("user_id boş olamaz")
        return v


VALID_EXPENSE_CATEGORIES = {
    "groceries", "transport", "health", "education",
    "entertainment", "clothing", "bills", "other",
}

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
    user_id: str = Field(..., description="Kullanıcı ID")
    category: str = Field(..., description="Harcama kategorisi (slug)")
    amount: Union[float, int] = Field(..., gt=0, description="Harcama tutarı (TRY)")
    description: Optional[str] = Field(default=None, max_length=500, description="Açıklama")

    @validator("category")
    def category_must_be_valid(cls, v):
        if not v:
            raise ValueError("Kategori zorunludur")
        if v in LEGACY_EXPENSE_CATEGORY_MAP:
            return LEGACY_EXPENSE_CATEGORY_MAP[v]
        slug = v.strip().lower()
        if slug not in VALID_EXPENSE_CATEGORIES:
            raise ValueError(
                f"Geçersiz kategori. Geçerli kategoriler: {', '.join(sorted(VALID_EXPENSE_CATEGORIES))}"
            )
        return slug


class AffordabilityRequest(BaseModel):
    user_id: str = Field(..., description="Kullanıcı ID")
    amount: Union[float, int] = Field(..., gt=0, description="Kontrol edilecek tutar (TRY)")


class BudgetResponse(BaseModel):
    success: bool
    budget_id: Optional[str] = None
    message: str


class AnalysisResponse(BaseModel):
    success: bool
    user_id: str
    spending_type: str
    status: str
    message: str
