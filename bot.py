import os
import logging
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID", "1273008434"))

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Blacklisted commands ---
BLACKLIST = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    ":(){:|:&};:",
    "dd if=/dev/zero",
    "chmod -R 777 /",
    "shutdown",
    "halt",
    "poweroff",
]


# --- Security: only respond to your chat ---
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        "/shell <command> — run a command on the VM\n"
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
        "/shell `<command>` — run a command on the VM\n"
        "/help — show this menu\n\n"
        "_More commands coming soon..._",
        parse_mode="Markdown"
    )

@restricted
async def shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/shell <command>`\nExample: `/shell ls -la`",
            parse_mode="Markdown"
        )
        return

    command = " ".join(context.args)

    # Check blacklist
    for blocked in BLACKLIST:
        if blocked in command.lower():
            await update.message.reply_text(f"🚫 Blocked: `{blocked}`", parse_mode="Markdown")
            logger.warning(f"Blocked command attempt: {command}")
            return

    if "sudo" in command:
        await update.message.reply_text("⚠️ Running with sudo — be careful.")

    logger.info(f"Executing: {command}")
    await update.message.reply_text(f"⚙️ Running: `{command}`", parse_mode="Markdown")

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=30)

        output = stdout.decode().strip()
        errors = stderr.decode().strip()
        result = output or errors or "(no output)"

        if len(result) > 4000:
            result = result[:4000] + "\n... (truncated)"

        status = "✅" if process.returncode == 0 else "❌"
        await update.message.reply_text(
            f"{status} *Exit code: {process.returncode}*\n\n```\n{result}\n```",
            parse_mode="Markdown"
        )

    except asyncio.TimeoutError:
        await update.message.reply_text("⏱ Command timed out after 30 seconds.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: `{str(e)}`", parse_mode="Markdown")


# --- Main ---
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("shell", shell))

    logger.info("Bot started. Listening for commands...")
    app.run_polling()


if __name__ == "__main__":
    main()