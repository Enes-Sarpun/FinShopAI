PERSONALITY_SYSTEM = """
Sen bir finansal davranış analisti uzmanısın.
Kullanıcının harcama alışkanlıklarını ve finansal karakterini analiz ediyorsun.
Cevabın her zaman geçerli bir JSON olmalı, başka hiçbir şey yazma.
"""

PERSONALITY_ANALYSIS_PROMPT = """
Kullanıcının 10 soruya verdiği cevaplar aşağıda.
Kural tabanlı ön hesaplama sonucu: {rule_score} / 100
Tahmini kategori: {category}

CEVAPLAR:
{answers}

Aşağıdaki JSON formatında analiz yap:
{{
    "spending_type": "tutumlu | dengeli | savruk",
    "risk_score": <1-10 arası tam sayı>,
    "impulsive_score": <1-10 arası tam sayı>,
    "saving_score": <1-10 arası tam sayı>,
    "research_score": <1-10 arası tam sayı>,
    "strengths": ["güçlü yön 1", "güçlü yön 2", "güçlü yön 3"],
    "weaknesses": ["zayıf yön 1", "zayıf yön 2", "zayıf yön 3"],
    "recommendations": "Kişiye özel 2-3 cümle finansal tavsiye",
    "personality_summary": "Karakteri özetleyen 2-3 cümle"
}}

SADECE JSON DÖNDÜR.
"""
