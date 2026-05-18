from app.agents.base_agent import BaseAgent
from app.prompts.personality_prompts import PERSONALITY_SYSTEM, PERSONALITY_ANALYSIS_PROMPT

# 10 soruluk test seti
QUESTIONS = [
    {
        "id": 1,
        "text": "Maaşın yattığında ilk ne yaparsın?",
        "options": {
            "A": "Önce faturalarımı ve borçlarımı öderim",
            "B": "Bir kısmını birikime ayırır, kalanı harcama için kullanırım",
            "C": "İstediğim bir şeyi satın alırım, hak ettim",
            "D": "Tüm ay boyunca nasıl kullanacağımı planlarım",
        },
        # A=savruk_karsiti, B=dengeli, C=savruk, D=tutumlu
        "scores": {"A": 1, "B": 2, "C": 4, "D": 0},
    },
    {
        "id": 2,
        "text": "İndirim dönemlerinde (Black Friday vb.) nasıl davranırsın?",
        "options": {
            "A": "Önceden liste yaparım, sadece ihtiyacım olanları alırım",
            "B": "Birkaç ek ürün alabilirim ama kontrollü",
            "C": "Fırsatı kaçırmamak için çok şey satın alırım",
            "D": "İndirimlerle ilgilenmem, çok vakit kaybı",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 2},
    },
    {
        "id": 3,
        "text": "Büyük bir alışveriş yapmadan önce ne kadar araştırırsın?",
        "options": {
            "A": "Saatler/günler araştırırım, en iyi fiyatı bulurum",
            "B": "Birkaç site karşılaştırırım",
            "C": "Beğenirsem hemen alırım",
            "D": "Arkadaş tavsiyesiyle alırım",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 2},
    },
    {
        "id": 4,
        "text": "Ay sonunda paranın bittiğini fark ettiğinde ne hissedersin?",
        "options": {
            "A": "Bu hiç olmaz, bütçemi takip ederim",
            "B": "Nadiren olur, biraz kısarım",
            "C": "Sık olur, kredi kartına yüklenirim",
            "D": "Olur, ama bir sonraki ay telafi ederim",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 3},
    },
    {
        "id": 5,
        "text": "Sosyal medyada gördüğün bir ürünü satın alma olasılığın?",
        "options": {
            "A": "Çok düşük, reklamlara kanmam",
            "B": "Gerçekten ihtiyacım varsa düşünürüm",
            "C": "Beğenirsem hemen sipariş veririm",
            "D": "Önce araştırırım sonra karar veririm",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 2},
    },
    {
        "id": 6,
        "text": "Aylık gelirinizin ne kadarını birikimlere ayırırsınız?",
        "options": {
            "A": "%20'den fazla",
            "B": "%10-20 arası",
            "C": "%5-10 arası",
            "D": "Hiç biriktiremiyorum",
        },
        "scores": {"A": 0, "B": 1, "C": 3, "D": 4},
    },
    {
        "id": 7,
        "text": "Beklenmedik bir 5000 TL gelir olsa ne yaparsın?",
        "options": {
            "A": "Tamamını birikime/yatırıma koyarım",
            "B": "Yarısını birikime, yarısını harcamaya",
            "C": "Uzun süredir istediğim bir şeyi alırım",
            "D": "Borçlarımı kapatırım",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 2},
    },
    {
        "id": 8,
        "text": "Bütçe takip uygulaması kullanır mısın?",
        "options": {
            "A": "Evet, düzenli kullanırım",
            "B": "Bazen not alırım",
            "C": "Hayır, gerek görmüyorum",
            "D": "Kurmayı düşünüyorum ama kurmadım",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 3},
    },
    {
        "id": 9,
        "text": "Bir ürünün daha ucuz alternatifi varsa ne yaparsın?",
        "options": {
            "A": "Her zaman en ucuzu tercih ederim",
            "B": "Kalite/fiyat dengesine bakarım",
            "C": "Marka/kalite önemli, fiyat ikincil",
            "D": "Duruma göre değişir",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 2},
    },
    {
        "id": 10,
        "text": "5 yıl sonra finansal durumun hakkında ne düşünüyorsun?",
        "options": {
            "A": "Net bir hedefim ve planım var",
            "B": "Genel bir fikrim var, üzerinde çalışıyorum",
            "C": "Çok düşünmüyorum, nasıl olsa hallolur",
            "D": "Endişeleniyorum ama ne yapacağımı bilmiyorum",
        },
        "scores": {"A": 0, "B": 1, "C": 4, "D": 3},
    },
]


def calculate_rule_score(answers: dict) -> tuple[int, str]:
    """
    Cevapları puanlar (0=tutumlu, 40=savruk).
    Returns: (total_score, category)
    """
    total = 0
    for q in QUESTIONS:
        answer = answers.get(str(q["id"]), "B")
        total += q["scores"].get(answer.upper(), 2)

    if total <= 10:
        category = "tutumlu"
    elif total <= 24:
        category = "dengeli"
    else:
        category = "savruk"

    return total, category


