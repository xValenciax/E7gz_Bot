import os
from dotenv import load_dotenv
from typing import List

# Load environment variables from .env file
load_dotenv()

# Telegram Bot Configuration
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

# Admin Configuration
# Get admin chat IDs from environment variable (comma-separated list)
ADMIN_CHAT_IDS: List[str] = []
admin_ids_str = os.getenv('ADMIN_CHAT_IDS', '')
if admin_ids_str:
    ADMIN_CHAT_IDS = [chat_id.strip() for chat_id in admin_ids_str.split(',')]

# Google Sheets Configuration
GOOGLE_CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE')
GOOGLE_SHEET_NAME = os.getenv('GOOGLE_SHEET_NAME')
GOOGLE_SHEET_ID = os.getenv('GOOGLE_SHEET_ID')  # Optional: Sheet ID can be used instead of name

# Google API Scopes
GOOGLE_SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]