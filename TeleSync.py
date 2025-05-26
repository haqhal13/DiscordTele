import os
import asyncio
import discord
from discord.utils import get
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    CommandHandler,
)
from flask import Flask, request, abort

# ── CONFIG ────────────────────────────────────────────────────────────────
DISCORD_TOKEN     = os.environ['DISCORD_TOKEN']
DISCORD_GUILD_ID  = int(os.environ['DISCORD_GUILD_ID'])
TELEGRAM_TOKEN    = os.environ['TELEGRAM_BOT_TOKEN']
WEBHOOK_URL       = os.environ['WEBHOOK_URL'].rstrip('/') + '/webhook'

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

# ── Discord client ─────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.guilds   = True
intents.messages = True
discord_client = discord.Client(intents=intents)
# ────────────────────────────────────────────────────────────────────────────

# ── Telegram application ───────────────────────────────────────────────────
tg_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
# ────────────────────────────────────────────────────────────────────────────


async def start_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    # 1) immediate confirmation
    await update.message.reply_text(
        "👋 Getting up to date list please wait 2–5 mins…"
    )

    # 2) longer-running notice
    await update.message.reply_text(
        "⏳ Fetching Model channels please wait, this could take 2–5 mins as we have hundreds…"
    )

    # 3) actually fetch and reply
    try:
        guild = discord_client.get_guild(DISCORD_GUILD_ID)
        if not guild:
            await update.message.reply_text("❌ Guild not found.")
            return

        lines = []
        for cat_name in CATEGORIES_TO_INCLUDE:
            # find that category object
            cat = get(guild.categories, name=cat_name)
            if not cat:
                continue
            lines.append(f"*{cat_name}*")
            for ch in cat.text_channels:
                lines.append(f"• {ch.name}")
            lines.append("")  # blank line between categories

        if not lines:
            await update.message.reply_text("⚠️ No matching categories found.")
        else:
            text = "\n".join(lines).strip()
            # Use Markdown so the *bold* category names render nicely
            await update.message.reply_markdown(text)
    except Exception as e:
        await update.message.reply_text(f"❌ Could not fetch channels: {e}")


tg_app.add_handler(CommandHandler("start", start_handler))
# ────────────────────────────────────────────────────────────────────────────


# ── Flask webhook receiver ─────────────────────────────────────────────────
app = Flask(__name__)

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    if request.method == 'POST':
        data = request.get_json(force=True)
        update = Update.de_json(data, tg_app.bot)
        # queue it for the telegram dispatcher
        tg_app.update_queue.put_nowait(update)
        return 'OK'
    abort(400)
# ────────────────────────────────────────────────────────────────────────────


async def set_telegram_webhook():
    # await the coroutine so you don't get "never awaited" warnings
    await tg_app.bot.set_webhook(WEBHOOK_URL)


async def run_bots():
    # 1) register webhook
    await set_telegram_webhook()

    # 2) start discord client (this runs forever)
    await discord_client.start(DISCORD_TOKEN)


if __name__ == '__main__':
    # 1) start Flask in a background thread
    from threading import Thread
    Thread(
        target=lambda: app.run(
            host='0.0.0.0',
            port=int(os.environ.get('PORT', 10000)),
            debug=False
        )
    ).start()

    # 2) run Telegram webhook setup + Discord client
    asyncio.run(run_bots())
