"""
Orchestrator v2
===============
İYİLEŞTİRMELER:
  1. Servis Singleton      — LLMService/SupabaseService bir kez oluşturulur
  2. Paralel node_prepare  — personality + budget + history asyncio.gather
  3. Timing metrikleri     — her node süresi timing dict'e kaydedilir
  4. WatchlistAgent node   — 'takibe al' intent'i yakalanır
  5. Intent-based routing  — koşullu kenarlarla gereksiz node'lar atlanır

Intent → Pipeline eşlemesi:
  product_search   → route → prepare → search → review → recommendation → END
  quick_search     → route → search  → recommendation → END
  budget_query     → route → budget_only → END
  watchlist_action → route → watchlist → END
"""

import asyncio
import time
from typing import TypedDict, Optional

from langgraph.graph import StateGraph, END

from app.agents.budget_agent import BudgetAgent
from app.agents.search_agent import SearchAgent
from app.agents.review_agent import ReviewAgent
from app.agents.recommendation_agent import RecommendationAgent
from app.agents.watchlist_agent import WatchlistAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.logger import get_logger

logger = get_logger("orchestrator")


# ================================================================
# 1. SERVİS SINGLETON
# ================================================================

_llm_instance: Optional[LLMService] = None
_db_instance: Optional[SupabaseService] = None


def get_services() -> tuple[LLMService, SupabaseService]:
    """Per-process tek örnek — her node yeni nesne oluşturmaz."""
    global _llm_instance, _db_instance
    if _llm_instance is None:
        _llm_instance = LLMService()
        logger.info("LLMService singleton oluşturuldu")
    if _db_instance is None:
        _db_instance = SupabaseService()
        logger.info("SupabaseService singleton oluşturuldu")
    return _llm_instance, _db_instance


# ================================================================
# 5. INTENT SINIFLANDIRICI
# ================================================================

_WATCHLIST_KW = [
    "takibe al", "takip et", "yıldızla", "favorile", "kaydet",
    "alarm kur", "izle", "bildirim ver", "fiyat düşünce",
    "indirim olunca", "ucuzlayınca", "watchlist",
]
_BUDGET_KW = [
    "bütçem", "harcamam", "harcadım", "ne kadar harcadım",
    "bütçe durumu", "mali durum", "bu ay ne", "aylık harcama",
]


def _classify_intent(message: str) -> str:
    """
    Döndürür: 'product_search' | 'quick_search' | 'budget_query' | 'watchlist_action'
    """
    lower = message.lower()
    if any(kw in lower for kw in _WATCHLIST_KW):
        return "watchlist_action"
    if any(kw in lower for kw in _BUDGET_KW):
        return "budget_query"
    has_budget_hint = any(kw in lower for kw in ["tl", "lira", "₺", "bütçe", "fiyat"])
    return "product_search" if has_budget_hint else "quick_search"


# ================================================================
# STATE
# ================================================================

class OrchestratorState(TypedDict):
    user_id: str
    message: str
    intent: Optional[str]             # [v2]

    personality: Optional[dict]
    budget: Optional[dict]
    search: Optional[dict]
    reviews: Optional[list]
    recommendation: Optional[dict]
    watchlist_result: Optional[dict]  # [v2]
    chat_history: Optional[list]

    error: Optional[str]
    steps_completed: list
    timing: dict                       # [v2]


# ================================================================
# NODE: Route  (5 — intent routing)
# ================================================================

