import os
import logging
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Logging setup
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
        # Using gemini-pro which is highly stable and supported everywhere
        model = genai.GenerativeModel("gemini-pro")
        logger.info("Gemini AI (gemini-pro) configured successfully.")
    except Exception as e:
        logger.error(f"Gemini Config Error: {e}")
        model = None
else:
    model = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Bot is online ✅. Ask me anything!")

async def chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not model:
        await update.message.reply_text("❌ Error: GEMINI_API_KEY is not set or invalid in Railway variables.")
        return

    user_text = update.message.text
    try:
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        # Safety settings to avoid blocked messages
        safety_settings = [
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ]

        response = model.generate_content(user_text, safety_settings=safety_settings)

        if response and response.candidates:
            # Check if response has text
            try:
                bot_response = response.text
                if bot_response:
                    await update.message.reply_text(bot_response)
                else:
                    await update.message.reply_text("AI returned an empty response.")
            except Exception as inner_e:
                # This happens if Gemini blocks the response
                logger.error(f"Response Error: {inner_e}")
                await update.message.reply_text("⚠️ AI blocked this response due to safety policies.")
        else:
            await update.message.reply_text("❌ AI could not generate any response.")

    except Exception as e:
        error_msg = str(e)
        logger.error(f"Chat Error: {error_msg}")
        # Send actual error for debugging
        await update.message.reply_text(f"❌ Error: {error_msg}")

def main():
    if not TOKEN:
        logger.error("TOKEN missing!")
        return

    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    logger.info("Bot starting...")
    app.run_polling()

if __name__ == "__main__":
    main()
