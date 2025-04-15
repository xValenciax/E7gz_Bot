# State Pattern - Base State
from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

class BookingState(ABC):
    """Base State interface for implementing State Pattern"""
    @abstractmethod
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        pass