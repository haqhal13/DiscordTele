import os
import threading
from datetime import datetime
from flask import Flask, request
import discord
from discord import Intents
from telegram import Bot, Update
from telegram.ext import CommandHandler, CallbackContext
from telegram.ext.dispatcher import Dispatcher

# ─── Configuration ─────────────────────────────────────────────────────────────

DISCORD_TOKEN   = os.environ["DISCORD_TOKEN"]
TELEGRAM_TOKEN  = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL     = os.environ["WEBHOOK_URL"]   # e.g. https://myapp.example.com
GUILD_ID        = int(os.environ["GUILD_ID"])
PORT            = int(os.environ.get("PORT", "10000"))

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

# ─── Discord client ────────────────────────────────────────────────────────────

intents = Intents.default()
intents.guilds = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    print(f"✅ Discord logged in as {discord_client.user}")

# ─── Telegram setup ─────────────────────────────────────────────────────────────

bot        = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, 0)   # v20: import from telegram.ext.dispatcher

app        = Flask(__name__)
last_list  = {}  # chat_id → message_id

def fetch_and_send(chat_id):
    # delete old
    old = last_list.get(chat_id)
    if old:
        try: bot.delete_message(chat_id, old)
        except: pass

    guild = discord_client.get_guild(GUILD_ID)
    if not guild:
        bot.send_message(chat_id, "❌ Guild not found.")
        return

    parts = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    parts.append(f"📅 <b>Updated:</b> {now}\n")
    for name in CATEGORIES_TO_INCLUDE:
        cat = discord.utils.get(guild.categories, name=name)
        if not cat: continue
        emoji = name.split()[0]
        parts.append(f"{emoji} <b>{name[len(emoji)+1:]}:</b>")
        for ch in cat.channels:
            if isinstance(ch, discord.TextChannel):
                parts.append(f"• {emoji}|<code>{ch.name}</code>")
        parts.append("")

    parts.append("Press <b>/refresh</b> to update again.")
    text = "\n".join(parts)

    # split if >4k chars
    for chunk in (text[i:i+3900] for i in range(0, len(text), 3900)):
        msg = bot.send_message(chat_id, chunk, parse_mode="HTML")
    last_list[chat_id] = msg.message_id

def cmd_start(update: Update, context: CallbackContext):
    cid = update.effective_chat.id
    bot.send_message(
        cid,
        "👋 Hi there! Type <b>/start</b> or <b>/refresh</b> to get an up-to-date model list.",
        parse_mode="HTML"
    )
    bot.send_message(
        cid,
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…",
        parse_mode="HTML"
    )
    threading.Thread(target=fetch_and_send, args=(cid,), daemon=True).start()

def cmd_refresh(update: Update, context: CallbackContext):
    cid = update.effective_chat.id
    bot.send_message(cid, "🔄 Refreshing…", parse_mode="HTML")
    threading.Thread(target=fetch_and_send, args=(cid,), daemon=True).start()

dispatcher.add_handler(CommandHandler("start",   cmd_start))
dispatcher.add_handler(CommandHandler("refresh", cmd_refresh))

@app.route("/webhook", methods=["POST"])
def webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK"

if __name__ == "__main__":
    # set telegram webhook
    bot.delete_webhook()
    bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    # run flask in background, then discord
    threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=PORT),
        daemon=True
    ).start()

    discord_client.run(DISCORD_TOKEN)
