#!/usr/bin/env python3
import os
import asyncio
import logging
from datetime import datetime
from threading import Thread

import discord
from discord.utils import get
from flask import Flask, request
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, error as tg_error
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# ─── LOGGING CONFIG ─────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
    level=logging.DEBUG
)
logger = logging.getLogger("TeleSync")
# ────────────────────────────────────────────────────────────────────────────

# ─── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

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

# ─── DISCORD CLIENT ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ─── TELEGRAM APP ──────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────

# track last batch of messages per chat for deletion
last_messages = {}

def split_chunks(text: str, limit: int = 4000):
    lines = text.splitlines(keepends=True)
    chunks, current = [], ""
    for line in lines:
        if len(current) + len(line) > limit:
            chunks.append(current)
            current = line
        else:
            current += line
    if current:
        chunks.append(current)
    return chunks

async def build_channel_listing():
    logger.debug("Building channel listing from Discord guild %s", DISCORD_GUILD_ID)
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        logger.error("Discord guild not found")
        return ["❌ Guild not found."]
    out = []
    for cat_name in CATEGORIES_TO_INCLUDE:
        cat = get(guild.categories, name=cat_name)
        if not cat:
            logger.debug("Category missing: %s", cat_name)
            continue
        out.append(f"*{cat_name}*")
        for ch in cat.text_channels:
            out.append(f"• `{ch.name}`")
        out.append("")
    if not out:
        logger.warning("No matching categories found")
        return ["⚠️ No matching categories found."]
    full = "\n".join(out)
    logger.debug("Total characters in listing: %d", len(full))
    return split_chunks(full)

async def do_refresh(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    bot = ctx.bot
    logger.info("Refreshing for chat_id=%s", chat_id)

    # delete old messages
    to_delete = last_messages.get(chat_id, [])
    logger.debug("Deleting %d old messages", len(to_delete))
    for msg_id in to_delete:
        try:
            await bot.delete_message(chat_id, msg_id)
        except Exception as e:
            logger.warning("Failed deleting msg %s: %s", msg_id, e)
    last_messages[chat_id] = []

    # 1) immediate loading notice
    logger.debug("Sending loading message")
    load = await bot.send_message(
        chat_id=chat_id,
        text="⏳ Loading Model channels please wait, this could take 2–5 mins (we have hundreds)…"
    )
    last_messages[chat_id].append(load.message_id)

    # 2) actual list in triple-backtick blocks
    chunks = await build_channel_listing()
    for idx, chunk in enumerate(chunks):
        header = "" if idx == 0 else "*(continued)*\n"
        try:
            msg = await bot.send_message(
                chat_id=chat_id,
                text=f"```\n{header}{chunk}\n```",
                parse_mode="MarkdownV2"
            )
            last_messages[chat_id].append(msg.message_id)
            logger.debug("Sent chunk %d/%d", idx+1, len(chunks))
        except Exception as e:
            logger.error("Failed sending chunk %d: %s", idx, e)

    # 3) footer with timestamp + buttons
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        InlineKeyboardButton("💎 Join VIP", url="https://t.me/YourVIPBotPlaceholder")
    ]])
    logger.debug("Sending footer with timestamp %s", ts)
    footer = await bot.send_message(
        chat_id=chat_id,
        text=(
            f"Last updated on {ts}\n\n"
            "If your model isn’t listed yet, buy VIP & let us know which one you want added !"
        ),
        reply_markup=keyboard
    )
    last_messages[chat_id].append(footer.message_id)

# ─── TELEGRAM HANDLERS ────────────────────────────────────────────────────
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info("Received /start from chat_id=%s", chat_id)
    await do_refresh(chat_id, ctx)

async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    logger.info("CallbackQuery refresh from chat_id=%s", chat_id)
    try:
        await update.callback_query.answer()
    except tg_error.BadRequest as e:
        logger.warning("CallbackQuery.answer failed: %s", e)
        await update.effective_message.reply_text(
            "🔄 Refresh timed out—please send /start instead."
        )
        return
    await do_refresh(chat_id, ctx)

async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    logger.debug("Unknown message, sending help prompt")
    await update.message.reply_text(
        "🤖 I only understand /start or the 🔄 Refresh button to fetch the model list."
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(CommandHandler("refresh", start_handler))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))
# ────────────────────────────────────────────────────────────────────────────

# ─── FLASK WEBHOOK ─────────────────────────────────────────────────────────
app = Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def home():
    logger.debug("Health check")
    return "🤖 Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    logger.debug("Webhook received: %s", data)
    upd = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put_nowait(upd)
    return 'OK'
# ────────────────────────────────────────────────────────────────────────────

async def set_webhook():
    logger.info("Setting Telegram webhook to %s", WEBHOOK_URL)
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    logger.info("Initializing Telegram app")
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    logger.info("Starting Discord client")
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info("Launching Flask on port %d", port)
    Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    asyncio.run(main())
