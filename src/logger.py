import logging
import os
from logging.handlers import RotatingFileHandler
import sys

def setup_logger():
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure logging
    logger = logging.getLogger('telegram_bot')
    logger.setLevel(logging.INFO)

    # Console handler with UTF-8 encoding
    # Ensure the console uses UTF-8 encoding for Windows
    class UTF8ConsoleHandler(logging.StreamHandler):
        def __init__(self, stream=None):
            super().__init__(stream)
            if sys.platform == 'win32':
                # Reconfigure stdout to use UTF-8 on Windows
                import io
                sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='backslashreplace')
                sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='backslashreplace')
            self.stream = sys.stdout

    console_handler = UTF8ConsoleHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)

    # File handler
    file_handler = RotatingFileHandler(
        'logs/bot.log',
        maxBytes=1024 * 1024,
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.INFO)
    file_formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_formatter)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger