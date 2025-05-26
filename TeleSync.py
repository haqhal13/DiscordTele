import os
import asyncio
import discord
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# === LOAD ENVIRONMENT ===
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEB_PORT = int(os.getenv("PORT", 10000))

# === CATEGORY FILTER ===
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

# === LOGGING CONFIGURATION ===
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
        logging.debug("🔍 Checking for guild and categories...")
        guild = client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            logging.error("❌ Discord guild not found!")
            return "Error: Guild not found."
        logging.info(f"✅ Found guild: {guild.name} ({guild.id})")

        result = ""
        for category in guild.categories:
            if category.name not in CATEGORIES_TO_INCLUDE:
                logging.debug(f"⏭ Skipping category: {category.name}")
                continue
            logging.debug(f"📂 Processing category: {category.name}")
            result += f"\n📂 {category.name}\n"
            for ch in category.channels:
                if isinstance(ch, discord.TextChannel):
                    logging.debug(f"   - Found channel: {ch.name}")
                    result += f"   - {ch.name}\n"
        return result.strip() or "No channels found."
    except Exception:
        logging.exception("❌ Exception in fetch_discord_channels")
        return "Error fetching channels."

# === TELEGRAM BOT ===
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logging.info(f"🚀 /start from {user.username} ({user.id})")
    await update.message.reply_text("⏳ Fetching latest model list...")
    data = await fetch_discord_channels()
    msg = f"📋 **Current Model List:**\n\n{data}\n\n💸 Pay here: https://t.me/YourPaymentBot"
    await update.message.reply_text(msg, parse_mode="Markdown")
    logging.info("✅ Sent model list to Telegram.")

# === FLASK HEALTHCHECK ===
app = Flask(__name__)
@app.route('/')
def home():
    logging.info("🌐 Healthcheck pinged.")
    return "OK"

# === MAIN ===
async def main():
    logging.info("🚀 Starting bots...")
    # Start Discord
    discord_task = asyncio.create_task(client.start(DISCORD_TOKEN))
    # Start Telegram
    tg_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    tg_app.add_handler(CommandHandler("start", start_command))
    logging.info("✅ Telegram initialized.")
    # Run polling without closing loop
    telegram_task = asyncio.create_task(tg_app.run_polling(close_loop=False))
    await asyncio.gather(discord_task, telegram_task)

if __name__ == '__main__':
    import threading
    # Start Flask in thread
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=WEB_PORT)).start()
    # Run async
    asyncio.run(main())
