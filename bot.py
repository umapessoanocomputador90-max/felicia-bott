import logging
import os
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from memory import MemoryManager
from tom import TomPsychologist

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

memory_manager = MemoryManager()
tom = TomPsychologist(memory_manager)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_name = user.first_name or "amigo(a)"

    memory_manager.initialize_user(user_id, user_name)

    welcome_message = (
        f"Olá, {user_name}! 👋\n\n"
        f"Meu nome é *Tom*, e estou aqui para ser um espaço seguro para você.\n\n"
        f"Sou um assistente especializado em escuta ativa e apoio emocional. "
        f"Aqui você pode falar sobre seus sentimentos, conflitos internos, "
        f"desafios do dia a dia — sem julgamentos.\n\n"
        f"_Lembre-se: sou uma ferramenta de apoio, não substituto de um profissional de saúde mental. "
        f"Em situações de crise, procure ajuda especializada (CVV: 188)._\n\n"
        f"Como você está se sentindo hoje?"
    )

    await update.message.reply_text(welcome_message, parse_mode="Markdown")


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    user_name = update.effective_user.first_name or "amigo(a)"

    memory_manager.reset_user(user_id, user_name)

    await update.message.reply_text(
        "✨ Nossa conversa foi reiniciada. Estou aqui, pronto para ouvir você novamente.\n\n"
        "Como posso te ajudar hoje?",
        parse_mode="Markdown",
    )


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    stats = memory_manager.get_user_stats(user_id)

    if not stats:
        await update.message.reply_text("Use /start para começarmos nossa conversa.")
        return

    msg = (
        f"📊 *Seu perfil de sessão*\n\n"
        f"👤 Nome: {stats['name']}\n"
        f"💬 Mensagens trocadas: {stats['message_count']}\n"
        f"🗓 Sessões: {stats['session_count']}\n"
        f"📅 Primeira sessão: {stats['first_session']}\n"
        f"🕐 Última atividade: {stats['last_active']}\n"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_text = (
        "🧠 *Tom — Seu espaço de apoio emocional*\n\n"
        "*Comandos disponíveis:*\n"
        "/start — Iniciar ou retomar a conversa\n"
        "/reset — Reiniciar a sessão atual\n"
        "/status — Ver estatísticas da sua sessão\n"
        "/help — Mostrar esta mensagem\n\n"
        "*Como usar:*\n"
        "Simplesmente escreva o que está sentindo ou pensando. "
        "Tom vai ouvir, fazer perguntas e te ajudar a explorar seus pensamentos.\n\n"
        "⚠️ _Em casos de emergência, ligue 188 (CVV) ou 192 (SAMU)._"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = str(user.id)
    user_name = user.first_name or "amigo(a)"
    user_message = update.message.text

    if not memory_manager.user_exists(user_id):
        memory_manager.initialize_user(user_id, user_name)

    await context.bot.send_chat_action(
        chat_id=update.effective_chat.id, action="typing"
    )

    try:
        response = await tom.respond(user_id, user_message)
        await update.message.reply_text(response, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error generating response for user {user_id}: {e}")
        await update.message.reply_text(
            "Desculpe, tive uma dificuldade técnica agora. "
            "Pode repetir o que você disse? Estou aqui para ouvir. 💙"
        )


def main() -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("TELEGRAM_BOT_TOKEN não encontrado nas variáveis de ambiente.")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("Tom está online e pronto para ajudar! 🧠")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
