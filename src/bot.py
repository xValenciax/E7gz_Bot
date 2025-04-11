import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import TELEGRAM_TOKEN, GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, GOOGLE_SCOPES
from logger import setup_logger

# Setup logging
logger = setup_logger()

# Google Sheets setup
try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE,
        GOOGLE_SCOPES
    )
    gc = gspread.authorize(credentials)
    sheet = gc.open(GOOGLE_SHEET_NAME).sheet1
    logger.info('Successfully connected to Google Sheets')
except Exception as e:
    logger.error(f'Failed to connect to Google Sheets: {str(e)}')
    raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        welcome_message = f'Hello {user.first_name}! I am your Telegram bot integrated with Google Sheets.\n'
        welcome_message += 'Available commands:\n'
        welcome_message += '/add item value - Add a new item with value\n'
        welcome_message += '/view - View all data in the sheet'
        
        await update.message.reply_text(welcome_message)
        logger.info(f'Start command used by user {user.id}')
    except Exception as e:
        logger.error(f'Error in start command: {str(e)}')
        await update.message.reply_text('An error occurred while processing your request.')

async def add_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        data = context.args
        
        if len(data) >= 2:
            item = data[0]
            value = data[1]
            # Append to the next empty row
            sheet.append_row([item, value])
            response = f'Added {item}: {value} to the sheet!'
            logger.info(f'User {user.id} added data: {item}: {value}')
        else:
            response = 'Please use format: /add item value'
            logger.warning(f'User {user.id} attempted to add data with invalid format')
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f'Error in add_data command: {str(e)}')
        await update.message.reply_text('An error occurred while adding data to the sheet.')

async def view_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        values = sheet.get_all_values()
        
        if values:
            response = "Here's your data:\n"
            for row in values:
                response += f"{' | '.join(row)}\n"
            logger.info(f'User {user.id} viewed data')
        else:
            response = 'No data found in the sheet.'
            logger.info(f'User {user.id} attempted to view empty sheet')
        
        await update.message.reply_text(response)
    except Exception as e:
        logger.error(f'Error in view_data command: {str(e)}')
        await update.message.reply_text('An error occurred while retrieving data from the sheet.')

def main():
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add command handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("add", add_data))
        application.add_handler(CommandHandler("view", view_data))

        logger.info('Bot started successfully')
        # Start the bot
        application.run_polling()
    except Exception as e:
        logger.error(f'Failed to start bot: {str(e)}')
        raise

if __name__ == '__main__':
    main()