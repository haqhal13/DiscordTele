import os
import asyncio
import discord
from discord.utils import get
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from telegram.error import BadRequest
from flask import Flask, request
from threading import Thread
from datetime import datetime

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

# ─── Discord client ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ─── Telegram app ──────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────

# keep track of what messages we sent last time in each chat
chat_histories: dict[int, list[int]] = {}

def split_chunks(text: str, limit: int = 4000) -> list[str]:
    """Split a long string into ≤ limit-char chunks by line."""
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

async def do_refresh(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    bot = ctx.bot
    # 1) delete previous run
    for msg_id in chat_histories.get(chat_id, []):
        try:
            await bot.delete_message(chat_id, msg_id)
        except:
            pass

    new_ids: list[int] = []

    # 2) fetch Discord categories
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        msg = await bot.send_message(chat_id, "❌ Guild not found.")
        chat_histories[chat_id] = [msg.message_id]
        return

    out = []
    for cat_name in CATEGORIES_TO_INCLUDE:
        cat = get(guild.categories, name=cat_name)
        if not cat:
            continue
        out.append(f"*{cat_name}*")
        for ch in cat.text_channels:
            out.append(f"• `{ch.name}`")
        out.append("")

    if not out:
        msg = await bot.send_message(chat_id, "⚠️ No matching categories found.")
        chat_histories[chat_id] = [msg.message_id]
        return

    full = "\n".join(out)

    # 3) stream each chunk in a <pre> block
    for chunk in split_chunks(full):
        msg = await bot.send_message(
            chat_id,
            f"<pre>{chunk}</pre>",
            parse_mode='HTML'
        )
        new_ids.append(msg.message_id)

    # 4) footer + buttons
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    footer = (
        f"Last updated on {timestamp}\n\n"
        "We have so many more models we couldnt inlcude on the list If a model you want isn’t listed yet, buy VIP & let us know which one you want added and we will do it asap!"
    )
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        InlineKeyboardButton("💎 Join VIP", url="https://t.me/HOB_VIP_BOT")
    ]])
    msg = await bot.send_message(chat_id, footer, reply_markup=keyboard)
    new_ids.append(msg.message_id)

    chat_histories[chat_id] = new_ids

# ─── Handlers ───────────────────────────────────────────────────────────────

async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    # 1) immediate loading notice
    msg = await update.message.reply_text(
        "⏳ Loading Model channels please wait, this could take 2–5 mins (we have hundreds)…"
    )
    chat_histories[chat_id] = [msg.message_id]
    # 2) background refresh
    asyncio.create_task(do_refresh(chat_id, ctx))

async def refresh_command(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # if user types /refresh
    await start_handler(update, ctx)

async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # if user presses 🔄 button
    query = update.callback_query
    chat_id = query.message.chat.id
    try:
        await query.answer()
    except BadRequest:
        # too old → fallback
        await query.message.reply_text("🔄 Refresh timed out—please send /start instead.")
        return

    msg = await query.message.reply_text(
        "⏳ Loading Model channels please wait, this could take 2–5 mins (we have hundreds)…"
    )
    chat_histories[chat_id] = [msg.message_id]
    asyncio.create_task(do_refresh(chat_id, ctx))

async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start or 🔄 Refresh."
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CommandHandler("refresh", refresh_command))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))

# ─── Flask webhook ──────────────────────────────────────────────────────────
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

async def set_webhook():
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    # start Telegram
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    # then Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # run Flask in a background thread
    port = int(os.environ.get('PORT', 5000))
    Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    # start both bots
    asyncio.run(main())
