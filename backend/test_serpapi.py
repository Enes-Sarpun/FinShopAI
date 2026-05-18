"""
SerpAPI bağlantı testi — backend klasöründen çalıştır:
  python test_serpapi.py
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

from serpapi import GoogleSearch

key = os.getenv("SERPAPI_KEY", "")
if not key:
    print("❌ SERPAPI_KEY boş!")
    sys.exit(1)

print(f"✅ SERPAPI_KEY var: {key[:8]}...")

queries = ["erkek kol saati", "bluetooth kulaklık", "babalar günü hediye"]

for q in queries:
    params = {
        "engine": "google_shopping",
        "q": q,
        "gl": "tr",
        "hl": "tr",
        "api_key": key,
    }
    try:
        results = GoogleSearch(params).get_dict()
        items = results.get("shopping_results", [])
        error = results.get("error")
        print(f"\n📦 Query: '{q}' → {len(items)} ürün | error={error}")
        if items:
            p = items[0]
            print(f"   Örnek: {p.get('title','?')[:50]} | fiyat={p.get('price','?')}")
        else:
            # Hangi key'ler var response'da?
            print(f"   Response keys: {list(results.keys())}")
    except Exception as e:
        print(f"❌ Hata: {type(e).__name__}: {e}")
