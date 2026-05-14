"""
WatchlistAgent v2 Testleri
===========================
Test çalıştırma:
    cd <proje_koku>
    venv/Scripts/python.exe -m pytest backend/tests/test_watchlist_agent.py -v --asyncio-mode=auto
"""

import pytest
import importlib
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch, call

# BaseAgent'ın başka testlerden bozulmuş olma ihtimaline karşı reload
import app.agents.base_agent as _base_mod
importlib.reload(_base_mod)
import app.agents.watchlist_agent as _wl_mod
importlib.reload(_wl_mod)

from app.agents.watchlist_agent import WatchlistAgent, NOTIFICATION_COOLDOWN_HOURS


# ── Fixture'lar ──────────────────────────────────────────────────────────────

@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate = AsyncMock(return_value="🎉 Fiyat düştü! Hemen al.")
    llm.generate_json = AsyncMock(return_value={})
    return llm


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.client = MagicMock()

    # Varsayılan: boş liste döndür
    _make_chain = lambda data=None: _ChainMock(data or [])
    db.client.table.return_value = _make_chain()
    return db


class _ChainMock:
    """Supabase query zincirini taklit eden minimal mock."""
    def __init__(self, data=None):
        self._data = data or []
        self.data = self._data
        self.count = len(self._data)

    def select(self, *a, **kw):  return self
    def insert(self, *a, **kw):  return self
    def update(self, *a, **kw):  return self
    def delete(self, *a, **kw):  return self
    def eq(self, *a, **kw):      return self
    def gte(self, *a, **kw):     return self
    def order(self, *a, **kw):   return self
    def limit(self, *a, **kw):   return self
    def execute(self):           return self


@pytest.fixture
def agent(mock_llm, mock_db):
    return WatchlistAgent(llm=mock_llm, db=mock_db)


# ── Temel Mod Testleri ───────────────────────────────────────────────────────

class TestWatchlistAgentModes:

    @pytest.mark.asyncio
    async def test_missing_user_id_returns_error(self, agent):
        result = await agent.execute({"mode": "list"})
        assert result["success"] is False
        assert "user_id" in result["error"]

    @pytest.mark.asyncio
    async def test_unknown_mode_returns_error(self, agent):
        result = await agent.execute({"user_id": "u1", "mode": "nonexistent"})
        assert result["success"] is False
        assert "Bilinmeyen mod" in result["error"]

    @pytest.mark.asyncio
    async def test_add_product_missing_name_returns_error(self, agent):
        result = await agent.execute({
            "user_id": "u1",
            "mode": "add",
            "product": {"price": 100.0}
        })
        assert result["success"] is False

    @pytest.mark.asyncio
    async def test_remove_without_watchlist_id_returns_error(self, agent):
        result = await agent.execute({"user_id": "u1", "mode": "remove"})
        assert result["success"] is False
        assert "watchlist_id" in result["error"]

    @pytest.mark.asyncio
    async def test_history_without_watchlist_id_returns_error(self, agent):
        result = await agent.execute({"user_id": "u1", "mode": "history"})
        assert result["success"] is False
        assert "watchlist_id" in result["error"]


# ── Fiyat Ayrıştırma Testleri ────────────────────────────────────────────────

class TestPriceParsing:

    def test_parse_turkish_format(self, agent):
        assert agent._parse_price("13.999,00") == 13999.0

    def test_parse_english_format(self, agent):
        assert agent._parse_price("13,999.00") == 13999.0

    def test_parse_simple_price(self, agent):
        assert agent._parse_price("1500") == 1500.0

    def test_parse_with_currency_symbol(self, agent):
        assert agent._parse_price("₺2.500,99") == 2500.99

    def test_parse_empty_string_returns_none(self, agent):
        assert agent._parse_price("") is None

    def test_parse_invalid_string_returns_none(self, agent):
        assert agent._parse_price("N/A") is None

    def test_parse_with_tl_suffix(self, agent):
        assert agent._parse_price("4999 TL") == 4999.0


