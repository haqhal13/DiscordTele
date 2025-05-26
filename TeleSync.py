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
PAYMENT_LINK = "https://t.me/YourPaymentBot"  # Replace with your actual payment bot link
WEB_PORT = int(os.getenv("PORT", 3000))  # For Render or any host

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

# === Fetch Discord Channels ===
async def fetch_discord_channels():
    try:
        await discord_client.wait_until_ready()
        logging.debug("🔍 Fetching categories and channels from Discord...")
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            logging.warning("⚠️ Discord guild not found!")
            return "Error: Discord guild not found."

        result = ""
        for category in guild.categories:
            logging.debug(f"📂 Category: {category.name} (ID: {category.id})")
            result += f"\n📂 {category.name}\n"
            for channel in category.channels:
                if isinstance(channel, discord.TextChannel):
                    logging.debug(f"   - Channel: {channel.name} (ID: {channel.id})")
                    result += f"   - {channel.name}\n"

        if not result.strip():
            logging.warning("⚠️ No channels found.")
            return "No channels found."
        return result.strip()

    except Exception as e:
        logging.error("❌ Error in fetch_discord_channels:\n" + traceback.format_exc())
        return "Error: Unable to fetch channels."

# === Telegram Bot Command ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        logging.info(f"🚀 /start triggered by {user.username} (ID: {user.id})")
        await update.message.reply_text("Fetching the latest model list... Please wait.")

        model_list = await fetch_discord_channels()
        message = f"📋 **Current Model List:**\n\n{model_list}\n\n💸 To unlock full access, pay here: {PAYMENT_LINK}"
        await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        logging.error("❌ Error in Telegram /start command:\n" + traceback.format_exc())
        await update.message.reply_text("An error occurred. Please try again later.")

# === Flask Web Service ===
flask_app = Flask(__name__)

@flask_app.route('/')
def home():
    logging.debug("🌐 Flask / endpoint pinged.")
    return "✅ Discord-Telegram Model List Bot is running."

# === Main Runner ===
async def main():
    try:
        logging.info("🚀 Starting Discord client...")
        asyncio.create_task(discord_client.start(DISCORD_TOKEN))

        logging.info("🚀 Starting Telegram bot...")
        telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
        telegram_app.add_handler(CommandHandler("start", start))
        logging.info("✅ Telegram bot ready and waiting for commands.")
        await telegram_app.run_polling()

    except Exception as e:
        logging.error("❌ Error in main runner:\n" + traceback.format_exc())

# === Run Everything ===
if __name__ == "__main__":
    import threading

    try:
        logging.info(f"🌐 Starting Flask web server on port {WEB_PORT}...")
        threading.Thread(target=lambda: flask_app.run(host="0.0.0.0", port=WEB_PORT)).start()

        logging.info("🚀 Launching main async tasks...")
        asyncio.run(main())

    except Exception as e:
        logging.error("❌ Fatal Error:\n" + traceback.format_exc())
