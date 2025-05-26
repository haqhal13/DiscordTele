# TeleSync.py
import os
import asyncio
import discord
from discord.utils import get
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
from threading import Thread
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

VIP_URL = "https://t.me/YourVIPPaymentBot"  # replace with your VIP link

CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS',
    '🧔 MALE CREATORS  / AGENCY',
    '💪 HGF',
    '🎥 NET VIDEO GIRLS',
    '🇨🇳 ASIAN .1',
    '🇨🇳 ASIAN .2',
    '🇲🇽 LATINA .1',
    '🇲🇽 LATINA .2',
    '❄ SNOWBUNNIE .1',
    '❄ SNOWBUNNIE .2',
    '🇮🇳 INDIAN / DESI',
    '🇸🇦 ARAB',
    '🧬 MIXED / LIGHTSKIN',
    '🏴 BLACK',
    '🌺 POLYNESIAN',
    '☠ GOTH / ALT',
    '🏦 VAULT BANKS',
    '🔞 PORN',
    'Uncatagorised Girls'
]
# ────────────────────────────────────────────────────────────────────────────

# ─── Discord client ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ─── Telegram app ──────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────

# per-chat locks & message tracking
chat_locks = {}
chat_messages = {}

def split_chunks(text: str, limit: int = 4000):
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) > limit:
            chunks.append(current); current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks

async def cleanup_chat(chat_id: int):
    if chat_id in chat_messages:
        for msg_id in chat_messages[chat_id]:
            try:
                await tg_app.bot.delete_message(chat_id, msg_id)
            except:
                pass
        chat_messages[chat_id].clear()

async def fetch_and_send_channels():
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return ["❌ Guild not found."]
    out = []
    for cat_name in CATEGORIES_TO_INCLUDE:
        cat = get(guild.categories, name=cat_name)
        if not cat:
            continue
        out.append(f"*{cat_name}*")
        for ch in cat.text_channels:
            out.append(f"• {ch.name}")
        out.append("")
    if not out:
        return ["⚠️ No matching categories found."]
    full = "\n".join(out)
    # wrap in preformatted
    return [f"```{chunk}```" for chunk in split_chunks(full)]

async def do_refresh(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    lock = chat_locks.setdefault(chat_id, asyncio.Lock())
    async with lock:
        # delete old messages
        await cleanup_chat(chat_id)

        # loading notice
        m = await context.bot.send_message(
            chat_id,
            "⏳ Loading Model channels please wait, this could take 2–5 mins…"
        )
        chat_messages.setdefault(chat_id, []).append(m.message_id)

        # send categories
        blocks = await fetch_and_send_channels()
        for block in blocks:
            m = await context.bot.send_message(chat_id, block, parse_mode="Markdown")
            chat_messages[chat_id].append(m.message_id)

        # footer
        ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        footer = (
            "If you don't see the model you want, no worries – when you purchase VIP, "
            "let us know who you'd like added and we'll get them ASAP!\n\n"
            f"Last updated: {ts}"
        )
        m = await context.bot.send_message(chat_id, footer)
        chat_messages[chat_id].append(m.message_id)

        # buttons with fallback note
        kb = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
            InlineKeyboardButton("💎 Join VIP", url=VIP_URL),
        ]])
        m = await context.bot.send_message(
            chat_id,
            "Press 🔄 *Refresh* to update the list. If it doesn’t work, type /start.\n"
            "Use 💎 *Join VIP* to upgrade.",
            parse_mode="Markdown",
            reply_markup=kb
        )
        chat_messages[chat_id].append(m.message_id)

# handlers
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    asyncio.create_task(do_refresh(chat_id, context))

async def refresh_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    chat_id = update.effective_chat.id
    asyncio.create_task(do_refresh(chat_id, context))

async def help_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 Press 🔄 *Refresh* or type /start to update the model list.",
        parse_mode="Markdown"
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))

# Flask webhook
web = Flask(__name__)

@web.route('/', methods=['GET','HEAD'])
def home():
    return "🤖 Bot is alive!", 200

@web.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    upd = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put_nowait(upd)
    return 'OK'

async def set_webhook():
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    Thread(
        target=lambda: web.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    asyncio.run(main())
