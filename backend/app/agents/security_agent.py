from app.agents.base_agent import BaseAgent
from app.services.llm_service import LLMService
from app.services.supabase_service import SupabaseService
from app.prompts.security_prompts import (
    CONTENT_MODERATION_PROMPT,
    BANNED_WORDS_CHECK_PROMPT,
    FAKE_REVIEW_DETECTION_PROMPT,
    RATE_LIMIT_PROMPT
)
from datetime import datetime, timezone

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

        # 1. Hızlı kural tabanlı ön kontrol (LLM yok)
        quick_result = self._quick_safety_check(content)
        word_check = await self._check_banned_words(content)

        # Kesin tehlikeli → LLM'e gerek yok, direkt engelle
        if quick_result == "block":
            moderation = {
                "is_safe": False,
                "risk_level": "critical",
                "action": "block",
                "violations": ["forbidden_pattern"],
                "reason": "Yasak içerik tespit edildi.",
                "clean_content": None,
                "is_spam": False,
                "has_personal_info": False,
                "has_injection": True,
            }
            await self._take_action(user_id, content, moderation)
            await self._log_violation(user_id, content, moderation)
            return {
                "original_content": content,
                **{k: moderation[k] for k in
                   ("is_safe", "risk_level", "action", "violations",
                    "reason", "clean_content", "is_spam",
                    "has_personal_info", "has_injection")},
                "clean_content": moderation.get("clean_content", content),
                "word_check": word_check,
            }

        # Normal içerik → LLM çağrısı YOK, hızlıca geçir
        if quick_result == "safe":
            self.logger.debug(f"[security] quick=safe, LLM atlandı")
            return {
                "original_content": content,
                "is_safe": True,
                "risk_level": "low",
                "action": "allow",
                "clean_content": content,
                "violations": [],
                "reason": "",
                "is_spam": False,
                "has_personal_info": False,
                "has_injection": False,
                "word_check": word_check,
            }

        # Şüpheli → LLM ile tam moderasyon
        moderation = await self._moderate_content(content, user_id, content_type)
        await self._take_action(user_id, content, moderation)
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
            "word_check": word_check,
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

    # ── Hızlı kural tabanlı kontrol (LLM çağırmadan) ───────────────────
    # Kesin tehlikeli — direkt block
    _HARD_BLOCK = {
        "drop table", "delete from", "truncate table",
        "<script>", "javascript:", "onerror=", "onload=",
        "prompt injection", "ignore previous instructions",
        "ignore above", "disregard all",
    }
    # Şüpheli — LLM'e gönder
    _SUSPICIOUS_PATTERNS = {
        "hack", "exploit", "injection", "sql", "xss",
        "select * from", "insert into", "union select",
    }

    BANNED_WORDS = _HARD_BLOCK  # geriye dönük uyumluluk

    def _quick_safety_check(self, content: str) -> str:
        """
        Hızlı kural tabanlı ön kontrol.
        Döndürür: 'safe' | 'suspicious' | 'block'
        """
        lower = content.lower()

        # Kesin tehlikeli
        if any(kw in lower for kw in self._HARD_BLOCK):
            return "block"

        # Şüpheli — LLM'e bırak
        if any(kw in lower for kw in self._SUSPICIOUS_PATTERNS):
            return "suspicious"

        # Çok uzun mesaj (prompt injection girişimi olabilir)
        if len(content) > 2000:
            return "suspicious"

        return "safe"

    async def _check_banned_words(self, content: str) -> dict:
        lower = content.lower()
        found = [w for w in self._HARD_BLOCK if w in lower]
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
            # LLM hatası = içeriği geçir, engelleme (false-positive önleme)
            return {"is_safe": True, "action": "allow", "reason": "Moderasyon servisi geçici olarak kullanılamıyor"}

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
                # "anonymous" gibi UUID olmayan değerler NULL olarak kaydedilir
                safe_user_id = None
                try:
                    import uuid
                    uuid.UUID(str(user_id))
                    safe_user_id = user_id
                except (ValueError, AttributeError):
                    pass

                self.db.client.table("security_logs").insert({
                    "user_id": safe_user_id,
                    "content": content[:500],
                    "risk_level": moderation.get("risk_level", "low"),
                    "action": moderation.get("action", "allow"),
                    "violations": str(moderation.get("violations", [])),
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }).execute()
        except Exception as e:
            self.logger.error(f"Log yazma hatası: {e}")

    async def _ban_user(self, user_id: str, reason: str):
        try:
            self.db.client.table("profiles").update({
                "is_banned": True,
                "ban_reason": reason,
                "banned_at": datetime.now(timezone.utc).isoformat()
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