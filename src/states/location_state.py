# State Pattern - Location State
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState

class LocationState(BookingState):
    """State for handling location selection"""
    def __init__(self, sheets_facade):
        self.sheets_facade = sheets_facade
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            query = update.callback_query
            await query.answer()
            
            # Extract location from callback data
            location = query.data.split(':')[1]
            context.user_data['location'] = location
            
            # Get available pitches for this location
            location_pitches = self.sheets_facade.get_pitches_by_location(location)
            
            if not location_pitches:
                await query.edit_message_text(f"No pitches available in {location}. Please try another location.")
                self.logger.warning(f'User {query.from_user.id} selected location with no pitches: {location}')
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
            
            self.logger.info(f'User {query.from_user.id} selected location: {location}')
            return 1  # PITCH_SELECTION state
        except Exception as e:
            user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
            self.logger.error(f'Error in handle_location for user {user_id}: {str(e)}')
            await update.callback_query.edit_message_text('An error occurred while processing your request.')
            return ConversationHandler.END