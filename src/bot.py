import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import TELEGRAM_TOKEN, GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, GOOGLE_SHEET_ID, GOOGLE_SCOPES
from logger import setup_logger

# Setup logging
logger = setup_logger()

# Define conversation states
LOCATION, TIMESLOT, PITCH_SELECTION, CONFIRMATION, CONTACT_INFO = range(5)

# Google Sheets setup
try:
    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        GOOGLE_CREDENTIALS_FILE,
        GOOGLE_SCOPES
    )
    gc = gspread.authorize(credentials)
    # Try to open by ID first if provided, otherwise use name
    if GOOGLE_SHEET_ID:
        try:
            workbook = gc.open_by_key(GOOGLE_SHEET_ID)
            logger.info(f'Opened workbook by ID: {GOOGLE_SHEET_ID}')
        except Exception as e:
            logger.error(f'Could not open workbook with ID: {GOOGLE_SHEET_ID}. Error: {str(e)}')
            raise
    else:
        try:
            workbook = gc.open(GOOGLE_SHEET_NAME)
            logger.info(f'Opened workbook by name: {GOOGLE_SHEET_NAME}')
        except gspread.exceptions.SpreadsheetNotFound:
            # Log a more helpful error message
            logger.error(f'Could not open workbook with name: {GOOGLE_SHEET_NAME}')
            logger.error('Make sure the workbook exists and is shared with the service account email in your credentials file')
            raise
    
    # Get or create the required worksheets
    try:
        pitches_sheet = workbook.worksheet('Pitches')
        logger.info('Accessed Pitches worksheet')
    except gspread.exceptions.WorksheetNotFound:
        # Create Pitches worksheet with headers if it doesn't exist
        pitches_sheet = workbook.add_worksheet(title='Pitches', rows=100, cols=20)
        pitches_sheet.append_row(['Location', 'Pitch Name', 'Time Slots', 'Owner Phone'])
        logger.info('Created new Pitches worksheet')
    
    try:
        bookings_sheet = workbook.worksheet('Bookings')
        logger.info('Accessed Bookings worksheet')
        
        # Check if the Bookings sheet has the required columns
        headers = bookings_sheet.row_values(1)
        if 'Phone Number' not in headers or 'User Name' not in headers:
            # Add the new columns if they don't exist
            if 'Phone Number' not in headers:
                bookings_sheet.append_col(['Phone Number'] + [''] * (len(bookings_sheet.col_values(1)) - 1))
                logger.info('Added Phone Number column to Bookings worksheet')
            if 'User Name' not in headers:
                bookings_sheet.append_col(['User Name'] + [''] * (len(bookings_sheet.col_values(1)) - 1))
                logger.info('Added User Name column to Bookings worksheet')
    except gspread.exceptions.WorksheetNotFound:
        # Create Bookings worksheet with headers if it doesn't exist
        bookings_sheet = workbook.add_worksheet(title='Bookings', rows=100, cols=20)
        bookings_sheet.append_row(['User ID', 'Pitch Name', 'Date/Time', 'Status', 'Phone Number', 'User Name'])
        logger.info('Created new Bookings worksheet')
    
    logger.info('Successfully connected to Google Sheets')
