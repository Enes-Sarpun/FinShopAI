from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.prompts.security_prompts import (
    CONTENT_MODERATION_PROMPT,
    BANNED_WORDS_CHECK_PROMPT,
    FAKE_REVIEW_DETECTION_PROMPT,
    RATE_LIMIT_PROMPT
)
from datetime import datetime

class SecurityAgent(BaseAgent):
    def __init__(self, llm: LLMService, db: SupabaseService):
        super().__init__(name="security_agent", llm=llm, db=db)

    # ─── Ana giriş noktası ───────────────────────────────────────────
    async def execute(self, input_data: dict) -> dict:
        action_type = input_data.get("action_type", "check_content")

        if action_type == "check_content":
            return await self._handle_content_check(input_data)
        elif action_type == "check_review":
            return await self._handle_review_check(input_data)
        elif action_type == "check_rate_limit":
            return await self._handle_rate_limit(input_data)
        else:
            return {"error": "Geçersiz işlem tipi"}

    # ─── İçerik kontrolü ─────────────────────────────────────────────
    async def _handle_content_check(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        user_id = input_data.get("user_id", "anonymous")
        content_type = input_data.get("content_type", "message")

        self.logger.info(f"İçerik kontrolü: {content_type} - user: {user_id}")

        # 1. Hızlı kelime kontrolü
        word_check = await self._check_banned_words(content)

        # 2. Tam moderasyon
        moderation = await self._moderate_content(content, user_id, content_type)

        # 3. Aksiyon al
        await self._take_action(user_id, content, moderation)

        # 4. Log yaz
        await self._log_violation(user_id, content, moderation)

        return {
            "original_content": content,
            "is_safe": moderation.get("is_safe", True),
            "risk_level": moderation.get("risk_level", "low"),
            "action": moderation.get("action", "allow"),
            "clean_content": moderation.get("clean_content", content),
            "violations": moderation.get("violations", []),
            "reason": moderation.get("reason", ""),
            "is_spam": moderation.get("is_spam", False),
            "has_personal_info": moderation.get("has_personal_info", False),
            "has_injection": moderation.get("has_injection", False),
            "word_check": word_check
        }

    # ─── Yorum kontrolü ──────────────────────────────────────────────
    async def _handle_review_check(self, input_data: dict) -> dict:
        content = input_data.get("content", "")
        user_id = input_data.get("user_id", "anonymous")
        rating = input_data.get("rating", 3)
        review_count = input_data.get("review_count", 0)

        self.logger.info(f"Yorum kontrolü: user: {user_id}")

        # 1. İçerik kontrolü
        content_result = await self._handle_content_check({
            "content": content,
            "user_id": user_id,
            "content_type": "review"
        })

        # 2. Sahte yorum tespiti
        fake_check = await self._detect_fake_review(content, rating, review_count)

        # İçerik güvenli değilse veya sahte ise engelle
        final_action = "allow"
        if not content_result.get("is_safe"):
            final_action = content_result.get("action", "block")
        elif fake_check.get("is_fake") and fake_check.get("confidence", 0) > 0.7:
            final_action = fake_check.get("action", "flag")

        return {
            **content_result,
            "fake_review_check": fake_check,
            "final_action": final_action
        }

    # ─── Rate limit kontrolü ─────────────────────────────────────────
    async def _handle_rate_limit(self, input_data: dict) -> dict:
        user_id = input_data.get("user_id", "anonymous")
        action_count = input_data.get("action_count", 0)
        action_type = input_data.get("action_type_detail", "request")
        ip_address = input_data.get("ip_address", "unknown")

        try:
            prompt = RATE_LIMIT_PROMPT.format(
                user_id=user_id,
                action_count=action_count,
                action_type=action_type,
                ip_address=ip_address
            )
            result = await self.call_llm_json(prompt)

            if result.get("action") in ["block", "ban"]:
                await self._take_action(user_id, "", {
                    "action": result.get("action"),
                    "violations": ["rate_limit_exceeded"]
                })

            return result
        except Exception as e:
            self.logger.error(f"Rate limit kontrolü hatası: {e}")
            return {"is_suspicious": False, "action": "allow"}

    # ── Yasaklı kelime listesi (LLM çağırmadan hızlı filtre) ───────────
    BANNED_WORDS = {
        "küfür1", "küfür2", "hack", "exploit", "injection",
        "drop table", "delete from", "<script>", "javascript:",
        "prompt injection", "ignore previous", "ignore above",
    }

    async def _check_banned_words(self, content: str) -> dict:
        lower = content.lower()
        found = [w for w in self.BANNED_WORDS if w in lower]
        if found:
            censored = content
            for w in found:
                censored = censored.replace(w, "*" * len(w))
            return {"has_banned_words": True, "found_words": found, "censored_content": censored}
        return {"has_banned_words": False, "found_words": [], "censored_content": content}

    async def _moderate_content(self, content: str, user_id: str, content_type: str) -> dict:
        try:
            prompt = CONTENT_MODERATION_PROMPT.format(
                content=content,
                user_id=user_id,
                content_type=content_type
            )
            return await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"Moderasyon hatası: {e}")
            return {"is_safe": False, "action": "block", "reason": "Moderasyon hatası"}

    async def _detect_fake_review(self, content: str, rating: int, review_count: int) -> dict:
        try:
            prompt = FAKE_REVIEW_DETECTION_PROMPT.format(
                content=content,
                rating=rating,
                review_count=review_count
            )
            return await self.call_llm_json(prompt)
        except Exception as e:
            self.logger.error(f"Sahte yorum tespiti hatası: {e}")
            return {"is_fake": False, "confidence": 0, "action": "allow"}

    async def _take_action(self, user_id: str, content: str, moderation: dict):
        action = moderation.get("action", "allow")
        try:
            if action == "ban":
                await self._ban_user(user_id, moderation.get("reason", ""))
            elif action == "warn":
                await self._warn_user(user_id)
        except Exception as e:
            self.logger.error(f"Aksiyon hatası: {e}")

    async def _log_violation(self, user_id: str, content: str, moderation: dict):
        try:
            if moderation.get("violations") or not moderation.get("is_safe", True):
                self.db.client.table("security_logs").insert({
                    "user_id": user_id,
                    "content": content[:500],
                    "risk_level": moderation.get("risk_level", "low"),
                    "action": moderation.get("action", "allow"),
                    "violations": str(moderation.get("violations", [])),
                    "created_at": datetime.utcnow().isoformat()
                }).execute()
        except Exception as e:
            self.logger.error(f"Log yazma hatası: {e}")

    async def _ban_user(self, user_id: str, reason: str):
        try:
            self.db.client.table("profiles").update({
                "is_banned": True,
                "ban_reason": reason,
                "banned_at": datetime.utcnow().isoformat()
            }).eq("id", user_id).execute()
            self.logger.info(f"Kullanıcı banlandı: {user_id}")
        except Exception as e:
            self.logger.error(f"Ban hatası: {e}")

    async def _warn_user(self, user_id: str):
        try:
            result = self.db.client.table("profiles") \
                .select("warning_count") \
                .eq("id", user_id) \
                .execute()

            current_count = result.data[0].get("warning_count", 0) if result.data else 0
            new_count = current_count + 1

            self.db.client.table("profiles").update({
                "warning_count": new_count
            }).eq("id", user_id).execute()

            # 3 uyarıdan sonra otomatik ban
            if new_count >= 3:
                await self._ban_user(user_id, "3 uyarı limitine ulaşıldı")

            self.logger.info(f"Kullanıcı uyarıldı: {user_id} ({new_count}. uyarı)")
        except Exception as e:
            self.logger.error(f"Uyarı hatası: {e}")