# ── İYİLEŞTİRME 1: Paralel Kontrol ──────────────────────────────────────────

class TestConcurrentChecking:

    @pytest.mark.asyncio
    async def test_empty_watchlist_returns_zero_checked(self, agent):
        with patch.object(agent, "_get_watchlist", new_callable=AsyncMock,
                          return_value={"watchlist": [], "success": True}):
            result = await agent.execute({"user_id": "u1", "mode": "check"})

        assert result["success"] is True
        assert result["checked"] == 0
        assert result["alerts_triggered"] == 0

    @pytest.mark.asyncio
    async def test_multiple_products_checked_in_parallel(self, agent):
        """5 ürün paralel kontrol edilmeli, sıralı değil."""
        items = [
            {"id": f"wl-{i}", "product_name": f"Ürün {i}",
             "search_query": f"urun{i}", "reference_price": 1000.0,
             "alert_threshold_pct": 3.0, "last_notified_at": None}
            for i in range(5)
        ]

        with patch.object(agent, "_get_watchlist", new_callable=AsyncMock,
                          return_value={"watchlist": items, "success": True}):
            with patch.object(agent, "_fetch_current_price_with_retry", return_value=None):
                with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                    result = await agent.execute({"user_id": "u1", "mode": "check"})

        assert result["checked"] == 5

    @pytest.mark.asyncio
    async def test_one_product_failure_does_not_stop_others(self, agent):
        """Bir ürün patlarsa diğerleri çalışmaya devam etmeli."""
        items = [
            {"id": "wl-ok", "product_name": "Sağlam Ürün",
             "search_query": "q", "reference_price": 1000.0,
             "alert_threshold_pct": 3.0, "last_notified_at": None},
            {"id": "wl-bad", "product_name": "Hatalı Ürün",
             "search_query": "bad", "reference_price": 1000.0,
             "alert_threshold_pct": 3.0, "last_notified_at": None},
        ]

        async def side_effect(user_id, item):
            if item["id"] == "wl-bad":
                raise RuntimeError("SerpAPI patladı")
            return {"watchlist_id": item["id"], "alert_sent": False}

        with patch.object(agent, "_get_watchlist", new_callable=AsyncMock,
                          return_value={"watchlist": items, "success": True}):
            with patch.object(agent, "_check_single_product", side_effect=side_effect):
                result = await agent.execute({"user_id": "u1", "mode": "check"})

        assert result["checked"] == 2   # Her iki ürün de işlendi
        outcomes = {o["watchlist_id"]: o for o in result["results"]}
        assert "error" in outcomes["wl-bad"]   # Hatalı ürün raporlandı
        assert "error" not in outcomes["wl-ok"]  # Sağlam ürün etkilenmedi


# ── İYİLEŞTİRME 2: Cooldown ─────────────────────────────────────────────────

class TestNotificationCooldown:

    def test_cooldown_active_when_notified_recently(self, agent):
        recent = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
        item = {"last_notified_at": recent}
        assert agent._is_cooldown_active(item) is True

    def test_cooldown_inactive_when_notified_long_ago(self, agent):
        old = (
            datetime.now(timezone.utc)
            - timedelta(hours=NOTIFICATION_COOLDOWN_HOURS + 1)
        ).isoformat()
        item = {"last_notified_at": old}
        assert agent._is_cooldown_active(item) is False

    def test_cooldown_inactive_when_never_notified(self, agent):
        item = {"last_notified_at": None}
        assert agent._is_cooldown_active(item) is False

    def test_cooldown_inactive_on_invalid_date(self, agent):
        item = {"last_notified_at": "invalid-date"}
        assert agent._is_cooldown_active(item) is False

    @pytest.mark.asyncio
    async def test_no_notification_during_cooldown(self, agent):
        """Cooldown aktifken bildirim oluşturulmamalı."""
        recent = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        item = {
            "id": "wl-1",
            "product_name": "Test",
            "search_query": "test",
            "reference_price": 1000.0,
            "alert_threshold_pct": 3.0,
            "last_notified_at": recent,
        }

        with patch.object(agent, "_fetch_current_price_with_retry", return_value=800.0):
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                with patch.object(agent, "_create_notification",
                                  new_callable=AsyncMock) as mock_notify:
                    outcome = await agent._check_single_product("u1", item)

        mock_notify.assert_not_called()
        assert outcome["alert_sent"] is False
        assert outcome.get("skipped_cooldown") is True


