# tests/test_budget_agent.py

"""
Budget Agent Test
=================

Mock LLM ve DB servisleri ile Budget Agent'ı test eder.
Supabase'e gerçek bağlantı olmadan çalışır.
"""

import asyncio
import sys
import os

# Path ayarı (backend klasöründen çalıştırmak için)
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


# ==================== MOCK SERVİSLER ====================

class MockLLMService:
    """Gemini yerine mock LLM"""
    
    async def generate(self, prompt: str, system: str = None):
        return "Mock LLM response"


class MockSupabaseService:
    """Gerçek Supabase yerine mock DB"""
    
    async def get_personality(self, user_id: str):
        """Mock personality profili döndür"""
        profiles = {
            "user-savruk": {
                "user_id": "user-savruk",
                "spending_type": "savruk",
                "risk_score": 8,
                "impulsive_score": 9,
                "saving_score": 2,
                "research_score": 3
            },
            "user-dengeli": {
                "user_id": "user-dengeli",
                "spending_type": "balanced",
                "risk_score": 5,
                "impulsive_score": 5,
                "saving_score": 6,
                "research_score": 6
            },
            "user-tutumlu": {
                "user_id": "user-tutumlu",
                "spending_type": "tutumlu",
                "risk_score": 2,
                "impulsive_score": 2,
                "saving_score": 9,
                "research_score": 8
            }
        }
        return profiles.get(user_id, profiles["user-dengeli"])
    
    async def get_budget(self, user_id: str):
        """Mock bütçe döndür"""
        return {
            "id": f"budget-{user_id}",
            "user_id": user_id,
            "monthly_income": 9000,
            "monthly_fixed_expenses": 4350,
            "available_budget": 4650,
            "savings_goal": 1000,
            "currency": "TRY"
        }
    
    async def upsert_budget(self, data: dict):
        """Mock bütçe kaydet"""
        print(f"   💾 Supabase'e kaydedildi: budgets tablosu")
        return {
            "id": "budget-uuid-123",
            **data
        }
    
    async def add_expense(self, data: dict):
        """Mock harcama kaydet"""
        print(f"   💾 Supabase'e kaydedildi: expenses tablosu")
        return {
            "id": "expense-uuid-123",
            **data
        }


class MockBaseAgent:
    """Mock BaseAgent"""
    
    def __init__(self, name: str, llm, db):
        self.name = name
        self.llm = llm
        self.db = db
    
    def log_action(self, action: str, data: dict = None):
        if data:
            print(f"   📋 {action}: {data}")
        else:
            print(f"   📋 {action}")
    
    async def call_llm_json(self, prompt: str, system: str = None):
        return {
            "detailed_analysis": "Mock LLM analizi",
            "key_recommendations": [
                "Aylık harcamalarınızı takip edin",
                "Tasarruf hedeflerinizi belirleyin"
            ],
            "risk_level": "medium"
        }


# ==================== BUDGET AGENT IMPORT ====================

# BaseAgent'ı mock ile değiştir
import app.agents.base_agent as base_module
base_module.BaseAgent = MockBaseAgent

import app.services.supabase_service as supabase_module
supabase_module.SupabaseService = MockSupabaseService

from app.agents.budget_agent import BudgetAgent


# ==================== TEST FONKSİYONLARI ====================

