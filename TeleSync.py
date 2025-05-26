```python
import os
import discord
import asyncio
from discord import Intents
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from flask import Flask, request
from datetime import datetime

env = os.getenv
DISCORD_TOKEN = env("DISCORD_TOKEN")
TELEGRAM_TOKEN = env("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = env("WEBHOOK_URL")  # e.g. https://discordtele.onrender.com
GUILD_ID = int(env("DISCORD_GUILD_ID"))

# Only these categories will be shown
CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS',
    '🧔 MALE CREATORS  / AGENCY',
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

app = Flask(__name__)

# Discord client setup
discord_intents = Intents.default()
discord_intents.guilds = True
client = discord.Client(intents=discord_intents)

# Telegram bot setup
telegram_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
bot = Bot(token=TELEGRAM_TOKEN)

async def fetch_channels_text():
    guild = client.get_guild(GUILD_ID)
    categories = sorted(
        [c for c in guild.categories if c.name in CATEGORIES_TO_INCLUDE],
        key=lambda c: CATEGORIES_TO_INCLUDE.index(c.name)
    )

    lines = []
    for cat in categories:
        lines.append(f"📦 <b>{cat.name}</b>")
        for ch in cat.text_channels:
            lines.append(f"• {ch.mention}")
        lines.append("")

    # footer with timestamp and refresh prompt
    updated = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
    lines.append(f"<i>Updated on {updated}. Press /refresh to update.</i>")
    return "\n".join(lines)

async def send_channel_list(update: Update, context: ContextTypes.DEFAULT_TYPE, initial=False):
    if initial:
        await update.message.reply_html(
            "👋 Hi there! Type /start or /refresh to receive an up-to-date model list."
        )
    status = "⏳ Fetching Model channels please wait, this could take 2–5 mins…"
    if initial:
        msg = await update.message.reply_text(status)
    else:
        msg = await update._bot.send_message(chat_id=update.effective_chat.id, text="🔄 Refreshing…")

    try:
        text = await fetch_channels_text()
        await msg.edit_text(text, parse_mode='HTML', disable_web_page_preview=True)
    except Exception as e:
        await msg.edit_text(f"❌ Could not fetch channels: {e}")

# Handlers for /start and /refresh
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_channel_list(update, context, initial=True)

async def refresh(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_channel_list(update, context, initial=False)

telegram_app.add_handler(CommandHandler('start', start))
telegram_app.add_handler(CommandHandler('refresh', refresh))

# Flask endpoint for Telegram webhook
@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    asyncio.create_task(telegram_app.process_update(Update.de_json(data, bot)))
    return 'OK'

if __name__ == '__main__':
    # set Telegram webhook
    asyncio.get_event_loop().run_until_complete(bot.set_webhook(WEBHOOK_URL + '/webhook'))

    # start Discord
    @client.event
    async def on_ready():
        print(f"✅ Discord logged in as {client.user} (ID: {client.user.id})")

    # run both Flask and Discord
    discord_task = asyncio.create_task(client.start(DISCORD_TOKEN))
    flask_task = asyncio.create_task(app.run_task(host='0.0.0.0', port=int(os.getenv('PORT', '10000'))))
    asyncio.get_event_loop().run_until_complete(asyncio.gather(discord_task, flask_task))
```
