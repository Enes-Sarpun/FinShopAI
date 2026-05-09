# FinShop AI — Backend

## Kurulum

```bash
# 1. Sanal ortam oluştur
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Mac/Linux

# 2. Bağımlılıkları yükle
pip install -r requirements.txt

# 3. .env dosyasını oluştur
cp .env.example .env
# .env dosyasını doldurun (Supabase ve Gemini key'leri)

# 4. Sunucuyu başlat
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Swagger UI: http://localhost:8000/docs  
Health check: http://localhost:8000/health

## Supabase Kurulumu

1. [supabase.com](https://supabase.com) üzerinde yeni proje oluştur (Frankfurt region)
2. `supabase_schema.sql` dosyasını SQL Editor'e yapıştır ve çalıştır
3. Project Settings > API'den URL ve key'leri kopyala
4. `.env` dosyasına yapıştır

## Veritabanı Seed

```bash
python scripts/seed_database.py
```

## LLM Testi

```bash
python scripts/test_agents.py
```

## Endpoint'ler

| Method | Path | Açıklama |
|--------|------|----------|
| GET | /health | Sunucu sağlık kontrolü |
| POST | /api/auth/register | Kayıt |
| POST | /api/auth/login | Giriş |
| GET | /api/auth/me | Mevcut kullanıcı |
| GET | /api/personality/questions | Sorular |
| POST | /api/personality/submit | Cevap gönder |
| GET | /api/personality/{user_id} | Profil getir |
| POST | /api/budget/create | Bütçe oluştur |
| GET | /api/budget/{user_id} | Bütçe getir |
| POST | /api/budget/expense | Harcama ekle |
| GET | /api/products/search | Ürün ara |
| GET | /api/products/{id}/reviews | Yorumlar |
| POST | /api/chat | Ana chat endpoint |
