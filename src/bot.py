import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, ConversationHandler, CallbackQueryHandler
from src.config import TELEGRAM_TOKEN, GOOGLE_CREDENTIALS_FILE, GOOGLE_SHEET_NAME, GOOGLE_SHEET_ID, GOOGLE_SCOPES
from src.logger import setup_logger

# Import components from modular structure
from src.facades.sheets_facade import SheetsFacade
from src.observers.notification_manager import NotificationManager
from src.states.state_manager import StateManager
from src.commands.booking_commands import BookingCommand, CancelCommand

# Setup logging
logger = setup_logger()

# Define conversation states
LOCATION, PITCH_SELECTION, TIMESLOT, CONFIRMATION, CONTACT_INFO_NAME, CONTACT_INFO_PHONE = range(6)

# Initialize components directly
try:
    # Create facade
    sheets_facade = SheetsFacade(
        GOOGLE_CREDENTIALS_FILE,
        GOOGLE_SCOPES,
        GOOGLE_SHEET_NAME,
        GOOGLE_SHEET_ID
    )
    
    # Create observer
    notification_manager = NotificationManager()
    # booking_event = 
    
    # Add user notifier
    from src.observers.notification_manager import UserNotifier, AdminNotifier
    notification_manager.add_observer(UserNotifier())
    
    # Add admin notifier if admin chat IDs are configured
    from src.config import ADMIN_CHAT_IDS
    if ADMIN_CHAT_IDS:
        notification_manager.add_observer(AdminNotifier(ADMIN_CHAT_IDS))
        logger.info(f'Added AdminNotifier with {len(ADMIN_CHAT_IDS)} admin chat IDs')
    
    # Create state manager
    state_manager = StateManager(sheets_facade, notification_manager)
    
    # Create commands
    booking_command = BookingCommand(state_manager)
    cancel_command = CancelCommand()
    
    logger.info('Successfully initialized components')
except Exception as e:
    logger.error(f'Failed to initialize components: {str(e)}')
    raise

# Command handlers using Command Pattern
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the booking process using the BookingCommand"""
    return await booking_command.execute(update, context)

async def book_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Alias for start command to restart booking process"""
    return await booking_command.execute(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the conversation using the CancelCommand"""
    return await cancel_command.execute(update, context)

# State handlers using State Pattern
async def handle_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle location selection using LocationState"""
    return await state_manager.location_state.handle(update, context)

async def handle_pitch_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle pitch selection using PitchSelectionState"""
    return await state_manager.pitch_selection_state.handle(update, context)

async def handle_timeslot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle time slot selection using TimeSlotState"""
    return await state_manager.time_slot_state.handle(update, context)

async def handle_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle booking confirmation using ConfirmationState"""
    return await state_manager.confirmation_state.handle(update, context)

async def handle_contact_info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle contact information collection using ContactInfoState"""
    return await state_manager.contact_info_state.handle(update, context)

def main():
    try:
        # Create application
        application = Application.builder().token(TELEGRAM_TOKEN).build()

        # Add conversation handler for booking flow
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler("start", start), CommandHandler("book", book_command)],
            states={
                LOCATION: [CallbackQueryHandler(handle_location)],
                PITCH_SELECTION: [CallbackQueryHandler(handle_pitch_selection)],
                TIMESLOT: [CallbackQueryHandler(handle_timeslot)],
                CONFIRMATION: [CallbackQueryHandler(handle_confirmation)],
                CONTACT_INFO_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_info)],
                CONTACT_INFO_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_contact_info)],
            },
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        
        application.add_handler(conv_handler)

        logger.info('Bot started successfully')
        
        # Set up signal handlers for graceful shutdown
        import signal
        import sys
        
        def shutdown_handler(signum, frame):
            logger.info('Shutdown signal received, closing connections...')
            # Perform cleanup operations
            try:
                # Any cleanup needed
                logger.info('Closing connections')
            except Exception as e:
                logger.error(f'Error during shutdown: {str(e)}')
            finally:
                logger.info('Bot shutdown complete')
                sys.exit(0)
        
        # Register signal handlers
        signal.signal(signal.SIGINT, shutdown_handler)  # Ctrl+C
        signal.signal(signal.SIGTERM, shutdown_handler)  # Termination signal
        
        # Start the bot
        application.run_polling()
    except Exception as e:
        logger.error(f'Failed to start bot: {str(e)}')
        raise

if __name__ == '__main__':
    main()