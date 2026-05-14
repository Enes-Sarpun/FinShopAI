"""
conftest.py — Test ortamı konfigürasyonu
=========================================
pytest başlamadan önce gerekli ortam değişkenlerini mock olarak ayarlar.
Gerçek Supabase / Gemini bağlantısı gerektirmeyen unit testler için.
"""

import os
import sys

# Backend dizinini Python path'ine ekle (proje kökünden çalışıldığında)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# ── Sahte ortam değişkenleri (API çağrısı yapılmayacak) ──────────────────────
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_KEY", "test-service-key")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-key")
os.environ.setdefault("GEMINI_MODEL", "gemini-2.5-flash")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret-minimum-32-chars-long")
os.environ.setdefault("SERPAPI_KEY", "test-serpapi-key")
os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("ALLOWED_ORIGINS", '["http://localhost:3000"]')

import pytest


@pytest.fixture(autouse=True)
def _reset_orchestrator_singletons():
    """Her test sonunda orchestrator singleton'larını sıfırla.
    Böylece test dosyaları arası mock sızıntısı önlenir."""
    # BaseAgent ve SupabaseService orijinallerini sakla
    import app.agents.base_agent as base_mod
    import app.services.supabase_service as supa_mod
    orig_base = base_mod.BaseAgent
    orig_supa = supa_mod.SupabaseService

    yield

    # Geri yükle
    base_mod.BaseAgent = orig_base
    supa_mod.SupabaseService = orig_supa

    try:
        import app.agents.orchestrator as orch
        orch._llm_instance = None
        orch._db_instance = None
    except (ImportError, AttributeError):
        pass
