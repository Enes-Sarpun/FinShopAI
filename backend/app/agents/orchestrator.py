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
import re
import time
from typing import TypedDict, Optional


# ================================================================
# RESPONSE FILTER — Sistem metni sızıntısı önleme
# ================================================================

_INTERNAL_PATTERNS = [
    r"profil[ei]?\s+göre\s+\w+",
    r"savruk|tasarrufçu|dengeli|harcamacı|dürtüsel\s+profil",
    r"kullanıcının?\s+(kişilik|profil)\w*\s+",
    r"bütçe\s+ayarlandı",
    r"intent\s+tespit",
    r"agent\s+çalış",
    r"pipeline\s+",
    r"node\s+(prepare|search|route)",
    r"affordability\s+(tagging|score)",
    r"value_score",
    r"sentiment_score",
    r"spending_type",
    r"spendable_after",
]


def clean_user_text(text: str) -> str:
    """Kullanıcıya gidecek metinden internal/debug ifadeleri temizler."""
    if not text:
        return text
    lines = text.split("\n")
    cleaned = []
    for line in lines:
        if not any(re.search(p, line, re.IGNORECASE) for p in _INTERNAL_PATTERNS):
            cleaned.append(line)
    result = "\n".join(cleaned)
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()

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

# ConversationAgent intent → Orchestrator intent mapping
_CONV_TO_ORCH_INTENT = {
    "PRODUCT_SEARCH": "product_search",
    "COMPARISON":     "product_search",  # comparison flag ayrı taşınıyor
    "BUDGET_QUERY":   "budget_query",
    "COMPLAINT":      "product_search",  # şikayet sonrası yeniden arama
}


def _classify_intent(message: str, conv_intent: str = None) -> str:
    """
    ConversationAgent'tan gelen LLM-tabanlı intent varsa onu kullan,
    yoksa kural tabanlı fallback.
    Döndürür: 'product_search' | 'quick_search' | 'budget_query' | 'watchlist_action'
    """
    # 1. ConversationAgent'tan gelen intent (LLM tabanlı, güvenilir)
    if conv_intent and conv_intent in _CONV_TO_ORCH_INTENT:
        mapped = _CONV_TO_ORCH_INTENT[conv_intent]
        logger.info(f"[route] ConversationAgent intent kullanılıyor: {conv_intent} → {mapped}")
        return mapped

    # 2. Kural tabanlı fallback (ConversationAgent intent yoksa)
    lower = message.lower()
    if any(kw in lower for kw in _WATCHLIST_KW):
        return "watchlist_action"
    if any(kw in lower for kw in _BUDGET_KW):
        return "budget_query"
    # Fallback: artık her zaman product_search — quick_search'ü kaldırıyoruz
    # çünkü prepare node'u atlamak context kaybına yol açıyordu
    return "product_search"


# ================================================================
# STATE
# ================================================================

class OrchestratorState(TypedDict):
    user_id: str
    message: str
    intent: Optional[str]             # [v2]
    conv_intent: Optional[str]        # [v3] ConversationAgent'tan gelen intent
    extracted_query: Optional[str]    # [v3] ConversationAgent'tan gelen temizlenmiş sorgu
    is_comparison: bool               # [v3] Karşılaştırma modu
    comparison_products: list         # [v3] Karşılaştırılacak ürünler

    personality: Optional[dict]
    budget: Optional[dict]
    search: Optional[dict]
    reviews: Optional[list]
    recommendation: Optional[dict]
    watchlist_result: Optional[dict]  # [v2]
    chat_history: Optional[list]
    over_budget_products: Optional[list]
    budget_exceeded_warning: Optional[dict]

    error: Optional[str]
    steps_completed: list
    timing: dict                       # [v2]


# ================================================================
# NODE: Route  (5 — intent routing)
# ================================================================

