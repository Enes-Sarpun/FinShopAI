"""Quick test for SearchAgent"""
import asyncio
import logging

logging.basicConfig(level=logging.INFO)

from app.agents.search_agent import SearchAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService


async def test():
    llm = LLMService()
    db = SupabaseService()
    agent = SearchAgent(llm=llm, db=db)

    result = await agent.execute({
        "query": "babalar gunu hediye",
        "budget": None,
        "user_id": "test",
    })

    total = result.get("total_found", 0)
    print(f"\ntotal_found: {total}")

    products = result.get("products", [])
    if products:
        for p in products[:3]:
            name = p.get("name", "?")[:50]
            price = p.get("price", 0)
            seller = p.get("seller", "?")
            print(f"  - {name} | {price} TL | {seller}")
    else:
        print("  NO PRODUCTS FOUND")

    gc = result.get("gift_context")
    if gc:
        print(f"  gift_context: {gc}")


if __name__ == "__main__":
    asyncio.run(test())
