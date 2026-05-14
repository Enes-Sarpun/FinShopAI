"""
Orchestrator — Geliştirilmiş Sürüm
======================================
Değişiklikler:
  - Personality + Budget paralel çalıştırma (asyncio.gather)
  - Intent bilgisi state'e eklendi → COMPARISON modu desteği
  - Hata izolasyonu: bir agent başarısız olursa diğerleri devam ediyor
  - Adım süreleri loglanıyor
"""

import asyncio
import time
from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.agents.personality_agent import PersonalityAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.search_agent import SearchAgent
from app.agents.review_agent import ReviewAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.logger import get_logger

logger = get_logger("orchestrator")


# ================================================================
# STATE — tüm agent'lar arasında akan veri
# ================================================================

class OrchestratorState(TypedDict):
    user_id: str
    message: str

    # Intent bilgisi (ConversationAgent'tan gelir)
    intent: Optional[str]          # PRODUCT_SEARCH | COMPARISON
    is_comparison: Optional[bool]
    comparison_products: Optional[list]  # ["iPhone 15", "Galaxy S24"]
    extracted_query: Optional[str]       # Temizlenmiş arama sorgusu

    # Agent çıktıları
    personality: Optional[dict]
    budget: Optional[dict]
    search: Optional[dict]
    reviews: Optional[list]
    recommendation: Optional[dict]

    # Conversation context
    chat_history: Optional[list]

    # Kontrol
    error: Optional[str]
    steps_completed: list


# ================================================================
# NODE FONKSİYONLARI
# ================================================================

def _services():
    """Her çağrıda yeni service instance'ı (thread-safe)."""
    return LLMService(), SupabaseService()


async def node_personality_and_budget(state: OrchestratorState) -> OrchestratorState:
    """
    Personality ve Budget'ı PARALEL çeker.
    İkisi birbirinden bağımsız Supabase sorgusu — paralel çalışması güvenli.
    """
    logger.info(f"[personality+budget] user_id={state['user_id']}")
    t0 = time.monotonic()

    _, db = _services()
    llm, db2 = _services()

    async def get_personality():
        try:
            profile = await db.get_personality(state["user_id"])
            history = await db.get_chat_history(state["user_id"], limit=6)
            return profile, history
        except Exception as e:
            logger.error(f"[personality] error: {e}")
            return None, []

    async def get_budget():
        try:
            agent = BudgetAgent(llm=llm, db=db2)
            result = await agent.execute({
                "action": "analyze",
                "user_id": state["user_id"]
            })
            return result
        except Exception as e:
            logger.error(f"[budget] error: {e}")
            return None

    # Paralel çalıştır
    (profile, history), budget_result = await asyncio.gather(
        get_personality(),
        get_budget(),
    )

    elapsed = (time.monotonic() - t0) * 1000
    logger.info(f"[personality+budget] done | {elapsed:.0f}ms")

    completed = state["steps_completed"] + ["personality", "budget"]
    return {
        **state,
        "personality": profile,
        "chat_history": history,
        "budget": budget_result,
        "steps_completed": completed,
    }


async def node_search(state: OrchestratorState) -> OrchestratorState:
    """Kullanıcı mesajına göre ürün arar. Karşılaştırma modunda genişletilmiş sorgu kullanır."""
    t0 = time.monotonic()

    # Arama sorgusunu belirle
    if state.get("is_comparison") and state.get("comparison_products"):
        # Karşılaştırma: tüm ürünleri tek sorguda ara
        query = " vs ".join(state["comparison_products"])
        logger.info(f"[search] COMPARISON mode | query={query}")
    else:
        query = state.get("extracted_query") or state["message"]
        logger.info(f"[search] PRODUCT_SEARCH mode | query={query}")

    try:
        llm, db = _services()
        agent = SearchAgent(llm=llm, db=db)

        # Bütçeden max fiyatı al
        budget_data = state.get("budget") or {}
        available = None
        if budget_data.get("success"):
            available = budget_data.get("financial_metrics", {}).get("spendable_after_savings")

        # Son chat geçmişinden önceki arama konularını çıkar
        history = state.get("chat_history") or []
        previous_queries = [
            h.get("message", "") for h in history
            if h.get("role") == "user" and h.get("message") != state["message"]
        ][:3]

        result = await agent.execute({
            "query": query,
            "budget": None,
            "user_id": state["user_id"],
            "max_budget": available,
            "previous_queries": previous_queries,
            "is_comparison": state.get("is_comparison", False),
            "comparison_products": state.get("comparison_products", []),
        })

        elapsed = (time.monotonic() - t0) * 1000
        logger.info(
            f"[search] done | found={result.get('total_found')} | {elapsed:.0f}ms"
        )
        return {
            **state,
            "search": result,
            "steps_completed": state["steps_completed"] + ["search"],
        }
    except Exception as e:
        logger.error(f"[search] error: {e}")
        return {**state, "search": None, "error": str(e)}