async def node_route(state: OrchestratorState) -> OrchestratorState:
    t0 = time.monotonic()
    # ConversationAgent'tan gelen LLM-tabanlı intent'i kullan, yoksa fallback
    intent = _classify_intent(state["message"], state.get("conv_intent"))
    elapsed = time.monotonic() - t0
    logger.info(
        f"[route] intent={intent} | conv_intent={state.get('conv_intent')} "
        f"| {state['message'][:50]}"
    )
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

    # chat_history zaten chat.py'de konuşmaya özgü olarak çekildiyse DB'ye gitme
    prefetched_history = state.get("chat_history")
    if prefetched_history is not None:
        logger.info(f"[prepare] history pre-fetched ({len(prefetched_history)} msgs), skipping DB | user={state['user_id']}")
        personality, budget = await asyncio.gather(
            db.get_personality(state["user_id"]),
            BudgetAgent(llm=llm, db=db).execute({"action": "analyze", "user_id": state["user_id"]}),
            return_exceptions=True,
        )
        history = prefetched_history
    else:
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
    # ConversationAgent'tan gelen temizlenmiş sorguyu kullan, yoksa ham mesaj
    search_query = state.get("extracted_query") or state["message"]
    logger.info(f"[search] query={search_query} | original={state['message'][:50]}")
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

        # Daha önce önerilen ürün isimlerini topla — tekrar arama yapılınca aynı ürün gelmemesi için
        previously_shown: list[str] = []
        for h in history:
            if h.get("role") != "assistant":
                continue
            import json as _json
            meta = h.get("metadata") or {}
            if isinstance(meta, str):
                try:
                    meta = _json.loads(meta)
                except Exception:
                    meta = {}
            if meta.get("type") == "products":
                payload = meta.get("payload") or {}
                for p in (payload.get("products") or []):
                    name = p.get("name", "")
                    if name:
                        previously_shown.append(name[:60])
                for p in (payload.get("over_budget_products") or []):
                    name = p.get("name", "")
                    if name:
                        previously_shown.append(name[:60])

        result = await SearchAgent(llm=llm, db=db).execute({
            "query": search_query,
            "budget": None,           # kullanıcının sorgusunda açık fiyat var mı — LLM parse eder
            "user_id": state["user_id"],
            "max_budget": available,
            "previous_queries": previous_queries,
            "previously_shown": previously_shown[:15],
            "user_budget": budget_data.get("financial_metrics") or {},
            "personality": state.get("personality") or {},
            "is_comparison": state.get("is_comparison", False),
            "comparison_products": state.get("comparison_products", []),
        })
        elapsed = time.monotonic() - t0
        logger.info(
            f"[search] found={result.get('total_found')} | "
            f"over_budget={len(result.get('over_budget_products') or [])} | "
            f"{elapsed:.3f}s"
        )
        return {
            **state,
            "search": result,
            "over_budget_products": result.get("over_budget_products") or [],
            "budget_exceeded_warning": result.get("budget_exceeded_warning"),
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
        search_data = state.get("search") or {}
        gift_context = search_data.get("gift_context") or {}
        result = await RecommendationAgent(llm=llm, db=db).execute({
            "message": state["message"],
            "personality": state.get("personality"),
            "budget": state.get("budget"),
            "products": state.get("reviews") or [],
            "is_comparison": state.get("is_comparison", False),
            "comparison_products": state.get("comparison_products", []),
            "occasion": gift_context.get("occasion", ""),
            "recipient": gift_context.get("recipient", ""),
            "over_budget_products": state.get("over_budget_products") or [],
            "budget_exceeded_warning": state.get("budget_exceeded_warning"),
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
        "budget_query":     "budget_only",
        "watchlist_action": "watchlist",
    }.get(state.get("intent", "product_search"), "prepare")


def _route_after_search(state: OrchestratorState) -> str:
    """Arama sonrası review node'una geç."""
    return "review"


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

    # quick_search kaldırıldı — tüm ürün aramaları prepare → search → review yolundan geçer
    g.add_conditional_edges(
        "route", _route_after_route,
        {"prepare": "prepare",
         "budget_only": "budget_only", "watchlist": "watchlist"},
    )
    g.add_edge("prepare", "search")
    g.add_edge("search",         "review")
    g.add_edge("review",         "recommendation")
    g.add_edge("recommendation", END)
    g.add_edge("budget_only",    END)
    g.add_edge("watchlist",      END)

    return g.compile()


_graph = build_graph()


# ================================================================
# ANA FONKSİYON
# ================================================================

async def run_orchestrator(
    user_id: str,
    message: str,
    conv_intent: str = None,
    extracted_query: str = None,
    is_comparison: bool = False,
    comparison_products: list = None,
    chat_history: list = None,
) -> dict:
    """Chat endpoint'inden çağrılır. ConversationAgent'tan gelen intent bilgisini kullanır."""
    t_total = time.monotonic()
    logger.info(
        f"Orchestrator v3 | user={user_id} | msg={message[:60]} "
        f"| conv_intent={conv_intent} | extracted_query={extracted_query}"
    )

    initial_state: OrchestratorState = {
        "user_id": user_id, "message": message, "intent": None,
        "conv_intent": conv_intent,
        "extracted_query": extracted_query,
        "is_comparison": is_comparison,
        "comparison_products": comparison_products or [],
        "personality": None, "budget": None, "search": None,
        "reviews": None, "recommendation": None, "watchlist_result": None,
        # Önceden çekilen konuşmaya özgü geçmiş varsa kullan, yoksa node_prepare çeker
        "chat_history": chat_history if chat_history is not None else None,
        "over_budget_products": None,
        "budget_exceeded_warning": None,
        "error": None,
        "steps_completed": [], "timing": {},
    }

    final_state = await _graph.ainvoke(initial_state)
    final_state["timing"]["total"] = round(time.monotonic() - t_total, 3)

    logger.info(
        f"Orchestrator done | intent={final_state.get('intent')} "
        f"| steps={final_state['steps_completed']} "
        f"| timing={final_state['timing']}"
    )

    rec = final_state.get("recommendation") or {}
    # Kullanıcıya giden metin alanlarını temizle
    if rec:
        for field in ("summary", "financial_advice"):
            if rec.get(field):
                rec[field] = clean_user_text(rec[field])
        if rec.get("top_pick") and isinstance(rec["top_pick"], dict):
            for f in ("reason", "personality_fit"):
                if rec["top_pick"].get(f):
                    rec["top_pick"][f] = clean_user_text(rec["top_pick"][f])
        if rec.get("winner") and rec["winner"].get("reasoning_for_user"):
            rec["winner"]["reasoning_for_user"] = clean_user_text(rec["winner"]["reasoning_for_user"])

    return {
        "message":               message,
        "intent":                final_state.get("intent"),
        "steps_completed":       final_state["steps_completed"],
        "timing":                final_state.get("timing", {}),
        "personality":           final_state.get("personality"),
        "budget_status":         (final_state.get("budget") or {}).get("status"),
        "products":              final_state.get("reviews") or [],
        "recommendation":        rec,
        "watchlist_result":      final_state.get("watchlist_result"),
        "over_budget_products":  final_state.get("over_budget_products") or [],
        "budget_exceeded_warning": final_state.get("budget_exceeded_warning"),
        "error":                 final_state.get("error"),
    }
