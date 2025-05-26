import os
import asyncio
import logging
from datetime import datetime
from flask import Flask, request
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import discord
from discord import Intents

# Configuration
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID"))

CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS', '🧔 MALE CREATORS  / AGENCY', '💪 HGF',
    '🎥 NET VIDEO GIRLS', '🇨🇳 ASIAN .1', '🇨🇳 ASIAN .2',
    '🇲🇽 LATINA .1', '🇲🇽 LATINA .2', '❄ SNOWBUNNIE .1', '❄ SNOWBUNNIE .2',
    '🇮🇳 INDIAN / DESI', '🇸🇦 ARAB', '🧬 MIXED / LIGHTSKIN', '🏴 BLACK',
    '🌺 POLYNESIAN', '☠ GOTH / ALT', '🏦 VAULT BANKS', '🔞 PORN',
    'Uncatagorised Girls'
]

logging.basicConfig(level=logging.INFO)
app = Flask(__name__)

discord_client = discord.Client(intents=Intents.default())

@discord_client.event
async def on_ready():
    logging.info(f"✅ Discord logged in as {discord_client.user}")

# Telegram handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # initial welcome prompt
    await context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="👋 Hi there! Type /start or /refresh to receive an up-to-date model list."
    )

async def fetch_and_send(update: Update, context: ContextTypes.DEFAULT_TYPE, is_refresh=False):
    chat_id = update.effective_chat.id
    msg = await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Fetching Model channels please wait, this could take 2–5 mins…"
    )

    guild = discord_client.get_guild(GUILD_ID)
    if guild is None:
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=msg.message_id,
            text="❌ Could not fetch channels: Guild not found"
        )
        return

    lines = []
    for category in guild.categories:
        if category.name in CATEGORIES_TO_INCLUDE:
            lines.append(f"<b>{category.name}</b>")
            for ch in category.text_channels:
                lines.append(f"• {ch.name}")
            lines.append("")

    if not lines:
        text = "❌ No matching categories found"
    else:
        timestamp = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
        text = "\n".join(lines)
        text += f"\nUpdated: {timestamp}\nType /refresh to refresh the list."

    # replace message
    await context.bot.edit_message_text(
        chat_id=chat_id,
        message_id=msg.message_id,
        text=text,
        parse_mode='HTML'
    )

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await fetch_and_send(update, context)

async def refresh_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    await fetch_and_send(update, context, is_refresh=True)

# Flask endpoint for Telegram webhook
@app.route('/webhook', methods=['POST'])
async def webhook():
    data = request.get_json()
    update = Update.de_json(data, Bot(TELEGRAM_TOKEN))
    await telegram_app.update_queue.put(update)
    return 'OK'

if __name__ == '__main__':
    # Start Discord
    asyncio.create_task(discord_client.start(DISCORD_TOKEN))

    # Build Telegram app
    telegram_app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .build()
    )
    telegram_app.add_handler(CommandHandler('start', start_handler))
    telegram_app.add_handler(CommandHandler('refresh', refresh_handler))

    # Set webhook
    asyncio.get_event_loop().create_task(
        telegram_app.bot.set_webhook(WEBHOOK_URL + '/webhook')
    )

    # Run Flask
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))

