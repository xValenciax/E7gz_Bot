# State Pattern - Confirmation State
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState

class ConfirmationState(BookingState):
    """State for handling booking confirmation"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            query = update.callback_query
            await query.answer()
            
            if query.data == "cancel":
                await query.edit_message_text('Booking cancelled. Send /start to begin again.')
                return ConversationHandler.END
            
            # Extract confirmation from callback data
            confirmation = query.data.split(':')[1]
            
            if confirmation != "yes":
                await query.edit_message_text('Booking cancelled. Send /start to begin again.')
                return ConversationHandler.END
            
            # Get booking details from context
            pitch_name = context.user_data.get('pitch_name', 'Unknown')
            time_slot = context.user_data.get('time_slot', 'Unknown')
            location = context.user_data.get('location', 'Unknown')
            
            # Double-check availability
            if not self.sheets_facade.is_slot_available(pitch_name, time_slot):
                await query.edit_message_text(
                    f"Sorry, the time slot {time_slot} for {pitch_name} is no longer available. Please try another time slot."
                )
                self.logger.warning(f'User {query.from_user.id} confirmed unavailable time slot: {time_slot}')
                return ConversationHandler.END
            
            # Ask for contact information
            await query.edit_message_text(
                f"Great! You're booking {time_slot} at {pitch_name} in {location}.\n\n"
                f"Please enter your phone number to complete the booking:"
            )
            
            self.logger.info(f'User {query.from_user.id} confirmed booking')
            return 4  # CONTACT_INFO state
        except Exception as e:
            user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
            self.logger.error(f'Error in handle_confirmation for user {user_id}: {str(e)}')
            await update.callback_query.edit_message_text('An error occurred while processing your request.')
            return ConversationHandler.END