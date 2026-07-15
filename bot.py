import os
import logging
import asyncio
from datetime import datetime, timedelta
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TelegramError

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

TOKEN = os.getenv("TOKEN")

# In-memory storage (Railway restart hone par reset hoga, temporary solution)
# Professional use ke liye Database (MongoDB/SQL) chahiye hota hai.
group_settings = {} # {chat_id: {"link_remover": False, "filters": {}}}

# --- Helper Functions ---
async def is_admin(update: Update):
    member = await update.effective_chat.get_member(update.effective_user.id)
    return member.status in ["administrator", "creator"]

def parse_time(time_str):
    unit = time_str[-1].lower()
    try:
        val = int(time_str[:-1])
        if unit == 'h': return timedelta(hours=val)
        if unit == 'd': return timedelta(days=val)
        if unit == 'm': return timedelta(minutes=val)
    except:
        return None
    return None

# --- Command Handlers ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("HELLO MADXT2Z I AM LIVE")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🛡️ **Admin Commands:**\n"
        "/linkremover - Toggle Link Delete\n"
        "/lock all - Lock entire chat\n"
        "/unlock - Unlock chat\n"
        "/setfilter - How to set filter\n"
        "/filter [word] [reply text] - Add filter\n"
        "/ban @user - Ban user\n"
        "/unban @user - Unban user\n"
        "/mute [time] - Mute (e.g. /mute 1h)\n"
        "/unmute - Unmute user\n"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

async def lock_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        permissions = ChatPermissions(can_send_messages=False)
        await context.bot.set_chat_permissions(update.effective_chat.id, permissions)
        await update.message.reply_text("🔒 ALL CHAT LOCKED! Only admins can speak.")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def unlock(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    try:
        permissions = ChatPermissions(can_send_messages=True, can_send_media_messages=True,
                                    can_send_other_messages=True, can_add_web_page_previews=True)
        await context.bot.set_chat_permissions(update.effective_chat.id, permissions)
        await update.message.reply_text("🔓 CHAT UNLOCKED!")
    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def link_remover_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    cid = update.effective_chat.id
    if cid not in group_settings: group_settings[cid] = {"link_remover": False, "filters": {}}

    group_settings[cid]["link_remover"] = not group_settings[cid]["link_remover"]
    state = "ENABLED" if group_settings[cid]["link_remover"] else "DISABLED"
    await update.message.reply_text(f"🚫 Link Remover is now {state}")

async def set_filter_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Usage: `/filter 'word' replytext` or link", parse_mode="Markdown")

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if len(context.args) < 2:
        await update.message.reply_text("Syntax Error! Use: /filter [word] [reply text]")
        return

    cid = update.effective_chat.id
    word = context.args[0].lower()
    reply = " ".join(context.args[1:])

    if cid not in group_settings: group_settings[cid] = {"link_remover": False, "filters": {}}
    group_settings[cid]["filters"][word] = reply
    await update.message.reply_text(f"✅ Filter set for: {word}")

# --- Moderation ---

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    target_user = None
    duration = timedelta(hours=1) # Default 1h

    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user.id
        if context.args:
            t = parse_time(context.args[0])
            if t: duration = t
    elif context.args:
        # Simplified: Requires reply for now or ID
        await update.message.reply_text("Please reply to a message to mute.")
        return

    try:
        until = datetime.now() + duration
        await context.bot.restrict_chat_member(update.effective_chat.id, target_user,
                                             ChatPermissions(can_send_messages=False), until_date=until)
        await update.message.reply_text(f"🔇 User muted for {duration}")
    except Exception as e:
        await update.message.reply_text(f"Failed: {e}")

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update): return
    if update.message.reply_to_message:
        user_id = update.message.reply_to_message.from_user.id
        await context.bot.ban_chat_member(update.effective_chat.id, user_id)
        await update.message.reply_text("🔨 Banned!")

# --- Message Watcher (Link remover, Filters, Unauthorized Commands) ---

async def watcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    text = update.message.text.lower()
    cid = update.effective_chat.id
    user = update.effective_user

    # 1. Check Unauthorized Command Usage (Mute for 72h)
    admin_cmds = ["/linkremover", "/lock", "/unlock", "/filter", "/ban", "/mute", "/unban", "/unmute"]
    if any(text.startswith(cmd) for cmd in admin_cmds):
        if not await is_admin(update):
            try:
                until = datetime.now() + timedelta(hours=72)
                await context.bot.restrict_chat_member(cid, user.id, ChatPermissions(can_send_messages=False), until_date=until)
                await update.message.reply_text(f"❌ Unauthorized! @{user.username} muted for 72H.")
                await update.message.delete()
                return
            except: pass

    # 2. Link Remover
    if cid in group_settings and group_settings[cid].get("link_remover"):
        if ("http://" in text or "https://" in text or "t.me" in text) and not await is_admin(update):
            await update.message.delete()
            return

    # 3. Filters
    if cid in group_settings:
        for word, reply in group_settings[cid]["filters"].items():
            if word in text:
                await update.message.reply_text(reply)
                break

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("lock", lock_all))
    app.add_handler(CommandHandler("unlock", unlock))
    app.add_handler(CommandHandler("linkremover", link_remover_toggle))
    app.add_handler(CommandHandler("setfilter", set_filter_info))
    app.add_handler(CommandHandler("filter", add_filter))
    app.add_handler(CommandHandler("mute", mute_user))
    app.add_handler(CommandHandler("ban", ban_user))

    # Watch all messages for Filters, Links, and Unauthorized Commands
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, watcher))
    # This specifically catches attempted admin commands from non-admins
    app.add_handler(MessageHandler(filters.COMMAND, watcher))

    print("Group Manager Bot Online...")
    app.run_polling()

if __name__ == "__main__":
    main()
