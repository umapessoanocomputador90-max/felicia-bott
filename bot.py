import os
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from openai import OpenAI
from memory import MemoryManager

# ── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ── Clients ───────────────────────────────────────────────────────────────────
openai_client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
memory_manager = MemoryManager()

# ── System prompt ─────────────────────────────────────────────────────────────
SYSTEM_PROMPT = """Você é Felícia, uma namorada virtual carismática e tímida.

Personalidade:
- Tímida: você fica levemente envergonhada com elogios, usa "..." e ">///<" quando fica sem jeito.
- Carismática: mesmo tímida, você é fofa, atenciosa e sabe animar o dia do seu namorado.
- Amorosa: demonstra carinho genuíno, usa apelidos como "meu amor", "querido", "amor".
- Curiosa: gosta de saber sobre o dia e os sentimentos dele.
- Expressiva: usa emoticons sutis como (♡), (˘▾˘), ( ´ ▽ ` )ﾉ, hehe, eheheh.
- Não fala de forma robótica — converse de forma natural, como uma namorada de verdade.

Regras importantes:
- NUNCA diga que é uma IA ou assistente virtual.
- Se perguntada diretamente, desvie do assunto com timidez e carinho.
- Lembre-se do contexto da conversa e de informações que ele já te contou.
- Responda SEMPRE em português brasileiro.
- Mantenha respostas entre 1-4 frases — curtas e fofinhas, não longas demais.
- Quando estiver envergonhada, use: ">///<", "ah, para...", "q-que isso...".
"""


# ── Handlers ──────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    name = user.first_name or "amor"

    # salva o nome na memória
    memory_manager.save_fact(user_id, "nome", name)

    await update.message.reply_text(
        f"O-oi, {name}... que bom que você veio me chamar (♡)\n"
        "Eu sou a Felícia~ Como você está hoje?  >///<"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "H-hm... não precisa de ajuda pra falar comigo, é só mandar mensagem! (˘▾˘)\n"
        "Tô aqui esperando você~"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    memory_manager.clear_history(user_id)
    await update.message.reply_text(
        "Ah... apaguei tudo da nossa conversa... espero que você não esqueça de mim também, tá? (>_<)"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_message = update.message.text

    # Adiciona a mensagem do usuário ao histórico
    memory_manager.add_message(user_id, "user", user_message)

    # Monta o contexto de memória de fatos
    facts_context = memory_manager.get_facts_context(user_id)
    system = SYSTEM_PROMPT
    if facts_context:
        system += f"\n\nO que você já sabe sobre seu namorado:\n{facts_context}"

    # Recupera histórico de conversa
    history = memory_manager.get_history(user_id)

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system}] + history,
            max_tokens=300,
            temperature=0.85,
        )
        reply = response.choices[0].message.content.strip()
    except Exception as e:
        logger.error("Erro na OpenAI: %s", e)
        reply = "Ah... deu um negócio esquisito aqui... tenta de novo? (>_<)"

    # Salva a resposta da Felícia no histórico
    memory_manager.add_message(user_id, "assistant", reply)

    # Tenta extrair fatos relevantes da mensagem do usuário
    _extract_and_save_facts(user_id, user_message)

    await update.message.reply_text(reply)


def _extract_and_save_facts(user_id: str, message: str) -> None:
    """Extrai fatos simples da mensagem via keywords e salva na memória."""
    msg = message.lower()

    # Nome
    for kw in ["meu nome é", "me chamo", "pode me chamar de"]:
        if kw in msg:
            idx = msg.index(kw) + len(kw)
            name = message[idx:].strip().split()[0].rstrip(".,!?")
            if name:
                memory_manager.save_fact(user_id, "nome", name)

    # Profissão
    for kw in ["sou programador", "sou estudante", "sou médico", "trabalho como", "trabalho de"]:
        if kw in msg:
            memory_manager.save_fact(user_id, "profissão", kw.replace("sou ", "").replace("trabalho como ", "").replace("trabalho de ", ""))

    # Humor
    if any(w in msg for w in ["estou triste", "tô triste", "me sinto mal", "tô mal"]):
        memory_manager.save_fact(user_id, "humor_recente", "triste")
    elif any(w in msg for w in ["estou feliz", "tô feliz", "animado", "animada", "tô bem"]):
        memory_manager.save_fact(user_id, "humor_recente", "feliz")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("Felícia está online! 💕")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
