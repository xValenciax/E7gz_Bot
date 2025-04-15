# State Pattern - Contact Info State
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState
from ..observers.booking_event import BookingEvent

class ContactInfoState(BookingState):
    """State for handling contact information collection"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            # Get phone number from user input
            phone_number = update.message.text.strip()
            user = update.effective_user
            user_id = str(user.id)
            user_name = user.first_name
            
            # Get booking details from context
            pitch_name = context.user_data.get('pitch_name', 'Unknown')
            time_slot = context.user_data.get('time_slot', 'Unknown')
            location = context.user_data.get('location', 'Unknown')
            
            # Final check for availability
            if not self.sheets_facade.is_slot_available(pitch_name, time_slot):
                await update.message.reply_text(
                    f"Sorry, the time slot {time_slot} for {pitch_name} is no longer available. Please try another time slot."
                )
                self.logger.warning(f'User {user_id} tried to book unavailable time slot: {time_slot}')
                return ConversationHandler.END
            
            # Add booking to the sheet
            success = self.sheets_facade.add_booking(
                user_id=user_id,
                user_name=user_name,
                phone_number=phone_number,
                pitch_name=pitch_name,
                time_slot=time_slot,
                status='Booked'
            )
            
            if not success:
                await update.message.reply_text(
                    "Sorry, there was an error processing your booking. Please try again later."
                )
                self.logger.error(f'Failed to add booking for user {user_id}')
                return ConversationHandler.END
            
            # Create booking event for notification
            booking_event = BookingEvent(
                user_id=user_id,
                user_name=user_name,
                phone_number=phone_number,
                pitch_name=pitch_name,
                time_slot=time_slot,
                location=location
            )
            
            # Notify observers about the booking
            await self.notification_manager.notify(booking_event, context)
            
            # Send confirmation to user
            await update.message.reply_text(
                f"✅ Your booking is confirmed!\n\n"
                f"You've booked {time_slot} at {pitch_name} ({location}).\n\n"
                f"Thank you for using E7gz Bot! Send /start to make another booking."
            )
            
            self.logger.info(f'User {user_id} completed booking for {pitch_name} at {time_slot}')
            return ConversationHandler.END
        except Exception as e:
            user_id = update.effective_user.id if update.effective_user else 'Unknown'
            self.logger.error(f'Error in handle_contact_info for user {user_id}: {str(e)}')
            await update.message.reply_text('An error occurred while processing your request.')
            return ConversationHandler.END