# ── İYİLEŞTİRME 3: Per-ürün Eşik ────────────────────────────────────────────

class TestPerProductThreshold:

    @pytest.mark.asyncio
    async def test_custom_threshold_respected(self, agent):
        """alert_threshold_pct=10 → %5 indirim bildirim tetiklememeli."""
        item = {
            "id": "wl-1",
            "product_name": "Laptop",
            "search_query": "laptop",
            "reference_price": 10000.0,
            "alert_threshold_pct": 10.0,  # %10 eşik
            "last_notified_at": None,
        }

        with patch.object(agent, "_fetch_current_price_with_retry", return_value=9500.0):  # %5 indirim
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                with patch.object(agent, "_create_notification",
                                  new_callable=AsyncMock) as mock_notify:
                    outcome = await agent._check_single_product("u1", item)

        mock_notify.assert_not_called()
        assert outcome["alert_sent"] is False

    @pytest.mark.asyncio
    async def test_custom_threshold_triggers_at_boundary(self, agent):
        """%10 eşikle tam %10 indirim → alarm tetiklenmeli."""
        item = {
            "id": "wl-2",
            "product_name": "Telefon",
            "search_query": "telefon",
            "reference_price": 10000.0,
            "alert_threshold_pct": 10.0,
            "last_notified_at": None,
        }

        with patch.object(agent, "_fetch_current_price_with_retry", return_value=9000.0):  # tam %10
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                with patch.object(agent, "_get_trend_label",
                                  new_callable=AsyncMock, return_value="düşüyor"):
                    with patch.object(agent, "_create_notification", new_callable=AsyncMock):
                        outcome = await agent._check_single_product("u1", item)

        assert outcome["alert_sent"] is True
        assert outcome["discount_pct"] == 10.0


# ── İYİLEŞTİRME 4: SerpAPI Retry ────────────────────────────────────────────

class TestSerpAPIRetry:

    def test_retry_succeeds_on_second_attempt(self, agent):
        """İlk denemede exception, ikincide başarı."""
        attempt = {"count": 0}

        def flaky_fetch(query):
            attempt["count"] += 1
            if attempt["count"] == 1:
                raise ConnectionError("timeout")
            return 5000.0

        with patch.object(agent, "_fetch_current_price_sync", side_effect=flaky_fetch):
            with patch("time.sleep"):   # sleepleri atla
                result = agent._fetch_current_price_with_retry("test sorgu")

        assert result == 5000.0
        assert attempt["count"] == 2

    def test_retry_exhausted_returns_none(self, agent):
        """Tüm retry denemeleri başarısız → None döner."""
        with patch.object(agent, "_fetch_current_price_sync",
                          side_effect=ConnectionError("always fails")):
            with patch("time.sleep"):
                result = agent._fetch_current_price_with_retry("test sorgu")

        assert result is None

    def test_none_result_does_not_retry(self, agent):
        """SerpAPI başarılı ama ürün bulunamadı (None) → retry yapılmamalı."""
        with patch.object(agent, "_fetch_current_price_sync",
                          return_value=None) as mock_fetch:
            with patch("time.sleep") as mock_sleep:
                result = agent._fetch_current_price_with_retry("bulunmayan ürün")

        assert result is None
        assert mock_fetch.call_count == 1  # Sadece bir kez denendi
        mock_sleep.assert_not_called()


