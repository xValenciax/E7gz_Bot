# E7gz Bot

A Telegram bot for booking football pitches with Google Sheets integration.

## Overview

E7gz Bot is a Telegram bot that allows users to book football pitches through a simple, interactive conversation flow. The bot integrates with Google Sheets to store pitch information, availability, and manage bookings.

## Features

- **Interactive Booking Flow**: Step-by-step booking process with location, pitch, and time slot selection
- **Google Sheets Integration**: Seamlessly connects to Google Sheets API to store and retrieve booking data
- **Real-time Availability**: Checks and displays only available time slots for each pitch
- **Contact Information Collection**: Collects user name and phone number for booking confirmation
- **Logging System**: Comprehensive logging for monitoring bot activities and troubleshooting
- **Graceful Shutdown**: Proper handling of shutdown signals for clean termination

## Commands

- `/start` - Initiates the booking process
- `/book` - Alternative command to start the booking process
- `/cancel` - Cancels the current booking process

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
GOOGLE_SHEET_ID=your_sheet_id_here  # Optional: Use either SHEET_NAME or SHEET_ID
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

### Google Sheets Structure

The bot requires two worksheets in your Google Sheet:

1. **Pitches** - Contains information about available football pitches with columns:
   - Location
   - Pitch Name
   - Time Slots (comma-separated values)
   - Owner Phone

2. **Bookings** - Stores booking information with columns:
   - User ID
   - User Name
   - Phone Number
   - Pitch Name
   - Date/Time
   - Status

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
6. Ensure your Google Sheet has the required worksheets (Pitches and Bookings) with the correct column structure

## Booking Flow

1. User starts the bot with `/start` or `/book` command
2. Bot presents available locations
3. User selects a location
4. Bot presents available pitches at that location
5. User selects a pitch
6. Bot presents available time slots for the selected pitch
7. User selects a time slot
8. Bot asks for confirmation
9. User confirms the booking
10. Bot collects user's name and phone number
11. Booking is confirmed and stored in the Google Sheet

## License

This project is licensed under the MIT License - see the LICENSE file for details.