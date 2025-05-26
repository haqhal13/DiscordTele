import os
import threading
import asyncio
import discord
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv

# === Load environment variables ===
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_PORT = int(os.getenv("PORT", 10000))

# === Category filter ===
CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS',
    '🧔 MALE CREATORS / AGENCY',
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

# === Logging configuration ===
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

# === Discord client setup ===
intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)

def start_discord_loop():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(client.start(DISCORD_TOKEN))

@client.event
async def on_ready():
    logging.info(f"✅ Discord connected: {client.user} (ID: {client.user.id})")

async def fetch_discord_channels():
    await client.wait_until_ready()
    guild = client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        logging.error("❌ Guild not found!")
        return "Error: Guild not found."
    logging.info(f"✅ Found guild: {guild.name}")
    output = ""
    for category in guild.categories:
        if category.name not in CATEGORIES_TO_INCLUDE:
            logging.debug(f"⏭ Skipping category {category.name}")
            continue
        logging.debug(f"📂 Category: {category.name}")
        output += f"\n📂 {category.name}\n"
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                logging.debug(f"   - Channel: {ch.name}")
                output += f"   - {ch.name}\n"
    return output.strip() or "No channels found."

# === Telegram handler ===
def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    logging.info(f"🚀 /start triggered by {user.username} ({user.id})")
    update.message.reply_text("⏳ Fetching latest model list...")
    try:
        future = fetch_future = asyncio.run_coroutine_threadsafe(fetch_discord_channels(), discord_loop)
        data = future.result(timeout=30)
        msg = f"📋 **Model List:**\n\n{data}\n\n💸 Pay here: https://t.me/YourPaymentBot"
        update.message.reply_text(msg, parse_mode="Markdown")
        logging.info("✅ Sent model list to Telegram.")
    except Exception:
        logging.exception("❌ Error fetching/sending model list")
        update.message.reply_text("❌ Failed to fetch model list.")

# === Flask health check ===
app = Flask(__name__)
@app.route('/')
def home():
    logging.info("🌐 Healthcheck ping")
    return "OK"

# === Main entrypoint ===
if __name__ == '__main__':
    # Start Discord in its own thread/event loop
    discord_loop = asyncio.new_event_loop()
    threading.Thread(target=start_discord_loop, daemon=True).start()

    # Start Flask server for health checks
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=WEB_PORT), daemon=True).start()

    # Initialize Telegram bot (PTB v13)
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    # Remove any existing webhook and start polling
    updater.bot.delete_webhook()
    logging.info("✅ Cleared previous Telegram webhook; switching to polling.")
    dispatcher.add_handler(CommandHandler('start', start_command))
    logging.info("✅ Telegram bot initialized, polling started.")
    updater.start_polling()
    updater.idle()
