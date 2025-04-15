# Command Pattern - Base Command
from abc import ABC, abstractmethod
from telegram import Update
from telegram.ext import ContextTypes

class Command(ABC):
    """Base Command interface for implementing Command Pattern"""
    @abstractmethod
    async def execute(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        pass