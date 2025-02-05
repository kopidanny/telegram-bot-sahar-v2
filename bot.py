from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
CallbackContext
import os
from dotenv import load_dotenv

# טוען את ה-Token מקובץ .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

def start(update: Update, context: CallbackContext):
    update.message.reply_text("שלח לי פעולה")

def save_action(update: Update, context: CallbackContext):
    text = update.message.text
    update.message.reply_text(f"הפעולה '{text}' נשמרה!")

updater = Updater(TOKEN)
dp = updater.dispatcher
dp.add_handler(CommandHandler("start", start))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, 
save_action))

updater.start_polling()
updater.idle()

