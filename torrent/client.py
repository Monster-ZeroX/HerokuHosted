"""
Torrent client implementation using libtorrent.
"""
import asyncio
import hashlib
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, List
from urllib.parse import unquote

import libtorrent as lt

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class TorrentFile:
    """Represents a file in a torrent."""
    index: int
    path: str
    size: int
    selected: bool = False


@dataclass
class TorrentInfo:
    """Torrent metadata."""
    name: str
    total_size: int
    num_files: int
    files: List[TorrentFile]
    info_hash: str


@dataclass
class DownloadProgress:
    """Download progress information."""
    status: str
    downloaded: int
    total_size: int
    download_rate: float
    upload_rate: float
    num_peers: int
    progress: float
    eta: int


class TorrentClient:
    """Manages torrent downloads using libtorrent."""

    def __init__(self, download_dir: str = None):
        self.download_dir = download_dir or settings.DOWNLOAD_DIR
        self.session = lt.session()
        self._configure_session()
        self.handles = {}

    def _configure_session(self):
        """Configure libtorrent session."""
        settings_pack = {
            "user_agent": "TorrentToDriveBot/1.0",
            "listen_interfaces": "0.0.0.0:6881",
            "enable_dht": True,
            "enable_lsd": True,
            "enable_upnp": True,
            "enable_natpmp": True,
            "announce_to_all_tiers": True,
            "announce_to_all_trackers": True,
            "aio_threads": 8,
            "checking_mem_usage": 1024,
        }
        self.session.apply_settings(settings_pack)

        # Add DHT routers
        self.session.add_dht_router("router.utorrent.com", 6881)
        self.session.add_dht_router("router.bittorrent.com", 6881)
        self.session.add_dht_router("dht.transmissionbt.com", 6881)
        self.session.add_dht_router("dht.aelitis.com", 6881)

        logger.info("Torrent session configured")

    async def get_torrent_info(self, magnet_or_file: str) -> TorrentInfo:
        """
        Get torrent metadata without downloading.

        Args:
            magnet_or_file: Magnet link or path to .torrent file

        Returns:
            TorrentInfo object with torrent metadata
        """
        logger.info(f"Getting torrent info for: {magnet_or_file[:50]}...")

        # Create temporary handle to get metadata
        params = {
            "save_path": self.download_dir,
            "storage_mode": lt.storage_mode_t.storage_mode_sparse,
        }

        if magnet_or_file.startswith("magnet:"):
            handle = lt.add_magnet_uri(self.session, magnet_or_file, params)
        else:
            # Assume it's a file path
            info = lt.torrent_info(magnet_or_file)
            params["ti"] = info
            handle = self.session.add_torrent(params)

        # Wait for metadata
        logger.info("Waiting for metadata...")
        timeout = 60  # 60 seconds timeout
        start_time = time.time()

        while not handle.has_metadata():
            if time.time() - start_time > timeout:
                self.session.remove_torrent(handle)
                raise TimeoutError("Failed to fetch torrent metadata")
            await asyncio.sleep(0.5)

        # Extract torrent info
        torrent_info = handle.get_torrent_info()
        files = []

        for i in range(torrent_info.num_files()):
            file_entry = torrent_info.files().at(i)
            files.append(TorrentFile(
                index=i,
                path=file_entry.path,
                size=file_entry.size,
                selected=False
            ))

        info = TorrentInfo(
            name=torrent_info.name(),
            total_size=torrent_info.total_size(),
            num_files=torrent_info.num_files(),
            files=files,
            info_hash=str(torrent_info.info_hash())
        )

        # Store handle for later use
        self.handles[info.info_hash] = handle

        logger.info(f"Got torrent info: {info.name} ({len(files)} files)")
        return info

    async def download(
        self,
        info_hash: str,
        selected_indices: Optional[List[int]] = None,
        progress_callback: Optional[Callable[[DownloadProgress], None]] = None
    ) -> str:
        """
        Download torrent files.

        Args:
            info_hash: Torrent info hash
            selected_indices: List of file indices to download (None = all)
            progress_callback: Callback for progress updates

        Returns:
            Path to downloaded files
        """
        if info_hash not in self.handles:
            raise ValueError(f"No torrent handle found for hash: {info_hash}")

        handle = self.handles[info_hash]
        torrent_info = handle.get_torrent_info()

        # Configure file priorities
        file_priorities = []
        for i in range(torrent_info.num_files()):
            if selected_indices is None or i in selected_indices:
                file_priorities.append(4)  # High priority
            else:
                file_priorities.append(0)  # Don't download

        handle.prioritize_files(file_priorities)
        handle.resume()

        logger.info(f"Starting download: {torrent_info.name()}")

        # Wait for download to complete
        last_update = 0
        while not handle.is_seed():
            status = handle.status()

            # Check for errors
            if status.error:
                raise Exception(f"Download error: {status.error}")

            # Update progress
            current_time = time.time()
            if progress_callback and (current_time - last_update) >= settings.PROGRESS_UPDATE_INTERVAL:
                progress = DownloadProgress(
                    status=status.state.name,
                    downloaded=status.total_done,
                    total_size=status.total_wanted,
                    download_rate=status.download_rate,
                    upload_rate=status.upload_rate,
                    num_peers=status.num_peers,
                    progress=status.progress * 100,
                    eta=self._calculate_eta(status)
                )
                await progress_callback(progress)
                last_update = current_time

            await asyncio.sleep(1)

        logger.info(f"Download completed: {torrent_info.name()}")

        # Get the download path
        save_path = Path(handle.save_path()) / torrent_info.name()

        # Optional: seed for configured time
        if settings.SEED_TIME > 0:
            logger.info(f"Seeding for {settings.SEED_TIME} seconds...")
            await asyncio.sleep(settings.SEED_TIME)

        return str(save_path)

    def _calculate_eta(self, status) -> int:
        """Calculate estimated time to completion."""
        if status.download_rate <= 0:
            return -1
        remaining = status.total_wanted - status.total_done
        return int(remaining / status.download_rate)

    def cancel_download(self, info_hash: str):
        """Cancel an ongoing download."""
        if info_hash in self.handles:
            handle = self.handles[info_hash]
            self.session.remove_torrent(handle)
            del self.handles[info_hash]
            logger.info(f"Cancelled download: {info_hash}")

    def cleanup(self, info_hash: str):
        """Clean up after download."""
        if info_hash in self.handles:
            handle = self.handles[info_hash]
            self.session.remove_torrent(handle)
            del self.handles[info_hash]

    def shutdown(self):
        """Shutdown the torrent client."""
        logger.info("Shutting down torrent client...")
        for info_hash in list(self.handles.keys()):
            self.cleanup(info_hash)


def format_size(size_bytes: int) -> str:
    """Format bytes to human-readable size."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


def format_speed(bytes_per_sec: float) -> str:
    """Format bytes/sec to human-readable speed."""
    return f"{format_size(int(bytes_per_sec))}/s"
