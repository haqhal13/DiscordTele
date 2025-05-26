# bot.py

import os
import threading
import asyncio
import logging

import discord
from flask import Flask, request

from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from dotenv import load_dotenv

# ─── CONFIG ─────────────────────────────────────────────────────────────────────

load_dotenv()

# Discord
DISCORD_TOKEN      = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID   = int(os.environ["DISCORD_GUILD_ID"])

# Telegram
TELEGRAM_TOKEN     = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL        = os.environ["WEBHOOK_URL"]   # e.g. https://myapp.example.com
WEB_PORT           = int(os.environ.get("PORT", 3000))

# Only include these Discord categories:
CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS', '🧔 MALE CREATORS / AGENCY', '💪 HGF',
    '🎥 NET VIDEO GIRLS', '🇨🇳 ASIAN .1', '🇨🇳 ASIAN .2',
    '🇲🇽 LATINA .1', '🇲🇽 LATINA .2', '❄ SNOWBUNNIE .1',
    '❄ SNOWBUNNIE .2', '🇮🇳 INDIAN / DESI', '🇸🇦 ARAB',
    '🧬 MIXED / LIGHTSKIN', '🏴 BLACK', '🌺 POLYNESIAN',
    '☠ GOTH / ALT', '🏦 VAULT BANKS', '🔞 PORN',
    'Uncatagorised Girls'
]

# ─── LOGGING ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

# ─── DISCORD CLIENT ────────────────────────────────────────────────────────────

discord_loop   = asyncio.new_event_loop()
discord_client = discord.Client(intents=discord.Intents(guilds=True))

def start_discord():
    """Run Discord client in its own loop/thread."""
    asyncio.set_event_loop(discord_loop)
    discord_loop.run_until_complete(discord_client.start(DISCORD_TOKEN))

@discord_client.event
async def on_ready():
    logging.info(f"✅ Discord ready as {discord_client.user} (ID {discord_client.user.id})")

async def fetch_discord_channels():
    """Fetch and format the filtered channel list for Telegram."""
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        logging.error("❌ Discord guild not found!")
        return "Error: Discord guild not found."

    logging.info(f"✅ Found guild: {guild.name}")
    out = []
    for cat in guild.categories:
        if cat.name not in CATEGORIES_TO_INCLUDE:
            logging.debug(f"⏭ Skipping category {cat.name}")
            continue
        logging.debug(f"📂 Including category {cat.name}")
        out.append(f"📂 {cat.name}")
        for ch in cat.channels:
            if isinstance(ch, discord.TextChannel):
                logging.debug(f"   - {ch.name}")
                out.append(f"   – {ch.name}")
    return "\n".join(out) if out else "No channels found."

# ─── TELEGRAM BOT & DISPATCHER ─────────────────────────────────────────────────

bot        = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, use_context=True, workers=4)

def start_handler(update: Update, context):
    user = update.effective_user
    logging.info(f"🚀 /start by {user.username} ({user.id})")
    update.message.reply_text("⏳ Fetching latest model list…")

    # run Discord fetch in Discord's loop
    future = asyncio.run_coroutine_threadsafe(fetch_discord_channels(), discord_loop)
    try:
        data = future.result(timeout=20)
        resp = f"📋 **Model List**:\n\n{data}\n\n💸 Pay here: https://t.me/YourPaymentBot"
        update.message.reply_text(resp, parse_mode="Markdown")
        logging.info("✅ Sent model list to Telegram.")
    except Exception as e:
        logging.exception("❌ Failed to fetch/send model list")
        update.message.reply_text("❌ Failed to fetch model list.")

dispatcher.add_handler(CommandHandler("start", start_handler))

# ─── FLASK WEBHOOK APP ─────────────────────────────────────────────────────────

app = Flask(__name__)

@app.route("/", methods=["GET", "HEAD"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    """Receive Telegram updates via webhook."""
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "OK", 200

# ─── MAIN ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # 1) Launch Discord client
    threading.Thread(target=start_discord, daemon=True).start()

    # 2) Configure Telegram webhook
    bot.delete_webhook()
    webhook_endpoint = f"{WEBHOOK_URL}/webhook"
    bot.set_webhook(webhook_endpoint)
    logging.info(f"✅ Telegram webhook set to {webhook_endpoint}")

    # 3) Run Flask server (health + webhook)
    logging.info(f"🌐 Starting Flask on port {WEB_PORT}")
    app.run(host="0.0.0.0", port=WEB_PORT, threaded=True)