async def test_save_and_analyze():
    """Test 1: Veri girişi ve analiz"""
    
    print("\n" + "=" * 70)
    print("TEST 1: VERİ GİRİŞİ VE ANALİZ (save_and_analyze)")
    print("=" * 70)
    
    agent = BudgetAgent(MockLLMService(), None)
    
    result = await agent.execute({
        "action": "save_and_analyze",
        "user_id": "user-dengeli",
        "income_data": {
            "salary": 8000,
            "extra_income": 1000
        },
        "expense_data": {
            # Sabit giderler
            "rent": 2500,
            "electricity": 300,
            "water": 100,
            "gas": 200,
            "internet": 150,
            "phone": 100,
            "loan_payment": 500,
            "insurance": 200,
            "other_fixed": 0,
            # Değişken giderler
            "groceries": 1000,
            "transportation": 500,
            "health": 200,
            "education": 300,
            "entertainment": 200,
            "clothing": 100,
            "other_variable": 0
        },
        "savings_data": {
            "savings_goal": 1000,
            "savings_purpose": "Tatil"
        }
    })
    
    print(f"\n✓ Başarılı: {result['success']}")
    
    if result["success"]:
        print(f"\n📊 GELİR ÖZETİ:")
        inc = result["income_summary"]
        print(f"   Maaş:        ₺{inc['salary']}")
        print(f"   Ek Gelir:    ₺{inc['extra_income']}")
        print(f"   Toplam:      ₺{inc['total_income']}")
        
        print(f"\n💸 GİDER ÖZETİ:")
        exp = result["expense_summary"]
        print(f"   Sabit:       ₺{exp['total_fixed_expenses']}")
        print(f"   Değişken:    ₺{exp['total_variable_expenses']}")
        print(f"   Toplam:      ₺{exp['total_all_expenses']}")
        
        print(f"\n💰 BÜTÇE ANALİZİ:")
        ba = result["budget_analysis"]
        print(f"   Gelir:       ₺{ba.get('monthly_income', 0)}")
        print(f"   Sabit Gider: ₺{ba.get('fixed_expenses', 0)}")
        print(f"   Harcanabilir:₺{ba.get('available_budget', 0)}")
        print(f"   Sağlık Skoru:{ba.get('health_score', 0)}/100")
        
        print(f"\n💡 TAVSİYELER:")
        for tip in result.get("savings_tips", []):
            print(f"   {tip}")
        
        print(f"\n📈 DURUM: {result['status']}")
    else:
        print(f"❌ Hata: {result.get('error')}")
    
    return result["success"]


async def test_analyze_by_personality():
    """Test 2: Farklı personality tipleri için analiz"""
    
    print("\n" + "=" * 70)
    print("TEST 2: PERSONALITY TİPİNE GÖRE ANALİZ")
    print("=" * 70)
    
    agent = BudgetAgent(MockLLMService(), None)
    
    users = ["user-savruk", "user-dengeli", "user-tutumlu"]
    
    for user_id in users:
        print(f"\n👤 Kullanıcı: {user_id}")
        print("-" * 40)
        
        result = await agent.execute({
            "action": "analyze",
            "user_id": user_id
        })
        
        if result["success"]:
            print(f"   Spending Type: {result['spending_type']}")
            print(f"   Durum: {result['status']}")
            print(f"   Harcanabilir: ₺{result['financial_metrics']['available_budget']}")
            print(f"   💡 İlk Tavsiye: {result['savings_tips'][0]}")
        else:
            print(f"   ❌ Hata: {result.get('error')}")
    
    return True


async def test_add_expense():
    """Test 3: Harcama ekleme"""
    
    print("\n" + "=" * 70)
    print("TEST 3: HARCAMA EKLEME (add_expense)")
    print("=" * 70)
    
    agent = BudgetAgent(MockLLMService(), None)
    
    harcamalar = [
        {"category": "Gıda", "amount": 450, "description": "Market alışverişi"},
        {"category": "Ulaşım", "amount": 200, "description": "Taksi"},
        {"category": "Eğlence", "amount": 150, "description": "Sinema"},
        {"category": "Sağlık", "amount": 300, "description": "Eczane"},
    ]
    
    for h in harcamalar:
        result = await agent.execute({
            "action": "add_expense",
            "user_id": "user-dengeli",
            "category": h["category"],
            "amount": h["amount"],
            "description": h["description"]
        })
        
        if result["success"]:
            print(f"\n✓ {result['category']}: ₺{result['amount']}")
            print(f"  ID: {result['expense_id']}")
        else:
            print(f"❌ Hata: {result.get('error')}")
    
    return True


