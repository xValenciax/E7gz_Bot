# Design Patterns Implementation for E7gz Bot
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Callable
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

# ===== Command Pattern =====
class Command(ABC):
    """Base Command interface for implementing Command Pattern"""
    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        pass

class BookingCommand(Command):
    """Command for handling the booking process"""
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.logger = logging.getLogger('telegram_bot')

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        self.logger.info(f'Starting booking process for user {update.effective_user.id}')
        return await self.state_manager.start_booking(update, context)

class CancelCommand(Command):
    """Command for canceling the booking process"""
    def __init__(self):
        self.logger = logging.getLogger('telegram_bot')

    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        user = update.effective_user
        self.logger.info(f'User {user.id} cancelled the conversation')
        await update.message.reply_text('Booking cancelled. Send /start to begin again.')
        return ConversationHandler.END

# ===== State Pattern =====
class BookingState(ABC):
    """Base State interface for implementing State Pattern"""
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        pass

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

class PitchSelectionState(BookingState):
    """State for handling pitch selection"""
    def __init__(self, sheets_facade):
        self.sheets_facade = sheets_facade
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Implementation similar to handle_pitch_selection in bot.py
        # Using sheets_facade to get data
        pass

class TimeSlotState(BookingState):
    """State for handling time slot selection"""
    def __init__(self, sheets_facade):
        self.sheets_facade = sheets_facade
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Implementation similar to handle_timeslot in bot.py
        # Using sheets_facade to get data
        pass

