import json
import os
import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# Maximum messages kept in active context window
MAX_CONTEXT_MESSAGES = 30
# Messages threshold to trigger summarization
SUMMARIZE_THRESHOLD = 40


class MemoryManager:
    """
    Manages conversation memory with Redis persistence.
    Falls back to in-memory storage if Redis is unavailable.
    """

    def __init__(self):
        self._local: dict = {}
        self.redis = self._connect_redis()

    def _connect_redis(self):
        redis_url = os.environ.get("REDIS_URL")
        if not redis_url:
            logger.warning("REDIS_URL not set — using in-memory storage (data lost on restart).")
            return None
        try:
            import redis
            client = redis.from_url(redis_url, decode_responses=True)
            client.ping()
            logger.info("Redis connected successfully.")
            return client
        except Exception as e:
            logger.warning(f"Redis connection failed: {e}. Using in-memory fallback.")
            return None

    # ─── Low-level storage ───────────────────────────────────────────────────

    def _get(self, key: str) -> Optional[dict]:
        if self.redis:
            try:
                data = self.redis.get(key)
                return json.loads(data) if data else None
            except Exception as e:
                logger.error(f"Redis GET error: {e}")
        return self._local.get(key)

    def _set(self, key: str, value: dict) -> None:
        if self.redis:
            try:
                self.redis.set(key, json.dumps(value, ensure_ascii=False))
                return
            except Exception as e:
                logger.error(f"Redis SET error: {e}")
        self._local[key] = value

    def _user_key(self, user_id: str) -> str:
        return f"tom:user:{user_id}"

    # ─── User lifecycle ───────────────────────────────────────────────────────

    def user_exists(self, user_id: str) -> bool:
        return self._get(self._user_key(user_id)) is not None

    def initialize_user(self, user_id: str, name: str) -> None:
        existing = self._get(self._user_key(user_id))
        now = datetime.now().strftime("%d/%m/%Y %H:%M")

        if existing:
            existing["session_count"] = existing.get("session_count", 1) + 1
            existing["last_active"] = now
            existing["name"] = name
            self._set(self._user_key(user_id), existing)
        else:
            user_data = {
                "name": name,
                "first_session": now,
                "last_active": now,
                "session_count": 1,
                "message_count": 0,
                "history": [],
                "summary": "",
                "themes": [],
            }
            self._set(self._user_key(user_id), user_data)

    def reset_user(self, user_id: str, name: str) -> None:
        now = datetime.now().strftime("%d/%m/%Y %H:%M")
        existing = self._get(self._user_key(user_id)) or {}
        user_data = {
            "name": name,
            "first_session": existing.get("first_session", now),
            "last_active": now,
            "session_count": existing.get("session_count", 0) + 1,
            "message_count": 0,
            "history": [],
            "summary": existing.get("summary", ""),
            "themes": existing.get("themes", []),
        }
        self._set(self._user_key(user_id), user_data)

    # ─── Conversation history ─────────────────────────────────────────────────

    def add_message(self, user_id: str, role: str, content: str) -> None:
        data = self._get(self._user_key(user_id))
        if not data:
            return

        data["history"].append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
        })
        data["message_count"] = data.get("message_count", 0) + 1
        data["last_active"] = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Keep history manageable — trim oldest messages beyond threshold
        if len(data["history"]) > SUMMARIZE_THRESHOLD:
            # Keep the last MAX_CONTEXT_MESSAGES messages
            data["history"] = data["history"][-MAX_CONTEXT_MESSAGES:]

        self._set(self._user_key(user_id), data)

    def get_conversation_history(self, user_id: str) -> list:
        data = self._get(self._user_key(user_id))
        if not data:
            return []
        history = data.get("history", [])
        # Return only the last MAX_CONTEXT_MESSAGES for context window
        return history[-MAX_CONTEXT_MESSAGES:]

    # ─── User context & stats ─────────────────────────────────────────────────

    def get_user_context(self, user_id: str) -> dict:
        data = self._get(self._user_key(user_id))
        if not data:
            return {}
        return {
            "name": data.get("name", "Paciente"),
            "summary": data.get("summary", ""),
            "themes": data.get("themes", []),
            "session_count": data.get("session_count", 1),
            "message_count": data.get("message_count", 0),
        }

    def get_user_stats(self, user_id: str) -> Optional[dict]:
        data = self._get(self._user_key(user_id))
        if not data:
            return None
        return {
            "name": data.get("name", "Paciente"),
            "message_count": data.get("message_count", 0),
            "session_count": data.get("session_count", 0),
            "first_session": data.get("first_session", "N/A"),
            "last_active": data.get("last_active", "N/A"),
        }

    def update_summary(self, user_id: str, summary: str, themes: list) -> None:
        """Update the long-term summary for a user (called externally if needed)."""
        data = self._get(self._user_key(user_id))
        if data:
            data["summary"] = summary
            data["themes"] = themes
            self._set(self._user_key(user_id), data)
