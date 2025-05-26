#!/usr/bin/env python3
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

import discord
from discord import Intents

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

# ─── Config & Logging ─────────────────────────────────────────────────────────

load_dotenv()
DISCORD_TOKEN   = os.environ["DISCORD_TOKEN"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL     = os.environ["WEBHOOK_URL"]    # e.g. https://your-domain.com
GUILD_ID        = int(os.environ["GUILD_ID"])  # your Discord guild ID

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

_last_messages: dict[int, list[int]] = {}

# ─── Discord Client Setup ────────────────────────────────────────────────────

intents = Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)

async def fetch_model_list() -> str:
    guild = discord_client.get_guild(GUILD_ID)
    if guild is None:
        await discord_client.wait_until_ready()
        guild = discord_client.get_guild(GUILD_ID)
    lines: list[str] = []
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"*Model channels list (updated {ts})*\n")
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

# ─── Telegram Helpers ────────────────────────────────────────────────────────

async def _delete_old(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    if chat_id in _last_messages:
        for msg_id in _last_messages[chat_id]:
            try:
                await context.bot.delete_message(chat_id, msg_id)
            except:
                pass
        _last_messages.pop(chat_id, None)

async def _send_list(chat_id: int, context: ContextTypes.DEFAULT_TYPE):
    text = await fetch_model_list()
    parts, curr = [], ""
    for line in text.split("\n"):
        if len(curr) + len(line) + 1 > 4000:
            parts.append(curr); curr = line + "\n"
        else:
            curr += line + "\n"
    if curr: parts.append(curr)

    await _delete_old(chat_id, context)
    sent_ids: list[int] = []
    for part in parts:
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=part,
            parse_mode="MarkdownV2",
            disable_web_page_preview=True,
        )
        sent_ids.append(msg.message_id)

    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    footer = await context.bot.send_message(
        chat_id=chat_id,
        text=(
            f"Our list is above (updated {ts}).\n"
            "Press /refresh to get the latest."
        ),
    )
    sent_ids.append(footer.message_id)
    _last_messages[chat_id] = sent_ids

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(
        chat_id=chat_id,
        text="👋 Hi there! Type /start or /refresh to receive an up-to-date model list."
    )
    await context.bot.send_message(
        chat_id=chat_id,
        text="⏳ Fetching Model channels, please wait—this could take 2–5 mins…"
    )
    await _send_list(chat_id, context)

async def refresh_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await context.bot.send_message(chat_id=chat_id, text="🔄 Refreshing…")
    await _send_list(chat_id, context)

# ─── Bootstrap & Run ────────────────────────────────────────────────────────

async def main():
    asyncio.create_task(discord_client.start(DISCORD_TOKEN))

    app = (ApplicationBuilder()
           .token(TELEGRAM_TOKEN)
           .build())
    app.add_handler(CommandHandler("start",   start_cmd))
    app.add_handler(CommandHandler("refresh", refresh_cmd))

    # point Telegram at our webhook endpoint
    await app.bot.set_webhook(WEBHOOK_URL + "/webhook")

    # run the webhook listener—note `url_path`, not `webhook_path`
    await app.run_webhook(
        listen="0.0.0.0",
        port=int(os.environ.get("PORT", 8443)),
        url_path="/webhook",
    )

if __name__ == "__main__":
    asyncio.run(main())
