from pydantic import BaseModel
from typing import Dict, List


class PersonalitySubmitRequest(BaseModel):
    answers: Dict[str, int]


class PersonalityResponse(BaseModel):
    profile_id: str
    spending_type: str
    rule_score: float
    risk_score: float
    impulsive_score: float
    saving_score: float
    research_score: float
    strengths: List[str]
    weaknesses: List[str]
    recommendations: str
    personality_summary: str


class QuestionsResponse(BaseModel):
    questions: List[dict]
    total: int
