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

_BASE_DELAY = 1.5

# ── Key rotation state ───────────────────────────────────────────────────────
# Her key için ayrı model cache. Quota bitince _current_key_idx ilerler.
_current_key_idx = 0
# key_str → {base: GenerativeModel, system_cache: {str: GenerativeModel}}
_KEY_MODEL_CACHE: dict[str, dict] = {}


def _is_quota_error(err_str: str) -> bool:
    return any(kw in err_str for kw in ["quota", "rate", "429", "resource exhausted", "too many requests"])


def _build_models_for_key(api_key: str) -> dict:
    genai.configure(api_key=api_key)
    base = genai.GenerativeModel(settings.GEMINI_MODEL)
    return {"base": base, "system_cache": {}}


def _get_model_for_key(api_key: str, system: str | None) -> "genai.GenerativeModel":
    entry = _KEY_MODEL_CACHE.get(api_key)
    if entry is None:
        entry = _build_models_for_key(api_key)
        _KEY_MODEL_CACHE[api_key] = entry
    if not system:
        return entry["base"]
    cached = entry["system_cache"].get(system)
    if cached is None:
        genai.configure(api_key=api_key)
        cached = genai.GenerativeModel(settings.GEMINI_MODEL, system_instruction=system)
        entry["system_cache"][system] = cached
    return cached


class LLMService:
    """Gemini multi-key facade.
    Quota/rate-limit hatası alındığında otomatik olarak bir sonraki key'e geçer.
    Tüm key'ler tükenirse son hatayı fırlatır.
    """

    def __init__(self):
        keys = settings.gemini_api_keys
        if not keys:
            raise RuntimeError("Hiç geçerli GEMINI_API_KEY bulunamadı.")
        logger.info(f"LLMService başlatıldı | {len(keys)} Gemini key mevcut | model={settings.GEMINI_MODEL}")

    # ── Ana üretim metodu ────────────────────────────────────────────────────
    async def generate(self, prompt: str, system: str = None) -> str:
        global _current_key_idx
        keys = settings.gemini_api_keys
        last_error = None

        # Her key'i en fazla bir kez dene; quota hatası → sonraki key
        for offset in range(len(keys)):
            idx = (_current_key_idx + offset) % len(keys)
            api_key = keys[idx]
            model = _get_model_for_key(api_key, system)

            try:
                t0 = time.monotonic()
                response = await asyncio.to_thread(model.generate_content, prompt)
                elapsed = (time.monotonic() - t0) * 1000

                usage = getattr(response, "usage_metadata", None)
                if usage:
                    logger.debug(
                        f"LLM tokens | key_idx={idx} "
                        f"prompt={getattr(usage, 'prompt_token_count', '?')} "
                        f"output={getattr(usage, 'candidates_token_count', '?')} "
                        f"elapsed={elapsed:.0f}ms"
                    )
                else:
                    logger.debug(f"LLM call done | key_idx={idx} | elapsed={elapsed:.0f}ms")

                # Başarılı — key indeksini bu key'de bırak
                _current_key_idx = idx
                return response.text

            except Exception as e:
                last_error = e
                err_str = str(e).lower()

                if _is_quota_error(err_str):
                    logger.warning(f"Gemini key_idx={idx} quota/rate-limit — sonraki key'e geçiliyor. Hata: {e}")
                    # Bir sonraki key'e geç
                    _current_key_idx = (idx + 1) % len(keys)
                    continue
                else:
                    # Quota olmayan hata: exponential backoff ile aynı key'de yeniden dene
                    for attempt in range(1, 3):
                        delay = _BASE_DELAY * (2 ** (attempt - 1))
                        logger.warning(f"LLM error (attempt {attempt}/2), retrying in {delay:.1f}s: {e}")
                        await asyncio.sleep(delay)
                        try:
                            response = await asyncio.to_thread(model.generate_content, prompt)
                            _current_key_idx = idx
                            return response.text
                        except Exception as e2:
                            last_error = e2
                    break

        raise last_error  # type: ignore[misc]

    # ── JSON üretimi ─────────────────────────────────────────────────────────
    async def generate_json(self, prompt: str, system: str = None) -> dict:
        text = await self.generate(prompt, system)
        return self._parse_json_safe(text)

    # ── JSON parse yardımcısı ─────────────────────────────────────────────────
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

        logger.error(f"JSON parse tamamen başarısız:\n{text[:300]}")
        raise ValueError(f"LLM geçerli JSON döndürmedi: {text[:200]}")
