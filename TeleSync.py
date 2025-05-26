import os
import asyncio
import datetime
import discord
from discord.utils import get
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    CallbackQueryHandler,
    filters,
)
from flask import Flask, request
from threading import Thread

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

async def fetch_and_send_channels(chat_id: int, bot):
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        await bot.send_message(chat_id, "❌ Guild not found.")
        return

    out = []
    for cat_name in CATEGORIES_TO_INCLUDE:
        cat = get(guild.categories, name=cat_name)
        if not cat:
            continue
        out.append(f"```\n{cat_name}```")
        for ch in cat.text_channels:
            out.append(f"`• {ch.name}`")
        out.append("")

    if not out:
        await bot.send_message(chat_id, "⚠️ No matching categories found.")
        return

    full = "\n".join(out)
    for chunk in split_chunks(full):
        await bot.send_message(chat_id, chunk, parse_mode='Markdown')

async def send_footer(chat_id: int, bot):
    last_updated = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    footer_text = (
        f"Last updated: {last_updated}\n"
        "If you don't see your model, when you purchase VIP let us know and we'll add it ASAP!"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton('🔄 Refresh', callback_data='refresh')],
        [InlineKeyboardButton('💳 Join VIP', url='https://t.me/VIPPaymentBot')]
    ])
    await bot.send_message(chat_id, footer_text, reply_markup=keyboard)

# Handlers
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    bot = ctx.bot
    # instant loading message
    await bot.send_message(chat_id, "⏳ Loading Model channels please wait, this could take 2–5 mins…")
    # fetch and send
    await fetch_and_send_channels(chat_id, bot)
    # footer with buttons
    await send_footer(chat_id, bot)

async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    bot = ctx.bot
    chat_id = query.message.chat_id
    # acknowledge callback (ignore timeout)
    try:
        await query.answer()
    except:
        pass
    # clear previous bot messages in chat
    async for msg in bot.get_chat(chat_id).history(limit=100):
        if msg.from_user and msg.from_user.id == bot.id:
            await msg.delete()
    # resend
    await fetch_and_send_channels(chat_id, bot)
    await send_footer(chat_id, bot)

async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start and /refresh to fetch the model list."
    )

# register handlers
tg_app.add_handler(CommandHandler('start', start_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern='^refresh$'))
# fallback for text
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))

# ─── Flask webhook server ───────────────────────────────────────────────────
app = Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "🤖 Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    upd = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put_nowait(upd)
    return 'OK'

async def set_webhook():
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    # start Flask thread
    Thread(target=lambda: app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000))), daemon=True).start()
    # telegram webhook
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    # start discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    asyncio.run(main())