async def test_check_affordability():
    """Test 4: Uygunluk kontrolü"""
    
    print("\n" + "=" * 70)
    print("TEST 4: UYGUNLUK KONTROLÜ (check_affordability)")
    print("=" * 70)
    
    agent = BudgetAgent(MockLLMService(), None)
    
    test_cases = [
        {"user_id": "user-savruk",  "amount": 500,  "label": "Düşük tutar - Savruk"},
        {"user_id": "user-dengeli", "amount": 2000, "label": "Orta tutar - Dengeli"},
        {"user_id": "user-tutumlu", "amount": 3000, "label": "Yüksek tutar - Tutumlu"},
        {"user_id": "user-dengeli", "amount": 9000, "label": "Aşan tutar - Dengeli"},
    ]
    
    for tc in test_cases:
        print(f"\n📌 {tc['label']}")
        print(f"   Tutar: ₺{tc['amount']}")
        
        result = await agent.execute({
            "action": "check_affordability",
            "user_id": tc["user_id"],
            "amount": tc["amount"]
        })
        
        if result["success"]:
            status = "✓ UYGUN" if result["is_affordable"] else "✗ UYGUN DEĞİL"
            print(f"   Sonuç: {status}")
            print(f"   Harcanabilir: ₺{result['spendable_budget']}")
            print(f"   Kalan: ₺{result['remaining_after']}")
            print(f"   Tavsiye: {result['recommendation']}")
            if result.get("personality_note"):
                print(f"   Not: {result['personality_note']}")
        else:
            print(f"   ❌ Hata: {result.get('error')}")
    
    return True


async def test_validation():
    """Test 5: Validasyon kontrolleri"""
    
    print("\n" + "=" * 70)
    print("TEST 5: VALİDASYON KONTROLLERİ")
    print("=" * 70)
    
    agent = BudgetAgent(MockLLMService(), None)
    
    # Test 5a: Sıfır gelir
    print("\n📌 Sıfır gelir testi:")
    result = await agent.execute({
        "action": "save_and_analyze",
        "user_id": "user-dengeli",
        "income_data": {"salary": 0},
        "expense_data": {},
        "savings_data": {}
    })
    print(f"   Başarılı: {result['success']}")
    print(f"   Mesaj: {result['message']}")
    
    # Test 5b: Negatif tutar
    print("\n📌 Negatif tutar testi:")
    result = await agent.execute({
        "action": "add_expense",
        "user_id": "user-dengeli",
        "category": "Gıda",
        "amount": -100
    })
    print(f"   Başarılı: {result['success']}")
    print(f"   Mesaj: {result['message']}")
    
    # Test 5c: Bilinmeyen action
    print("\n📌 Bilinmeyen action testi:")
    result = await agent.execute({
        "action": "unknown_action",
        "user_id": "user-dengeli"
    })
    print(f"   Başarılı: {result['success']}")
    print(f"   Mesaj: {result['message']}")
    
    return True


# ==================== TESTLERI ÇALIŞTIR ====================

async def run_all_tests():
    """Tüm testleri çalıştır"""
    
    print("\n" + "🚀" * 35)
    print("BUDGET AGENT - TAM TEST SÜİTİ")
    print("🚀" * 35)
    
    results = []
    
    # Test 1: Veri girişi ve analiz
    r1 = await test_save_and_analyze()
    results.append(("Test 1: save_and_analyze", r1))
    
    # Test 2: Personality tipine göre analiz
    r2 = await test_analyze_by_personality()
    results.append(("Test 2: analyze by personality", r2))
    
    # Test 3: Harcama ekleme
    r3 = await test_add_expense()
    results.append(("Test 3: add_expense", r3))
    
    # Test 4: Uygunluk kontrolü
    r4 = await test_check_affordability()
    results.append(("Test 4: check_affordability", r4))
    
    # Test 5: Validasyon
    r5 = await test_validation()
    results.append(("Test 5: validation", r5))
    
    # Sonuçlar
    print("\n" + "=" * 70)
    print("TEST SONUÇLARI")
    print("=" * 70)
    
    all_passed = True
    for test_name, passed in results:
        status = "✅ GEÇTI" if passed else "❌ KALDI"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 70)
    if all_passed:
        print("✅ TÜM TESTLER BAŞARIYLA TAMAMLANDI!")
    else:
        print("❌ BAZI TESTLER BAŞARISIZ OLDU!")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(run_all_tests())