"""
Mock ürün ve yorum verilerini Supabase'e yükler.
Çalıştır: python scripts/seed_database.py
"""
import json
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from supabase import create_client

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_SERVICE_KEY = os.environ["SUPABASE_SERVICE_KEY"]

client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

data_file = Path(__file__).parent.parent / "app" / "data" / "mock_products.json"
with open(data_file, encoding="utf-8") as f:
    data = json.load(f)

products = data["products"]
reviews = data["reviews"]

print(f"Seeding {len(products)} products...")
result = client.table("mock_products").insert(products).execute()
print(f"  Inserted: {len(result.data)} products")

# Map product name -> id for reviews
inserted_products = {p["name"]: p["id"] for p in result.data}

# Attach product_id to reviews
for r in reviews:
    r["product_id"] = inserted_products.get(r.pop("product_name", None))

reviews = [r for r in reviews if r["product_id"]]
print(f"Seeding {len(reviews)} reviews...")
result = client.table("mock_reviews").insert(reviews).execute()
print(f"  Inserted: {len(result.data)} reviews")

print("Done!")
