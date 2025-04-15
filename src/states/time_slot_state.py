# State Pattern - Time Slot State
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState

class TimeSlotState(BookingState):
    """State for handling time slot selection"""
    def __init__(self, sheets_facade):
        self.sheets_facade = sheets_facade
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel":
                await query.edit_message_text('Booking cancelled. Send /start to begin again.')
                return ConversationHandler.END
            
            # Extract time slot from callback data
            time_slot = query.data.split(':')[1]
            context.user_data['time_slot'] = time_slot
            pitch_name = context.user_data.get('pitch_name', 'Unknown')
            location = context.user_data.get('location', 'Unknown')
            
            # Check if the time slot is still available (double-check)
            if not self.sheets_facade.is_slot_available(pitch_name, time_slot):
                await query.edit_message_text(
                    f"Sorry, the time slot {time_slot} for {pitch_name} is no longer available. Please try another time slot."
                )
                self.logger.warning(f'User {query.from_user.id} selected unavailable time slot: {time_slot}')
                return ConversationHandler.END
            
            # Create confirmation buttons
            keyboard = [
                [InlineKeyboardButton("Confirm Booking", callback_data="confirm:yes")],
                [InlineKeyboardButton("Cancel", callback_data="cancel")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"You selected {time_slot} at {pitch_name} in {location}.\n\n"
                f"Please confirm your booking:",
                reply_markup=reply_markup
            )
            
            self.logger.info(f'User {query.from_user.id} selected time slot: {time_slot}')
            return 3  # CONFIRMATION state
        except Exception as e:
            user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
            self.logger.error(f'Error in handle_timeslot for user {user_id}: {str(e)}')
            await update.callback_query.edit_message_text('An error occurred while processing your request.')
            return ConversationHandler.END