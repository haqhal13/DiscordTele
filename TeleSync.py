# TeleSync.py
import os
import logging
import threading

from flask import Flask, request
import discord
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ────── CONFIG ──────
DISCORD_TOKEN      = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID   = int(os.environ["DISCORD_GUILD_ID"])
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
# WEBHOOK_URL should be like "https://myapp.onrender.com"
WEBHOOK_URL        = os.environ["WEBHOOK_URL"].rstrip("/") + "/webhook"
PORT               = int(os.environ.get("PORT", "5000"))

# only these categories will be echoed
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

# ────── LOGGER ──────
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ────── HELPERS ──────
def chunked(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i : i + n]

def escape_md2(text: str) -> str:
    """Escape just periods for MarkdownV2."""
    return text.replace(".", r"\.")

# ────── DISCORD CLIENT ──────
intents = discord.Intents.default()
intents.guilds   = True
intents.messages = False
discord_client   = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    logger.info(f"✅ Discord logged in as {discord_client.user} (ID {discord_client.user.id})")

# ────── TELEGRAM BOT ──────
app = Flask(__name__)
telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # 1) immediate “we’re working” prompt:
    await update.message.reply_text(
        "📡 Getting up to date list please wait 2-5 mins…"
    )
    # 2) long-fetch warning:
    await update.message.reply_text(
        "⏳ Fetching Model channels please wait this could take 2-5 mins as we have hundreds…"
    )

    # 3) build fresh list
    output_sections = []
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return await update.message.reply_text("❌ Guild not found.")

    for category in CATEGORIES_TO_INCLUDE:
        matched = [
            ch.name
            for ch in guild.text_channels
            if ch.category
            and ch.category.name.strip().lower() == category.strip().lower()
        ]
        if matched:
            lines = "\n".join(f"• {escape_md2(name)}" for name in matched)
            header = f"*{escape_md2(category)}*"
            output_sections.append(f"{header}\n{lines}")

    if not output_sections:
        return await update.message.reply_text("❌ No configured categories found.")

    # 4) send in 5-section chunks so we never exceed Telegram limits
    for batch in chunked(output_sections, 5):
        text = "\n\n".join(batch)
        await update.message.reply_markdown_v2(text)

telegram_app.add_handler(CommandHandler("start", start_handler))


# ────── FLASK WEBHOOK ──────
@app.route("/", methods=["GET"])
def index():
    return "ok"


@app.route("/webhook", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "OK"


def run_webhook():
    # tell Telegram where to send updates
    telegram_app.bot.set_webhook(WEBHOOK_URL)
    # run flask
    app.run(host="0.0.0.0", port=PORT)


# ────── START EVERYTHING ──────
if __name__ == "__main__":
    # 1) start webhook + Flask in thread
    threading.Thread(target=run_webhook, daemon=True).start()
    # 2) start Discord client (blocking)
    discord_client.run(DISCORD_TOKEN)
