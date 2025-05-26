import os
import asyncio
import logging
from threading import Thread

from flask import Flask, request, abort
import discord
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ── CONFIG ────────────────────────────────────────────────────────────────────
DISCORD_TOKEN   = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
TELEGRAM_TOKEN  = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_PATH    = f"/{TELEGRAM_TOKEN}"   # Telegram will POST here
WEBHOOK_URL     = os.environ["WEBHOOK_URL"]  # e.g. https://discordtele.onrender.com
PORT            = int(os.environ.get("PORT", 3000))

# ── DISCORD SETUP ─────────────────────────────────────────────────────────────
discord_intents = discord.Intents.default()
discord_intents.guilds = True

discord_client = discord.Client(intents=discord_intents)

@discord_client.event
async def on_ready():
    logging.info(f"✅ Discord logged in as {discord_client.user} (ID {discord_client.user.id})")

async def fetch_discord_channels() -> str:
    """Return a formatted list of text channels in the given guild."""
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return "❌ Could not find your Discord guild."
    out = []
    for cat in guild.categories:
        lines = [f"📂 *{cat.name}*"]
        for ch in cat.text_channels:
            lines.append(f"   • `{ch.name}`")
        if len(lines) > 1:
            out.append("\n".join(lines))
    return "\n\n".join(out) or "_No channels found._"

# ── TELEGRAM SETUP ────────────────────────────────────────────────────────────
telegram_app = (
    ApplicationBuilder()
    .token(TELEGRAM_TOKEN)
    .build()
)

async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logging.info(f"🚀 /start from {user.username} ({user.id})")
    await update.message.reply_text("⏳ Fetching Discord channels…")
    try:
        channel_list = await fetch_discord_channels()
        await update.message.reply_markdown_v2(
            f"*Current Channels:*\n\n{channel_list}"
        )
    except Exception as e:
        logging.exception("Error fetching channels")
        await update.message.reply_text("❌ Failed to fetch channels.")

telegram_app.add_handler(CommandHandler("start", start_cmd))

# ── FLASK WEBHOOK ─────────────────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def healthcheck():
    return "✅ OK", 200

@flask_app.route(WEBHOOK_PATH, methods=["POST"])
def telegram_webhook():
    """Receive updates from Telegram and push them into PTB's queue."""
    if request.headers.get("content-type") != "application/json":
        return abort(400)
    data = request.get_json(force=True)
    update = Update.de_json(data, telegram_app.bot)
    telegram_app.update_queue.put(update)
    return "OK", 200

def run_flask():
    # Make sure your RENDER or Heroku port is exposed
    flask_app.run(host="0.0.0.0", port=PORT)

# ── MAIN ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    # 1) Launch Flask in its own thread
    Thread(target=run_flask, daemon=True).start()
    logging.info(f"🌐 Flask running on port {PORT}")
    # 2) Start Discord (async) and Telegram webhook runner
    async def main():
        # Start Discord in background
        asyncio.create_task(discord_client.start(DISCORD_TOKEN))
        logging.info("🚀 Discord client started")
        # Initialize PTB (this also starts its update‐queue processor)
        await telegram_app.initialize()
        await telegram_app.start()
        # We DO NOT call run_polling(); instead Telegram will POST into Flask
        logging.info("🚀 Telegram webhook initialized")
        # Keep the loop alive
        await asyncio.Event().wait()

    asyncio.run(main())
