import logging
import os
import datetime
import json

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEET_NAME = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_JSON = os.getenv("GOOGLE_CREDENTIALS_JSON")

# Price list
PRICE_LIST = {
    "שתל": 500,
    "עקירה": 150,
    "הרמת סינוס פתוחה": 750,
    "הרמת סינוס סגורה": 300
}

# Google Sheets setup
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
creds_dict = json.loads(GOOGLE_CREDENTIALS_JSON)
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
sheet = client.open(GOOGLE_SHEET_NAME).sheet1

# Bot commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("היי! שלח לי פעולה (למשל: '3 שתל') ואני אשמור אותה!")

async def save_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = update.effective_user.username or update.effective_user.first_name
    date = datetime.datetime.today().strftime("%Y-%m-%d")

    found = False
    for action, price in PRICE_LIST.items():
        if action in text:
            try:
                qty = int(text.split()[0])
                amount = qty * price
                sheet.append_row([str(date), username, action, qty, amount])
                await update.message.reply_text(f"הוספתי: {qty} × {action} = {amount} ש\"ח ✅")
                found = True
                break
            except Exception as e:
                logger.error(f"Error parsing text: {e}")
                await update.message.reply_text("בעיה בקריאת הפעולה. נסה שוב בפורמט: 3 שתל")
                return

    if not found:
        await update.message.reply_text("לא זיהיתי את סוג הפעולה. נסה משהו כמו: 2 עקירה")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("השתמש כך: /summary daily | weekly | monthly")
        return

    period = args[0].lower()
    today = datetime.date.today()

    if period == "daily":
        start_date = today
        title = "סיכום יומי"
    elif period == "weekly":
        start_date = today - datetime.timedelta(days=7)
        title = "סיכום שבועי"
    elif period == "monthly":
        start_date = today - datetime.timedelta(days=30)
        title = "סיכום חודשי"
    else:
        await update.message.reply_text("בחר רק: daily, weekly, monthly")
        return

    try:
        data = sheet.get_all_values()[1:]  # skip header
        total_amount = 0
        action_count = {}

        for row in data:
            try:
                row_date = datetime.datetime.strptime(row[0], "%Y-%m-%d").date()
                if row_date >= start_date:
                    action = row[2]
                    qty = int(row[3])
                    amount = int(row[4])
                    total_amount += amount
                    action_count[action] = action_count.get(action, 0) + qty
            except:
                continue

        result = f"*{title}*\n"
        for action, qty in action_count.items():
            result += f"- {action}: {qty} פעמים\n"
        result += f"\nסה\"כ לתשלום: {total_amount} ש\"ח"

        await update.message.reply_text(result, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"Error generating summary: {e}")
        await update.message.reply_text("אירעה שגיאה. נסה שוב מאוחר יותר.")

# Run bot
def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("summary", summary))
    applica
