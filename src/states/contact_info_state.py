# State Pattern - Contact Info State
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .base import BookingState
from ..observers.booking_event import BookingEvent

# Define state constants
NAME, PHONE = range(4, 6)  # Continue from previous states

class ContactInfoState(BookingState):
    """State for handling contact information collection"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            user = update.effective_user
            message_text = update.message.text
            
            # If this is the first message (name), store it and ask for phone number
            if 'user_name' not in context.user_data:
                context.user_data['user_name'] = message_text
                await update.message.reply_text(
                    f"Thank you, {message_text}. Now please enter your phone number:"
                )
                self.logger.info(f'User {user.id} provided name: {message_text}')
                return NAME
            
            # This is the second message (phone number)
            phone_number = message_text
            user_name = context.user_data['user_name']
            
            # Add booking to the sheet
            success = self.sheets_facade.add_booking(
                user_id=user.id,
                user_name=user_name,
                phone_number=phone_number,
                pitch_name=context.user_data['pitch_name'],
                time_slot=context.user_data['time_slot'],
                status='Booked'
            )

            if not success:
                    await update.message.reply_text(
                        "Sorry, there was an error processing your booking. Please try again later."
                    )
                    self.logger.error(f'Failed to add booking for user {user.id}')
                    return ConversationHandler.END

            # Create booking event for notification
            booking_event = BookingEvent(
                user_id=user.id,
                user_name=user_name,
                phone_number=phone_number,
                pitch_name=context.user_data['pitch_name'],
                time_slot=context.user_data['time_slot'],
                location=context.user_data['location']
            )

            # Notify observers about the booking
            self.logger.info(f'Notifying observers about booking for user {user.id}')

            # Assuming notification_manager.notify is an async method that sends notifications via emai
            await self.notification_manager.notify(booking_event, context)  

            await update.message.reply_text(
                f"✅ Your booking is confirmed!\n\n"
                f"You've booked {context.user_data['time_slot']} at {context.user_data['pitch_name']} ({context.user_data['location']}).\n\n"
                f"Your contact information has been saved.\n\n"
                f"Thank you for using E7gz Bot! Send /start to make another booking."
            )
            
            self.logger.info(f'User {user.id} successfully completed booking with contact info')
            return ConversationHandler.END

        except Exception as e:
            user_id = update.effective_user.id
            self.logger.error(f'Error in handle_contact_info for user {user_id}: {str(e)}')
            await update.message.reply_text('An error occurred while processing your request.')
            return ConversationHandler.END
