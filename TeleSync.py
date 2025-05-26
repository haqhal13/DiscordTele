import os
import asyncio
import logging
import html
from threading import Thread

from flask import Flask, request, abort

import discord
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID = int(os.environ["DISCORD_GUILD_ID"])
TELEGRAM_TOKEN   = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL      = os.environ["WEBHOOK_URL"]  # e.g. https://discordtele.onrender.com
PORT             = int(os.environ.get("PORT", 3000))

# ─── DISCORD CLIENT ────────────────────────────────────────────────────────
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
    lines = []
    for cat in guild.categories:
        lines.append(f"{cat.name}:")
        for ch in cat.text_channels:
            lines.append(f"  • {ch.name}")
        lines.append("")  # blank between categories
    return "\n".join(lines).strip()

# ─── TELEGRAM BOT ──────────────────────────────────────────────────────────
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

def chunk_text(text: str, max_len: int=4000):
    """Yield successive chunks ≤ max_len, cutting on newline."""
    while text:
        if len(text) <= max_len:
            yield text
            break
        # find last newline before max_len
        cut = text.rfind("\n", 0, max_len)
        if cut == -1:
            cut = max_len
        yield text[:cut]
        text = text[cut:].lstrip("\n")

async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logging.info(f"🚀 /start by {update.effective_user.id}")
    await update.message.reply_text("⏳ Fetching Discord channels…")
    try:
        raw = await fetch_discord_channels()
        safe = html.escape(raw)
        for chunk in chunk_text(safe):
            # wrap each chunk in a <pre> block
            await update.message.reply_html(f"<pre>{chunk}</pre>")
    except Exception:
        logging.exception("Failed to fetch channels")
        await update.message.reply_text("❌ Could not fetch channels.")

app.add_handler(CommandHandler("start", start_handler))

# ─── FLASK WEBHOOK SERVER ─────────────────────────────────────────────────
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
    app.update_queue.put_nowait(upd)
    return "OK", 200

def run_flask():
    logging.info(f"🌐 Flask starting on port {PORT}")
    flask_app.run(host="0.0.0.0", port=PORT)

# ─── MAIN ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s [%(levelname)s] %(message)s")

    Thread(target=run_flask, daemon=True).start()

    async def main():
        asyncio.create_task(discord_client.start(DISCORD_TOKEN))
        logging.info("🚀 Discord client started")

        await app.initialize()
        await app.start()
        logging.info("🚀 Telegram webhook initialized")

        await asyncio.Event().wait()

    asyncio.run(main())
