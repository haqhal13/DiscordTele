import os
import logging
import datetime
import asyncio
from dotenv import load_dotenv
import discord
from discord import Intents
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment variables
load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GUILD_ID = int(os.getenv("DISCORD_GUILD_ID", 0))
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # e.g. https://your-render-app.onrender.com/webhook

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

# Discord client setup
tokens_intents = Intents.default()
tokens_intents.guilds = True

discord_client = discord.Client(intents=tokens_intents)

# Categories to include
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

async def fetch_channels_text() -> str:
    """
    Fetch and format the channels from Discord according to the included categories.
    """
    guild = discord_client.get_guild(GUILD_ID)
    if guild is None:
        raise RuntimeError("Guild not found")

    channels = guild.channels
    by_category = {}
    for ch in channels:
        # Only keep text channels
        if not isinstance(ch, discord.TextChannel):
            continue
        cat_name = ch.category.name if ch.category else "Uncategorized"
        if cat_name not in CATEGORIES_TO_INCLUDE:
            continue
        by_category.setdefault(cat_name, []).append(ch.name)

    lines = []
    for cat in CATEGORIES_TO_INCLUDE:
        names = by_category.get(cat)
        if not names:
            continue
        lines.append(f"<b>📦 {cat}</b>")
        for name in sorted(names):
            lines.append(f"• <code>{name}</code>")
        lines.append("")  # blank line after each category

    now = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"<i>Updated on {now}</i>")
    lines.append("
Press /refresh to update the list.")
    return "\n".join(lines)

async def send_model_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Delete any previously sent list, post a loading message, fetch channels, then replace with the real list.
    """
    chat_id = update.effective_chat.id
    # Delete the old list if it exists
    last_msg = context.user_data.get('last_list_msg_id')
    if last_msg:
        try:
            await context.bot.delete_message(chat_id, last_msg)
        except Exception:
            pass

    # Send loading notice
    loading = await context.bot.send_message(chat_id, 
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…")

    try:
        text = await fetch_channels_text()
        msg = await context.bot.send_message(chat_id, text, parse_mode="HTML")
        # Save which message to delete next time
        context.user_data['last_list_msg_id'] = msg.message_id
    except Exception as e:
        await context.bot.send_message(chat_id, f"❌ Could not fetch channels: {e}")
    finally:
        # Remove the loading message
        try:
            await context.bot.delete_message(chat_id, loading.message_id)
        except Exception:
            pass

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Greet the user and immediately fetch & send the model list.
    """
    await update.message.reply_text(
        "👋 Hi there! Type /start or /refresh to receive an up-to-date model list.")
    await send_model_list(update, context)

async def refresh_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Explicitly refresh the model list.
    """
    await update.message.reply_text("🔄 Refreshing…")
    await send_model_list(update, context)

async def run_discord_client():
    await discord_client.start(DISCORD_TOKEN)

def main():
    # Launch Discord client in background
    loop = asyncio.get_event_loop()
    loop.create_task(run_discord_client())

    # Build Telegram application
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("refresh", refresh_command))

    # Start webhook listener
    app.run_webhook(listen="0.0.0.0",
                    port=int(os.getenv("PORT", 10000)),
                    url_path="webhook",
                    webhook_url=WEBHOOK_URL)

if __name__ == '__main__':
    main()