# ── İYİLEŞTİRME 5: Trend Analizi ────────────────────────────────────────────

class TestTrendCalculation:

    def test_trend_dusuyor(self, agent):
        records = [
            {"price": 1000}, {"price": 980}, {"price": 960},
            {"price": 940}, {"price": 920}, {"price": 900},
        ]
        assert agent._calculate_trend(records) == "düşüyor"

    def test_trend_yukseliyor(self, agent):
        records = [
            {"price": 900}, {"price": 920}, {"price": 940},
            {"price": 960}, {"price": 980}, {"price": 1000},
        ]
        assert agent._calculate_trend(records) == "yükseliyor"

    def test_trend_sabit(self, agent):
        records = [
            {"price": 1000}, {"price": 1001}, {"price": 999},
            {"price": 1000}, {"price": 1002}, {"price": 998},
        ]
        assert agent._calculate_trend(records) == "sabit"

    def test_trend_insufficient_data(self, agent):
        records = [{"price": 1000}, {"price": 900}]
        assert agent._calculate_trend(records) == "veri yok"

    def test_trend_empty_records(self, agent):
        assert agent._calculate_trend([]) == "veri yok"

    def test_trend_ignores_records_without_price(self, agent):
        records = [
            {"price": 1000}, {"price": None}, {"price": 950},
            {"price": 900},  {"price": None}, {"price": 850},
        ]
        # None'lar filtrelenir, düşüş trendi görülmeli
        assert agent._calculate_trend(records) == "düşüyor"


# ── İndirim Mantığı (temel) ──────────────────────────────────────────────────

class TestDiscountLogic:

    @pytest.mark.asyncio
    async def test_no_alert_for_small_discount(self, agent):
        item = {
            "id": "wl-1", "product_name": "Test",
            "search_query": "test", "reference_price": 1000.0,
            "alert_threshold_pct": 3.0, "last_notified_at": None,
        }
        with patch.object(agent, "_fetch_current_price_with_retry", return_value=985.0):
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                outcome = await agent._check_single_product("u1", item)
        assert outcome["alert_sent"] is False

    @pytest.mark.asyncio
    async def test_alert_triggered_for_significant_discount(self, agent):
        item = {
            "id": "wl-2", "product_name": "Laptop",
            "search_query": "laptop", "reference_price": 20000.0,
            "alert_threshold_pct": 3.0, "last_notified_at": None,
        }
        with patch.object(agent, "_fetch_current_price_with_retry", return_value=17000.0):
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                with patch.object(agent, "_get_trend_label",
                                  new_callable=AsyncMock, return_value="düşüyor"):
                    with patch.object(agent, "_create_notification", new_callable=AsyncMock):
                        outcome = await agent._check_single_product("u1", item)
        assert outcome["alert_sent"] is True
        assert outcome["discount_pct"] == 15.0

    @pytest.mark.asyncio
    async def test_no_alert_when_price_increases(self, agent):
        item = {
            "id": "wl-3", "product_name": "Telefon",
            "search_query": "telefon", "reference_price": 15000.0,
            "alert_threshold_pct": 3.0, "last_notified_at": None,
        }
        with patch.object(agent, "_fetch_current_price_with_retry", return_value=16000.0):
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                outcome = await agent._check_single_product("u1", item)
        assert outcome["alert_sent"] is False

    @pytest.mark.asyncio
    async def test_no_alert_when_price_unavailable(self, agent):
        item = {
            "id": "wl-4", "product_name": "Tablet",
            "search_query": "tablet", "reference_price": 8000.0,
            "alert_threshold_pct": 3.0, "last_notified_at": None,
        }
        with patch.object(agent, "_fetch_current_price_with_retry", return_value=None):
            with patch.object(agent, "_save_price_history", new_callable=AsyncMock):
                outcome = await agent._check_single_product("u1", item)
        assert outcome["alert_sent"] is False
