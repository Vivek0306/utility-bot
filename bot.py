import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from dotenv import load_dotenv
load_dotenv()

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)


# --- Security: only respond to your chat ---
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.info(f"Received command from chat_id: {update.effective_chat.id}")
        if update.effective_chat.id != ALLOWED_CHAT_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            logger.warning(f"Unauthorized access attempt from chat_id: {update.effective_chat.id}")
            return
        return await func(update, context)
    return wrapper


# --- Commands ---
@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hey KamikazeX! Bot is online.\n\n"
        "Available commands:\n"
        "/ping — check if bot is alive\n"
        "/help — show this menu"
    )

@restricted
async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🏓 Pong! I'm alive and running.")

@restricted
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *Utility Bot — Command List*\n\n"
        "/ping — check if bot is alive\n"
        "/help — show this menu\n\n"
        "_More commands coming soon..._",
        parse_mode="Markdown"
    )


# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))

    logger.info("Bot started. Listening for commands...")
    app.run_polling()


if __name__ == "__main__":
    main()