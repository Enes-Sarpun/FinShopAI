# app/agents/budget_agent.py

"""
Budget Agent - Bütçe Analizi ve Yönetimi
==========================================

Kullanıcıdan detaylı gelir/gider verisi alır,
Supabase'e kaydeder, Personality verisiyle analiz yapar.

Veri Akışı:
1. Kullanıcı gelir/gider verilerini girer
2. Budget Agent verileri alır ve toplar
3. Supabase'e kaydeder (self.db.upsert_budget)
4. Personality verisiyle kişiselleştirilmiş analiz yapar
5. Sonuç döner
"""

from app.agents.base_agent import BaseAgent
from app.prompts.budget_prompts import BUDGET_SYSTEM, BUDGET_ANALYSIS_PROMPT


class BudgetAgent(BaseAgent):
    
    def __init__(self, llm, db):
        super().__init__("budget_agent", llm, db)
        # self.db BaseAgent'tan geliyor (PersonalityAgent gibi)
    
    
    async def execute(self, input_data: dict) -> dict:
        """
        input_data:
            action: "save_and_analyze" | "analyze" | "add_expense" | "check_affordability"
            user_id: str
            
            save_and_analyze için:
                income_data: dict
                expense_data: dict
                savings_data: dict
            
            add_expense için:
                category: str
                amount: float
                description: str (opsiyonel)
            
            check_affordability için:
                amount: float
        """
        
        action = input_data.get("action", "save_and_analyze")
        user_id = input_data.get("user_id")
        
        if action == "save_and_analyze":
            return await self.save_and_analyze(
                user_id=user_id,
                income_data=input_data.get("income_data", {}),
                expense_data=input_data.get("expense_data", {}),
                savings_data=input_data.get("savings_data", {})
            )
        
        elif action == "analyze":
            return await self.analyze_budget(user_id)
        
        elif action == "add_expense":
            return await self.add_expense(
                user_id=user_id,
                category=input_data.get("category"),
                amount=input_data.get("amount"),
                description=input_data.get("description")
            )
        
        elif action == "check_affordability":
            return await self.check_affordability(
                user_id=user_id,
                amount=input_data.get("amount")
            )
        
        else:
            return {
                "success": False,
                "error": f"Bilinmeyen action: {action}",
                "message": "Geçerli: save_and_analyze, analyze, add_expense, check_affordability"
            }
    
    
    # ==================== 1. VERİ KAYDET VE ANALİZ ET ====================
    
    async def save_and_analyze(
        self,
        user_id: str,
        income_data: dict,
        expense_data: dict,
        savings_data: dict
    ) -> dict:
        """
        Kullanıcının bütçe verilerini alır, Supabase'e kaydeder ve analiz eder.
        """
        
        try:
            self.log_action("Saving and analyzing budget", {"user_id": user_id})
            
            # 1. Gelirleri topla
            income_summary = self._calculate_income(income_data)
            
            # 2. Giderleri topla ve grupla
            expense_summary = self._calculate_expenses(expense_data)
            
            # 3. Validasyon
            if income_summary["total_income"] <= 0:
                raise ValueError("Gelir sıfırdan büyük olmalıdır")
            
            # 4. Harcanabilir bütçe hesapla
            savings_goal = savings_data.get("savings_goal", 0) or 0
            available_budget = (
                income_summary["total_income"] -
                expense_summary["total_fixed_expenses"]
            )
            
            # 5. Supabase'e kaydet (self.db - PersonalityAgent gibi!)
            record = {
                "user_id": user_id,
                "monthly_income": income_summary["total_income"],
                "monthly_fixed_expenses": expense_summary["total_fixed_expenses"],
                "available_budget": available_budget,
                "savings_goal": savings_goal,
                "currency": "TRY"
            }
            
            saved = await self.db.upsert_budget(record)
            
            self.log_action("Budget saved", {
                "budget_id": saved.get("id"),
                "total_income": income_summary["total_income"],
                "total_expenses": expense_summary["total_fixed_expenses"]
            })
            
            # 6. Personality verisiyle analiz yap
            analysis = await self.analyze_budget(user_id)
            
            return {
                "success": True,
                "budget_id": saved.get("id"),
                "income_summary": income_summary,
                "expense_summary": expense_summary,
                "savings_goal": savings_goal,
                "savings_purpose": savings_data.get("savings_purpose", ""),
                "budget_analysis": analysis.get("budget_analysis", {}),
                "savings_tips": analysis.get("savings_tips", []),
                "llm_analysis": analysis.get("llm_analysis", {}),
                "status": analysis.get("status", "healthy"),
                "message": "Bütçe kaydedildi ve analiz edildi"
            }
        
        except Exception as e:
            self.log_action("Save and analyze failed", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": "Bütçe kaydetme ve analiz hatası"
            }
    
    
    # ==================== 2. BÜTÇE ANALİZİ ====================
    
    async def analyze_budget(self, user_id: str) -> dict:
        """
        Supabase'deki bütçeyi Personality verisiyle analiz et.
        """
        
        try:
            self.log_action("Analyzing budget", {"user_id": user_id})
            
            # 1. Personality al (self.db - PersonalityAgent gibi!)
            personality = await self.db.get_personality(user_id)
            if not personality:
                self.log_action("Personality bulunamadı, varsayılan profil kullanılıyor", {"user_id": user_id})
                personality = {"spending_type": "dengeli", "risk_score": 5}
            
            spending_type = personality.get("spending_type", "dengeli")
            risk_score = personality.get("risk_score", 5)
            
            # 2. Bütçeyi al (self.db - PersonalityAgent gibi!)
            budget = await self.db.get_budget(user_id)
            if not budget:
                raise Exception("Bütçe bulunamadı. Önce bütçe bilgilerini girin.")
            
            self.log_action("Data loaded", {
                "spending_type": spending_type,
                "income": budget.get("monthly_income")
            })
            
            # 3. Matematiksel analiz
            budget_analysis = self._analyze_budget(
                budget["monthly_income"],
                budget["monthly_fixed_expenses"],
                budget.get("savings_goal")
            )
            
            # 4. Durum belirle
            available = budget_analysis["available_budget"]
            savings_goal = budget.get("savings_goal", 0) or 0
            
            if available < 0:
                status = "critical"
            elif available < savings_goal:
                status = "warning"
            else:
                status = "healthy"
            
            # 5. Tavsiyeler
            savings_tips = self._get_savings_tips(spending_type, budget_analysis)

            # 5b. Bu ay yapılan harcamalar — "harcanabilir" hesabına dahil edilir
            try:
                month_spending = await self.db.get_current_month_expense_total(user_id)
            except Exception as e:
                self.log_action("Failed to load current month expenses", {"error": str(e)})
                month_spending = 0.0

            spendable_after_savings = available - savings_goal
            remaining_spendable = spendable_after_savings - month_spending

            # 6. LLM analizi
            llm_analysis = await self._get_llm_analysis(
                budget=budget,
                spending_type=spending_type,
                risk_score=risk_score
            )
            
            self.log_action("Analysis complete", {"status": status})
            
            return {
                "success": True,
                "user_id": user_id,
                "spending_type": spending_type,
                "budget_analysis": budget_analysis,
                "financial_metrics": {
                    "total_income": round(budget["monthly_income"], 2),
                    "fixed_expenses": round(budget["monthly_fixed_expenses"], 2),
                    "available_budget": round(available, 2),
                    "savings_goal": round(savings_goal, 2),
                    "spendable_after_savings": round(spendable_after_savings, 2),
                    "current_month_spending": round(month_spending, 2),
                    "remaining_spendable": round(remaining_spendable, 2),
                    "expense_ratio": round(
                        (budget["monthly_fixed_expenses"] / budget["monthly_income"] * 100), 2
                    )
                },
                "savings_tips": savings_tips,
                "llm_analysis": llm_analysis,
                "status": status,
                "message": f"{spending_type} harcayıcı için analiz tamamlandı"
            }
        
        except Exception as e:
            self.log_action("Analysis failed", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": "Bütçe analizi hatası"
            }
    
    
    # ==================== 3. HARCAMA EKLE ====================
    
    async def add_expense(
        self,
        user_id: str,
        category: str,
        amount: float,
        description: str = None
    ) -> dict:
        """
        Gerçekleşen harcamayı Supabase'e kaydet.
        """
        
        try:
            self.log_action("Adding expense", {
                "user_id": user_id,
                "category": category,
                "amount": amount
            })
            
            if not category or amount <= 0:
                raise ValueError("Kategori ve tutar gereklidir")
            
            record = {
                "user_id": user_id,
                "category": category,
                "amount": amount,
                "description": description
            }
            
            # self.db - PersonalityAgent gibi!
            saved = await self.db.add_expense(record)
            
            self.log_action("Expense added", {"expense_id": saved.get("id")})

            return {
                "success": True,
                "expense_id": saved.get("id"),
                "category": category,
                "amount": round(amount, 2),
                "description": description,
                "created_at": saved.get("created_at"),
                "message": "Harcama başarıyla kaydedildi"
            }
        
        except Exception as e:
            self.log_action("Add expense failed", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": "Harcama kaydetme hatası"
            }
    
    
    # ==================== 4. UYGUNLUK KONTROL ====================
    
    async def check_affordability(
        self,
        user_id: str,
        amount: float
    ) -> dict:
        """
        Belirli bir harcamayı yapıp yapamayacağını kontrol et.
        Personality verisiyle kişiselleştirilmiş tavsiye verir.
        """
        
        try:
            self.log_action("Checking affordability", {
                "user_id": user_id,
                "amount": amount
            })
            
            # Bütçeyi al (self.db - PersonalityAgent gibi!)
            budget = await self.db.get_budget(user_id)
            if not budget:
                raise Exception("Bütçe bulunamadı")
            
            available = budget["available_budget"]
            savings_goal = budget.get("savings_goal", 0) or 0
            spendable = available - savings_goal
            
            # Personality al (self.db - PersonalityAgent gibi!)
            personality = await self.db.get_personality(user_id)
            spending_type = personality.get("spending_type", "dengeli") if personality else "dengeli"
            
            # Kontrol et
            is_affordable = amount <= spendable
            remaining = spendable - amount if is_affordable else 0
            spending_pct = (amount / spendable * 100) if spendable > 0 else 0
            
            # Tavsiye
            if is_affordable:
                if spending_pct <= 25:
                    recommendation = "✓ Rahat harcayabilirsiniz"
                elif spending_pct <= 50:
                    recommendation = "⚠ Uygun ama dikkat edin"
                else:
                    recommendation = "⚠ Bütçenizin büyük kısmı bu harcama"
            else:
                deficit = amount - spendable
                recommendation = f"✗ Bütçe yetersiz. ₺{deficit:.2f} eksik"
            
            # Personality notu
            personality_note = ""
            if spending_type == "savruk" and is_affordable and spending_pct > 50:
                personality_note = "⚠ Savruk harcayıcılar için yüksek risk!"
            elif spending_type == "tutumlu" and is_affordable:
                personality_note = "✓ Tutumlu harcayıcı olarak iyi kontrol ediyorsunuz"
            
            self.log_action("Affordability check complete", {
                "is_affordable": is_affordable
            })
            
            return {
                "success": True,
                "is_affordable": is_affordable,
                "available_budget": round(available, 2),
                "spendable_budget": round(spendable, 2),
                "amount_to_spend": round(amount, 2),
                "remaining_after": round(remaining, 2),
                "spending_percentage": round(spending_pct, 2),
                "recommendation": recommendation,
                "personality_note": personality_note,
                "spending_type": spending_type,
                "message": "Uygunluk kontrolü tamamlandı"
            }
        
        except Exception as e:
            self.log_action("Affordability check failed", {"error": str(e)})
            return {
                "success": False,
                "error": str(e),
                "message": "Uygunluk kontrolü hatası"
            }
    
    
    # ==================== HELPER METHODS ====================
    
    def _calculate_income(self, income_data: dict) -> dict:
        """Gelir verilerini topla"""
        
        salary = float(income_data.get("salary", 0) or 0)
        extra = float(income_data.get("extra_income", 0) or 0)
        total = salary + extra
        
        return {
            "salary": round(salary, 2),
            "extra_income": round(extra, 2),
            "total_income": round(total, 2)
        }
    
    
    def _calculate_expenses(self, expense_data: dict) -> dict:
        """Gider verilerini topla ve grupla"""
        
        # Sabit giderler
        fixed = {
            "rent": float(expense_data.get("rent", 0) or 0),
            "electricity": float(expense_data.get("electricity", 0) or 0),
            "water": float(expense_data.get("water", 0) or 0),
            "gas": float(expense_data.get("gas", 0) or 0),
            "internet": float(expense_data.get("internet", 0) or 0),
            "phone": float(expense_data.get("phone", 0) or 0),
            "loan_payment": float(expense_data.get("loan_payment", 0) or 0),
            "insurance": float(expense_data.get("insurance", 0) or 0),
            "other_fixed": float(expense_data.get("other_fixed", 0) or 0),
        }
        
        # Değişken giderler
        variable = {
            "groceries": float(expense_data.get("groceries", 0) or 0),
            "transportation": float(expense_data.get("transportation", 0) or 0),
            "health": float(expense_data.get("health", 0) or 0),
            "education": float(expense_data.get("education", 0) or 0),
            "entertainment": float(expense_data.get("entertainment", 0) or 0),
            "clothing": float(expense_data.get("clothing", 0) or 0),
            "other_variable": float(expense_data.get("other_variable", 0) or 0),
        }
        
        total_fixed = sum(fixed.values())
        total_variable = sum(variable.values())
        total_all = total_fixed + total_variable
        
        return {
            "fixed": {k: round(v, 2) for k, v in fixed.items()},
            "variable": {k: round(v, 2) for k, v in variable.items()},
            "total_fixed_expenses": round(total_fixed, 2),
            "total_variable_expenses": round(total_variable, 2),
            "total_all_expenses": round(total_all, 2)
        }
    
    
    def _analyze_budget(
        self,
        monthly_income: float,
        fixed_expenses: float,
        savings_goal: float = None
    ) -> dict:
        """Matematiksel bütçe analizi"""
        
        available = monthly_income - fixed_expenses
        savings_goal = savings_goal or 0
        
        result = {
            "monthly_income": round(monthly_income, 2),
            "fixed_expenses": round(fixed_expenses, 2),
            "available_budget": round(available, 2),
            "health_score": self._calculate_health_score(
                monthly_income, fixed_expenses, savings_goal
            )
        }
        
        if savings_goal > 0:
            result["savings_goal"] = round(savings_goal, 2)
            result["spendable_after_savings"] = round(available - savings_goal, 2)
            result["savings_percentage"] = round(
                (savings_goal / monthly_income * 100), 2
            )
        
        return result
    
    
    def _calculate_health_score(
        self,
        monthly_income: float,
        fixed_expenses: float,
        savings_goal: float = None
    ) -> int:
        """Bütçe sağlığı skoru (0-100)"""
        
        if monthly_income == 0:
            return 0
        
        score = 0
        savings_goal = savings_goal or 0
        
        # 1. Sabit gider oranı (max 50 puan)
        expense_ratio = (fixed_expenses / monthly_income) * 100
        
        if expense_ratio <= 30:
            score += 50
        elif expense_ratio <= 50:
            score += 30
        else:
            score += 10
        
        # 2. Tasarruf hedefi (max 50 puan)
        if savings_goal > 0:
            savings_ratio = (savings_goal / monthly_income) * 100
            
            if savings_ratio >= 20:
                score += 50
            elif savings_ratio >= 10:
                score += 30
            else:
                score += 10
        else:
            score += 15
        
        return min(100, max(0, score))
    
    
    def _get_savings_tips(self, spending_type: str, budget_analysis: dict) -> list:
        """Spending type'a göre tasarruf önerileri.

        Çıktı, frontend tarafından i18n ile çevrilebilmesi için yapılandırılmış
        bir liste olarak döner: her öğe bir sözlüktür:
            { "key": "<i18n-anahtarı>", "params": { ... } }
        """

        tips: list[dict] = []
        available = budget_analysis.get("available_budget", 0)
        savings_goal = budget_analysis.get("savings_goal", 0) or 0

        if spending_type == "savruk":
            tips = [
                {"key": "savings.tip.savruk.budget"},
                {"key": "savings.tip.savruk.creditCard"},
                {"key": "savings.tip.savruk.trackCategory"},
                {"key": "savings.tip.savruk.avoidImpulse"},
                {"key": "savings.tip.savruk.shoppingList"},
            ]

        elif spending_type == "dengeli":
            rec_savings = int(round(available * 0.2))
            tips = [
                {"key": "savings.tip.balanced.goodHabits"},
                {"key": "savings.tip.balanced.targetSavings", "params": {"amount": rec_savings}},
                {"key": "savings.tip.balanced.emergencyFund"},
                {"key": "savings.tip.balanced.reviewBudget"},
                {"key": "savings.tip.balanced.checkSubscriptions"},
            ]

        else:  # tutumlu
            tips = [
                {"key": "savings.tip.frugal.discipline"},
                {"key": "savings.tip.frugal.invest"},
                {"key": "savings.tip.frugal.passiveIncome"},
                {"key": "savings.tip.frugal.rewardYourself"},
            ]

        if savings_goal > 0:
            if savings_goal > available:
                tips.append({
                    "key": "savings.tip.goalExceeds",
                    "params": {
                        "goal": int(round(savings_goal)),
                        "available": int(round(available)),
                    },
                })
            else:
                spendable = int(round(available - savings_goal))
                tips.append({
                    "key": "savings.tip.spendableAfterSavings",
                    "params": {"amount": spendable},
                })

        return tips
    
    
    async def _get_llm_analysis(
        self,
        budget: dict,
        spending_type: str,
        risk_score: int
    ) -> dict:
        """LLM ile detaylı analiz yap"""
        
        try:
            prompt = BUDGET_ANALYSIS_PROMPT.format(
                monthly_income=budget.get("monthly_income", 0),
                fixed_expenses=budget.get("monthly_fixed_expenses", 0),
                savings_goal=budget.get("savings_goal", 0),
                spending_type=spending_type,
                risk_score=risk_score
            )
            
            analysis = await self.call_llm_json(
                prompt,
                system=BUDGET_SYSTEM
            )
            
            self.log_action("LLM analysis complete")
            return analysis
        
        except Exception as e:
            self.log_action("LLM analysis failed", {"error": str(e)})
            return {
                "error": str(e),
                "message": "LLM analizi başarısız"
            }