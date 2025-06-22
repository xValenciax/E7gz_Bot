# State Pattern - Confirmation State
import logging
import time
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
                await query.edit_message_text('تم الغاء العملية. أرسل /start للبدء من جديد.')
                return ConversationHandler.END
            
            # Extract confirmation from callback data
            confirmation = query.data.split(':')[1]
            
            if confirmation != "yes":
                await query.edit_message_text('تم الغاء العملية. أرسل /start للبدء من جديد.')
                return ConversationHandler.END
            
            # Get booking details from context
            pitch_name = context.user_data.get('pitch_name', 'Unknown')
            time_slot = context.user_data.get('time_slot', 'Unknown')
            location = context.user_data.get('location', 'Unknown')
            
            # Double-check availability
            if not self.sheets_facade.is_slot_available(pitch_name, time_slot):
                await query.edit_message_text(
                    f"للأسف الوقت اللي انت اخترته {time_slot} للملعب {pitch_name}.\n"
                    f"غير متوفر حاليا.\n"
                    f"جرب تختار معاد تاني.",
                )
                self.logger.warning(f'User {query.from_user.id} confirmed unavailable time slot: {time_slot}')
                return ConversationHandler.END
            
            # Ask for contact information
            await query.edit_message_text(
                f"انت حاليا عايز تحجز ملعب {pitch_name}.\n\n"
                f"في {location} في وقت {time_slot}.\n\n"
                f"الرجاء إدخال الاسم بالكامل للاتمام عملية الحجز:"
            )
            
            self.logger.info(f'User {query.from_user.id} confirmed booking')
            return 4  # CONTACT_INFO state
        except Exception as e:
            user_id = update.callback_query.from_user.id if update.callback_query else 'Unknown'
            self.logger.error(f'Error in handle_confirmation for user {user_id}: {str(e)}')
            await update.callback_query.edit_message_text('An error occurred while processing your request.')
            return ConversationHandler.END