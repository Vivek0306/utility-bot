import os
import logging
import asyncio
import io
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

load_dotenv()

# --- Config ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
ALLOWED_CHAT_ID = int(os.getenv("ALLOWED_CHAT_ID"))
CREDENTIALS_FILE = os.getenv("CREDENTIALS_FILE", "credentials.json")

# --- Logging ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Blacklisted commands ---
BLACKLIST = [
    "rm -rf /", "rm -rf /*", "mkfs", ":(){:|:&};:",
    "dd if=/dev/zero", "chmod -R 777 /", "shutdown", "halt", "poweroff",
]

# --- Session state ---
# Stores per-user upload session: { chat_id: { "album": str, "active": bool, "count": int } }
upload_sessions = {}


# --- Google Drive ---
def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        CREDENTIALS_FILE,
        scopes=["https://www.googleapis.com/auth/drive.file"]
    )
    return build("drive", "v3", credentials=creds)


def create_drive_folder(service, folder_name):
    """Create a folder in root of Drive, return its ID."""
    metadata = {
        "name": folder_name,
        "mimeType": "application/vnd.google-apps.folder"
    }
    folder = service.files().create(body=metadata, fields="id").execute()
    return folder.get("id")


def upload_to_drive(service, folder_id, filename, file_bytes, mime_type):
    """Upload a file to a specific Drive folder."""
    metadata = {
        "name": filename,
        "parents": [folder_id]
    }
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
    file = service.files().create(body=metadata, media_body=media, fields="id, name").execute()
    return file


# --- Security ---
def restricted(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if update.effective_chat.id != ALLOWED_CHAT_ID:
            await update.message.reply_text("⛔ Unauthorized.")
            logger.warning(f"Unauthorized access from: {update.effective_chat.id}")
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
        "/album <name> — set album name for upload\n"
        "/startUpload — start receiving images\n"
        "/endUpload — finish and save to Drive\n"
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
        "/shell `<command>` — run a command on the VM\n\n"
        "*Google Drive Upload:*\n"
        "/album `<name>` — set album name\n"
        "/startUpload — start receiving images\n"
        "/endUpload — finish upload session\n\n"
        "_More commands coming soon..._",
        parse_mode="Markdown"
    )

@restricted
async def album(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/album <name>`\nExample: `/album Goa Trip 2024`",
            parse_mode="Markdown"
        )
        return

    album_name = " ".join(context.args)
    chat_id = update.effective_chat.id

    # Save album name in session
    upload_sessions[chat_id] = {
        "album": album_name,
        "active": False,
        "folder_id": None,
        "count": 0
    }

    await update.message.reply_text(
        f"📁 Album set to: *{album_name}*\n"
        f"Now send /startUpload when ready to upload images.",
        parse_mode="Markdown"
    )

@restricted
async def start_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = upload_sessions.get(chat_id)

    if not session:
        await update.message.reply_text("⚠️ Set an album first using `/album <name>`", parse_mode="Markdown")
        return

    if session["active"]:
        await update.message.reply_text("⚠️ Upload already in progress. Send /endUpload to finish.")
        return

    await update.message.reply_text("⏳ Creating folder on Google Drive...")

    try:
        service = get_drive_service()
        folder_id = create_drive_folder(service, session["album"])

        upload_sessions[chat_id]["active"] = True
        upload_sessions[chat_id]["folder_id"] = folder_id
        upload_sessions[chat_id]["count"] = 0

        await update.message.reply_text(
            f"✅ Ready! Send your images now.\n"
            f"📁 Album: *{session['album']}*\n"
            f"Send /endUpload when done.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to create Drive folder: `{str(e)}`", parse_mode="Markdown")
        logger.error(f"Drive folder creation error: {e}")

@restricted
async def end_upload(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    session = upload_sessions.get(chat_id)

    if not session or not session["active"]:
        await update.message.reply_text("⚠️ No active upload session.")
        return

    count = session["count"]
    album_name = session["album"]

    # Clear session
    upload_sessions[chat_id] = {
        "album": album_name,
        "active": False,
        "folder_id": None,
        "count": 0
    }

    await update.message.reply_text(
        f"✅ *Upload complete!*\n"
        f"📁 Album: *{album_name}*\n"
        f"🖼 {count} image(s) uploaded to Google Drive.",
        parse_mode="Markdown"
    )

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle incoming photos during an active upload session."""
    chat_id = update.effective_chat.id

    # Security check
    if chat_id != ALLOWED_CHAT_ID:
        return

    session = upload_sessions.get(chat_id)

    if not session or not session["active"]:
        await update.message.reply_text("⚠️ No active upload session. Use /album then /startUpload first.")
        return

    try:
        # Get highest resolution photo
        photo = update.message.photo[-1]
        file = await context.bot.get_file(photo.file_id)
        file_bytes = await file.download_as_bytearray()

        # Generate filename
        count = session["count"] + 1
        filename = f"{session['album'].replace(' ', '_')}_{count:03d}.jpg"

        # Upload to Drive
        service = get_drive_service()
        upload_to_drive(service, session["folder_id"], filename, bytes(file_bytes), "image/jpeg")

        upload_sessions[chat_id]["count"] = count

        await update.message.reply_text(f"📤 Uploaded: `{filename}` ({count} total)", parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"❌ Upload failed: `{str(e)}`", parse_mode="Markdown")
        logger.error(f"Photo upload error: {e}")


# --- Shell command ---
@restricted
async def shell(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "⚠️ Usage: `/shell <command>`\nExample: `/shell ls -la`",
            parse_mode="Markdown"
        )
        return

    command = " ".join(context.args)

    for blocked in BLACKLIST:
        if blocked in command.lower():
            await update.message.reply_text(f"🚫 Blocked: `{blocked}`", parse_mode="Markdown")
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
    app.add_handler(CommandHandler("album", album))
    app.add_handler(CommandHandler("startUpload", start_upload))
    app.add_handler(CommandHandler("endUpload", end_upload))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))

    logger.info("Bot started. Listening for commands...")
    app.run_polling()


if __name__ == "__main__":
    main()