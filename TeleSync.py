#!/usr/bin/env python3
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

import discord
from discord import Intents
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# Load environment
load_dotenv()
DISCORD_TOKEN = os.environ["DISCORD_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GUILD_ID = int(os.environ["GUILD_ID"])

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

# Store last sent message IDs
_last_messages: dict[int, list[int]] = {}

# Discord client
intents = Intents.default()
intents.guilds = True
intents.messages = False

discord_client = discord.Client(intents=intents)

async def fetch_model_list() -> str:
    """Fetch and format the channel list from Discord."""
    guild = discord_client.get_guild(GUILD_ID)
    if guild is None:
        await discord_client.wait_until_ready()
        guild = discord_client.get_guild(GUILD_ID)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines = [f"*Model channels (updated {ts})*\n"]
    for cat in guild.categories:
        if cat.name not in CATEGORIES_TO_INCLUDE:
            continue
        emoji, _, rest = cat.name.partition(" ")
        lines.append(f"{emoji} *{rest}*")
        for ch in cat.channels:
            if isinstance(ch, discord.TextChannel):
                lines.append(f"• `{ch.name}`")
        lines.append("")
    return "\n".join(lines)

async def _delete_old(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    """Delete previous messages to keep chat clean."""
    ids = _last_messages.pop(chat_id, [])
    for m_id in ids:
        try:
            await ctx.bot.delete_message(chat_id, m_id)
        except:
            pass

async def _send_list(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    text = await fetch_model_list()
    # Split into parts avoiding Telegram limits
    parts, curr = [], ""
    for line in text.split("\n"):
        if len(curr) + len(line) + 1 > 3900:
            parts.append(curr)
            curr = line + "\n"
        else:
            curr += line + "\n"
    if curr:
        parts.append(curr)

    await _delete_old(chat_id, ctx)
    sent_ids = []
    for part in parts:
        msg = await ctx.bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True
        )
        sent_ids.append(msg.message_id)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    footer = await ctx.bot.send_message(
        chat_id=chat_id,
        text=(
            f"Our list is above (updated {ts}).\n"
            "Press /refresh to update."
        )
    )
    sent_ids.append(footer.message_id)
    _last_messages[chat_id] = sent_ids

# Telegram handlers
async def start_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    await ctx.bot.send_message(
        chat_id=cid,
        text=(
            "👋 Hi! Type /start or /refresh to get the latest model list.\n"
            "⏳ Fetching Model channels… this could take 2–5 mins."
        )
    )
    await _send_list(cid, ctx)

async def refresh_cmd(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    cid = update.effective_chat.id
    await ctx.bot.send_message(chat_id=cid, text="🔄 Refreshing list…")
    await _send_list(cid, ctx)

async def main():
    # Start Discord bot in background
    asyncio.create_task(discord_client.start(DISCORD_TOKEN))
    
    # Build and run Telegram polling
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("refresh", refresh_cmd))
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
