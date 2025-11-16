"""
Background torrent processor for web app submissions.
Monitors database for queued torrents and processes them using the bot's download system.
"""
import asyncio
import logging
import os
import shutil
from pathlib import Path
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import settings
from torrent import TorrentClient
from drive import RcloneManager
from webapp.models import Torrent, TorrentFile, db

logger = logging.getLogger(__name__)


class WebTorrentProcessor:
    """Processes torrents submitted via web app."""

    def __init__(self):
        self.torrent_client = TorrentClient()
        self.rclone_manager = RcloneManager()
        self.running = False
        self.processing_hashes = set()  # Track currently processing torrent IDs

    async def start(self):
        """Start the processor."""
        self.running = True
        logger.info("Web torrent processor started")

        # Process queued torrents in loop
        while self.running:
            try:
                await self.process_queued_torrents()
                await asyncio.sleep(5)  # Check every 5 seconds
            except Exception as e:
                logger.error(f"Error in processor loop: {e}", exc_info=True)
                await asyncio.sleep(10)

    async def stop(self):
        """Stop the processor."""
        self.running = False
        self.torrent_client.shutdown()
        logger.info("Web torrent processor stopped")

    async def process_queued_torrents(self):
        """Check database for queued torrents and process them."""
        from webapp.app import app

        with app.app_context():
            # Get all queued torrents
            torrents = Torrent.query.filter(
                Torrent.status == 'queued'
            ).limit(settings.CONCURRENT_DOWNLOADS).all()

            for torrent_record in torrents:
                # Skip if already processing (check by ID)
                if torrent_record.id in self.processing_hashes:
                    continue

                # Process in background
                asyncio.create_task(self.process_torrent(torrent_record.id))

    async def process_torrent(self, torrent_id: int):
        """Process a single torrent."""
        from webapp.app import app

        # Mark as processing
        self.processing_hashes.add(torrent_id)

        with app.app_context():
            torrent_record = Torrent.query.get(torrent_id)
            if not torrent_record or torrent_record.status != 'queued':
                self.processing_hashes.discard(torrent_id)
                return

            magnet_link = torrent_record.magnet_link

            try:
                logger.info(f"Processing web torrent {torrent_id}: {magnet_link[:50]}...")

                # Step 1: Fetch metadata
                torrent_record.status = 'downloading'
                db.session.commit()

                torrent_info = await self.torrent_client.get_metadata(magnet_link)

                # Update torrent record with metadata
                torrent_record.info_hash = torrent_info.info_hash
                torrent_record.name = torrent_info.name
                torrent_record.total_size = torrent_info.total_size
                db.session.commit()

                logger.info(f"Metadata fetched for {torrent_info.name}")

                # Step 2: Download all files (web app doesn't support file selection yet)
                download_path = await self.download_torrent(torrent_info, torrent_record)

                # Step 3: Upload to Google Drive
                torrent_record.status = 'uploading'
                torrent_record.progress = 0.0
                db.session.commit()

                gdrive_link = await self.upload_to_drive(download_path, torrent_info.name, torrent_record)

                # Step 4: Create file records
                await self.create_file_records(torrent_record, download_path, torrent_info.name)

                # Step 5: Mark as completed
                torrent_record.status = 'completed'
                torrent_record.progress = 100.0
                torrent_record.gdrive_link = gdrive_link
                db.session.commit()

                logger.info(f"Torrent {torrent_id} completed successfully")

                # Cleanup
                self.cleanup_download(download_path)

            except Exception as e:
                logger.error(f"Error processing torrent {torrent_id}: {e}", exc_info=True)

                with app.app_context():
                    torrent_record = Torrent.query.get(torrent_id)
                    if torrent_record:
                        torrent_record.status = 'failed'
                        db.session.commit()

            finally:
                self.processing_hashes.discard(torrent_id)

    async def download_torrent(self, torrent_info, torrent_record) -> Path:
        """Download torrent files."""
        download_dir = Path(settings.DOWNLOAD_DIR)
        download_dir.mkdir(parents=True, exist_ok=True)

        def progress_callback(progress):
            """Update database with download progress."""
            from webapp.app import app

            with app.app_context():
                torrent_record = Torrent.query.get(torrent_record.id)
                if torrent_record:
                    torrent_record.progress = progress.progress
                    db.session.commit()

        # Download all files
        download_path = await self.torrent_client.download(
            torrent_info.info_hash,
            selected_indices=None,  # Download all files
            progress_callback=progress_callback
        )

        logger.info(f"Download completed: {download_path}")
        return Path(download_path)

    async def upload_to_drive(self, local_path: Path, torrent_name: str, torrent_record) -> str:
        """Upload files to Google Drive."""
        remote_path = f"{settings.RCLONE_BASE_DIR}/{torrent_name}"

        def progress_callback(progress):
            """Update database with upload progress."""
            from webapp.app import app

            with app.app_context():
                torrent_record = Torrent.query.get(torrent_record.id)
                if torrent_record:
                    # Upload progress is 50-100% of total
                    torrent_record.progress = 50.0 + (progress.progress / 2.0)
                    db.session.commit()

        gdrive_link = await self.rclone_manager.upload(
            str(local_path),
            remote_path,
            progress_callback=progress_callback
        )

        logger.info(f"Upload completed: {gdrive_link}")
        return gdrive_link

    async def create_file_records(self, torrent_record, download_path: Path, torrent_name: str):
        """Create TorrentFile records in database."""
        from webapp.app import app

        with app.app_context():
            torrent_record = Torrent.query.get(torrent_record.id)
            if not torrent_record:
                return

            # Get all files in download directory
            if download_path.is_file():
                files = [download_path]
            else:
                files = list(download_path.rglob('*'))
                files = [f for f in files if f.is_file()]

            for file_path in files:
                # Get relative path for index URL
                if download_path.is_file():
                    relative_path = file_path.name
                else:
                    relative_path = file_path.relative_to(download_path)

                # Construct index link if INDEX_BASE_URL is set
                index_link = None
                if settings.INDEX_BASE_URL:
                    index_path = f"{settings.RCLONE_BASE_DIR}/{torrent_name}/{relative_path}"
                    index_link = f"{settings.INDEX_BASE_URL.rstrip('/')}/{index_path}"

                # Create file record
                torrent_file = TorrentFile(
                    torrent_id=torrent_record.id,
                    file_path=str(relative_path),
                    file_size=file_path.stat().st_size,
                    index_link=index_link
                )
                db.session.add(torrent_file)

            db.session.commit()
            logger.info(f"Created {len(files)} file records for torrent {torrent_record.id}")

    def cleanup_download(self, download_path: Path):
        """Clean up downloaded files."""
        try:
            if download_path.exists():
                if download_path.is_file():
                    download_path.unlink()
                else:
                    shutil.rmtree(download_path)
                logger.info(f"Cleaned up download: {download_path}")
        except Exception as e:
            logger.error(f"Error cleaning up {download_path}: {e}")


async def main():
    """Main entry point for standalone processor."""
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=getattr(logging, settings.LOG_LEVEL)
    )

    processor = WebTorrentProcessor()

    try:
        await processor.start()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal")
    finally:
        await processor.stop()


if __name__ == '__main__':
    asyncio.run(main())
