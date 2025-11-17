"""
Rclone integration for uploading to Google Drive.
"""
import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from config import settings

logger = logging.getLogger(__name__)


@dataclass
class UploadProgress:
    """Upload progress information."""
    uploaded: int
    total_size: int
    progress: float
    speed: float
    eta: int
    current_file: str


class RcloneManager:
    """Manages rclone operations for Google Drive."""

    def __init__(self):
        self.config_path = settings.RCLONE_CONFIG_PATH
        self._ensure_config()

    def _ensure_config(self):
        """Ensure rclone config exists."""
        if not os.path.exists(self.config_path):
            # Try to create from environment variable
            rclone_config_content = os.getenv("RCLONE_CONFIG")
            if rclone_config_content:
                os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
                with open(self.config_path, "w") as f:
                    f.write(rclone_config_content)
                logger.info(f"Created rclone config from environment variable")
            else:
                logger.warning(f"Rclone config not found at {self.config_path}")

    async def upload(
        self,
        local_path: str,
        remote_path: str,
        progress_callback: Optional[Callable[[UploadProgress], None]] = None
    ) -> str:
        """
        Upload file or directory to Google Drive using rclone.

        Args:
            local_path: Local file or directory path
            remote_path: Remote path relative to base directory
            progress_callback: Callback for progress updates

        Returns:
            Remote path on Google Drive
        """
        local_path = Path(local_path)
        if not local_path.exists():
            raise FileNotFoundError(f"Local path not found: {local_path}")

        # Construct full remote path
        full_remote_path = settings.get_gdrive_path(remote_path)

        logger.info(f"Uploading {local_path} to {full_remote_path}")

        # Build rclone command
        cmd = [
            "rclone",
            "copy" if local_path.is_file() else "copy",
            str(local_path) if local_path.is_file() else str(local_path),
            full_remote_path,
            "--config", self.config_path,
            "--progress",
            "--stats", "2s",
            "--stats-one-line",
            "--drive-chunk-size", "64M",
            "--transfers", "4",
            "--checkers", "8",
            "--buffer-size", "16M",
            "--drive-upload-cutoff", "8M",
        ]

        # If uploading a directory, ensure we copy its contents
        if local_path.is_dir():
            # For directories, we want to copy all contents
            cmd = [
                "rclone",
                "copy",
                str(local_path),
                full_remote_path,
                "--config", self.config_path,
                "--progress",
                "--stats", "2s",
                "--stats-one-line",
                "--drive-chunk-size", "64M",
                "--transfers", "4",
                "--checkers", "8",
                "--buffer-size", "16M",
                "--drive-upload-cutoff", "8M",
            ]

        # Execute rclone
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        # Monitor progress
        total_size = self._get_size(local_path)
        last_progress = None

        while True:
            line = await process.stdout.readline()
            if not line:
                break

            line = line.decode().strip()
            if not line:
                continue

            # Parse progress from rclone output
            if progress_callback:
                progress = self._parse_progress(line, total_size)
                if progress and progress != last_progress:
                    await progress_callback(progress)
                    last_progress = progress

            logger.debug(f"Rclone: {line}")

        # Wait for process to complete
        await process.wait()

        if process.returncode != 0:
            raise Exception(f"Rclone upload failed with code {process.returncode}")

        logger.info(f"Upload completed: {full_remote_path}")
        return remote_path

    def _get_size(self, path: Path) -> int:
        """Get total size of file or directory."""
        if path.is_file():
            return path.stat().st_size

        total = 0
        for item in path.rglob("*"):
            if item.is_file():
                total += item.stat().st_size
        return total

    def _parse_progress(self, line: str, total_size: int) -> Optional[UploadProgress]:
        """Parse progress from rclone output."""
        # Example line: "Transferred:   	  123.456 MiB / 1.234 GiB, 10%, 5.678 MiB/s, ETA 1m23s"
        match = re.search(
            r"Transferred:\s+[\d.]+\s*\w+\s*/\s*([\d.]+)\s*(\w+),\s*([\d.]+)%,\s*([\d.]+)\s*(\w+)/s",
            line
        )

        if match:
            # Extract values
            transferred_str = line.split("/")[0].split(":")[1].strip()
            progress_percent = float(match.group(3))
            speed_value = float(match.group(4))
            speed_unit = match.group(5)

            # Convert to bytes
            uploaded = int(total_size * progress_percent / 100)
            speed_bytes = self._convert_to_bytes(speed_value, speed_unit)

            # Calculate ETA
            remaining = total_size - uploaded
            eta = int(remaining / speed_bytes) if speed_bytes > 0 else -1

            # Try to get current file
            current_file = ""
            file_match = re.search(r"\*\s+(.+?):", line)
            if file_match:
                current_file = file_match.group(1)

            return UploadProgress(
                uploaded=uploaded,
                total_size=total_size,
                progress=progress_percent,
                speed=speed_bytes,
                eta=eta,
                current_file=current_file
            )

        return None

    def _convert_to_bytes(self, value: float, unit: str) -> float:
        """Convert size with unit to bytes."""
        units = {
            "B": 1,
            "k": 1024,
            "M": 1024 ** 2,
            "G": 1024 ** 3,
            "T": 1024 ** 4,
            "Ki": 1024,
            "Mi": 1024 ** 2,
            "Gi": 1024 ** 3,
            "Ti": 1024 ** 4,
        }
        return value * units.get(unit, 1)

    async def get_file_link(self, remote_path: str) -> Optional[str]:
        """
        Get Google Drive shareable link for a file.

        Args:
            remote_path: Remote path relative to base directory

        Returns:
            Shareable link or None
        """
        full_remote_path = settings.get_gdrive_path(remote_path)

        cmd = [
            "rclone",
            "link",
            full_remote_path,
            "--config", self.config_path
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                link = stdout.decode().strip()
                return link if link else None
            else:
                logger.error(f"Failed to get link: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Error getting file link: {e}")
            return None

    async def list_files(self, remote_path: str = "") -> list:
        """
        List files in remote directory.

        Args:
            remote_path: Remote path relative to base directory

        Returns:
            List of file information
        """
        full_remote_path = settings.get_gdrive_path(remote_path)

        cmd = [
            "rclone",
            "lsjson",
            full_remote_path,
            "--config", self.config_path
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                return json.loads(stdout.decode())
            else:
                logger.error(f"Failed to list files: {stderr.decode()}")
                return []

        except Exception as e:
            logger.error(f"Error listing files: {e}")
            return []

    async def get_folder_weblink(self, remote_path: str) -> Optional[str]:
        """
        Get Google Drive folder web view link.

        Args:
            remote_path: Remote path relative to base directory

        Returns:
            Web view link for the folder or None
        """
        full_remote_path = settings.get_gdrive_path(remote_path)

        # Get folder ID using lsjson with --files-only=false --dirs-only
        cmd = [
            "rclone",
            "lsjson",
            full_remote_path,
            "--config", self.config_path,
            "--max-depth", "1"
        ]

        try:
            # First, we need to get the parent directory and find this folder
            parent_path = str(Path(remote_path).parent) if remote_path != "." else ""
            folder_name = Path(remote_path).name if remote_path != "." else remote_path

            full_parent_path = settings.get_gdrive_path(parent_path) if parent_path else settings.get_gdrive_path("")

            cmd = [
                "rclone",
                "lsjson",
                full_parent_path,
                "--config", self.config_path,
                "--dirs-only"
            ]

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                items = json.loads(stdout.decode())
                for item in items:
                    if item.get("Name") == folder_name and item.get("IsDir"):
                        folder_id = item.get("ID")
                        if folder_id:
                            # Construct Google Drive folder view URL
                            return f"https://drive.google.com/drive/folders/{folder_id}"

                logger.warning(f"Could not find folder ID for {remote_path}")
                return None
            else:
                logger.error(f"Failed to get folder info: {stderr.decode()}")
                return None

        except Exception as e:
            logger.error(f"Error getting folder weblink: {e}")
            return None

    async def delete(self, remote_path: str):
        """
        Delete file or directory from Google Drive.

        Args:
            remote_path: Remote path relative to base directory
        """
        full_remote_path = settings.get_gdrive_path(remote_path)

        cmd = [
            "rclone",
            "purge" if remote_path.endswith("/") else "delete",
            full_remote_path,
            "--config", self.config_path
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            await process.wait()

            if process.returncode == 0:
                logger.info(f"Deleted: {full_remote_path}")
            else:
                stderr = await process.stderr.read()
                logger.error(f"Failed to delete: {stderr.decode()}")

        except Exception as e:
            logger.error(f"Error deleting: {e}")

    async def empty_drive_folder(self) -> dict:
        """
        Empty the entire Google Drive base folder (admin only).

        Returns:
            Dict with success status and message
        """
        base_path = settings.get_gdrive_path("")

        logger.warning(f"EMPTYING ENTIRE DRIVE FOLDER: {base_path}")

        cmd = [
            "rclone",
            "delete",
            base_path,
            "--config", self.config_path,
            "--rmdirs"  # Also remove empty directories
        ]

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode == 0:
                logger.info(f"Successfully emptied drive folder: {base_path}")
                return {
                    'success': True,
                    'message': 'Drive folder emptied successfully'
                }
            else:
                error_msg = stderr.decode()
                logger.error(f"Failed to empty drive folder: {error_msg}")
                return {
                    'success': False,
                    'message': f'Failed to empty drive: {error_msg}'
                }

        except Exception as e:
            logger.error(f"Error emptying drive folder: {e}")
            return {
                'success': False,
                'message': f'Error: {str(e)}'
            }
