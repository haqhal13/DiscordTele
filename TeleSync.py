import os
import threading
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import discord
from discord import Intents

# Load environment variables
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
DISCORD_GUILD_ID = int(os.environ.get("DISCORD_GUILD_ID", 0))
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
WEBHOOK_URL = os.environ["WEBHOOK_URL"]
PORT = int(os.environ.get("PORT", 10000))

# Categories to include
CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS', '🧔 MALE CREATORS  / AGENCY', '💪 HGF', '🎥 NET VIDEO GIRLS',
    '🇨🇳 ASIAN .1', '🇨🇳 ASIAN .2', '🇲🇽 LATINA .1', '🇲🇽 LATINA .2',
    '❄ SNOWBUNNIE .1', '❄ SNOWBUNNIE .2', '🇮🇳 INDIAN / DESI', '🇸🇦 ARAB',
    '🧬 MIXED / LIGHTSKIN', '🏴 BLACK', '🌺 POLYNESIAN', '☠ GOTH / ALT',
    '🏦 VAULT BANKS', '🔞 PORN', 'Uncatagorised Girls'
]

# Initialize Flask app for Telegram webhook
app = Flask(__name__)

# Initialize Discord client
intents = Intents.default()
discord_client = discord.Client(intents=intents)

# Telegram: generate and format model list message
def build_model_list():
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return "❌ Couldn't find the configured Discord guild."

    # Collect channels under desired categories
    lines = []
    for category in guild.categories:
        if category.name in CATEGORIES_TO_INCLUDE:
            for ch in category.channels:
                prefix = '•'
                lines.append(f"{prefix} {ch.name}")

    if not lines:
        return "🚫 No channels found in the specified categories."

    # Header with timestamp
    header = f"<b>Model Channels (updated)</b>\n"
    body = "\n".join(lines)
    return header + body

# Telegram: /start and /refresh handler
def make_intro_keyboard():
    kb = [[InlineKeyboardButton("🔄 Refresh", callback_data="refresh")]]
    return InlineKeyboardMarkup(kb)

async def start_or_refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # On first /start or /refresh, clear previous messages
    chat_id = update.effective_chat.id
    # Send waiting message
    waiting = await context.bot.send_message(
        chat_id,
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…",
        parse_mode='HTML'
    )

    # Build the list (may be slow)
    text = build_model_list()

    # Delete waiting message
    await waiting.delete()

    # Send the list with refresh button
    await context.bot.send_message(
        chat_id,
        text,
        parse_mode='HTML',
        reply_markup=make_intro_keyboard()
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'refresh':
        # Treat refresh same as start
        await start_or_refresh(update, context)

# Telegram setup
def setup_telegram(app_obj: Application):
    app_obj.add_handler(CommandHandler('start', start_or_refresh))
    app_obj.add_handler(CommandHandler('refresh', start_or_refresh))
    app_obj.add_handler(CommandHandler('help', start_or_refresh))
    app_obj.add_handler(telegram.ext.CallbackQueryHandler(button_callback))

# Flask route for Telegram webhook
@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = Update.de_json(request.get_json(force=True), telegram_app.bot)
    telegram_app.update_queue.put(update)
    return 'OK'

# Discord event handlers
@discord_client.event
async def on_ready():
    print(f"✅ Discord logged in as {discord_client.user} (ID: {discord_client.user.id})")

# Main entry
if __name__ == '__main__':
    # Telegram bot
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    setup_telegram(telegram_app)
    # Set Telegram webhook
    telegram_app.bot.set_webhook(WEBHOOK_URL + '/webhook')

    # Run Flask in background
    flask_thread = threading.Thread(
        target=app.run,
        kwargs={'host': '0.0.0.0', 'port': PORT}
    )
    flask_thread.daemon = True
    flask_thread.start()

    # Finally, run Discord client (blocks)
    discord_client.run(DISCORD_TOKEN)
