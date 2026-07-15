import os
import google.generativeai as genai
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Environment Variables
TOKEN = os.getenv("TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-pro")
else:
    model = None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        await update.message.reply_text("Gemini API key is missing ❌. Please set the GEMINI_API_KEY environment variable.")
        return

    user_text = update.message.text
    try:
        # Send a typing action to show the bot is thinking
        await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

        response = model.generate_content(user_text)
        await update.message.reply_text(response.text)
    except Exception as e:
        print(f"Error: {e}")
        await update.message.reply_text("Something went wrong while talking to AI ❌")


def main():
    if not TOKEN:
        print("ERROR: TOKEN variable missing ❌")
        return

    app = Application.builder().token(TOKEN).build()

    # Handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("ping", ping))
    app.add_handler(CommandHandler("help", help_command))

    # AI Chat Handler - handles all text messages that are not commands
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, chat))

    print("Bot is online ✅")

    app.run_polling()


if __name__ == "__main__":
    main()
