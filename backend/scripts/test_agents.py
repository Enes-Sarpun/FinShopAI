"""
Agent'ları hızlıca test eder.
Çalıştır: python scripts/test_agents.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.services.llm_service import LLMService


async def test_llm():
    print("=== LLM Connection Test ===")
    llm = LLMService()
    response = await llm.generate("Merhaba! Tek cümlede kendini tanıt.")
    print(f"Response: {response}")
    print("LLM OK\n")


if __name__ == "__main__":
    asyncio.run(test_llm())
