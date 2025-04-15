# State Pattern - Pitch Selection State
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState

class PitchSelectionState(BookingState):
    """State for handling pitch selection"""
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
            
            # Extract pitch name from callback data
            pitch_name = query.data.split(':')[1]
            context.user_data['pitch_name'] = pitch_name
            location = context.user_data.get('location', 'Unknown')
            
            # Get available time slots for this pitch
            time_slots = self.sheets_facade.get_available_time_slots(pitch_name)
            
            if not time_slots:
                await query.edit_message_text(f"No available time slots for {pitch_name}. Please try another pitch.")
                self.logger.warning(f'User {query.from_user.id} selected pitch with no available slots: {pitch_name}')
                return ConversationHandler.END
            
            # Create inline keyboard with time slot buttons
            keyboard = []
            for i in range(0, len(time_slots), 2):  # 2 buttons per row
                row = []
                row.append(InlineKeyboardButton(time_slots[i], callback_data=f"time:{time_slots[i]}"))
                if i + 1 < len(time_slots):
                    row.append(InlineKeyboardButton(time_slots[i+1], callback_data=f"time:{time_slots[i+1]}"))
                keyboard.append(row)
            
            # Add cancel button
            keyboard.append([InlineKeyboardButton("Cancel", callback_data="cancel")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"You selected {pitch_name} in {location}. Please choose a time slot:",
                reply_markup=reply_markup
            )
            
            self.logger.info(f'User {query.from_user.id} selected pitch: {pitch_name}')
            return 2  # TIMESLOT state
        except Exception as e:
            user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
            self.logger.error(f'Error in handle_pitch_selection for user {user_id}: {str(e)}')
            await update.callback_query.edit_message_text('An error occurred while processing your request.')
            return ConversationHandler.END