class PersonalityAgent(BaseAgent):
    def __init__(self, llm, db):
        super().__init__("personality_agent", llm, db)

    def _rule_based_analysis(self, category: str, score: int) -> dict:
        profiles = {
            "tutumlu": {
                "spending_type": "tutumlu",
                "risk_score": 2, "impulsive_score": 1, "saving_score": 9, "research_score": 8,
                "strengths": ["Güçlü tasarruf alışkanlığı", "Düşük impulsif harcama", "Uzun vadeli finansal planlama"],
                "weaknesses": ["Kendine harcama yapmakta zorlanabilir", "Fırsatları kaçırabilir"],
                "recommendations": "Tasarruf alışkanlıklarınız mükemmel. Birikimlerinizi yatırıma yönlendirmeyi düşünün.",
                "personality_summary": "Finansal konularda oldukça tutumlu ve disiplinli bir profilsiniz.",
            },
            "dengeli": {
                "spending_type": "dengeli",
                "risk_score": 3, "impulsive_score": 2, "saving_score": 8, "research_score": 6,
                "strengths": ["Dengeli harcama alışkanlığı", "Kontrollü birikim", "Finansal farkındalık"],
                "weaknesses": ["Bütçe takibini daha sistematik hale getirebilir", "Büyük alışverişlerde daha fazla araştırma yapabilir"],
                "recommendations": "Mevcut dengeli yaklaşımınızı koruyun. Aylık bütçe takibi ile daha iyi sonuçlar alabilirsiniz.",
                "personality_summary": "Mali konularda dengeli, kontrollü ve bilinçli bir yaklaşım sergiliyorsunuz.",
            },
            "savruk": {
                "spending_type": "savruk",
                "risk_score": 7, "impulsive_score": 8, "saving_score": 3, "research_score": 3,
                "strengths": ["Anlık kararlar alabilme", "Yaşamdan keyif alma"],
                "weaknesses": ["Yüksek impulsif harcama", "Düşük tasarruf eğilimi", "Bütçe takibi eksikliği"],
                "recommendations": "Aylık bütçe planı oluşturun ve harcamalarınızı kategorize edin. Otomatik birikim talimatı verin.",
                "personality_summary": "Harcamalarınızda impulsif davranma eğiliminiz var. Bilinçli adımlarla bunu dengeleyebilirsiniz.",
            },
        }
        return profiles.get(category, profiles["dengeli"])

    def get_questions(self) -> list:
        return [
            {
                "id": q["id"],
                "text": q["text"],
                "options": q["options"],
            }
            for q in QUESTIONS
        ]

    async def execute(self, input_data: dict) -> dict:
        """
        input_data:
            user_id: str
            answers: dict  {"1": "A", "2": "C", ...}
        """
        user_id = input_data["user_id"]
        answers = input_data["answers"]

        self.log_action("Starting personality analysis", {"user_id": user_id})

        # 1. Kural tabanlı puanlama
        rule_score, category = calculate_rule_score(answers)
        self.log_action("Rule score calculated", {"score": rule_score, "category": category})

        # 2. Cevapları okunabilir formata çevir
        readable_answers = []
        for q in QUESTIONS:
            answer_key = answers.get(str(q["id"]), "?").upper()
            answer_text = q["options"].get(answer_key, "Belirtilmedi")
            readable_answers.append(f"S{q['id']}: {q['text']}\nCevap: {answer_text}")
        answers_text = "\n\n".join(readable_answers)

        # 3. LLM analizi (rate limit durumunda kural tabanlı fallback)
        try:
            prompt = PERSONALITY_ANALYSIS_PROMPT.format(
                rule_score=rule_score,
                category=category,
                answers=answers_text,
            )
            analysis = await self.call_llm_json(prompt, system=PERSONALITY_SYSTEM)
            self.log_action("LLM analysis complete")
        except Exception as e:
            self.log_action("LLM analysis failed, using rule-based fallback", {"error": str(e)})
            analysis = self._rule_based_analysis(category, rule_score)

        # 4. DB'ye kaydet
        record = {
            "user_id": user_id,
            "spending_type": analysis.get("spending_type", category),
            "risk_score": analysis.get("risk_score", 5),
            "impulsive_score": analysis.get("impulsive_score", 5),
            "saving_score": analysis.get("saving_score", 5),
            "research_score": analysis.get("research_score", 5),
            "raw_answers": answers,
            "llm_analysis": str(analysis),
            "strengths": analysis.get("strengths", []),
            "weaknesses": analysis.get("weaknesses", []),
            "recommendations": analysis.get("recommendations", ""),
        }
        saved = await self.db.save_personality(record)
        self.log_action("Personality saved to DB", {"id": saved.get("id")})

        return {
            "profile_id": saved.get("id"),
            "spending_type": record["spending_type"],
            "rule_score": rule_score,
            "risk_score": record["risk_score"],
            "impulsive_score": record["impulsive_score"],
            "saving_score": record["saving_score"],
            "research_score": record["research_score"],
            "strengths": record["strengths"],
            "weaknesses": record["weaknesses"],
            "recommendations": record["recommendations"],
            "personality_summary": analysis.get("personality_summary", ""),
        }
