import os
import threading
from datetime import datetime
from flask import Flask, request
import discord
from discord import Intents
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler, CallbackContext

# ─── Configuration ─────────────────────────────────────────────────────────────

DISCORD_TOKEN   = os.environ["DISCORD_TOKEN"]
TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
WEBHOOK_URL     = os.environ["WEBHOOK_URL"]  # e.g. https://myapp.example.com
GUILD_ID        = int(os.environ["GUILD_ID"])
PORT            = int(os.environ.get("PORT", "10000"))

# Only these categories will be included
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
dispatcher = Dispatcher(bot, update_queue=None, use_context=True)
app        = Flask(__name__)

# Keep track of the last list message per chat so we can delete it
last_list_message = {}

def fetch_and_send_list(chat_id: int, context: CallbackContext):
    """Fetches the filtered channels and sends (after deleting old)."""
    # delete previous list
    old_id = last_list_message.get(chat_id)
    if old_id:
        try:
            bot.delete_message(chat_id, old_id)
        except:
            pass

    guild = discord_client.get_guild(GUILD_ID)
    if not guild:
        bot.send_message(chat_id, "❌ Could not find configured guild.")
        return

    lines = []
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    lines.append(f"📅 <b>Updated:</b> {now}\n")

    for cat_name in CATEGORIES_TO_INCLUDE:
        category = discord.utils.get(guild.categories, name=cat_name)
        if not category:
            continue

        # e.g. emoji = '📦'
        emoji = cat_name.split()[0]
        # header: 📦 ETHNICITY VAULTS:
        lines.append(f"{emoji} <b>{cat_name[len(emoji)+1:]}:</b>")
        for ch in category.channels:
            if isinstance(ch, discord.TextChannel):
                # • 📦|channel-name
                lines.append(f"• {emoji}|<code>{ch.name}</code>")
        lines.append("")  # blank line

    lines.append("Press <b>/refresh</b> to update again.")
    full = "\n".join(lines)

    # Telegram max length ~4096; split if needed
    parts = [full[i:i+3900] for i in range(0, len(full), 3900)]
    msg = None
    for part in parts:
        msg = bot.send_message(chat_id, part, parse_mode="HTML")
    if msg:
        last_list_message[chat_id] = msg.message_id

def start(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    # On first /start or webhook hit, greet
    bot.send_message(chat_id,
        "👋 Hi there! Type <b>/start</b> or <b>/refresh</b> to receive an up-to-date model list.",
        parse_mode="HTML"
    )
    # Immediately fetch & send
    bot.send_message(chat_id,
        "⏳ Fetching Model channels please wait, this could take 2–5 mins…",
        parse_mode="HTML"
    )
    threading.Thread(target=fetch_and_send_list, args=(chat_id, context), daemon=True).start()

def refresh(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    bot.send_message(chat_id, "🔄 Refreshing…", parse_mode="HTML")
    threading.Thread(target=fetch_and_send_list, args=(chat_id, context), daemon=True).start()

dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(CommandHandler("refresh", refresh))

# ─── Flask webhook route ───────────────────────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True)
    update = Update.de_json(data, bot)
    dispatcher.process_update(update)
    return "OK"

# ─── Entrypoint ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    # make sure Telegram is using our webhook
    bot.delete_webhook()
    bot.set_webhook(f"{WEBHOOK_URL}/webhook")

    # Run Flask in a thread, then start Discord client
    threading.Thread(target=lambda: app.run(host="0.0.0.0", port=PORT), daemon=True).start()
    discord_client.run(DISCORD_TOKEN)
