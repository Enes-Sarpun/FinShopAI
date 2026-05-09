from pydantic import BaseModel, Field
from typing import Dict, List, Optional


class PersonalitySubmitRequest(BaseModel):
    answers: Dict[str, str] = Field(
        ...,
        description="Soru ID -> cevap harfi (A/B/C/D)",
        example={"1": "A", "2": "B", "3": "C", "4": "A", "5": "B",
                 "6": "B", "7": "A", "8": "A", "9": "B", "10": "A"},
    )


class PersonalityResponse(BaseModel):
    profile_id: str
    spending_type: str
    rule_score: int
    risk_score: int
    impulsive_score: int
    saving_score: int
    research_score: int
    strengths: List[str]
    weaknesses: List[str]
    recommendations: str
    personality_summary: str


class QuestionOption(BaseModel):
    A: str
    B: str
    C: str
    D: str


class Question(BaseModel):
    id: int
    text: str
    options: QuestionOption


class QuestionsResponse(BaseModel):
    questions: List[Question]
    total: int
