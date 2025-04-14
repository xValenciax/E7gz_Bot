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
        pitches_sheet.append_row(['Pitch Name', 'Location', 'Time Slots', 'Owner Phone'])
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
        
        # Get all available time slots for this location
        available_slots = {}
        for pitch in location_pitches:
            pitch_name = pitch['Pitch Name']
            slots = [slot.strip() for slot in pitch['Time Slots'].split(',')]
            for slot in slots:
                if slot not in available_slots:
                    available_slots[slot] = []
                available_slots[slot].append(pitch_name)
        
        # Check which slots are already booked
        bookings = bookings_sheet.get_all_records()
        for booking in bookings:
            if booking['Status'] == 'Booked' and booking['Pitch Name'] in [p['Pitch Name'] for p in location_pitches]:
                slot = booking['Date/Time']
                if slot in available_slots and booking['Pitch Name'] in available_slots[slot]:
                    available_slots[slot].remove(booking['Pitch Name'])
                    # If no more pitches available for this slot, remove the slot
                    if not available_slots[slot]:
                        del available_slots[slot]
        
        if not available_slots:
            await query.edit_message_text(f"No available time slots in {location}. Please try another location.")
            logger.warning(f'User {query.from_user.id} selected location with no Time Slots: {location}')
            return ConversationHandler.END
        
        # Create inline keyboard with time slot buttons
        keyboard = []
        sorted_slots = sorted(available_slots.keys())
        for i in range(0, len(sorted_slots), 2):  # 2 buttons per row
            row = []
            slot = sorted_slots[i]
            row.append(InlineKeyboardButton(slot, callback_data=f"slot:{slot}"))
            if i + 1 < len(sorted_slots):
                slot = sorted_slots[i+1]
                row.append(InlineKeyboardButton(slot, callback_data=f"slot:{slot}"))
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {location}. Please choose an available time slot:",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected location: {location}')
        return TIMESLOT
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_location for user {user_id}: {str(e)}')
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
        
        # Find available pitches for this location and time slot
        all_pitches = pitches_sheet.get_all_records()
        location_pitches = [pitch for pitch in all_pitches if pitch['Location'] == location]
        
        available_pitches = []
        for pitch in location_pitches:
            slots = [slot.strip() for slot in pitch['Time Slots'].split(',')]
            if time_slot in slots:
                available_pitches.append(pitch['Pitch Name'])
        
        # Check which pitches are already booked for this time slot
        bookings = bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] in available_pitches):
                available_pitches.remove(booking['Pitch Name'])
        
        if not available_pitches:
            await query.edit_message_text(
                f"Sorry, all pitches in {location} for {time_slot} are now booked. Please try another time slot."
            )
            logger.warning(f'User {query.from_user.id} selected time slot with no available pitches: {time_slot}')
            return ConversationHandler.END
        
        # Create keyboard with available pitches
        keyboard = []
        for i in range(0, len(available_pitches), 2):  # 2 buttons per row
            row = []
            row.append(InlineKeyboardButton(available_pitches[i], callback_data=f"pitch:{available_pitches[i]}"))
            if i + 1 < len(available_pitches):
                row.append(InlineKeyboardButton(available_pitches[i+1], callback_data=f"pitch:{available_pitches[i+1]}"))
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {time_slot} at {location}.\n\n"
            f"Please select a pitch:",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected time slot: {time_slot}')
        return PITCH_SELECTION
    except Exception as e:
        user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
        logger.error(f'Error in handle_timeslot for user {user_id}: {str(e)}')
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
        time_slot = context.user_data['time_slot']
        
        # Check one more time if the pitch is still available
        bookings = bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] == selected_pitch):
                await query.edit_message_text(
                    f"Sorry, {selected_pitch} at {time_slot} has just been booked by someone else. Please try again."
                )
                logger.warning(f'User {query.from_user.id} attempted to book an already booked pitch: {selected_pitch} at {time_slot}')
                return ConversationHandler.END
        
        # Create confirmation keyboard
        keyboard = [
            [InlineKeyboardButton("Confirm Booking", callback_data="confirm")],
            [InlineKeyboardButton("Cancel", callback_data="cancel")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"You selected {selected_pitch} at {location} for {time_slot}.\n\n"
            f"Would you like to confirm your booking?",
            reply_markup=reply_markup
        )
        
        logger.info(f'User {query.from_user.id} selected pitch: {selected_pitch}')
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
                    f"Sorry, {pitch} at {time_slot} has just been booked by someone else. Please try again."
                )
                logger.warning(f'User {user_id} attempted to book an already booked slot: {pitch} at {time_slot}')
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
            f"Your booking for {pitch} at {location} for {time_slot} is almost complete.\n\n"
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
            f"You've booked {booking_details['pitch']} at {booking_details['location']} for {booking_details['time_slot']}.\n\n"
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
                TIMESLOT: [CallbackQueryHandler(handle_timeslot)],
                PITCH_SELECTION: [CallbackQueryHandler(handle_pitch_selection)],
                CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
                CONTACT_INFO: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_info)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        application.add_handler(conv_handler)

        logger.info('Bot started successfully')
        # Start the bot
        application.run_polling()
    except Exception as e:
        logger.error(f'Failed to start bot: {str(e)}')
        raise

if __name__ == '__main__':
    main()