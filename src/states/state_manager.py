# State Pattern - State Manager
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from .location_state import LocationState
from .pitch_selection_state import PitchSelectionState
from .time_slot_state import TimeSlotState
from .confirmation_state import ConfirmationState
from .contact_info_state import ContactInfoState, NAME, PHONE
from ..observers.notification_manager import NotificationManager

class StateManager:
    """Manages the different states of the booking conversation"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')
        
        # Initialize states
        self.location_state = LocationState(sheets_facade)
        self.pitch_selection_state = PitchSelectionState(sheets_facade)
        self.time_slot_state = TimeSlotState(sheets_facade)
        self.confirmation_state = ConfirmationState(sheets_facade, notification_manager)
        self.contact_info_state = ContactInfoState(sheets_facade, notification_manager)
    
    async def start_booking(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        try:
            user = update.effective_user
            welcome_message = f'أهلا بيك يا {user.first_name}!.\n\n أنا E7gz بوت حجز الملاعب!'
            
            # Get unique locations from the Pitches sheet
            locations = self.sheets_facade.get_unique_locations()
            
            if not locations:
                await update.message.reply_text(
                    f"للأسف مفيش مناطق متاح فيها ملاعب حاليا ,قريبا ان شاء الله هنبدأ نضيف ملاعب جديدة"
                )
                self.logger.warning(f'User {user.id} attempted to book but no locations available')
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
                f"{welcome_message}\n\n"
                "أيه المنطقة اللي حابب تحجز فيها:",
                reply_markup=reply_markup
            )
            
            self.logger.info(f'Start command used by user {user.id}')
            return 0  # LOCATION state
        except Exception as e:
            self.logger.error(f'Error in start command: {str(e)}')
            await update.message.reply_text('An error occurred while processing your request.')
            return ConversationHandler.END