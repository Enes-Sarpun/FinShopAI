PERSONALITY_SYSTEM = """Sen bir finansal psikoloji uzmanısın. Kullanıcının harcama alışkanlıklarını analiz ederek kişilik profili çıkarıyorsun. Yanıtlarını her zaman geçerli JSON formatında ver."""

PERSONALITY_ANALYSIS_PROMPT = """Kullanıcının kişilik testi sonuçlarını analiz et.

Kural tabanlı puan: {rule_score}/40 (0=tutumlu, 40=savruk)
Kategori: {category}

Cevaplar:
{answers}

Aşağıdaki JSON formatında analiz döndür:
{{
  "spending_type": "tutumlu|dengeli|savruk",
  "risk_score": 1-10,
  "impulsive_score": 1-10,
  "saving_score": 1-10,
  "research_score": 1-10,
  "strengths": ["güçlü yön 1", "güçlü yön 2", "güçlü yön 3"],
  "weaknesses": ["zayıf yön 1", "zayıf yön 2"],
  "recommendations": "Kişiye özel tavsiye metni",
  "personality_summary": "Kısa kişilik özeti (2-3 cümle)"
}}

Puanlar için referans:
- risk_score: 1=çok temkinli, 10=çok riskli
- impulsive_score: 1=çok planlı, 10=çok impulsif
- saving_score: 1=hiç biriktirmiyor, 10=çok biriktiriyor
- research_score: 1=hiç araştırmıyor, 10=çok detaylı araştırıyor
"""