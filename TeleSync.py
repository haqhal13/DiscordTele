import os
import asyncio
import discord
from discord.utils import get
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
from threading import Thread
from collections import defaultdict

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

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

# ─── Concurrency Safeguards ─────────────────────────────────────────────────
fetch_semaphore = asyncio.Semaphore(2)
chat_locks = defaultdict(lambda: asyncio.Lock())
# ────────────────────────────────────────────────────────────────────────────

# ─── Discord client ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ─── Telegram app ──────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────

def split_chunks(text: str, limit: int = 4000):
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks

async def clear_previous_list(chat_id, bot, ctx):
    prev_ids = ctx.chat_data.get('last_msg_ids', [])
    for msg_id in prev_ids:
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass
    ctx.chat_data['last_msg_ids'] = []

async def fetch_and_send_channels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # concurrency locks
    async with fetch_semaphore, chat_locks[chat_id]:
        # clear old
        await clear_previous_list(chat_id, ctx.bot, ctx)
        out = []
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            msg = await update.message.reply_text("❌ Guild not found.")
            return ctx.chat_data.setdefault('last_msg_ids', []).append(msg.message_id)

        for cat_name in CATEGORIES_TO_INCLUDE:
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            out.append(f"{cat_name}")
            for ch in cat.text_channels:
                out.append(f"• {ch.name}")
            out.append("")

        if not out:
            msg = await update.message.reply_text("⚠️ No matching categories found.")
            return ctx.chat_data.setdefault('last_msg_ids', []).append(msg.message_id)

        full = "\n".join(out)
        sent_ids = []
        for i, chunk in enumerate(split_chunks(full)):
            code = f"```\n{chunk}```"
            msg = await update.message.reply_markdown(code)
            sent_ids.append(msg.message_id)
        # footer + buttons
        from datetime import datetime
        footer = (
            "If you don’t see the model you want, let us know when you purchase VIP and we’ll add them ASAP!\n"
            f"Last updated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
            InlineKeyboardButton("💰 Join VIP", url="https://t.me/YourVIPBotPlaceholder")
        ]])
        msg2 = await update.message.reply_text(footer, reply_markup=keyboard)
        sent_ids.append(msg2.message_id)
        ctx.chat_data['last_msg_ids'] = sent_ids

# /start
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # initial prompt
    init = await update.message.reply_text(
        "⏳ Loading Model channels please wait, this could take 2–5 mins…"
    )
    ctx.chat_data['last_msg_ids'] = [init.message_id]
    await fetch_and_send_channels(update, ctx)

# /refresh via command
async def refresh_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await fetch_and_send_channels(update, ctx)

# via button callback
async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    dummy = Update(
        update.callback_query.update_id,
        message=update.callback_query.message
    )
    # reuse same message object
    await fetch_and_send_channels(dummy, ctx)

# catch-all
async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start and /refresh to fetch the model list."
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CommandHandler("refresh", refresh_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt)
)
# ────────────────────────────────────────────────────────────────────────────

# ─── Flask webserver for webhook ───────────────────────────────────────────
app = Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "🤖 Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    upd  = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put_nowait(upd)
    return 'OK'
# ────────────────────────────────────────────────────────────────────────────

async def set_webhook():
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    # start Telegram
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    # start Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    asyncio.run(main())
