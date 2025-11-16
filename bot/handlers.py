"""
Telegram bot handlers for torrent to Google Drive bot.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Dict

from telegram import Update, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import settings
from torrent import TorrentClient, TorrentInfo, format_size, format_speed
from drive import RcloneManager
from utils import FileSelector, parse_callback_data, format_eta
from utils.queue import JobQueue, JobStatus

logger = logging.getLogger(__name__)


class BotHandlers:
    """Handles all bot commands and callbacks."""

    def __init__(self):
        self.torrent_client = TorrentClient()
        self.rclone_manager = RcloneManager()
        self.job_queue = JobQueue(max_concurrent=settings.CONCURRENT_DOWNLOADS)
        self.torrent_info_cache: Dict[str, TorrentInfo] = {}
        self.user_message_cache: Dict[str, int] = {}  # chat_id -> message_id for status updates

    async def start(self):
        """Start the handler services."""
        await self.job_queue.start()
        logger.info("Bot handlers initialized")

    async def stop(self):
        """Stop the handler services."""
        await self.job_queue.stop()
        self.torrent_client.shutdown()
        logger.info("Bot handlers stopped")

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        welcome_message = (
            "🤖 *Welcome to Torrent to Google Drive Bot!*\n\n"
            "Send me a magnet link or upload a `.torrent` file, and I'll:\n"
            "1️⃣ Let you choose which files to download\n"
            "2️⃣ Download them using BitTorrent\n"
            "3️⃣ Upload to your Google Drive\n"
            "4️⃣ Give you direct links to stream/download\n\n"
            "*Commands:*\n"
            "/start - Show this message\n"
            "/status - Check your active jobs\n"
            "/cancel - Cancel a job\n\n"
            "Just send a magnet link or .torrent file to get started!"
        )
        await update.message.reply_text(welcome_message, parse_mode="Markdown")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        user_id = update.effective_user.id
        jobs = await self.job_queue.get_user_jobs(user_id)

        if not jobs:
            await update.message.reply_text("You have no active jobs.")
            return

        status_lines = ["*Your Jobs:*\n"]
        for job in jobs:
            status_icon = {
                JobStatus.QUEUED: "⏳",
                JobStatus.DOWNLOADING: "⬇️",
                JobStatus.UPLOADING: "⬆️",
                JobStatus.COMPLETED: "✅",
                JobStatus.FAILED: "❌",
                JobStatus.CANCELLED: "🚫"
            }.get(job.status, "❓")

            status_lines.append(f"{status_icon} *{job.torrent_name}*")
            status_lines.append(f"   Status: {job.status.value}")
            if job.progress > 0:
                status_lines.append(f"   Progress: {job.progress:.1f}%")
            status_lines.append(f"   Job ID: `{job.job_id}`\n")

        await update.message.reply_text("\n".join(status_lines), parse_mode="Markdown")

    async def handle_magnet(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle magnet link or torrent file."""
        user_id = update.effective_user.id
        chat_id = update.effective_chat.id

        # Get magnet link or download torrent file
        magnet_or_file = None

        if update.message.text and update.message.text.startswith("magnet:"):
            magnet_or_file = update.message.text
        elif update.message.document:
            # Download torrent file
            file = await update.message.document.get_file()
            file_path = os.path.join(settings.DOWNLOAD_DIR, f"{user_id}_{update.message.document.file_name}")
            os.makedirs(settings.DOWNLOAD_DIR, exist_ok=True)
            await file.download_to_drive(file_path)
            magnet_or_file = file_path

        if not magnet_or_file:
            await update.message.reply_text("❌ Please send a valid magnet link or .torrent file.")
            return

        # Send fetching message
        status_msg = await update.message.reply_text("🔍 Fetching torrent metadata...")

        try:
            # Get torrent info
            torrent_info = await self.torrent_client.get_torrent_info(magnet_or_file)
            self.torrent_info_cache[torrent_info.info_hash] = torrent_info

            # Create selection keyboard
            info_text = (
                f"📦 *{torrent_info.name}*\n\n"
                f"📊 Total Size: {format_size(torrent_info.total_size)}\n"
                f"📁 Files: {torrent_info.num_files}\n\n"
                f"What would you like to do?"
            )

            keyboard = FileSelector.create_simple_choice_keyboard(torrent_info.info_hash)
            await status_msg.edit_text(info_text, reply_markup=keyboard, parse_mode="Markdown")

        except TimeoutError:
            await status_msg.edit_text("❌ Failed to fetch torrent metadata. Please check the magnet link or try again.")
        except Exception as e:
            logger.error(f"Error handling magnet: {e}", exc_info=True)
            await status_msg.edit_text(f"❌ Error: {str(e)}")

    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle inline keyboard callbacks."""
        query = update.callback_query
        await query.answer()

        data = query.data
        parts = parse_callback_data(data)
        action = parts[0]

        try:
            if action == "downloadall":
                await self._handle_download_all(query, parts)
            elif action == "selectfiles":
                await self._handle_select_files(query, parts)
            elif action == "toggle":
                await self._handle_toggle_file(query, parts)
            elif action == "page":
                await self._handle_page_change(query, parts)
            elif action == "selectall":
                await self._handle_select_all(query, parts)
            elif action == "deselectall":
                await self._handle_deselect_all(query, parts)
            elif action == "confirm":
                await self._handle_confirm_download(query, parts)
            elif action == "cancel":
                await self._handle_cancel(query, parts)
            elif action == "noop":
                pass  # No operation (page indicator)

        except Exception as e:
            logger.error(f"Error handling callback: {e}", exc_info=True)
            await query.message.edit_text(f"❌ Error: {str(e)}")

    async def _handle_download_all(self, query, parts):
        """Handle download all files."""
        torrent_hash = parts[1]
        torrent_info = self.torrent_info_cache.get(torrent_hash)

        if not torrent_info:
            await query.message.edit_text("❌ Torrent info not found. Please try again.")
            return

        # Create job
        job = await self.job_queue.add_job(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            torrent_hash=torrent_hash,
            torrent_name=torrent_info.name,
            selected_files=None  # All files
        )

        await query.message.edit_text(
            f"✅ Job created!\n\n"
            f"📦 {torrent_info.name}\n"
            f"🆔 Job ID: `{job.job_id}`\n"
            f"⏳ Status: Queued\n\n"
            f"You'll be notified when the download starts and completes.",
            parse_mode="Markdown"
        )

        # Start processing
        asyncio.create_task(self._process_job(job))

    async def _handle_select_files(self, query, parts):
        """Handle file selection."""
        torrent_hash = parts[1]
        torrent_info = self.torrent_info_cache.get(torrent_hash)

        if not torrent_info:
            await query.message.edit_text("❌ Torrent info not found. Please try again.")
            return

        # Show file list
        keyboard = FileSelector.create_file_list_keyboard(torrent_info.files, 0, torrent_hash)
        await query.message.edit_text(
            f"📂 *Select files to download:*\n\n"
            f"Tap to select/deselect files.\n"
            f"Use buttons below to navigate and confirm.",
            reply_markup=keyboard,
            parse_mode="Markdown"
        )

    async def _handle_toggle_file(self, query, parts):
        """Handle file toggle."""
        torrent_hash = parts[1]
        file_index = int(parts[2])
        page = int(parts[3])

        torrent_info = self.torrent_info_cache.get(torrent_hash)
        if not torrent_info:
            return

        # Toggle selection
        torrent_info.files[file_index].selected = not torrent_info.files[file_index].selected

        # Update keyboard
        keyboard = FileSelector.create_file_list_keyboard(torrent_info.files, page, torrent_hash)
        await query.message.edit_reply_markup(reply_markup=keyboard)

    async def _handle_page_change(self, query, parts):
        """Handle page navigation."""
        torrent_hash = parts[1]
        page = int(parts[2])

        torrent_info = self.torrent_info_cache.get(torrent_hash)
        if not torrent_info:
            return

        keyboard = FileSelector.create_file_list_keyboard(torrent_info.files, page, torrent_hash)
        await query.message.edit_reply_markup(reply_markup=keyboard)

    async def _handle_select_all(self, query, parts):
        """Handle select all files."""
        torrent_hash = parts[1]
        page = int(parts[2])

        torrent_info = self.torrent_info_cache.get(torrent_hash)
        if not torrent_info:
            return

        for file in torrent_info.files:
            file.selected = True

        keyboard = FileSelector.create_file_list_keyboard(torrent_info.files, page, torrent_hash)
        await query.message.edit_reply_markup(reply_markup=keyboard)

    async def _handle_deselect_all(self, query, parts):
        """Handle deselect all files."""
        torrent_hash = parts[1]
        page = int(parts[2])

        torrent_info = self.torrent_info_cache.get(torrent_hash)
        if not torrent_info:
            return

        for file in torrent_info.files:
            file.selected = False

        keyboard = FileSelector.create_file_list_keyboard(torrent_info.files, page, torrent_hash)
        await query.message.edit_reply_markup(reply_markup=keyboard)

    async def _handle_confirm_download(self, query, parts):
        """Handle download confirmation."""
        torrent_hash = parts[1]
        torrent_info = self.torrent_info_cache.get(torrent_hash)

        if not torrent_info:
            await query.message.edit_text("❌ Torrent info not found. Please try again.")
            return

        # Get selected files
        selected_indices = [f.index for f in torrent_info.files if f.selected]

        if not selected_indices:
            # No files selected, download all
            selected_indices = None

        # Create job
        job = await self.job_queue.add_job(
            user_id=query.from_user.id,
            chat_id=query.message.chat_id,
            torrent_hash=torrent_hash,
            torrent_name=torrent_info.name,
            selected_files=selected_indices
        )

        files_text = f"{len(selected_indices)} files" if selected_indices else "all files"
        await query.message.edit_text(
            f"✅ Job created!\n\n"
            f"📦 {torrent_info.name}\n"
            f"📁 Downloading: {files_text}\n"
            f"🆔 Job ID: `{job.job_id}`\n"
            f"⏳ Status: Queued\n\n"
            f"You'll be notified when the download starts and completes.",
            parse_mode="Markdown"
        )

        # Start processing
        asyncio.create_task(self._process_job(job))

    async def _handle_cancel(self, query, parts):
        """Handle cancellation."""
        torrent_hash = parts[1]

        # Clean up torrent handle
        self.torrent_client.cleanup(torrent_hash)

        # Remove from cache
        if torrent_hash in self.torrent_info_cache:
            del self.torrent_info_cache[torrent_hash]

        await query.message.edit_text("🚫 Operation cancelled.")

    async def _process_job(self, job):
        """Process a download job."""
        from telegram import Bot

        bot = Bot(settings.BOT_TOKEN)
        torrent_info = self.torrent_info_cache.get(job.torrent_hash)

        if not torrent_info:
            await self.job_queue.fail_job(job.job_id, "Torrent info not found")
            return

        try:
            # Send starting message
            msg = await bot.send_message(
                chat_id=job.chat_id,
                text=f"⬇️ *Downloading*\n\n📦 {job.torrent_name}\n⏳ Starting...",
                parse_mode="Markdown"
            )
            self.user_message_cache[job.job_id] = msg.message_id

            # Download callback
            async def download_progress_callback(progress):
                await self.job_queue.update_job(
                    job.job_id,
                    progress=progress.progress,
                    download_speed=progress.download_rate,
                    eta=progress.eta
                )

                # Update message
                text = (
                    f"⬇️ *Downloading*\n\n"
                    f"📦 {job.torrent_name}\n"
                    f"📊 Progress: {progress.progress:.1f}%\n"
                    f"⚡ Speed: {format_speed(progress.download_rate)}\n"
                    f"👥 Peers: {progress.num_peers}\n"
                    f"⏱️ ETA: {format_eta(progress.eta)}"
                )

                try:
                    await bot.edit_message_text(
                        chat_id=job.chat_id,
                        message_id=msg.message_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass  # Ignore if message hasn't changed

            # Download torrent
            await self.job_queue.update_job(job.job_id, status=JobStatus.DOWNLOADING)
            local_path = await self.torrent_client.download(
                job.torrent_hash,
                job.selected_files,
                download_progress_callback
            )

            await self.job_queue.update_job(job.job_id, local_path=local_path)

            # Upload to Google Drive
            await self.job_queue.update_job(job.job_id, status=JobStatus.UPLOADING)
            await bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=msg.message_id,
                text=f"⬆️ *Uploading to Google Drive*\n\n📦 {job.torrent_name}\n⏳ Starting...",
                parse_mode="Markdown"
            )

            # Upload callback
            async def upload_progress_callback(progress):
                text = (
                    f"⬆️ *Uploading to Google Drive*\n\n"
                    f"📦 {job.torrent_name}\n"
                    f"📊 Progress: {progress.progress:.1f}%\n"
                    f"⚡ Speed: {format_speed(progress.speed)}\n"
                    f"⏱️ ETA: {format_eta(progress.eta)}"
                )

                try:
                    await bot.edit_message_text(
                        chat_id=job.chat_id,
                        message_id=msg.message_id,
                        text=text,
                        parse_mode="Markdown"
                    )
                except Exception:
                    pass

            remote_path = job.torrent_name
            await self.rclone_manager.upload(local_path, remote_path, upload_progress_callback)

            # Get links
            gdrive_link = await self.rclone_manager.get_file_link(remote_path)
            index_link = settings.get_index_url(remote_path)

            # Complete job
            await self.job_queue.complete_job(job.job_id, gdrive_link, index_link)

            # Send completion message
            keyboard = FileSelector.create_completion_keyboard(gdrive_link, index_link)
            completion_text = (
                f"✅ *Upload Complete!*\n\n"
                f"📦 {job.torrent_name}\n"
                f"📊 Size: {format_size(torrent_info.total_size)}\n\n"
                f"Click the buttons below to access your files:"
            )

            await bot.edit_message_text(
                chat_id=job.chat_id,
                message_id=msg.message_id,
                text=completion_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )

            # Cleanup
            self.torrent_client.cleanup(job.torrent_hash)
            if os.path.exists(local_path):
                if os.path.isdir(local_path):
                    shutil.rmtree(local_path)
                else:
                    os.remove(local_path)

        except Exception as e:
            logger.error(f"Error processing job {job.job_id}: {e}", exc_info=True)
            await self.job_queue.fail_job(job.job_id, str(e))

            # Send error message
            try:
                await bot.send_message(
                    chat_id=job.chat_id,
                    text=f"❌ *Job Failed*\n\n📦 {job.torrent_name}\n\n⚠️ Error: {str(e)}",
                    parse_mode="Markdown"
                )
            except Exception:
                pass

            # Cleanup
            self.torrent_client.cleanup(job.torrent_hash)
