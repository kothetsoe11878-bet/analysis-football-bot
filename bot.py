import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "⚽ Analysis Football Bot\n\n"
        "Bot is online.\n"
        "Allowed: EPL • La Liga • Serie A • Bundesliga • Ligue 1 • UCL"
    )

app = Application.builder().token(BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))

app.run_polling()
