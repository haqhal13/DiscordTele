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

async def fetch_and_send_channels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Core logic: fetch only the categories you listed, then send."""
    try:
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            return await update.message.reply_text("❌ Guild not found.")

        lines = []
        for cat_name in CATEGORIES_TO_INCLUDE:
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            lines.append(f"*{cat_name}*")
            for ch in cat.text_channels:
                lines.append(f"• {ch.name}")
            lines.append("")

        if not lines:
            await update.message.reply_text("⚠️ No matching categories found.")
        else:
            await update.message.reply_markdown("\n".join(lines).strip())

    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch channels: {e}")

# /start
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # immediate welcome
    await update.message.reply_text(
        "👋 Hi there! Type /start or /refresh to receive an up-to-date model list."
    )
    # then kick off the fetch
    await update.message.reply_text(
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…"
    )
    await fetch_and_send_channels(update, ctx)

# /refresh just re‐runs the same
async def refresh_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔄 Refreshing…")
    await fetch_and_send_channels(update, ctx)

# catch any other text
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

# ─── Flask webserver ───────────────────────────────────────────────────────
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
    # start the Telegram application so handlers actually run
    await tg_app.initialize()
    await tg_app.start()

    # set up webhook
    await set_webhook()

    # now start Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # run Flask in a thread
    Thread(target=lambda: app.run(
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 10000)),
        debug=False
    )).start()
    asyncio.run(main())
