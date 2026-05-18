"""
Tüm LLM provider'ları için ortak abstract interface.
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any


class BaseLLMClient(ABC):

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        """Düz metin üret."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """JSON dict üret."""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass
