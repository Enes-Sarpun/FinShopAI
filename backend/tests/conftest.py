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
