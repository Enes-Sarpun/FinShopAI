from typing import TypedDict, Optional
from langgraph.graph import StateGraph, END

from app.agents.personality_agent import PersonalityAgent
from app.agents.budget_agent import BudgetAgent
from app.agents.search_agent import SearchAgent
from app.agents.review_agent import ReviewAgent
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

    # Agent çıktıları
    personality: Optional[dict]
    budget: Optional[dict]
    search: Optional[dict]
    reviews: Optional[list]
    recommendation: Optional[dict]

    # Kontrol
    error: Optional[str]
    steps_completed: list


# ================================================================
# NODE FONKSİYONLARI
# ================================================================

def _services():
    return LLMService(), SupabaseService()


async def node_personality(state: OrchestratorState) -> OrchestratorState:
    """Kullanıcının personality profilini Supabase'den çeker."""
    logger.info(f"[personality] user_id={state['user_id']}")
    try:
        _, db = _services()
        profile = await db.get_personality(state["user_id"])
        return {
            **state,
            "personality": profile,
            "steps_completed": state["steps_completed"] + ["personality"]
        }
    except Exception as e:
        logger.error(f"[personality] error: {e}")
        return {**state, "personality": None, "error": str(e)}


async def node_budget(state: OrchestratorState) -> OrchestratorState:
    """Kullanıcının bütçesini çeker ve affordability kontrolü yapar."""
    logger.info(f"[budget] user_id={state['user_id']}")
    try:
        llm, db = _services()
        agent = BudgetAgent(llm=llm, db=db)
        result = await agent.execute({
            "action": "analyze",
            "user_id": state["user_id"]
        })
        return {
            **state,
            "budget": result,
            "steps_completed": state["steps_completed"] + ["budget"]
        }
    except Exception as e:
        logger.error(f"[budget] error: {e}")
        return {**state, "budget": None, "error": str(e)}


async def node_search(state: OrchestratorState) -> OrchestratorState:
    """Kullanıcı mesajına göre ürün arar."""
    logger.info(f"[search] query={state['message']}")
    try:
        llm, db = _services()
        agent = SearchAgent(llm=llm, db=db)

        # Bütçeden max fiyatı al
        budget_data = state.get("budget") or {}
        available = None
        if budget_data.get("success"):
            available = budget_data.get("financial_metrics", {}).get("spendable_after_savings")
        logger.info(f"[search] available_budget={available}")

        result = await agent.execute({
            "query": state["message"],
            "budget": None,  # Bütçe LLM tarafından mesajdan parse edilecek
            "user_id": state["user_id"],
            "max_budget": available  # Bilgi amaçlı, filtreleme için değil
        })
        logger.info(f"[search] total_found={result.get('total_found')} products_len={len(result.get('products', []))}")
        return {
            **state,
            "search": result,
            "steps_completed": state["steps_completed"] + ["search"]
        }
    except Exception as e:
        logger.error(f"[search] error: {e}")
        return {**state, "search": None, "error": str(e)}


async def node_review(state: OrchestratorState) -> OrchestratorState:
    """Bulunan ilk 3 ürün için yorum analizi yapar."""
    logger.info("[review] analyzing products")
    try:
        llm, db = _services()
        agent = ReviewAgent(llm=llm, db=db)

        products = (state.get("search") or {}).get("products", [])[:3]
        reviews = []

        for product in products:
            result = await agent.execute({
                "product_name": product.get("name", ""),
                "product_id": product.get("id"),
                "price": product.get("price", 0),
                "seller": product.get("seller", ""),
                "rating": product.get("rating", 0)
            })
            reviews.append({**product, "review_analysis": result})

        return {
            **state,
            "reviews": reviews,
            "steps_completed": state["steps_completed"] + ["review"]
        }
    except Exception as e:
        logger.error(f"[review] error: {e}")
        return {**state, "reviews": [], "error": str(e)}


async def node_recommendation(state: OrchestratorState) -> OrchestratorState:
    """
    Recommendation Agent buraya bağlanacak.
    Şimdilik search + review çıktısını direkt döner.
    """
    logger.info("[recommendation] placeholder — RecommendationAgent bağlanacak")
    try:
        # TODO: RecommendationAgent entegre edilince burası güncellenecek
        # from app.agents.recommendation_agent import RecommendationAgent
        # llm, db = _services()
        # agent = RecommendationAgent(llm=llm, db=db)
        # result = await agent.execute({...})

        reviews = state.get("reviews") or []
        personality = state.get("personality") or {}
        spending_type = personality.get("spending_type", "dengeli")

        recommendation = {
            "spending_type": spending_type,
            "top_products": reviews[:3],
            "message": f"{spending_type.capitalize()} profili için öneriler hazırlandı.",
            "note": "RecommendationAgent entegre edilince bu alan güncellenecek"
        }

        return {
            **state,
            "recommendation": recommendation,
            "steps_completed": state["steps_completed"] + ["recommendation"]
        }
    except Exception as e:
        logger.error(f"[recommendation] error: {e}")
        return {**state, "recommendation": None, "error": str(e)}


# ================================================================
# GRAPH KURULUMU
# ================================================================

def build_graph() -> StateGraph:
    graph = StateGraph(OrchestratorState)

    # Node'ları ekle
    graph.add_node("personality", node_personality)
    graph.add_node("budget", node_budget)
    graph.add_node("search", node_search)
    graph.add_node("review", node_review)
    graph.add_node("recommendation", node_recommendation)

    # Akış: personality → budget → search → review → recommendation → END
    graph.set_entry_point("personality")
    graph.add_edge("personality", "budget")
    graph.add_edge("budget", "search")
    graph.add_edge("search", "review")
    graph.add_edge("review", "recommendation")
    graph.add_edge("recommendation", END)

    return graph.compile()


# Uygulama başlarken bir kez derlenir
_graph = build_graph()


# ================================================================
# ANA FONKSİYON
# ================================================================

async def run_orchestrator(user_id: str, message: str) -> dict:
    """
    Chat endpoint'inden çağrılır.
    Tüm agent'ları sırayla çalıştırıp sonucu döner.
    """
    logger.info(f"Orchestrator started | user_id={user_id} | message={message}")

    initial_state: OrchestratorState = {
        "user_id": user_id,
        "message": message,
        "personality": None,
        "budget": None,
        "search": None,
        "reviews": None,
        "recommendation": None,
        "error": None,
        "steps_completed": []
    }

    final_state = await _graph.ainvoke(initial_state)

    logger.info(f"Orchestrator done | steps={final_state['steps_completed']}")

    return {
        "message": message,
        "steps_completed": final_state["steps_completed"],
        "personality": final_state.get("personality"),
        "budget_status": final_state.get("budget", {}).get("status") if final_state.get("budget") else None,
        "products": final_state.get("reviews", []),
        "recommendation": final_state.get("recommendation"),
        "error": final_state.get("error")
    }
