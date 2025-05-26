#!/usr/bin/env python3
import os
import asyncio
import discord
from discord.utils import get
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
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

# store last batch of message_ids per chat so we can delete on refresh
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
    """Ask Discord for the categories → return list of markdown chunks."""
    guild = discord_client.get_guild(DISCORD_GUILD_ID)
    if not guild:
        return ["❌ Guild not found."]
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
        return ["⚠️ No matching categories found."]
    full = "\n".join(out)
    return split_chunks(full)

async def do_refresh(chat_id: int, ctx: ContextTypes.DEFAULT_TYPE):
    """Clear old messages, send loading msg, then send the listing + footer/buttons."""
    bot = ctx.bot

    # delete previous messages
    if chat_id in last_messages:
        for msg_id in last_messages[chat_id]:
            try:
                await bot.delete_message(chat_id, msg_id)
            except:
                pass
    last_messages[chat_id] = []

    # 1) immediate loading notice
    load = await bot.send_message(
        chat_id=chat_id,
        text="⏳ Loading Model channels please wait, this could take 2–5 mins (we have hundreds)…"
    )
    last_messages[chat_id].append(load.message_id)

    # 2) fetch & send the actual chunks in a pre block
    chunks = await build_channel_listing()
    for idx, chunk in enumerate(chunks):
        header = "" if idx == 0 else "*(continued)*\n"
        msg = await bot.send_message(
            chat_id=chat_id,
            text=f"```\n{header}{chunk}\n```",
            parse_mode="MarkdownV2"
        )
        last_messages[chat_id].append(msg.message_id)

    # 3) footer with last-updated timestamp + buttons
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔄 Refresh", callback_data="refresh"),
        InlineKeyboardButton("💎 Join VIP", url="https://t.me/YourVIPBotPlaceholder")
    ]])
    footer = await bot.send_message(
        chat_id=chat_id,
        text=(
            f"Last updated on {ts}\n\n"
            "If your model isn’t listed yet, buy VIP & let us know which one you want added !"
        ),
        reply_markup=keyboard
    )
    last_messages[chat_id].append(footer.message_id)

# ─── Handlers ───────────────────────────────────────────────────────────────
async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await do_refresh(update.effective_chat.id, ctx)

async def refresh_callback(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await do_refresh(update.effective_chat.id, ctx)

async def help_prompt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 I only understand /start or the 🔄 Refresh button to fetch the model list."
    )

tg_app.add_handler(CommandHandler("start", start_handler))
tg_app.add_handler(CallbackQueryHandler(refresh_callback, pattern="^refresh$"))
tg_app.add_handler(CommandHandler("refresh", start_handler))
tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, help_prompt))
# ────────────────────────────────────────────────────────────────────────────

# ─── Flask webserver for Telegram webhook ─────────────────────────────────
app = Flask(__name__)

@app.route('/', methods=['GET', 'HEAD'])
def home():
    return "🤖 Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(force=True)
    upd  = Update.de_json(data, tg_app.bot)
    tg_app.update_queue.put_nowait(upd)
    return 'OK'
# ────────────────────────────────────────────────────────────────────────────

async def set_webhook():
    await tg_app.bot.set_webhook(WEBHOOK_URL)

async def main():
    # start Telegram side
    await tg_app.initialize()
    await tg_app.start()
    await set_webhook()
    # then Discord
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    # bind to Render’s $PORT (default 5000 locally)
    port = int(os.environ.get('PORT', 5000))
    Thread(
        target=lambda: app.run(host='0.0.0.0', port=port, debug=False),
        daemon=True
    ).start()
    asyncio.run(main())
