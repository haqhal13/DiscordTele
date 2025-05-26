import os
import asyncio
import discord
import logging
import traceback
from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv

# === Load Environment ===
load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
DISCORD_GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
PAYMENT_LINK = "https://t.me/YourPaymentBot"
WEB_PORT = int(os.getenv("PORT", 3000))

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

# === Logging Config ===
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
)

logging.info("🔧 Environment Variables Loaded")
logging.info(f"DISCORD_GUILD_ID: {DISCORD_GUILD_ID}")
logging.info(f"DISCORD_TOKEN: {DISCORD_TOKEN[:10]}... (masked)")
logging.info(f"TELEGRAM_BOT_TOKEN: {TELEGRAM_TOKEN[:10]}... (masked)")

# === Discord Client ===
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    logging.info(f"✅ Discord Client connected as {discord_client.user} (ID: {discord_client.user.id})")
    logging.info(f"✅ Connected to Discord servers: {[g.name for g in discord_client.guilds]}")

async def fetch_discord_channels():
    try:
        await discord_client.wait_until_ready()
        logging.debug("🔍 Fetching filtered categories from Discord...")
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            logging.warning("⚠️ Discord guild not found!")
            return "Error: Discord guild not found."

        result = ""
        for category in guild.categories:
            if category.name.strip() in CATEGORIES_TO_INCLUDE:
                result += f"\n📂 {category.name}\n"
                for channel in category.channels:
                    if isinstance(channel, discord.TextChannel):
                        result += f"   - {channel.name}\n"
            else:
                logging.debug(f"⏭️ Skipped category: {category.name}")

        return result.strip() or "No matching channels found."
    except Exception as e:
        logging.error("❌ Error in fetch_discord_channels:\n" + traceback.format_exc())
        return "Error: Unable to fetch channels."

# === Telegram Bot ===
async def telegram_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logging.info(f"🚀 /start triggered by {user.username} (ID: {user.id})")
    try:
        await update.message.reply_text("Fetching the latest model list... Please wait.")
        model_list = await fetch_discord_channels()
        message = f"📋 **Current Model List:**\n\n{model_list}\n\n💸 To unlock full access, pay here: {PAYMENT_LINK}"
        await update.message.reply_text(message, parse_mode="Markdown")
        logging.info("✅ Model list sent to Telegram.")
    except Exception as e:
        logging.error("❌ Error in /start handler:\n" + traceback.format_exc())
        await update.message.reply_text("An error occurred while fetching the model list.")

# === Flask Web Service ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    logging.debug("🌐 Flask / endpoint pinged.")
    return "✅ Discord-Telegram Model List Bot is running."

async def start_telegram_bot():
    telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    telegram_app.add_handler(CommandHandler("start", telegram_start))
    await telegram_app.initialize()
    await telegram_app.start()
    await telegram_app.updater.start_polling()
    logging.info("✅ Telegram bot polling started.")
    await telegram_app.updater.wait()

async def main():
    discord_task = asyncio.create_task(discord_client.start(DISCORD_TOKEN))
    telegram_task = asyncio.create_task(start_telegram_bot())
    await asyncio.gather(discord_task, telegram_task)

if __name__ == "__main__":
    import threading
    threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=WEB_PORT)).start()
    asyncio.run(main())
