import os
import asyncio
import logging
import html
from threading import Thread

from flask import Flask, request, abort

import discord
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIG ──────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL      = os.environ["WEBHOOK_URL"]     # e.g. https://discordtele.onrender.com
PORT             = int(os.environ.get("PORT", 3000))

# ─── DISCORD CLIENT ──────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    logging.info(f"✅ Discord logged in as {discord_client.user} (ID {discord_client.user.id})")

async def fetch_discord_channels() -> str:
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return "❌ Discord guild not found!"
    parts = []
    for cat in guild.categories:
        lines = [f"{cat.name}:"]
        for txt in cat.text_channels:
            lines.append(f"  • {txt.name}")
        parts.append("\n".join(lines))
    return "\n\n".join(parts) or "_No channels found_"

# ─── TELEGRAM BOT ────────────────────────────────────────────────────────────
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logging.info(f"🚀 /start by {update.effective_user.id}")
    await update.message.reply_text("⏳ Fetching Discord channels…")
    try:
        raw = await fetch_discord_channels()
        safe = html.escape(raw)
        await update.message.reply_html(
            f"<b>Guild Channels:</b>\n<pre>{safe}</pre>"
        )
    except Exception:
        logging.exception("Failed to fetch channels")
        await update.message.reply_text("❌ Could not fetch channels.")

app.add_handler(CommandHandler("start", start_handler))

# ─── FLASK WEBHOOK SERVER ────────────────────────────────────────────────────
flask_app = Flask(__name__)

@flask_app.route("/")
def health():
    return "OK", 200

@flask_app.route("/webhook", methods=["POST"])
def telegram_webhook():
    if request.headers.get("content-type") != "application/json":
        return abort(400)
    data = request.get_json(force=True)
    upd = Update.de_json(data, app.bot)
    logging.debug(f"🔔 Incoming update: {upd}")
    app.update_queue.put_nowait(upd)
    return "OK", 200

def run_flask():
    logging.info(f"🌐 Flask starting on port {PORT}")
    flask_app.run(host="0.0.0.0", port=PORT)

# ─── MAIN ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    # 1) Start Flask in background
    Thread(target=run_flask, daemon=True).start()

    async def main():
        # 2) Run Discord
        asyncio.create_task(discord_client.start(DISCORD_TOKEN))
        logging.info("🚀 Discord client started")

        # 3) Initialize & start Telegram webhook dispatcher
        await app.initialize()
        await app.start()
        logging.info("🚀 Telegram webhook initialized")

        # 4) Hang forever
        await asyncio.Event().wait()

    asyncio.run(main())
