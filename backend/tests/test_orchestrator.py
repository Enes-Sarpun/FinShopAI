"""
Orchestrator v2 Testleri
=========================
Test çalıştırma:
    .\venv\Scripts\python.exe -m pytest backend/tests/test_orchestrator.py -v --asyncio-mode=auto
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.agents.orchestrator import (
    _classify_intent,
    _route_after_route,
    _route_after_search,
    OrchestratorState,
)


# ── Intent Sınıflandırıcı Testleri ───────────────────────────────────────────

class TestIntentClassifier:

    def test_watchlist_keywords(self):
        assert _classify_intent("Bu ürünü takibe al") == "watchlist_action"
        assert _classify_intent("Fiyat düşünce bildirim ver") == "watchlist_action"
        assert _classify_intent("Yıldızla bunu") == "watchlist_action"
        assert _classify_intent("Alarm kur bu ürüne") == "watchlist_action"

    def test_budget_keywords(self):
        assert _classify_intent("Bütçem nasıl?") == "budget_query"
        assert _classify_intent("Bu ay ne kadar harcadım") == "budget_query"
        assert _classify_intent("Mali durumum ne?") == "budget_query"

    def test_product_search_with_budget_hint(self):
        assert _classify_intent("1000 TL altında kulaklık") == "product_search"
        assert _classify_intent("500 liraya telefon var mı") == "product_search"

    def test_quick_search_without_budget(self):
        assert _classify_intent("En iyi laptop öner") == "quick_search"
        assert _classify_intent("Kablosuz kulaklık") == "quick_search"

    def test_watchlist_takes_priority_over_budget(self):
        """Hem watchlist hem budget kelimesi varsa watchlist kazanır."""
        assert _classify_intent("Bütçeme uygun ürünü takibe al") == "watchlist_action"


# ── Routing Fonksiyon Testleri ────────────────────────────────────────────────

class TestRoutingFunctions:

    def _state(self, intent: str) -> OrchestratorState:
        return {
            "user_id": "u1", "message": "test", "intent": intent,
            "personality": None, "budget": None, "search": None,
            "reviews": None, "recommendation": None, "watchlist_result": None,
            "chat_history": None, "error": None,
            "steps_completed": [], "timing": {},
        }

    def test_route_product_search_to_prepare(self):
        assert _route_after_route(self._state("product_search")) == "prepare"

    def test_route_quick_search_to_search(self):
        assert _route_after_route(self._state("quick_search")) == "search"

    def test_route_budget_query_to_budget_only(self):
        assert _route_after_route(self._state("budget_query")) == "budget_only"

    def test_route_watchlist_action_to_watchlist(self):
        assert _route_after_route(self._state("watchlist_action")) == "watchlist"

    def test_route_unknown_intent_defaults_to_prepare(self):
        assert _route_after_route(self._state("bilinmeyen")) == "prepare"

    def test_after_search_quick_search_skips_review(self):
        state = self._state("quick_search")
        assert _route_after_search(state) == "recommendation"

    def test_after_search_product_search_goes_to_review(self):
        state = self._state("product_search")
        assert _route_after_search(state) == "review"


# ── Node Testleri ─────────────────────────────────────────────────────────────

class TestOrchestatorNodes:

    def teardown_method(self):
        import app.agents.orchestrator as orch_module
        orch_module._llm_instance = None
        orch_module._db_instance = None

    def _base_state(self) -> OrchestratorState:
        return {
            "user_id": "u1", "message": "laptop öner", "intent": "product_search",
            "personality": None, "budget": None, "search": None,
            "reviews": None, "recommendation": None, "watchlist_result": None,
            "chat_history": None, "error": None,
            "steps_completed": [], "timing": {},
        }

    @pytest.mark.asyncio
    async def test_node_route_sets_intent(self):
        from app.agents.orchestrator import node_route
        state = self._base_state()
        state["message"] = "1000 TL kulaklık"
        result = await node_route(state)
        assert result["intent"] == "product_search"
        assert "route" in result["timing"]
        assert "route" in result["steps_completed"]

    @pytest.mark.asyncio
    async def test_node_route_timing_recorded(self):
        from app.agents.orchestrator import node_route
        state = self._base_state()
        result = await node_route(state)
        assert isinstance(result["timing"].get("route"), float)

    @pytest.mark.asyncio
    async def test_node_prepare_parallel_fetch(self):
        """prepare node'u 3 işlemi paralel çalıştırmalı."""
        from app.agents.orchestrator import node_prepare

        mock_db = MagicMock()
        mock_db.get_personality = AsyncMock(return_value={"spending_type": "dengeli"})
        mock_db.get_chat_history = AsyncMock(return_value=[])

        mock_budget_result = {"success": True, "status": "healthy"}

        with patch("app.agents.orchestrator.get_services") as mock_svc:
            with patch("app.agents.orchestrator.BudgetAgent") as MockBudget:
                mock_svc.return_value = (MagicMock(), mock_db)
                MockBudget.return_value.execute = AsyncMock(return_value=mock_budget_result)

                state = self._base_state()
                result = await node_prepare(state)

        assert result["personality"] == {"spending_type": "dengeli"}
        assert result["chat_history"] == []
        assert result["budget"] == mock_budget_result
        assert "prepare" in result["steps_completed"]
        assert "prepare" in result["timing"]

    @pytest.mark.asyncio
    async def test_node_prepare_partial_failure(self):
        """Bir işlem exception atarsa diğerleri çalışmaya devam etmeli."""
        from app.agents.orchestrator import node_prepare

        mock_db = MagicMock()
        mock_db.get_personality = AsyncMock(side_effect=Exception("DB hatası"))
        mock_db.get_chat_history = AsyncMock(return_value=["mesaj"])

        with patch("app.agents.orchestrator.get_services") as mock_svc:
            with patch("app.agents.orchestrator.BudgetAgent") as MockBudget:
                mock_svc.return_value = (MagicMock(), mock_db)
                MockBudget.return_value.execute = AsyncMock(return_value={"status": "healthy"})

                state = self._base_state()
                result = await node_prepare(state)

        # personality hataya rağmen None olmalı, diğerleri çalışmalı
        assert result["personality"] is None
        assert result["chat_history"] == ["mesaj"]
        assert result["budget"] is not None

    @pytest.mark.asyncio
    async def test_node_budget_only_skips_search(self):
        """budget_query intent → budget_only node çalışır, steps'te 'search' olmamalı."""
        from app.agents.orchestrator import node_budget_only

        mock_db = MagicMock()
        mock_db.get_personality = AsyncMock(return_value=None)
        mock_db.get_chat_history = AsyncMock(return_value=[])

        with patch("app.agents.orchestrator.get_services") as mock_svc:
            with patch("app.agents.orchestrator.BudgetAgent") as MockBudget:
                mock_svc.return_value = (MagicMock(), mock_db)
                MockBudget.return_value.execute = AsyncMock(return_value={"status": "warning"})

                state = self._base_state()
                result = await node_budget_only(state)

        assert "budget_only" in result["steps_completed"]
        assert "search" not in result["steps_completed"]

    @pytest.mark.asyncio
    async def test_node_watchlist_with_product(self):
        """Search sonucu varsa ilk ürünü watchlist'e eklemeli."""
        from app.agents.orchestrator import node_watchlist

        state = self._base_state()
        state["search"] = {"products": [{"name": "Laptop", "price": 15000.0}]}

        mock_wl_result = {"success": True, "message": "'Laptop' takip listesine eklendi."}

        with patch("app.agents.orchestrator.get_services") as mock_svc:
            with patch("app.agents.orchestrator.WatchlistAgent") as MockWL:
                mock_svc.return_value = (MagicMock(), MagicMock())
                MockWL.return_value.execute = AsyncMock(return_value=mock_wl_result)

                result = await node_watchlist(state)

        assert result["watchlist_result"] == mock_wl_result
        assert "watchlist" in result["steps_completed"]

        # execute'a "add" moduyla çağrıldı mı?
        call_args = MockWL.return_value.execute.call_args[0][0]
        assert call_args["mode"] == "add"
        assert call_args["product"]["name"] == "Laptop"

    @pytest.mark.asyncio
    async def test_node_watchlist_without_product(self):
        """Search sonucu yoksa 'list' moduna geçmeli."""
        from app.agents.orchestrator import node_watchlist

        state = self._base_state()
        state["search"] = None

        with patch("app.agents.orchestrator.get_services") as mock_svc:
            with patch("app.agents.orchestrator.WatchlistAgent") as MockWL:
                mock_svc.return_value = (MagicMock(), MagicMock())
                MockWL.return_value.execute = AsyncMock(return_value={"success": True, "watchlist": []})

                result = await node_watchlist(state)

        call_args = MockWL.return_value.execute.call_args[0][0]
        assert call_args["mode"] == "list"


# ── Servis Singleton Testleri ────────────────────────────────────────────────

class TestServiceSingleton:

    def setup_method(self):
        """Her testten önce singletonları sıfırla."""
        import app.agents.orchestrator as orch_module
        orch_module._llm_instance = None
        orch_module._db_instance = None

    def teardown_method(self):
        """Her testten sonra singletonları temizle (diğer test dosyalarını bozmaması için)."""
        import app.agents.orchestrator as orch_module
        orch_module._llm_instance = None
        orch_module._db_instance = None

    def test_get_services_returns_same_instances(self):
        """İki çağrı aynı instance'ları döndürmeli."""
        import app.agents.orchestrator as orch_module

        with patch("app.agents.orchestrator.LLMService") as MockLLM:
            with patch("app.agents.orchestrator.SupabaseService") as MockDB:
                MockLLM.return_value = MagicMock()
                MockDB.return_value = MagicMock()

                llm1, db1 = orch_module.get_services()
                llm2, db2 = orch_module.get_services()

        # Sadece bir kez oluşturulmalı
        assert MockLLM.call_count == 1
        assert MockDB.call_count == 1
        assert llm1 is llm2
        assert db1 is db2

