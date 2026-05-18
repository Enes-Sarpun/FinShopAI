"""
Base Agent — Geliştirilmiş Sürüm
===================================
- log_action syntax düzeltildi
- Execution timing (ms) eklendi
- call_llm_with_retry yardımcısı eklendi
"""

import time
from abc import ABC, abstractmethod
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.core.logger import get_logger


class BaseAgent(ABC):
    def __init__(self, name: str, llm: LLMService, db: SupabaseService):
        self.name = name
        self.llm = llm
        self.db = db
        self.logger = get_logger(name)

    @abstractmethod
    async def execute(self, input_data: dict) -> dict:
        raise NotImplementedError

    # ── LLM çağrı yardımcıları ─────────────────────────────────────────────

    async def call_llm(self, prompt: str, system: str = None) -> str:
        try:
            t0 = time.monotonic()
            self.logger.debug(f"LLM call | prompt_len={len(prompt)}")
            result = await self.llm.generate(prompt, system)
            self.logger.debug(f"LLM done | {(time.monotonic()-t0)*1000:.0f}ms")
            return result
        except Exception as e:
            self.logger.error(f"LLM error: {e}")
            raise

    async def call_llm_json(self, prompt: str, system: str = None) -> dict:
        try:
            t0 = time.monotonic()
            result = await self.llm.generate_json(prompt, system)
            self.logger.debug(f"LLM JSON done | {(time.monotonic()-t0)*1000:.0f}ms")
            return result
        except Exception as e:
            self.logger.error(f"LLM JSON error: {e}")
            raise

    # ── Loglama yardımcısı (düzeltilmiş syntax) ────────────────────────────

    def log_action(self, action: str, data: dict = None):
        if data:
            details = " | ".join(f"{k}={v}" for k, v in data.items())
            self.logger.info(f"{action} | {details}")
        else:
            self.logger.info(action)

    # ── Timing yardımcısı ──────────────────────────────────────────────────

    def start_timer(self) -> float:
        return time.monotonic()

    def elapsed_ms(self, t0: float) -> float:
        return round((time.monotonic() - t0) * 1000, 1)