except Exception as e:
    logger.error(f'Failed to connect to Google Sheets: {str(e)}')
    raise

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        welcome_message = f'Hello {user.first_name}! Welcome to E7gz Bot - your football pitch booking assistant.'
        
        # Get unique locations from the Pitches sheet
        all_pitches = pitches_sheet.get_all_records()
        locations = sorted(set(pitch['Location'] for pitch in all_pitches))
        
        if not locations:
            await update.message.reply_text(
                f"Hello {user.first_name}! No locations are currently available. Please try again later."
            )
            logger.warning(f'User {user.id} attempted to book but no locations available')
            return ConversationHandler.END
        
        # Create inline keyboard with location buttons
        keyboard = []
        for i in range(0, len(locations), 2):  # 2 buttons per row
            row = []
            row.append(InlineKeyboardButton(locations[i], callback_data=f"location:{locations[i]}"))
            if i + 1 < len(locations):
                row.append(InlineKeyboardButton(locations[i+1], callback_data=f"location:{locations[i+1]}"))
            keyboard.append(row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"{welcome_message}\n\nPlease select a location to book a football pitch:",
            reply_markup=reply_markup
        )
        
        logger.info(f'Start command used by user {user.id}')
        return LOCATION
    except Exception as e:
        logger.error(f'Error in start command: {str(e)}')
        await update.message.reply_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        # Extract location from callback data
        location = query.data.split(':')[1]
        context.user_data['location'] = location
        
        # Get available pitches for this location
        all_pitches = pitches_sheet.get_all_records()
        location_pitches = [pitch for pitch in all_pitches if pitch['Location'] == location]
        
        if not location_pitches:
            await query.edit_message_text(f"No pitches available in {location}. Please try another location.")
            logger.warning(f'User {query.from_user.id} selected location with no pitches: {location}')
            return ConversationHandler.END
        
        # Create inline keyboard with pitch buttons
        keyboard = []
        pitch_names = sorted([pitch['Pitch Name'] for pitch in location_pitches])
        for i in range(0, len(pitch_names), 2):  # 2 buttons per row
            row = []
            row.append(InlineKeyboardButton(pitch_names[i], callback_data=f"pitch:{pitch_names[i]}"))
            if i + 1 < len(pitch_names):
                row.append(InlineKeyboardButton(pitch_names[i+1], callback_data=f"pitch:{pitch_names[i+1]}"))
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {location}. Please choose a pitch:",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected location: {location}')
        return PITCH_SELECTION
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_location for user {user_id}: {str(e)}')
        await update.callback_query.edit_message_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def handle_pitch_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("Booking cancelled. Send /start to begin again.")
            logger.info(f'User {query.from_user.id} cancelled booking')
            return ConversationHandler.END
        
        # Extract pitch from callback data
        selected_pitch = query.data.split(':')[1]
        context.user_data['pitch'] = selected_pitch
        location = context.user_data['location']
        
        # Get time slots for the selected pitch
        all_pitches = pitches_sheet.get_all_records()
        pitch_data = next((pitch for pitch in all_pitches if pitch['Pitch Name'] == selected_pitch), None)
        
        if not pitch_data:
            await query.edit_message_text(f"Sorry, could not find data for {selected_pitch}. Please try again.")
            logger.warning(f'User {query.from_user.id} selected a pitch that does not exist: {selected_pitch}')
            return ConversationHandler.END
        
        # Get available time slots for this pitch
        available_slots = [slot.strip() for slot in pitch_data['Time Slots'].split(',')]
        
        # Check which slots are already booked for this pitch
        bookings = bookings_sheet.get_all_records()
        booked_slots = [booking['Date/Time'] for booking in bookings 
                       if booking['Status'] == 'Booked' and booking['Pitch Name'] == selected_pitch]
        
        # Remove booked slots from available slots
        available_slots = [slot for slot in available_slots if slot not in booked_slots]
        
        if not available_slots:
            await query.edit_message_text(
                f"Sorry, all time slots for {selected_pitch} at {location} are booked. Please select another pitch."
            )
            logger.warning(f'User {query.from_user.id} selected pitch with no available time slots: {selected_pitch}')
            return ConversationHandler.END
        
        # Create keyboard with available time slots
        keyboard = []
        sorted_slots = sorted(available_slots)
        for i in range(0, len(sorted_slots), 2):  # 2 buttons per row
            row = []
            row.append(InlineKeyboardButton(sorted_slots[i], callback_data=f"slot:{sorted_slots[i]}"))
            if i + 1 < len(sorted_slots):
                row.append(InlineKeyboardButton(sorted_slots[i+1], callback_data=f"slot:{sorted_slots[i+1]}"))
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {selected_pitch} at {location}.\n\n"
            f"Please select a time slot:",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected pitch: {selected_pitch}')
        return TIMESLOT
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_timeslot for user {user_id}: {str(e)}')
        await update.callback_query.edit_message_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def handle_timeslot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("Booking cancelled. Send /start to begin again.")
            logger.info(f'User {query.from_user.id} cancelled booking')
            return ConversationHandler.END
        
        # Extract time slot from callback data
        time_slot = query.data.split(':')[1]
        context.user_data['time_slot'] = time_slot
        location = context.user_data['location']
        selected_pitch = context.user_data['pitch']
        
        # Check one more time if the time slot is still available for this pitch
        bookings = bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] == selected_pitch):
                await query.edit_message_text(
                    f"Sorry, the time slot {time_slot} for {selected_pitch} has just been booked by someone else. Please try again."
                )
                logger.warning(f'User {query.from_user.id} attempted to book an already booked time slot: {time_slot} for {selected_pitch}')
                return ConversationHandler.END
        
        # Create confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("Confirm Booking", callback_data="confirm")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {time_slot} for {selected_pitch} at {location}.\n\n"
            f"Would you like to confirm your booking?",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected time slot: {time_slot} for pitch: {selected_pitch}')
        return CONFIRMATION
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_pitch_selection for user {user_id}: {str(e)}')
        await update.callback_query.edit_message_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel":
            await query.edit_message_text("Booking cancelled. Send /start to begin again.")
            logger.info(f'User {query.from_user.id} cancelled booking at confirmation stage')
            return ConversationHandler.END
        
        # Get booking details from context
        location = context.user_data['location']
        time_slot = context.user_data['time_slot']
        pitch = context.user_data['pitch']
        user_id = query.from_user.id
        
        # Check one more time if the slot is still available
        bookings = bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] == pitch):
                await query.edit_message_text(
                    f"Sorry, the time slot {time_slot} for {pitch} has just been booked by someone else. Please try again."
                )
                logger.warning(f'User {user_id} attempted to book an already booked time slot: {time_slot} for pitch {pitch}')
                return ConversationHandler.END
        
        # Store booking details in context for later use
        context.user_data['booking_details'] = {
            'user_id': str(user_id),
            'pitch': pitch,
            'time_slot': time_slot,
            'location': location
        }
        
        # Ask for contact information
        await query.edit_message_text(
            f"Your booking for {time_slot} at {pitch} ({location}) is almost complete.\n\n"
            f"Please enter your real name to continue:"
        )
        
        logger.info(f'User {user_id} confirmed booking, now collecting contact information')
        return CONTACT_INFO
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_confirmation for user {user_id}: {str(e)}')
        await update.callback_query.edit_message_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def handle_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user = update.effective_user
        message_text = update.message.text
        
        # If this is the first message (name), store it and ask for phone number
        if 'user_name' not in context.user_data:
            context.user_data['user_name'] = message_text
            await update.message.reply_text(
                f"Thank you, {message_text}. Now please enter your phone number:"
            )
            logger.info(f'User {user.id} provided name: {message_text}')
            return CONTACT_INFO
        
        # This is the second message (phone number)
        phone_number = message_text
        user_name = context.user_data['user_name']
        booking_details = context.user_data['booking_details']
        
        # Add booking to the sheet with contact information
        bookings_sheet.append_row([
            booking_details['user_id'], 
            user_name,
            phone_number,
            booking_details['pitch'], 
            booking_details['time_slot'], 
            'Booked'
        ])
        
        await update.message.reply_text(
            f"✅ Your booking is confirmed!\n\n"
            f"You've booked {booking_details['time_slot']} at {booking_details['pitch']} ({booking_details['location']}).\n\n"
            f"Your contact information has been saved.\n\n"
            f"Thank you for using E7gz Bot! Send /start to make another booking."
        )
        
        logger.info(f'User {user.id} successfully completed booking with contact info')
        return ConversationHandler.END
    except Exception as e:
        user_id = update.effective_user.id
        logger.error(f'Error in handle_contact_info for user {user_id}: {str(e)}')
        await update.message.reply_text('An error occurred while processing your request.')
        return ConversationHandler.END

