import os
import asyncio
import discord
from discord.utils import get
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from flask import Flask, request
from threading import Thread
from datetime import datetime

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

# only these categories will be fetched
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
# ────────────────────────────────────────────────────────────────────────────

# ─── Discord client ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ─── Telegram app ──────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────

def split_chunks(text: str, limit: int = 4000):
    """Split a long string into Telegram-safe chunks (≤ limit chars), by line."""
    lines = text.splitlines(keepends=True)
    chunks = []
    current = ""
    for line in lines:
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks

async def delete_previous(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    ids = ctx.user_data.get('last_message_ids', [])
    for msg_id in ids:
        try:
            await ctx.bot.delete_message(chat_id, msg_id)
        except:
            pass
    ctx.user_data['last_message_ids'] = []

async def fetch_and_send_channels(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Fetch only desired categories, then send as markdown in safe-sized chunks."""
    sent_ids = []
    try:
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            m = await update.message.reply_text("❌ Guild not found.")
            sent_ids.append(m.message_id)
            return sent_ids

        out = []
        for cat_name in CATEGORIES_TO_INCLUDE:
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            out.append(f"*{cat_name}*")
            for ch in cat.text_channels:
                out.append(f"• `{ch.name}`")
            out.append("")

        if not out:
            m = await update.message.reply_text("⚠️ No matching categories found.")
            sent_ids.append(m.message_id)
            return sent_ids

        full = "\n".join(out)
        for i, chunk in enumerate(split_chunks(full)):
            prefix = "*(continued)*\n" if i>0 else ""
            m = await update.message.reply_markdown(prefix + chunk)
            sent_ids.append(m.message_id)

    except Exception as e:
        m = await update.message.reply_text(f"❌ Could not fetch channels: {e}")
        sent_ids.append(m.message_id)

    return sent_ids

# /start
