"""
Main entry point for Torrent to Google Drive Bot.
"""
import asyncio
import logging
import os
import signal
import sys
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters

from config import settings
from bot import BotHandlers
from webapp.torrent_processor import WebTorrentProcessor

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TorrentBot:
    """Main bot application."""

    def __init__(self):
        self.app = None
        self.handlers = None
        self.web_processor = None

    async def initialize(self):
        """Initialize the bot application."""
        # Validate settings
        valid, error = settings.validate()
        if not valid:
            logger.error(f"Configuration error: {error}")
            sys.exit(1)

        logger.info("Initializing Torrent to Google Drive Bot...")

        # Create download directory
        os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)

        # Initialize handlers
        self.handlers = BotHandlers()
        await self.handlers.start()

        # Initialize web torrent processor
        self.web_processor = WebTorrentProcessor()
        logger.info("Web torrent processor initialized")

        # Build application
        self.app = Application.builder().token(settings.BOT_TOKEN).build()

        # Register handlers
        self.app.add_handler(CommandHandler("start", self.handlers.cmd_start))
        self.app.add_handler(CommandHandler("status", self.handlers.cmd_status))

        # Message handlers for magnet links and torrent files
        self.app.add_handler(MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            self.handlers.handle_magnet
        ))
        self.app.add_handler(MessageHandler(
            filters.Document.ALL,
            self.handlers.handle_magnet
        ))

        # Callback query handler for inline keyboards
        self.app.add_handler(CallbackQueryHandler(self.handlers.handle_callback))

        logger.info("Bot initialized successfully")

    async def start(self):
        """Start the bot."""
        await self.initialize()

        logger.info("Starting bot polling...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(drop_pending_updates=True)

        # Start web torrent processor in background
        asyncio.create_task(self.web_processor.start())
        logger.info("Web torrent processor started")

        logger.info("Bot is running!")

    async def stop(self):
        """Stop the bot."""
        logger.info("Stopping bot...")

        if self.web_processor:
            await self.web_processor.stop()

        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()

        if self.handlers:
            await self.handlers.stop()

        logger.info("Bot stopped")

    async def run(self):
        """Run the bot with proper signal handling."""
        # Setup signal handlers
        loop = asyncio.get_event_loop()

        def signal_handler(sig):
            logger.info(f"Received signal {sig}, shutting down...")
            loop.create_task(self.stop())
            loop.stop()

        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: signal_handler(s))

        try:
            await self.start()
            # Keep running
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            pass
        finally:
            await self.stop()


async def main():
    """Main entry point."""
    bot = TorrentBot()
    await bot.run()


if __name__ == "__main__":
    if sys.platform == "win32":
        # Windows-specific event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
