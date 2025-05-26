import os
import asyncio
import discord
from discord.utils import get
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
from threading import Thread

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

# only these categories will be fetched
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

async def fetch_and_send_channels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Fetch only desired categories, then send as markdown in safe-sized chunks."""
    try:
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            return await update.message.reply_text("❌ Guild not found.")

        # build a markdown list
        out = []
        for cat_name in CATEGORIES_TO_INCLUDE:
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            out.append(f"*{cat_name}*")
            for ch in cat.text_channels:
                out.append(f"• `{ch.name}`")
            out.append("")  # blank line

        if not out:
            return await update.message.reply_text("⚠️ No matching categories found.")

        full = "\n".join(out)
        for i, chunk in enumerate(split_chunks(full)):
            # label subsequent chunks
            prefix = "*(continued)*\n" if i>0 else ""
            await update.message.reply_markdown(prefix + chunk)

    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch channels: {e}")

# /start
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Hi there! Type /start or /refresh to receive an up-to-date model list."
    )
    await update.message.reply_text(
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…"
    )
    await fetch_and_send_channels(update, ctx)

# /refresh same logic
async def refresh_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing…")
    await fetch_and_send_channels(update, ctx)

# catch-all
async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start and /refresh to fetch the model list."
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CommandHandler("refresh", refresh_handler))
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
    # start Telegram side
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()

    # then Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # run Flask in its own thread
    Thread(target=lambda: app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 10000)),
        debug=False
    ), daemon=True).start()
    asyncio.run(main())
