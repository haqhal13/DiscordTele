import os
import asyncio
import discord
import logging
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIGURATION ===
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

# === LOGGING SETUP ===
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

# === Discord Client ===
intents = discord.Intents.default()
intents.guilds = True
intents.guild_messages = True
intents.messages = True
discord_client = discord.Client(intents=intents)

# === Fetch Discord Channels ===
async def fetch_discord_channels():
    try:
        logging.debug("🔍 Waiting for Discord client ready...")
        await discord_client.wait_until_ready()
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            logging.error("❌ Could not find Discord guild!")
            return "Error: Discord guild not found."
        
        logging.info(f"✅ Found guild: {guild.name} ({guild.id})")
        
        result = ""
        for category in guild.categories:
            if category.name in CATEGORIES_TO_INCLUDE:
                logging.debug(f"📂 Processing category: {category.name}")
                result += f"\n📂 {category.name}\n"
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel):
                        logging.debug(f"    - Found channel: {channel.name}")
                        result += f"   - {channel.name}\n"
        return result.strip() or "No channels found."
    except Exception as e:
        logging.exception("❌ Exception during Discord channel fetch:")
        return f"Error: {str(e)}"

# === Telegram Bot Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logging.info(f"🚀 /start command received from {user.username} ({user.id})")
    await update.message.reply_text("Fetching the latest model list... Please wait.")

    try:
        model_list = await fetch_discord_channels()
        message = f"📋 **Current Model List:**\n\n{model_list}\n\n💸 To unlock full access, pay here: [Payment Link](https://t.me/YourPaymentBot)"
        await update.message.reply_text(message, parse_mode="Markdown")
        logging.info("✅ Model list sent to Telegram user.")
    except Exception as e:
        logging.exception("❌ Exception in /start command:")
        await update.message.reply_text("An error occurred. Please try again later.")

# === Flask Web Service ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    logging.info("🌐 Flask / endpoint hit.")
    return "✅ Discord-Telegram bot is running."

# === Main Runner ===
async def main():
    logging.info("🚀 Starting main runner...")
    try:
        telegram_app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start))
        logging.info("✅ Telegram bot initialized.")

        discord_task = asyncio.create_task(discord_client.start(DISCORD_TOKEN))
        telegram_task = asyncio.create_task(telegram_app.run_polling())

        await asyncio.gather(discord_task, telegram_task)
    except Exception as e:
        logging.exception("❌ Exception in main runner:")

# === Run Everything ===
if __name__ == "__main__":
    import threading

    logging.info("🔧 Environment Variables Loaded")
    logging.info(f"DISCORD_GUILD_ID: {DISCORD_GUILD_ID}")
    logging.info(f"DISCORD_TOKEN: {DISCORD_TOKEN[:10]}... (masked)")
    logging.info(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_BOT_TOKEN[:10]}... (masked)")

    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=WEB_PORT)).start()

    asyncio.run(main())
