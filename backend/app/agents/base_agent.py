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

    async def call_llm(self, prompt: str, system: str = None) -> str:
        try:
            self.logger.debug(f"LLM call | prompt_len={len(prompt)}")
            return await self.llm.generate(prompt, system)
        except Exception as e:
            self.logger.error(f"LLM error: {e}")
            raise

    async def call_llm_json(self, prompt: str, system: str = None) -> dict:
        try:
            return await self.llm.generate_json(prompt, system)
        except Exception as e:
            self.logger.error(f"LLM JSON error: {e}")
            raise

    def log_action(self, action: str, data: dict = None):
        self.logger.info(f"{action}", **(data or {}))