async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for start command to restart booking process"""
    return await start(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation."""
    user = update.effective_user
    logger.info(f'User {user.id} cancelled the conversation')
    await update.message.reply_text('Booking cancelled. Send /start to begin again.')
    return ConversationHandler.END

def main():
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add conversation handler for booking flow
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start), CommandHandler("book", book_command)],
            states={
                LOCATION: [CallbackQueryHandler(handle_location)],
                PITCH_SELECTION: [CallbackQueryHandler(handle_pitch_selection)],
                TIMESLOT: [CallbackQueryHandler(handle_timeslot)],
                CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
                CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_info)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        application.add_handler(conv_handler)

        logger.info('Bot started successfully')
        
        # Set up signal handlers for graceful shutdown
        import signal
        import sys
        
        def shutdown_handler(signum, frame):
            logger.info('Shutdown signal received, closing connections...')
            # Perform cleanup operations
            try:
                # Close Google Sheets connection if needed
                if 'gc' in globals() and gc is not None:
                    logger.info('Closing Google Sheets connection')
                # Any other cleanup needed
            except Exception as e:
                logger.error(f'Error during shutdown: {str(e)}')
            finally:
                logger.info('Bot shutdown complete')
                sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, shutdown_handler)  # Termination signal
        
        # Start the bot
        application.run_polling()
    except Exception as e:
        logger.error(f'Failed to start bot: {str(e)}')
        raise

if __name__ == '__main__':
    main()