async def node_route(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    intent = _classify_intent(state["message"])
    elapsed = time.monotonic() - t0
    logger.info(f"[route] intent={intent} | {state['message'][:50]}")
    return {
        **state,
        "intent": intent,
        "timing": {**state.get("timing", {}), "route": round(elapsed, 3)},
        "steps_completed": state["steps_completed"] + ["route"],
    }


# ================================================================
# NODE: Prepare  (2 — paralel personality + budget + history)
# ================================================================

async def node_prepare(state: OrchestratorState) -> OrchestratorState:
    """personality, budget, history — tek gather, yarı sürede."""
    t0 = time.monotonic()
    llm, db = get_services()
    logger.info(f"[prepare] paralel fetch | user={state['user_id']}")

    personality, history, budget = await asyncio.gather(
        db.get_personality(state["user_id"]),
        db.get_chat_history(state["user_id"], limit=5),
        BudgetAgent(llm=llm, db=db).execute({"action": "analyze", "user_id": state["user_id"]}),
        return_exceptions=True,
    )

    if isinstance(personality, Exception):
        logger.error(f"[prepare] personality: {personality}")
        personality = None
    if isinstance(history, Exception):
        logger.error(f"[prepare] history: {history}")
        history = []
    if isinstance(budget, Exception):
        logger.error(f"[prepare] budget: {budget}")
        budget = None

    elapsed = time.monotonic() - t0
    logger.info(f"[prepare] done | {elapsed:.3f}s")
    return {
        **state,
        "personality": personality,
        "chat_history": history,
        "budget": budget,
        "timing": {**state.get("timing", {}), "prepare": round(elapsed, 3)},
        "steps_completed": state["steps_completed"] + ["prepare"],
    }


# ================================================================
# NODE: Budget Only  (4 — budget_query intent)
# ================================================================

async def node_budget_only(state: OrchestratorState) -> OrchestratorState:
    """Sadece bütçe sorguları — search/review/recommendation atlanır."""
    t0 = time.monotonic()
    llm, db = get_services()
    logger.info(f"[budget_only] user={state['user_id']}")
    try:
        personality, history, budget = await asyncio.gather(
            db.get_personality(state["user_id"]),
            db.get_chat_history(state["user_id"], limit=3),
            BudgetAgent(llm=llm, db=db).execute({"action": "analyze", "user_id": state["user_id"]}),
            return_exceptions=True,
        )
        elapsed = time.monotonic() - t0
        return {
            **state,
            "personality": None if isinstance(personality, Exception) else personality,
            "chat_history": [] if isinstance(history, Exception) else history,
            "budget": None if isinstance(budget, Exception) else budget,
            "timing": {**state.get("timing", {}), "budget_only": round(elapsed, 3)},
            "steps_completed": state["steps_completed"] + ["budget_only"],
        }
    except Exception as e:
        logger.error(f"[budget_only] error: {e}")
        return {**state, "budget": None, "error": str(e)}


# ================================================================
# NODE: Search
# ================================================================

async def node_search(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    logger.info(f"[search] query={state['message']}")
    try:
        llm, db = get_services()
        budget_data = state.get("budget") or {}
        available = None
        if budget_data.get("success"):
            available = budget_data.get("financial_metrics", {}).get("spendable_after_savings")

        history = state.get("chat_history") or []
        previous_queries = [
            h.get("message", "") for h in history
            if h.get("role") == "user" and h.get("message") != state["message"]
        ][:3]

        result = await SearchAgent(llm=llm, db=db).execute({
            "query": state["message"],
            "budget": None,
            "user_id": state["user_id"],
            "max_budget": available,
            "previous_queries": previous_queries,
        })
        elapsed = time.monotonic() - t0
        logger.info(f"[search] found={result.get('total_found')} | {elapsed:.3f}s")
        return {
            **state,
            "search": result,
            "timing": {**state.get("timing", {}), "search": round(elapsed, 3)},
            "steps_completed": state["steps_completed"] + ["search"],
        }
    except Exception as e:
        logger.error(f"[search] error: {e}")
        return {**state, "search": None, "error": str(e)}


# ================================================================
# NODE: Review  (ilk 3 ürün paralel analiz edilir)
# ================================================================

async def node_review(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    logger.info("[review] analyzing products")
    try:
        llm, db = get_services()
        agent = ReviewAgent(llm=llm, db=db)
        products = (state.get("search") or {}).get("products", [])[:3]

        async def _review_one(p: dict) -> dict:
            result = await agent.execute({
                "product_name": p.get("name", ""),
                "product_id": p.get("id"),
                "price": p.get("price", 0),
                "seller": p.get("seller", ""),
                "rating": p.get("rating", 0),
            })
            return {**p, "review_analysis": result}

        reviews = await asyncio.gather(*[_review_one(p) for p in products])
        elapsed = time.monotonic() - t0
        logger.info(f"[review] {len(reviews)} ürün analiz edildi | {elapsed:.3f}s")
        return {
            **state,
            "reviews": list(reviews),
            "timing": {**state.get("timing", {}), "review": round(elapsed, 3)},
            "steps_completed": state["steps_completed"] + ["review"],
        }
    except Exception as e:
        logger.error(f"[review] error: {e}")
        return {**state, "reviews": [], "error": str(e)}


# ================================================================
# NODE: Recommendation
# ================================================================

async def node_recommendation(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    logger.info("[recommendation] running")
    try:
        llm, db = get_services()
        result = await RecommendationAgent(llm=llm, db=db).execute({
            "message": state["message"],
            "personality": state.get("personality"),
            "budget": state.get("budget"),
            "products": state.get("reviews") or [],
        })
        elapsed = time.monotonic() - t0
        logger.info(f"[recommendation] done | {elapsed:.3f}s")
        return {
            **state,
            "recommendation": result,
            "timing": {**state.get("timing", {}), "recommendation": round(elapsed, 3)},
            "steps_completed": state["steps_completed"] + ["recommendation"],
        }
    except Exception as e:
        logger.error(f"[recommendation] error: {e}")
        return {**state, "recommendation": None, "error": str(e)}


# ================================================================
# NODE: Watchlist  (4 — watchlist_action intent)
# ================================================================

async def node_watchlist(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    logger.info(f"[watchlist] user={state['user_id']}")
    try:
        llm, db = get_services()
        agent = WatchlistAgent(llm=llm, db=db)

        products = (state.get("search") or {}).get("products", [])
        if products:
            p = products[0]
            result = await agent.execute({
                "user_id": state["user_id"],
                "mode": "add",
                "product": {
                    "name": p.get("name"),
                    "price": p.get("price"),
                    "url": p.get("url"),
                    "image_url": p.get("image_url"),
                    "seller": p.get("seller"),
                    "search_query": p.get("name"),
                },
            })
        else:
            result = await agent.execute({"user_id": state["user_id"], "mode": "list"})

        elapsed = time.monotonic() - t0
        logger.info(f"[watchlist] done | {elapsed:.3f}s")
        return {
            **state,
            "watchlist_result": result,
            "timing": {**state.get("timing", {}), "watchlist": round(elapsed, 3)},
            "steps_completed": state["steps_completed"] + ["watchlist"],
        }
    except Exception as e:
        logger.error(f"[watchlist] error: {e}")
        return {**state, "watchlist_result": None, "error": str(e)}


# ================================================================
# 5. ROUTING FONKSİYONLARI (Conditional Edges)
# ================================================================

def _route_after_route(state: OrchestratorState) -> str:
    """node_route çıkışı — intent'e göre ilk hedef node."""
    return {
        "product_search":   "prepare",
        "quick_search":     "search",
        "budget_query":     "budget_only",
        "watchlist_action": "watchlist",
    }.get(state.get("intent", "product_search"), "prepare")


def _route_after_search(state: OrchestratorState) -> str:
    """quick_search → recommendation (review atla); diğerleri → review."""
    return "recommendation" if state.get("intent") == "quick_search" else "review"


# ================================================================
# GRAPH
# ================================================================

def build_graph() -> StateGraph:
    g = StateGraph(OrchestratorState)

    g.add_node("route",          node_route)
    g.add_node("prepare",        node_prepare)
    g.add_node("search",         node_search)
    g.add_node("review",         node_review)
    g.add_node("recommendation", node_recommendation)
    g.add_node("budget_only",    node_budget_only)
    g.add_node("watchlist",      node_watchlist)

    g.set_entry_point("route")

    g.add_conditional_edges(
        "route", _route_after_route,
        {"prepare": "prepare", "search": "search",
         "budget_only": "budget_only", "watchlist": "watchlist"},
    )
    g.add_edge("prepare", "search")
    g.add_conditional_edges(
        "search", _route_after_search,
        {"review": "review", "recommendation": "recommendation"},
    )
    g.add_edge("review",         "recommendation")
    g.add_edge("recommendation", END)
    g.add_edge("budget_only",    END)
    g.add_edge("watchlist",      END)

    return g.compile()


_graph = build_graph()


# ================================================================
# ANA FONKSİYON
# ================================================================

async def run_orchestrator(user_id: str, message: str) -> dict:
    """Chat endpoint'inden çağrılır. Intent'e göre uygun pipeline çalışır."""
    t_total = time.monotonic()
    logger.info(f"Orchestrator v2 | user={user_id} | msg={message[:60]}")

    initial_state: OrchestratorState = {
        "user_id": user_id, "message": message, "intent": None,
        "personality": None, "budget": None, "search": None,
        "reviews": None, "recommendation": None, "watchlist_result": None,
        "chat_history": None, "error": None,
        "steps_completed": [], "timing": {},
    }

    final_state = await _graph.ainvoke(initial_state)
    final_state["timing"]["total"] = round(time.monotonic() - t_total, 3)

    logger.info(
        f"Orchestrator done | intent={final_state.get('intent')} "
        f"| steps={final_state['steps_completed']} "
        f"| timing={final_state['timing']}"
    )

    return {
        "message":          message,
        "intent":           final_state.get("intent"),
        "steps_completed":  final_state["steps_completed"],
        "timing":           final_state.get("timing", {}),
        "personality":      final_state.get("personality"),
        "budget_status":    (final_state.get("budget") or {}).get("status"),
        "products":         final_state.get("reviews") or [],
        "recommendation":   final_state.get("recommendation"),
        "watchlist_result": final_state.get("watchlist_result"),
        "error":            final_state.get("error"),
    }