class ConfirmationState(BookingState):
    """State for handling booking confirmation"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Implementation similar to handle_confirmation in bot.py
        # Using sheets_facade to check and store data
        # Using notification_manager to notify about booking
        pass

class ContactInfoState(BookingState):
    """State for handling contact information collection"""
    def __init__(self, sheets_facade, notification_manager):
        self.sheets_facade = sheets_facade
        self.notification_manager = notification_manager
        self.logger = logging.getLogger('telegram_bot')

    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        # Implementation similar to handle_contact_info in bot.py
        # Using sheets_facade to store data
        # Using notification_manager to notify about completed booking
        pass

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
            welcome_message = f'Hello {user.first_name}! Welcome to E7gz Bot - your football pitch booking assistant.'
            
            # Get unique locations from the Pitches sheet
            locations = self.sheets_facade.get_unique_locations()
            
            if not locations:
                await update.message.reply_text(
                    f"Hello {user.first_name}! No locations are currently available. Please try again later."
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
                f"{welcome_message}\n\nPlease select a location to book a football pitch:",
                reply_markup=reply_markup
            )
            
            self.logger.info(f'Start command used by user {user.id}')
            return 0  # LOCATION state
        except Exception as e:
            self.logger.error(f'Error in start command: {str(e)}')
            await update.message.reply_text('An error occurred while processing your request.')
            return ConversationHandler.END

# ===== Facade Pattern =====
class SheetsFacade:
    """Facade for Google Sheets operations"""
    def __init__(self, credentials_file, scopes, sheet_name=None, sheet_id=None):
        self.credentials_file = credentials_file
        self.scopes = scopes
        self.sheet_name = sheet_name
        self.sheet_id = sheet_id
        self.logger = logging.getLogger('telegram_bot')
        self.workbook = None
        self.pitches_sheet = None
        self.bookings_sheet = None
        self.initialize_connection()

    def initialize_connection(self):
        """Initialize connection to Google Sheets"""
        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                self.credentials_file,
                self.scopes
            )
            gc = gspread.authorize(credentials)
            
            # Try to open by ID first if provided, otherwise use name
            if self.sheet_id:
                try:
                    self.workbook = gc.open_by_key(self.sheet_id)
                    self.logger.info(f'Opened workbook by ID: {self.sheet_id}')
                except Exception as e:
                    self.logger.error(f'Could not open workbook with ID: {self.sheet_id}. Error: {str(e)}')
                    raise
            else:
                try:
                    self.workbook = gc.open(self.sheet_name)
                    self.logger.info(f'Opened workbook by name: {self.sheet_name}')
                except gspread.exceptions.SpreadsheetNotFound:
                    self.logger.error(f'Could not open workbook with name: {self.sheet_name}')
                    self.logger.error('Make sure the workbook exists and is shared with the service account email')
                    raise
            
            self._initialize_worksheets()
            self.logger.info('Successfully connected to Google Sheets')
        except Exception as e:
            self.logger.error(f'Failed to connect to Google Sheets: {str(e)}')
            raise

    def _initialize_worksheets(self):
        """Initialize or create required worksheets"""
        try:
            self.pitches_sheet = self.workbook.worksheet('Pitches')
            self.logger.info('Accessed Pitches worksheet')
        except gspread.exceptions.WorksheetNotFound:
            # Create Pitches worksheet with headers if it doesn't exist
            self.pitches_sheet = self.workbook.add_worksheet(title='Pitches', rows=100, cols=20)
            self.pitches_sheet.append_row(['Location', 'Pitch Name', 'Time Slots', 'Owner Phone'])
            self.logger.info('Created new Pitches worksheet')
        
        try:
            self.bookings_sheet = self.workbook.worksheet('Bookings')
            self.logger.info('Accessed Bookings worksheet')
            
            # Check if the Bookings sheet has the required columns
            headers = self.bookings_sheet.row_values(1)
            if 'Phone Number' not in headers or 'User Name' not in headers:
                # Add the new columns if they don't exist
                if 'Phone Number' not in headers:
                    self.bookings_sheet.append_col(['Phone Number'] + [''] * (len(self.bookings_sheet.col_values(1)) - 1))
                    self.logger.info('Added Phone Number column to Bookings worksheet')
                if 'User Name' not in headers:
                    self.bookings_sheet.append_col(['User Name'] + [''] * (len(self.bookings_sheet.col_values(1)) - 1))
                    self.logger.info('Added User Name column to Bookings worksheet')
        except gspread.exceptions.WorksheetNotFound:
            # Create Bookings worksheet with headers if it doesn't exist
            self.bookings_sheet = self.workbook.add_worksheet(title='Bookings', rows=100, cols=20)
            self.bookings_sheet.append_row(['User ID', 'Pitch Name', 'Date/Time', 'Status', 'Phone Number', 'User Name'])
            self.logger.info('Created new Bookings worksheet')

    def get_unique_locations(self) -> List[str]:
        """Get unique locations from the Pitches sheet"""
        all_pitches = self.pitches_sheet.get_all_records()
        return sorted(set(pitch['Location'] for pitch in all_pitches))

    def get_pitches_by_location(self, location: str) -> List[Dict]:
        """Get pitches for a specific location"""
        all_pitches = self.pitches_sheet.get_all_records()
        return [pitch for pitch in all_pitches if pitch['Location'] == location]

    def get_available_time_slots(self, pitch_name: str) -> List[str]:
        """Get available time slots for a specific pitch"""
        # Get all time slots for the pitch
        all_pitches = self.pitches_sheet.get_all_records()
        pitch_data = next((pitch for pitch in all_pitches if pitch['Pitch Name'] == pitch_name), None)
        
        if not pitch_data:
            return []
        
        available_slots = [slot.strip() for slot in pitch_data['Time Slots'].split(',')]
        
        # Check which slots are already booked
        bookings = self.bookings_sheet.get_all_records()
        booked_slots = [booking['Date/Time'] for booking in bookings 
                       if booking['Status'] == 'Booked' and booking['Pitch Name'] == pitch_name]
        
        # Remove booked slots from available slots
        return [slot for slot in available_slots if slot not in booked_slots]

    def is_slot_available(self, pitch_name: str, time_slot: str) -> bool:
        """Check if a specific time slot is available for a pitch"""
        bookings = self.bookings_sheet.get_all_records()
        for booking in bookings:
            if (booking['Status'] == 'Booked' and 
                booking['Date/Time'] == time_slot and 
                booking['Pitch Name'] == pitch_name):
                return False
        return True

    def add_booking(self, user_id: str, user_name: str, phone_number: str, 
                   pitch_name: str, time_slot: str, status: str = 'Booked') -> bool:
        """Add a new booking to the Bookings sheet"""
        try:
            self.bookings_sheet.append_row([
                user_id, 
                pitch_name, 
                time_slot, 
                status,
                phone_number,
                user_name
            ])
            return True
        except Exception as e:
            self.logger.error(f'Error adding booking: {str(e)}')
            return False

# ===== Observer Pattern =====
class BookingEvent:
    """Event data for booking notifications"""
    def __init__(self, user_id: str, user_name: str, phone_number: str, 
                 pitch_name: str, time_slot: str, location: str):
        self.user_id = user_id
        self.user_name = user_name
        self.phone_number = phone_number
        self.pitch_name = pitch_name
        self.time_slot = time_slot
        self.location = location
        self.timestamp = None  # Could add timestamp here

class BookingObserver(ABC):
    """Observer interface for booking events"""
    @abstractmethod
    async def update(self, event: BookingEvent) -> None:
        pass

class UserNotifier(BookingObserver):
    """Observer that notifies the user about booking events"""
    def __init__(self):
        self.logger = logging.getLogger('telegram_bot')

    async def update(self, event: BookingEvent, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
        if not context:
            self.logger.error(f'Cannot notify user {event.user_id}: context is None')
            return
        
        try:
            await context.bot.send_message(
                chat_id=event.user_id,
                text=f"✅ Your booking is confirmed!\n\n"
                     f"You've booked {event.time_slot} at {event.pitch_name} ({event.location}).\n\n"
                     f"Thank you for using E7gz Bot! Send /start to make another booking."
            )
            self.logger.info(f'Sent booking confirmation to user {event.user_id}')
        except Exception as e:
            self.logger.error(f'Failed to send notification to user {event.user_id}: {str(e)}')

class AdminNotifier(BookingObserver):
    """Observer that notifies admins about booking events"""
    def __init__(self, admin_chat_ids: List[str]):
        self.admin_chat_ids = admin_chat_ids
        self.logger = logging.getLogger('telegram_bot')

    async def update(self, event: BookingEvent, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
        if not context:
            self.logger.error('Cannot notify admins: context is None')
            return
        
        try:
            admin_message = (
                f"🔔 New Booking Alert!\n\n"
                f"User: {event.user_name} (ID: {event.user_id})\n"
                f"Phone: {event.phone_number}\n"
                f"Booked: {event.pitch_name} at {event.location}\n"
                f"Time: {event.time_slot}"
            )
            
            for admin_id in self.admin_chat_ids:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=admin_message
                )
            
            self.logger.info(f'Sent booking notifications to {len(self.admin_chat_ids)} admins')
        except Exception as e:
            self.logger.error(f'Failed to send notifications to admins: {str(e)}')

class NotificationManager:
    """Subject in the Observer pattern that manages notifications"""
    def __init__(self):
        self.observers: List[BookingObserver] = []
        self.logger = logging.getLogger('telegram_bot')

    def add_observer(self, observer: BookingObserver) -> None:
        """Add an observer to the notification list"""
        self.observers.append(observer)
        self.logger.info(f'Added observer: {observer.__class__.__name__}')

    def remove_observer(self, observer: BookingObserver) -> None:
        """Remove an observer from the notification list"""
        self.observers.remove(observer)
        self.logger.info(f'Removed observer: {observer.__class__.__name__}')

    async def notify(self, event: BookingEvent, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
        """Notify all observers about a booking event"""
        self.logger.info(f'Notifying {len(self.observers)} observers about booking event')
        for observer in self.observers:
            await observer.update(event, context)

# Factory function to create the design pattern components
def create_design_pattern_components(credentials_file, scopes, sheet_name=None, sheet_id=None, admin_chat_ids=None):
    """Factory function to create and wire up all design pattern components"""
    # Create the Facade
    sheets_facade = SheetsFacade(credentials_file, scopes, sheet_name, sheet_id)
    
    # Create the Observer pattern components
    notification_manager = NotificationManager()
    notification_manager.add_observer(UserNotifier())
    
    if admin_chat_ids:
        notification_manager.add_observer(AdminNotifier(admin_chat_ids))
    
    # Create the State pattern components
    state_manager = StateManager(sheets_facade, notification_manager)
    
    # Create the Command pattern components
    booking_command = BookingCommand(state_manager)
    cancel_command = CancelCommand()
    
    return {
        'sheets_facade': sheets_facade,
        'notification_manager': notification_manager,
        'state_manager': state_manager,
        'booking_command': booking_command,
        'cancel_command': cancel_command
    }