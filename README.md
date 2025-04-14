# E7gz Bot

A Telegram bot integrated with Google Sheets for easy data management and retrieval.

## Overview

E7gz Bot is a Telegram bot that allows users to interact with Google Sheets directly from Telegram. Users can add data to a Google Sheet and view the contents of the sheet through simple commands.

## Features

- **Google Sheets Integration**: Seamlessly connects to Google Sheets API to store and retrieve data
- **Data Management**: Add new entries to the Google Sheet with a simple command
- **Data Retrieval**: View all data stored in the connected Google Sheet
- **Logging System**: Comprehensive logging for monitoring bot activities and troubleshooting

## Commands

- `/start` - Initiates the bot and displays available commands
- `/add item value` - Adds a new item with the specified value to the Google Sheet
- `/view` - Displays all data currently stored in the Google Sheet

## Technical Details

### Requirements

- Python 3.7+
- python-telegram-bot 20.6
- gspread 5.12.0
- oauth2client 4.1.3
- python-dotenv 1.0.0

### Configuration

The bot requires the following environment variables to be set in a `.env` file:

```
# Telegram Bot Configuration
TELEGRAM_TOKEN=your_telegram_bot_token

# Google Sheets Configuration
GOOGLE_CREDENTIALS_FILE=path_to_your_google_credentials_json
GOOGLE_SHEET_NAME=your_google_sheet_name
```

### Project Structure

```
Root/
├── requirements.txt      # Python dependencies
├── README.md            # Project documentation
└── src/
    ├── .env             # Environment variables (not tracked in git)
    ├── .env.example     # Example environment file
    ├── bot.py           # Main bot implementation
    ├── config.py        # Configuration loader
    └── logger.py        # Logging setup
```

## Setup and Installation

1. Clone this repository
2. Install dependencies: `pip install -r requirements.txt`
3. Create a `.env` file based on `.env.example` with your credentials
4. Run the bot: `python src/bot.py`

## Google Sheets Setup

1. Create a project in Google Cloud Console
2. Enable Google Sheets API and Google Drive API
3. Create a service account and download the JSON credentials file
4. Share your Google Sheet with the service account email
5. Update the `.env` file with the path to your credentials file and either:
   - The name of your Google Sheet (GOOGLE_SHEET_NAME), or
   - The ID of your Google Sheet (GOOGLE_SHEET_ID) - this is the long string in the sheet URL

## License

This project is licensed under the MIT License - see the LICENSE file for details.