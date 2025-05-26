import os
import threading
import asyncio
import discord
import logging
from flask import Flask
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv

# === LOAD ENVIRONMENT ===
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_PORT = int(os.getenv("PORT", 10000))

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

# === LOGGING CONFIG ===
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

# === DISCORD CLIENT ===
intents = discord.Intents.default()
intents.guilds = True
client = discord.Client(intents=intents)

@client.event
async def on_ready():
    logging.info(f"✅ Discord connected as {client.user} (ID: {client.user.id})")

async def fetch_discord_channels():
    try:
        await client.wait_until_ready()
        logging.debug("🔍 Checking for guild...")
        guild = client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            logging.error("❌ Guild not found")
            return "Error: Guild not found."
        logging.info(f"✅ Found guild: {guild.name} ({guild.id})")

        output = ""
        for category in guild.categories:
            if category.name not in CATEGORIES_TO_INCLUDE:
                logging.debug(f"⏭ Skipping category {category.name}")
                continue
            logging.debug(f"📂 Processing category {category.name}")
            output += f"\n📂 {category.name}\n"
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    logging.debug(f"   - {ch.name}")
                    output += f"   - {ch.name}\n"
        return output.strip() or "No channels found."
    except Exception:
        logging.exception("❌ Error fetching channels")
        return "Error fetching channels."

# === TELEGRAM HANDLER ===
def start_command(update: Update, context: CallbackContext):
    user = update.effective_user
    logging.info(f"🚀 /start from {user.username} ({user.id})")
    update.message.reply_text("⏳ Fetching model list...")
    try:
        future = asyncio.run_coroutine_threadsafe(fetch_discord_channels(), discord_loop)
        data = future.result(timeout=30)
        message = f"📋 **Model List:**\n\n{data}\n\n💸 Pay: https://t.me/YourPaymentBot"
        update.message.reply_text(message, parse_mode="Markdown")
        logging.info("✅ Sent model list to Telegram.")
    except Exception:
        logging.exception("❌ Error sending model list")
        update.message.reply_text("❌ Failed to fetch list.")

# === FLASK HEALTHCHECK ===
app = Flask(__name__)
@app.route('/')
def home():
    logging.info("🌐 Healthcheck")
    return "OK"

# === MAIN ===
if __name__ == '__main__':
    # Start Flask
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=WEB_PORT)).start()
    # Start Discord in thread
    discord_loop = asyncio.new_event_loop()
    threading.Thread(target=lambda: discord_loop.run_until_complete(client.start(DISCORD_TOKEN))).start()
    # Start Telegram PTB v13
    updater = Updater(token=TELEGRAM_BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start_command))
    logging.info("✅ Telegram initialized")
    updater.start_polling()
    updater.idle()
