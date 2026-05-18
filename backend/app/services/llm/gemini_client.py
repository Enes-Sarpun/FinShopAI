"""
Gemini LLM client — mevcut llm_service.py mantığını BaseLLMClient interface'ine
sarar. Sohbet, review, bütçe, kişilik agent'ları bu client'ı kullanır.
"""
import asyncio
import json
import re
import time
from typing import Optional, Dict, Any

import google.generativeai as genai

from app.core.config import settings
from app.core.logger import get_logger
from app.services.llm.base import BaseLLMClient

logger = get_logger("gemini_client")

_MAX_RETRIES = 3
_BASE_DELAY = 1.5

_GEMINI_CONFIGURED = False
_BASE_MODEL = None
_SYSTEM_MODEL_CACHE: dict = {}


def _ensure_configured() -> None:
    global _GEMINI_CONFIGURED, _BASE_MODEL
    if _GEMINI_CONFIGURED:
        return
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _BASE_MODEL = genai.GenerativeModel(settings.GEMINI_MODEL)
    _GEMINI_CONFIGURED = True
    logger.info(f"GeminiClient initialized: {settings.GEMINI_MODEL}")


def _get_model(system: Optional[str]):
    _ensure_configured()
    if not system:
        return _BASE_MODEL
    cached = _SYSTEM_MODEL_CACHE.get(system)
    if cached is None:
        cached = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=system,
        )
        _SYSTEM_MODEL_CACHE[system] = cached
    return cached


class GeminiClient(BaseLLMClient):

    def __init__(self):
        _ensure_configured()

    @property
    def provider_name(self) -> str:
        return "gemini"

    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        **kwargs,
    ) -> str:
        model = _get_model(system)
        last_error = None

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                response = await asyncio.to_thread(model.generate_content, prompt)
                elapsed = (time.monotonic() - t0) * 1000

                usage = getattr(response, "usage_metadata", None)
                if usage:
                    logger.debug(
                        f"Gemini tokens | prompt={getattr(usage, 'prompt_token_count', '?')} "
                        f"output={getattr(usage, 'candidates_token_count', '?')} "
                        f"elapsed={elapsed:.0f}ms"
                    )
                else:
                    logger.debug(f"Gemini call done | elapsed={elapsed:.0f}ms")

                return response.text

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_rate_limit = any(
                    kw in err_str for kw in ["quota", "rate", "429", "resource exhausted"]
                )
                if is_rate_limit and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))
                    logger.warning(
                        f"Gemini rate limit (attempt {attempt}/{_MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Gemini error (attempt {attempt}): {e}")
                    break

        raise last_error

    async def generate_json(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        text = await self.generate(prompt, system, **kwargs)
        return self._parse_json_safe(text)

    @staticmethod
    def _parse_json_safe(text: str) -> dict:
        text = text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error(f"JSON parse başarısız:\n{text[:300]}")
        raise ValueError(f"Gemini geçerli JSON döndürmedi: {text[:200]}")
