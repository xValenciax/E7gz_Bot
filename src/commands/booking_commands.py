# Command Pattern - Concrete Commands
import logging
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from .base import Command

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