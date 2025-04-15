# Observer Pattern - Notification Manager
import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from telegram.ext import ContextTypes

from .booking_event import BookingEvent

class BookingObserver(ABC):
    """Observer interface for booking events"""
    @abstractmethod
    async def update(self, event: BookingEvent, context: Optional[ContextTypes.DEFAULT_TYPE] = None) -> None:
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