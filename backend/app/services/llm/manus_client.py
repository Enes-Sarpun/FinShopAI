"""
Manus API client — otonom ürün araştırması için.
Search Agent ve Watchlist Agent fiyat takibinde kullanılır.

Manus bir AI agent olduğu için davranışı klasik LLM'den farklı:
  - Otonom çalışır (kendi adımlarını belirler)
  - Birden fazla kaynak tarar (Trendyol, Hepsiburada, Amazon TR, N11...)
  - Yanıt süresi daha uzun (10-60 saniye)
  - Sonuç daha zengin (yorumlar, fiyatlar, alternatifler)

generate() / generate_json() intentionally NotImplemented —
bu client sadece research_products() ile kullanılır.
"""
import asyncio
import json
import re
import time
from typing import Optional, Dict, Any, List

import httpx

from app.core.config import settings
from app.core.logger import get_logger
from app.services.llm.base import BaseLLMClient

logger = get_logger("manus_client")


class ManusClient(BaseLLMClient):

    def __init__(self):
        self.base_url = settings.MANUS_BASE_URL.rstrip("/")
        self.timeout = settings.MANUS_TIMEOUT
        self.max_retries = settings.MANUS_MAX_RETRIES
        self._key_idx = 0  # aktif key indeksi

    @property
    def api_key(self) -> str:
        keys = settings.manus_api_keys
        if not keys:
            return ""
        return keys[self._key_idx % len(keys)]

    def _next_key(self) -> bool:
        """Sonraki key'e geç. Tüm key'ler tükendiyse False döner."""
        keys = settings.manus_api_keys
        if self._key_idx + 1 >= len(keys):
            return False
        self._key_idx += 1
        logger.warning(f"[manus] key_idx={self._key_idx} key'e geçiliyor ({len(keys)} key mevcut)")
        return True

    @property
    def provider_name(self) -> str:
        return "manus"

    # ── Ana araştırma metodu ─────────────────────────────────────────────────

    async def research_products(
        self,
        query: str,
        budget_range: Optional[Dict] = None,
        sources: Optional[List[str]] = None,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        """
        Manus'a otonom ürün araştırma görevi ver.

        Returns:
            {
                "products": [...],
                "sources_searched": [...],
                "research_summary": "...",
                "duration_seconds": 12.5
            }
        Hata durumunda: {"error": "...", "products": []}
        """
        task_prompt = self._build_research_prompt(query, budget_range, sources, max_results)
        t0 = time.monotonic()
        keys = settings.manus_api_keys
        total_keys = len(keys) if keys else 1

        # Her key için en fazla max_retries deneme, quota/429 → sonraki key
        for key_offset in range(total_keys):
            for attempt in range(1, self.max_retries + 1):
                try:
                    async with httpx.AsyncClient(
                        base_url=self.base_url,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                        timeout=self.timeout,
                    ) as client:
                        response = await client.post(
                            "/api/v1/chat/completions",
                            json={
                                "model": "manus",
                                "messages": [{"role": "user", "content": task_prompt}],
                                "stream": False,
                            },
                        )
                        response.raise_for_status()
                        duration = time.monotonic() - t0
                        logger.info(
                            f"[manus] research done | query={query[:50]} "
                            f"| key_idx={self._key_idx} | attempt={attempt} | {duration:.1f}s"
                        )
                        return self._parse_manus_response(response.json(), duration)

                except httpx.TimeoutException:
                    logger.warning(f"[manus] timeout (key_idx={self._key_idx} attempt {attempt}/{self.max_retries})")
                    if attempt == self.max_retries:
                        break
                    await asyncio.sleep(2)

                except httpx.HTTPStatusError as e:
                    status = e.response.status_code
                    if status in (429, 402, 403):
                        logger.warning(f"[manus] HTTP {status} — quota/limit, sonraki key'e geçiliyor")
                        break  # bu key için denemeler bitti, sonraki key'e geç
                    logger.error(f"[manus] HTTP {status}: {e.response.text[:200]}")
                    return {"error": f"manus_http_{status}", "products": []}

                except Exception as e:
                    logger.error(f"[manus] unexpected error (key_idx={self._key_idx} attempt {attempt}): {e}")
                    if attempt == self.max_retries:
                        break
                    await asyncio.sleep(2)

            # Bu key tükendi, sonrakine geç
            if not self._next_key():
                break

        return {"error": "manus_failed", "products": []}

    # ── Prompt builder ────────────────────────────────────────────────────────

    def _build_research_prompt(
        self,
        query: str,
        budget_range: Optional[Dict],
        sources: Optional[List[str]],
        max_results: int,
    ) -> str:
        prompt = (
            "Görev: Türkiye'deki online alışveriş sitelerinde ürün araştırması yap.\n\n"
            f"Sorgu: {query}\n"
        )

        if budget_range:
            mn = budget_range.get("min", 0)
            mx = budget_range.get("max")
            if mx:
                prompt += f"Bütçe aralığı: {mn}-{mx} TL\n"
            elif mn:
                prompt += f"Minimum bütçe: {mn} TL\n"

        if sources:
            prompt += f"Öncelikli kaynaklar: {', '.join(sources)}\n"
        else:
            prompt += "Kaynaklar: Trendyol, Hepsiburada, Amazon TR, N11\n"

        prompt += f"""
Yapman gerekenler:
1. Belirtilen sorguya uygun ürünleri ara
2. Birden fazla kaynaktan {max_results} en iyi seçeneği topla
3. Her ürün için: isim, fiyat, kaynak, link, rating, kısa açıklama
4. Sonuçları aşağıdaki JSON formatında döndür

JSON formatı (SADECE JSON, başka hiçbir şey yazma):
{{
  "products": [
    {{
      "name": "...",
      "price": 1234.50,
      "currency": "TRY",
      "source": "trendyol",
      "url": "...",
      "rating": 4.5,
      "review_count": 234,
      "image_url": "...",
      "description": "..."
    }}
  ],
  "sources_searched": ["trendyol", "hepsiburada"],
  "research_summary": "Kısa özet"
}}

DİKKAT:
- Sahte ürün/fiyat YOK
- Stokta olmayanları DAHİL ETME
- Türkçe sonuçları öncele
- Trendyol Yurt Dışı, AliExpress, Temu vb. DAHİL ETME
"""
        return prompt

    # ── Response parser ───────────────────────────────────────────────────────

    def _parse_manus_response(self, raw: dict, duration: float) -> dict:
        """
        Manus'tan dönen yanıtı standart formata çevir.
        OpenAI-compat format: choices[0].message.content içinde JSON bekliyoruz.
        """
        try:
            content = (
                raw.get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )
            parsed = self._extract_json(content)
            products = parsed.get("products", [])
            return {
                "products": products,
                "sources_searched": parsed.get("sources_searched", []),
                "research_summary": parsed.get("research_summary", ""),
                "duration_seconds": round(duration, 1),
            }
        except Exception as e:
            logger.error(f"[manus] response parse error: {e} | raw={str(raw)[:200]}")
            return {"error": "parse_error", "products": [], "duration_seconds": round(duration, 1)}

    @staticmethod
    def _extract_json(text: str) -> dict:
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

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        return {}

    # ── BaseLLMClient stubs (Manus generate() kullanmaz) ─────────────────────

    async def generate(self, prompt: str, system: Optional[str] = None, **kwargs) -> str:
        raise NotImplementedError(
            "ManusClient.generate() desteklenmiyor — research_products() kullan."
        )

    async def generate_json(self, prompt: str, system: Optional[str] = None, **kwargs) -> dict:
        raise NotImplementedError(
            "ManusClient.generate_json() desteklenmiyor — research_products() kullan."
        )
