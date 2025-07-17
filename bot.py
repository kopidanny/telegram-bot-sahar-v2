import os
import json
import base64
import logging
import datetime
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Load environment variables
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GOOGLE_SHEET_NAME   = os.getenv("GOOGLE_SHEET_NAME")
GOOGLE_CREDENTIALS_B64 = os.getenv("GOOGLE_CREDENTIALS_JSON_BASE64", "")

# Validate required environment variables
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("Missing TELEGRAM_BOT_TOKEN env var")
if not GOOGLE_SHEET_NAME:
    raise RuntimeError("Missing GOOGLE_SHEET_NAME env var")
if not GOOGLE_CREDENTIALS_B64:
    raise RuntimeError("Missing GOOGLE_CREDENTIALS_JSON_BASE64 env var")

# Decode and parse Google credentials from Base64
try:
    creds_json = base64.b64decode(GOOGLE_CREDENTIALS_B64)
    creds_dict = json.loads(creds_json)
    logging.info("Loaded Google credentials from Base64")
except Exception as e:
    raise RuntimeError("Invalid Base64 JSON in GOOGLE_CREDENTIALS_JSON_BASE64") from e

# Logging configuration
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Google Sheets setup
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)
worksheet = client.open(GOOGLE_SHEET_NAME).sheet1

# Price list
PRICE_LIST = {
    "עקירה": 150,
    "שתל": 500,
    "הרמת סינוס פתוחה": 750,
    "הרמת סינוס סגורה": 300,
}

# Bot handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלח לי פעולה לדוגמה: 3 שתלים")

async def save_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    username = update.message.from_user.username or "unknown"
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    try:
        qty_str, action_name = text.split(" ", 1)
        quantity = int(qty_str)
        price = PRICE_LIST.get(action_name.strip())
        if price is None:
            await update.message.reply_text(
                "לא מצאתי את סוג הפעולה. נסה: עקירה, שתל, הרמת סינוס פתוחה/סגורה."
            )
            return
        total = quantity * price
        worksheet.append_row([date, username, action_name, quantity, price, total])
        await update.message.reply_text(f"שמרתי {quantity}x {action_name} = {total} ש\"ח")
    except Exception:
        logger.exception("Error saving action")
        await update.message.reply_text("פורמט שגוי. נסה: 2 שתלים")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username or "unknown"
    records = worksheet.get_all_records()
    count = 0
    amount = 0
    for row in records:
        if row.get("username") == user:
            count += row.get("quantity", 0)
            amount += row.get("total", 0)
    await update.message.reply_text(
        f"סיכום עבור {user}:\nסה\"כ פעולות: {count}\nסה\"כ זיכוי: {amount} ש\"ח"
    )

def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_action))
    logger.info("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()
