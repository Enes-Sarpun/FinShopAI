"""
LLM Factory — hangi agent'ın hangi LLM'i kullanacağını belirler.

Kullanım:
    from app.services.llm.factory import LLMFactory

    gemini = LLMFactory.get_gemini()          # Her zaman Gemini
    manus  = LLMFactory.get_manus()           # Her zaman Manus
    client = LLMFactory.for_agent("search")   # Agent adına göre otomatik
"""
from typing import Optional
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("llm_factory")

# Agent → provider eşleştirmesi
_AGENT_LLM_MAP = {
    "search":         "manus",    # Paralel: Manus + SerpAPI
    "watchlist":      "manus",    # Fiyat takibi
    "review":         "gemini",
    "conversation":   "gemini",
    "recommendation": "gemini",
    "budget":         "gemini",
    "personality":    "gemini",
    "security":       "gemini",
    "orchestrator":   "gemini",
}


class LLMFactory:
    """Singleton instance'lar tutar; her istekte yeni nesne oluşturmaz."""

    _gemini = None
    _manus  = None

    @classmethod
    def get_gemini(cls):
        """GeminiClient singleton döndürür."""
        if cls._gemini is None:
            from app.services.llm.gemini_client import GeminiClient
            cls._gemini = GeminiClient()
            logger.info("GeminiClient singleton oluşturuldu")
        return cls._gemini

    @classmethod
    def get_manus(cls):
        """ManusClient singleton döndürür."""
        if cls._manus is None:
            from app.services.llm.manus_client import ManusClient
            cls._manus = ManusClient()
            logger.info("ManusClient singleton oluşturuldu")
        return cls._manus

    @classmethod
    def for_agent(cls, agent_name: str):
        """
        Agent adına göre doğru client döndürür.
        ENABLE_MANUS=false ise Manus gerektiren agent'lar için Gemini döner.
        """
        provider = _AGENT_LLM_MAP.get(agent_name, "gemini")

        if provider == "manus":
            if not settings.ENABLE_MANUS:
                logger.debug(
                    f"[factory] ENABLE_MANUS=false → {agent_name} için Gemini kullanılıyor"
                )
                return cls.get_gemini()
            return cls.get_manus()

        return cls.get_gemini()

    @classmethod
    def reset(cls):
        """Test için instance'ları sıfırla."""
        cls._gemini = None
        cls._manus  = None
