from app.agents.base_agent import BaseAgent

SYSTEM_PROMPT = """Sen FinShop AI'ın sohbet asistanısın. Kullanıcıyla Türkçe, samimi ve kısa konuş.
Görevin: gelen mesajın bir ürün/alışveriş isteği mi yoksa sıradan sohbet mi olduğuna karar ver.

Ürün isteği örnekleri:
- "Anneme hediye öner", "laptop arıyorum", "en ucuz kulaklık", "bütçeme uygun telefon"

Sohbet örnekleri:
- "Teşekkür ederim", "Nasılsın?", "Güzel", "Tamam", "Evet", "Hayır", "Neden?"

JSON formatında cevap ver:
{
  "is_product_request": true/false,
  "reply": "eğer sohbetse kısa ve samimi cevabın buraya"
}
"""

PRODUCT_KEYWORDS = [
    "öner", "arıyorum", "bul", "istiyorum", "almak", "satın", "hediye",
    "ucuz", "fiyat", "ürün", "laptop", "telefon", "bilgisayar", "kulaklık",
    "kamera", "tablet", "saat", "ayakkabı", "giysi", "kitap", "oyun",
    "tl", "lira", "bütçe", "indirim", "kampanya", "sipariş"
]


def _quick_check(message: str) -> bool:
    """LLM çağırmadan hızlı keyword kontrolü."""
    lower = message.lower()
    return any(kw in lower for kw in PRODUCT_KEYWORDS)


class ConversationAgent(BaseAgent):
    def __init__(self, llm, db):
        super().__init__("conversation_agent", llm, db)

    async def execute(self, input_data: dict) -> dict:
        """
        input_data:
            message: str
            chat_history: list (opsiyonel, bağlam için)

        Returns:
            is_product_request: bool
            reply: str | None  (sohbetse dolu, ürün isteğiyse None)
        """
        message = input_data.get("message", "")
        history = input_data.get("chat_history", [])

        # Kısa mesajlarda keyword yoksa kesinlikle sohbet — LLM çağırmaya gerek yok
        if len(message.strip()) < 60 and not _quick_check(message):
            try:
                # Yine de LLM'den nazik bir cevap al
                history_text = ""
                if history:
                    recent = history[-4:]
                    history_text = "\n".join(
                        f"{'Kullanıcı' if h.get('role') == 'user' else 'Asistan'}: {h.get('message', '')}"
                        for h in recent
                    )

                prompt = f"""Önceki sohbet:
{history_text}

Kullanıcının son mesajı: "{message}"

Bu bir ürün/alışveriş isteği değil. Kısa, samimi ve Türkçe cevap ver.
JSON: {{"is_product_request": false, "reply": "cevabın"}}"""

                result = await self.call_llm_json(prompt, system=SYSTEM_PROMPT)
                return {
                    "is_product_request": False,
                    "reply": result.get("reply", "😊")
                }
            except Exception:
                return {"is_product_request": False, "reply": "😊 Başka bir konuda yardımcı olabilir miyim?"}

        # Keyword varsa veya uzun mesajsa LLM ile karar ver
        try:
            history_text = ""
            if history:
                recent = history[-4:]
                history_text = "\n".join(
                    f"{'Kullanıcı' if h.get('role') == 'user' else 'Asistan'}: {h.get('message', '')}"
                    for h in recent
                )

            prompt = f"""Önceki sohbet:
{history_text}

Kullanıcının son mesajı: "{message}"

Bu mesaj ürün/alışveriş isteği mi yoksa sohbet mi? JSON formatında cevap ver."""

            result = await self.call_llm_json(prompt, system=SYSTEM_PROMPT)
            return {
                "is_product_request": result.get("is_product_request", True),
                "reply": result.get("reply")
            }
        except Exception:
            # Fallback: keyword varsa ürün isteği say
            return {
                "is_product_request": _quick_check(message),
                "reply": None if _quick_check(message) else "Anlıyorum! Başka bir konuda yardımcı olabilir miyim?"
            }
