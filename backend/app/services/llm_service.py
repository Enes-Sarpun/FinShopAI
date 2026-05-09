import json
import google.generativeai as genai
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("llm_service")


class LLMService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        logger.info(f"LLM initialized: {settings.GEMINI_MODEL}")

    async def generate(self, prompt: str, system: str = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            response = self.model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            logger.error(f"Gemini error: {e}")
            raise

    async def generate_json(self, prompt: str, system: str = None) -> dict:
        text = await self.generate(prompt, system)
        # Strip markdown code fences if present
        text = text.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nRaw: {text}")
            raise
