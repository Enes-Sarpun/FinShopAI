"""
LLM Service — Geliştirilmiş Sürüm
=====================================
- asyncio.to_thread: Blocking Gemini call'ları async wrapper içinde
- Exponential backoff retry (3 deneme)
- Token count logging
- JSON parse robustluğu
"""

import asyncio
import json
import time
import re
import google.generativeai as genai
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("llm_service")

_MAX_RETRIES = 3
_BASE_DELAY = 1.5  # saniye (exponential backoff için)

# ── Modül-seviyesi paylaşımlı durum ─────────────────────────────────────────
# Gemini'yi sadece bir kez configure et + her (system_instruction) için tek bir
# GenerativeModel instance'ı tut. Bu sayede her istekte yeni model nesnesi
# oluşturmuyor, log spam'ini ve gereksiz kurulum maliyetini ortadan kaldırıyoruz.
_GEMINI_CONFIGURED = False
_BASE_MODEL: "genai.GenerativeModel | None" = None
_SYSTEM_MODEL_CACHE: dict[str, "genai.GenerativeModel"] = {}


def _ensure_configured() -> None:
    global _GEMINI_CONFIGURED, _BASE_MODEL
    if _GEMINI_CONFIGURED:
        return
    genai.configure(api_key=settings.GEMINI_API_KEY)
    _BASE_MODEL = genai.GenerativeModel(settings.GEMINI_MODEL)
    _GEMINI_CONFIGURED = True
    logger.info(f"LLM initialized: {settings.GEMINI_MODEL}")


def _get_model(system: str | None) -> "genai.GenerativeModel":
    _ensure_configured()
    if not system:
        return _BASE_MODEL  # type: ignore[return-value]
    cached = _SYSTEM_MODEL_CACHE.get(system)
    if cached is None:
        cached = genai.GenerativeModel(
            settings.GEMINI_MODEL,
            system_instruction=system,
        )
        _SYSTEM_MODEL_CACHE[system] = cached
    return cached


class LLMService:
    """Hafif facade. Asıl Gemini yapılandırması ve model cache modül
    seviyesinde tutuluyor; bu sınıfı her istekte oluşturmak ucuz.
    """

    def __init__(self):
        _ensure_configured()

    # ── Ana üretim metodu (async, blocking Gemini thread'e taşındı) ──────────
    async def generate(self, prompt: str, system: str = None) -> str:
        last_error = None
        model = _get_model(system)

        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                t0 = time.monotonic()
                # Blocking SDK çağrısını ayrı thread'e taşı
                response = await asyncio.to_thread(
                    model.generate_content, prompt
                )
                elapsed = (time.monotonic() - t0) * 1000

                # Token kullanımını logla
                usage = getattr(response, "usage_metadata", None)
                if usage:
                    logger.debug(
                        f"LLM tokens | prompt={getattr(usage, 'prompt_token_count', '?')} "
                        f"output={getattr(usage, 'candidates_token_count', '?')} "
                        f"elapsed={elapsed:.0f}ms"
                    )
                else:
                    logger.debug(f"LLM call done | elapsed={elapsed:.0f}ms")

                return response.text

            except Exception as e:
                last_error = e
                err_str = str(e).lower()
                is_rate_limit = any(
                    kw in err_str for kw in ["quota", "rate", "429", "resource exhausted"]
                )

                if is_rate_limit and attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2 ** (attempt - 1))  # 1.5s, 3s, 6s
                    logger.warning(
                        f"LLM rate limit (attempt {attempt}/{_MAX_RETRIES}), "
                        f"retrying in {delay:.1f}s..."
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"LLM error (attempt {attempt}): {e}")
                    break

        raise last_error

    # ── JSON üretimi ─────────────────────────────────────────────────────────
    async def generate_json(self, prompt: str, system: str = None) -> dict:
        text = await self.generate(prompt, system)
        return self._parse_json_safe(text)

    # ── JSON parse yardımcısı ─────────────────────────────────────────────────
    @staticmethod
    def _parse_json_safe(text: str) -> dict:
        text = text.strip()

        # Markdown code fence temizle (``` veya ```json)
        if text.startswith("```"):
            # İlk satırı (```json veya ```) ve son satırı (```) sil
            lines = text.split("\n")
            lines = lines[1:] if lines[0].startswith("```") else lines
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()

        # Düz parse dene
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # Regex ile ilk JSON obje/array bul
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass

        logger.error(f"JSON parse tamamen başarısız:\n{text[:300]}")
        raise ValueError(f"LLM geçerli JSON döndürmedi: {text[:200]}")
