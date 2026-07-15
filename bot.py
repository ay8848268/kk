import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup taaki errors Railway logs mein dikhein
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Environment Variables
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        # Using gemini-1.5-flash as it's faster and better for bots
        model = genai.GenerativeModel("gemini-1.5-flash")
        logger.info("Gemini AI configured successfully.")
    except Exception as e:
        logger.error(f"Error configuring Gemini: {e}")
        model = None
else:
    logger.warning("GEMINI_API_KEY not found!")
    model = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.info("Start command received")
    await update.message.reply_text("Bot is online ✅. Ask me anything!")


async def ping(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Pong 🏓")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start - Start bot\n"
        "/ping - Check bot status\n"
        "/help - Show commands\n"
        "Just send a message to talk to Gemini AI!"
    )


async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not model:
        await update.message.reply_text("Gemini API key is missing ❌. Please set the GEMINI_API_KEY in Railway Variables.")
        return

    user_text = update.message.text
    try:
        # Show typing action
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        response = model.generate_content(user_text)

        if response.text:
            await update.message.reply_text(response.text)
        else:
            await update.message.reply_text("AI couldn't generate a response (maybe safety filters).")

    except Exception as e:
        logger.error(f"Chat Error: {e}")
        await update.message.reply_text("Something went wrong while talking to AI ❌")


def main():
    if not TOKEN:
        logger.error("TOKEN variable missing! Bot cannot start.")
        return

    logger.info("Starting bot...")
    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))

    # AI Chat Handler
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("Bot is polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
