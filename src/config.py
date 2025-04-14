import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Google Sheets Configuration
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')  # Optional: Sheet ID can be used instead of name

# Google API Scopes
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]