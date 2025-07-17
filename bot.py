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
from gspread.exceptions import SpreadsheetNotFound

# ---- Load environment variables ----
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
GOOGLE_SHEET_NAME  = os.getenv("GOOGLE_SHEET_NAME", "").strip()
RAW_CREDS_JSON     = os.getenv("GOOGLE_CREDENTIALS_JSON", "").strip()
CREDS_JSON_BASE64  = os.getenv("GOOGLE_CREDENTIALS_JSON_BASE64", "").strip()

# ---- Logging configuration ----
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# ---- Debug environment variables ----
logger.debug("Token after strip: %r", TELEGRAM_BOT_TOKEN)
logger.debug("Sheet name after strip: %r", GOOGLE_SHEET_NAME)

# ---- Validate required environment variables ----
missing = []
if not TELEGRAM_BOT_TOKEN:
    missing.append("TELEGRAM_BOT_TOKEN")
if not GOOGLE_SHEET_NAME:
    missing.append("GOOGLE_SHEET_NAME")
if not (RAW_CREDS_JSON or CREDS_JSON_BASE64):
    missing.append("GOOGLE_CREDENTIALS_JSON or GOOGLE_CREDENTIALS_JSON_BASE64")
if missing:
    logger.error("Missing env var(s): %s", missing)
    raise RuntimeError("Missing env var(s): " + ", ".join(missing))

# ---- Decode credentials ----
try:
    if RAW_CREDS_JSON:
        creds_content = RAW_CREDS_JSON
        logger.info("Using raw JSON credentials")
    else:
        creds_content = base64.b64decode(CREDS_JSON_BASE64).decode("utf-8")
        logger.info("Decoded Base64 JSON credentials")
    logger.debug("Creds content start: %r", creds_content[:200])
    creds_dict = json.loads(creds_content)
    logger.info("Parsed JSON credentials successfully")
except Exception:
    logger.exception("Failed to load credentials JSON")
    raise

# ---- Google Sheets setup ----
scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive",
]
creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
client = gspread.authorize(creds)

# ---- Debug: list visible spreadsheets ----
try:
    files = client.list_spreadsheet_files()
    names = [f.get('name') for f in files]
    logger.debug("Visible spreadsheets via service account: %s", names)
except Exception:
    logger.exception("Error listing spreadsheets")

# ---- Open spreadsheet, with fallback by ID ----
try:
    worksheet = client.open(GOOGLE_SHEET_NAME).sheet1
    logger.info("Opened spreadsheet by name: %s", GOOGLE_SHEET_NAME)
except SpreadsheetNotFound:
    logger.warning("Could not open by name, trying by ID lookup")
    matches = [f for f in files if f.get('name') == GOOGLE_SHEET_NAME]
    if not matches:
        logger.error("No matching spreadsheet found for %r", GOOGLE_SHEET_NAME)
        raise
    sheet_id = matches[0].get('id')
    logger.info("Found spreadsheet ID %s, opening by key", sheet_id)
    worksheet = client.open_by_key(sheet_id).sheet1

# ---- Price list ----
PRICE_LIST = {
    "עקירה": 150,
    "שתל": 500,
    "הרמת סינוס פתוחה": 750,
    "הרמת סינוס סגורה": 300,
}

# ---- Bot handlers ----
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלח לי פעולה לדוגמה: 3 שתלים")

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
        await update.message.reply_text("פורמט שגוי. נסה: 2 שתלים")

async def summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user.username or "unknown"
    records = worksheet.get_all_records()
    count = sum(r.get("quantity", 0) for r in records if r.get("username") == user)
    amount = sum(r.get("total",    0) for r in records if r.get("username") == user)
    await update.message.reply_text(
        f"סיכום עבור {user}:\nסה\"כ פעולות: {count}\nסה\"כ זיכוי: {amount} ש\"ח"
    )

# ---- Main function ----
def main():
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("summary", summary))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, save_action))
    logger.info("Bot started polling")
    app.run_polling()

if __name__ == "__main__":
    main()
