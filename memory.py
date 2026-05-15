"""
memory.py — Gerenciador de memória para a Felícia.

Estratégia:
- Histórico de conversa: mantém as últimas N mensagens por usuário (sliding window).
- Fatos persistentes: armazena informações relevantes extraídas da conversa
  (nome, humor, preferências, etc.) em um arquivo JSON local.
  No Railway, use um volume persistente montado em /data, caso contrário
  os arquivos se perdem a cada deploy. Veja o README para mais detalhes.
"""

import json
import os
import logging
from collections import deque
from typing import Literal

logger = logging.getLogger(__name__)

# Onde os dados persistentes ficam guardados
DATA_DIR = os.environ.get("DATA_DIR", "./data")
FACTS_FILE = os.path.join(DATA_DIR, "facts.json")

# Quantas mensagens manter no histórico de conversa por usuário
MAX_HISTORY = int(os.environ.get("MAX_HISTORY", "20"))


class MemoryManager:
    """Gerencia o histórico de conversa (em RAM) e fatos persistentes (em disco)."""

    def __init__(self) -> None:
        os.makedirs(DATA_DIR, exist_ok=True)
        # { user_id: deque([{"role": ..., "content": ...}, ...]) }
        self._histories: dict[str, deque] = {}
        # { user_id: { fact_key: fact_value } }
        self._facts: dict[str, dict] = self._load_facts()

    # ── Histórico de conversa ──────────────────────────────────────────────────

    def add_message(
        self,
        user_id: str,
        role: Literal["user", "assistant"],
        content: str,
    ) -> None:
        if user_id not in self._histories:
            self._histories[user_id] = deque(maxlen=MAX_HISTORY)
        self._histories[user_id].append({"role": role, "content": content})

    def get_history(self, user_id: str) -> list[dict]:
        """Retorna o histórico formatado para a API da OpenAI."""
        return list(self._histories.get(user_id, []))

    def clear_history(self, user_id: str) -> None:
        self._histories.pop(user_id, None)
        logger.info("Histórico limpo para usuário %s", user_id)

    # ── Fatos persistentes ────────────────────────────────────────────────────

    def save_fact(self, user_id: str, key: str, value: str) -> None:
        if user_id not in self._facts:
            self._facts[user_id] = {}
        self._facts[user_id][key] = value
        self._persist_facts()
        logger.info("Fato salvo [%s] %s = %s", user_id, key, value)

    def get_fact(self, user_id: str, key: str) -> str | None:
        return self._facts.get(user_id, {}).get(key)

    def get_facts_context(self, user_id: str) -> str:
        """Retorna os fatos do usuário formatados como texto para o system prompt."""
        facts = self._facts.get(user_id, {})
        if not facts:
            return ""
        lines = [f"- {k}: {v}" for k, v in facts.items()]
        return "\n".join(lines)

    def clear_facts(self, user_id: str) -> None:
        self._facts.pop(user_id, None)
        self._persist_facts()

    # ── Persistência ──────────────────────────────────────────────────────────

    def _load_facts(self) -> dict:
        if not os.path.exists(FACTS_FILE):
            return {}
        try:
            with open(FACTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Não foi possível carregar facts.json: %s", e)
            return {}

    def _persist_facts(self) -> None:
        try:
            with open(FACTS_FILE, "w", encoding="utf-8") as f:
                json.dump(self._facts, f, ensure_ascii=False, indent=2)
        except OSError as e:
            logger.error("Erro ao salvar facts.json: %s", e)
