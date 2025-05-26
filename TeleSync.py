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

def split_chunks(text: str, limit: int = 4000):
    """Split a long string into Telegram-safe chunks (≤ limit chars), by line."""
    lines = text.splitlines(keepends=True)
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks

async def clear_previous(chat_data, bot, chat_id):
    """Delete any previously sent messages stored in chat_data['msgs']"""
    msgs = chat_data.get('msgs', [])
    for msg_id in msgs:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception:
            pass
    chat_data['msgs'] = []

async def fetch_and_send_channels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # determine chat_id
    if update.callback_query:
        chat_id = update.callback_query.message.chat.id
    else:
        chat_id = update.effective_chat.id
    bot = ctx.bot

    # clear old messages
    await clear_previous(ctx.chat_data, bot, chat_id)

    # 1) send loading message
    loading = await bot.send_message(
        chat_id,
        "⏳ Loading Model channels please wait, this could take 2–5 mins… we have hundreds"
    )
    ctx.chat_data.setdefault('msgs', []).append(loading.message_id)

    # 2) build full plain-text list
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        err = await bot.send_message(chat_id, "❌ Guild not found.")
        ctx.chat_data['msgs'].append(err.message_id)
        return

    lines = []
    for cat_name in CATEGORIES_TO_INCLUDE:
        cat = get(guild.categories, name=cat_name)
        if not cat:
            continue
        lines.append(cat_name)
        for ch in cat.text_channels:
            lines.append(f"  • {ch.name}")
        lines.append("")

    if not lines:
        warn = await bot.send_message(chat_id, "⚠️ No matching categories found.")
        ctx.chat_data['msgs'].append(warn.message_id)
        return

    full_text = "\n".join(lines)

    # 3) send in code-block chunks
    for chunk in split_chunks(full_text):
        code_block = f"```{chunk}```"
        msg = await bot.send_message(
            chat_id,
            code_block,
            parse_mode="Markdown"
        )
        ctx.chat_data['msgs'].append(msg.message_id)

    # 4) footer + refresh button
    last_updated = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh")
    ]])
    footer = await bot.send_message(
        chat_id,
        ("If you don’t see the model you want, no worries – once you purchase VIP let us know who you want "
         "and we’ll get them added ASAP!\n\n"
         f"_List last updated: {last_updated}_"),
        parse_mode="Markdown",
        reply_markup=keyboard
    )
    ctx.chat_data['msgs'].append(footer.message_id)

# Handlers
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await fetch_and_send_channels(update, ctx)

async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # acknowledge the button press
    await update.callback_query.answer()
    await fetch_and_send_channels(update, ctx)

async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start and the button above to fetch the model list."
    )

# register handlers
tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))

# ─── Flask webhook server ─────────────────────────────────────────────────
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
    # Telegram
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    # Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    asyncio.run(main())