async def node_review(state: OrchestratorState) -> OrchestratorState:
    """İlk 3 ürün için yorum analizi yapar."""
    t0 = time.monotonic()
    logger.info("[review] analyzing products")

    try:
        llm, db = _services()
        agent = ReviewAgent(llm=llm, db=db)

        products = (state.get("search") or {}).get("products", [])[:3]

        if not products:
            return {
                **state,
                "reviews": [],
                "steps_completed": state["steps_completed"] + ["review"],
            }

        # Ürün yorumlarını paralel analiz et
        async def analyze_product(product):
            result = await agent.execute({
                "product_name": product.get("name", ""),
                "product_id": product.get("id"),
                "price": product.get("price", 0),
                "seller": product.get("seller", ""),
                "rating": product.get("rating", 0),
            })
            return {**product, "review_analysis": result}

        reviews = await asyncio.gather(*[analyze_product(p) for p in products])

        elapsed = (time.monotonic() - t0) * 1000
        logger.info(f"[review] done | products={len(reviews)} | {elapsed:.0f}ms")

        return {
            **state,
            "reviews": list(reviews),
            "steps_completed": state["steps_completed"] + ["review"],
        }
    except Exception as e:
        logger.error(f"[review] error: {e}")
        return {**state, "reviews": [], "error": str(e)}


async def node_recommendation(state: OrchestratorState) -> OrchestratorState:
    """RecommendationAgent ile kişiselleştirilmiş öneri üretir."""
    t0 = time.monotonic()
    logger.info("[recommendation] running RecommendationAgent")

    try:
        llm, db = _services()
        agent = RecommendationAgent(llm=llm, db=db)

        result = await agent.execute({
            "message": state["message"],
            "intent": state.get("intent", "PRODUCT_SEARCH"),
            "is_comparison": state.get("is_comparison", False),
            "comparison_products": state.get("comparison_products", []),
            "personality": state.get("personality"),
            "budget": state.get("budget"),
            "products": state.get("reviews") or [],
        })

        elapsed = (time.monotonic() - t0) * 1000
        logger.info(f"[recommendation] done | {elapsed:.0f}ms")

        return {
            **state,
            "recommendation": result,
            "steps_completed": state["steps_completed"] + ["recommendation"],
        }
    except Exception as e:
        logger.error(f"[recommendation] error: {e}")
        return {**state, "recommendation": None, "error": str(e)}


# ================================================================
# GRAPH KURULUMU
# ================================================================

def build_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    # Node'ları ekle (personality+budget tek node olarak birleştirildi)
    graph.add_node("personality_and_budget", node_personality_and_budget)
    graph.add_node("search", node_search)
    graph.add_node("review", node_review)
    graph.add_node("recommendation", node_recommendation)

    # Akış: personality+budget (paralel) → search → review (paralel) → recommendation → END
    graph.set_entry_point("personality_and_budget")
    graph.add_edge("personality_and_budget", "search")
    graph.add_edge("search", "review")
    graph.add_edge("review", "recommendation")
    graph.add_edge("recommendation", END)

    return graph.compile()


# Uygulama başlarken bir kez derlenir
_graph = build_graph()


# ================================================================
# ANA FONKSİYON
# ================================================================

async def run_orchestrator(
    user_id: str,
    message: str,
    intent: str = "PRODUCT_SEARCH",
    is_comparison: bool = False,
    comparison_products: list = None,
    extracted_query: str = None,
) -> dict:
    """
    Chat endpoint'inden çağrılır.
    Tüm agent'ları yönetir ve sonucu döner.
    """
    t0 = time.monotonic()
    logger.info(
        f"Orchestrator started | user_id={user_id} | intent={intent} | "
        f"is_comparison={is_comparison} | message={message[:80]}"
    )

    initial_state: OrchestratorState = {
        "user_id": user_id,
        "message": message,
        "intent": intent,
        "is_comparison": is_comparison,
        "comparison_products": comparison_products or [],
        "extracted_query": extracted_query or message,
        "personality": None,
        "budget": None,
        "search": None,
        "reviews": None,
        "recommendation": None,
        "chat_history": None,
        "error": None,
        "steps_completed": [],
    }

    final_state = await _graph.ainvoke(initial_state)

    elapsed = (time.monotonic() - t0) * 1000
    logger.info(
        f"Orchestrator done | steps={final_state['steps_completed']} | {elapsed:.0f}ms"
    )

    return {
        "message": message,
        "intent": intent,
        "is_comparison": is_comparison,
        "steps_completed": final_state["steps_completed"],
        "personality": final_state.get("personality"),
        "budget_status": (
            final_state.get("budget", {}).get("status")
            if final_state.get("budget") else None
        ),
        "products": final_state.get("reviews", []),
        "recommendation": final_state.get("recommendation"),
        "error": final_state.get("error"),
    }
