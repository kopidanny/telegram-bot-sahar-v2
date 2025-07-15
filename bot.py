import os
import logging
import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from dotenv import load_dotenv

# הגדרות לוגים
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# טוען משתני סביבה
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_CREDENTIALS_FILE = os.getenv("GOOGLE_CREDENTIALS_FILE")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")

# מחירון
PRICE_LIST = {
    "עקירה": 150,
    "שתל": 500,
    "הרמת סינוס פתוחה": 750,
    "הרמת סינוס סגורה": 300
}

# חיבור ל-Google Sheets
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDENTIALS_FILE, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

# פקודת /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלח לי פעולה (למשל: '2 שתלים') ואני אשמור אותה עם זיכוי.")

# שמירת פעולה
async def save_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = update.message.from_user.username
    date = datetime.datetime.now().strftime("%Y-%m-%d")

    try:
        amount, action = text.split(" ", 1)
        amount = int(amount)
        price = PRICE_LIST.get(action.strip())

        if price is None:
            await update.message.reply_text("סוג פעולה לא מוכר. נסה: עקירה, שתל, הרמת סינוס פתוחה/סגורה.")
            return

        total = price * amount
        sheet.append_row([date, username, action, amount, price, total])
        await update.message.reply_text(f"הפעולה נשמרה ✅\n{amount} {action} = {total} ש\"ח")
    except Exception as e:
        logger.error(e)
        await update.message.reply_text("הפורמט לא תקין. נסה לדוגמה: 2 שתלים")

# בניית הבוט
app = Application.builder().token(TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_action))

# הרצת הבוט
if __name__ == "__main__":
    logger.info("Bot started...")
    app.run_polling()
