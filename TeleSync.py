import os
import asyncio
import discord
from discord.utils import get
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from flask import Flask, request, abort

# ── CONFIG ─────────────────────────────────────────────────────────────────
DISCORD_TOKEN    = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN   = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL      = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

CATEGORIES_TO_INCLUDE = [
    '📦 ETHNICITY VAULTS',
    # … your other  items …
    '🔞 PORN',
    'Uncatagorised Girls'
]
# ────────────────────────────────────────────────────────────────────────────

# ── Discord client ─────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds   = True
intents.messages = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ── Telegram app ────────────────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────


async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Getting up to date list please wait 2–5 mins…"
    )
    await update.message.reply_text(
        "⏳ Fetching Model channels please wait, this could take 2–5 mins as we have hundreds…"
    )

    try:
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            return await update.message.reply_text("❌ Guild not found.")

        lines = []
        for cat_name in CATEGORIES_TO_INCLUDE:
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            lines.append(f"*{cat_name}*")
            for ch in cat.text_channels:
                lines.append(f"• {ch.name}")
            lines.append("")

        if not lines:
            await update.message.reply_text("⚠️ No matching categories.")
        else:
            text = "\n".join(lines).strip()
            await update.message.reply_markdown(text)

    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch channels: {e}")

tg_app.add_handler(CommandHandler("start", start_handler))


# ── HTTP server ────────────────────────────────────────────────────────────
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
    await set_webhook()
    await discord_client.start(DISCORD_TOKEN)

if __name__ == '__main__':
    from threading import Thread
    Thread(target=lambda: app.run(host='0.0.0.0',
                                 port=int(os.environ.get('PORT',10000)))).start()
    asyncio.run(main())
