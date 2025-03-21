import os
import sys
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from loguru import logger

from config import settings
from bot.handlers import start_command, help_command, handle_message, error_handler

# Configure logger
logger.remove()
logger.add(
    sys.stderr,
    format="{time} | {level} | {message}",
    level="INFO"
)
logger.add(
    "logs/bot.log",
    rotation="10 MB",
    retention="1 week",
    format="{time} | {level} | {message}",
    level="INFO"
)

# Ensure logs directory exists
os.makedirs("logs", exist_ok=True)

def setup_application():
    """Set up the application with all handlers."""
    # Validate token
    if not settings.bot_token:
        logger.error("Bot token not found. Set the BOT_TOKEN environment variable.")
        sys.exit(1)
    
    # Create application
    application = ApplicationBuilder().token(settings.bot_token).build()
    
    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    
    # Add message handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    return application

if __name__ == "__main__":
    # Если запускаем напрямую этот файл
    try:
        app = setup_application()
        logger.info("Starting bot...")
        app.run_polling()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user.")
    except Exception as e:
        logger.error(f"Bot stopped due to error: {str(e)}")
        sys.exit(1) 