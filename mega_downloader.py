"""
Mega.nz downloader module with premium account support.
Downloads files and folders from Mega.nz links using mega.py library.
"""
import os
import logging
from typing import Optional, Dict, List
from pathlib import Path

logger = logging.getLogger(__name__)

# Try to import mega.py
try:
    from mega import Mega
    MEGA_AVAILABLE = True
except ImportError as e:
    logger.error(f"mega.py library not available: {e}")
    MEGA_AVAILABLE = False
    Mega = None


class MegaDownloader:
    """Handle Mega.nz downloads with premium account support."""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Mega downloader.

        Args:
            email: Mega.nz account email (for premium features)
            password: Mega.nz account password
        """
        if not MEGA_AVAILABLE:
            raise ImportError("mega.py library is not available")

        self.email = email or os.environ.get('MEGA_EMAIL')
        self.password = password or os.environ.get('MEGA_PASSWORD')
        self.mega = None
        self.enabled = False  # Disabled by default
        self._login()

    def _login(self):
        """Login to Mega.nz account."""
        try:
            self.mega = Mega()
            if self.email and self.password:
                logger.info(f"Logging into Mega.nz with account: {self.email}")
                self.mega.login(self.email, self.password)
                logger.info("Successfully logged into Mega.nz premium account")
                self.enabled = True
            else:
                logger.warning("No Mega.nz credentials provided, using anonymous mode")
                self.enabled = True  # Anonymous mode is considered enabled
        except Exception as e:
            logger.error(f"Failed to login to Mega.nz: {e}. Mega.nz functionality will be disabled.")
            self.enabled = False
            # Do not raise exception, just disable the functionality

    def parse_mega_link(self, url: str) -> Dict[str, str]:
        """
        Parse Mega.nz link to extract type and ID.

        Args:
            url: Mega.nz URL (file or folder)

        Returns:
            Dict with 'type' (file/folder) and 'url'
        """
        if not self.enabled:
            raise RuntimeError("Mega.nz downloader is not available due to a login failure.")
        
        url = url.strip()

        # File link patterns:
        # https://mega.nz/file/ABC123#key
        # https://mega.nz/#!ABC123!key
        if '/file/' in url or '/#!' in url:
            return {'type': 'file', 'url': url}

        # Folder link patterns:
        # https://mega.nz/folder/ABC123#key
        # https://mega.nz/#F!ABC123!key
        elif '/folder/' in url or '/#F!' in url:
            return {'type': 'folder', 'url': url}

        else:
            raise ValueError(f"Invalid Mega.nz link format: {url}")

    def get_file_info(self, url: str) -> Dict:
        """
        Get information about a Mega.nz file.

        Args:
            url: Mega.nz file URL

        Returns:
            Dict with file name and size
        """
        if not self.enabled:
            raise RuntimeError("Mega.nz downloader is not available due to a login failure.")
            
        try:
            link_info = self.parse_mega_link(url)

            if link_info['type'] == 'file':
                # Get file details using mega.py
                file_info = self.mega.get_public_url_info(url)
                return {
                    'name': file_info.get('name', 'Mega File'),
                    'size': file_info.get('size', 0),
                    'type': 'file'
                }
            else:
                # For folders, we can't easily get info without downloading
                return {
                    'name': 'Mega Folder',
                    'size': 0,  # Unknown until download
                    'type': 'folder'
                }

        except Exception as e:
            logger.error(f"Failed to get Mega.nz file info: {e}")
            # Return default info
            return {
                'name': 'Mega Download',
                'size': 0,
                'type': 'file'
            }

    def download_file(self, url: str, dest_path: str, progress_callback=None) -> str:
        """
        Download a single file from Mega.nz.

        Args:
            url: Mega.nz file URL
            dest_path: Destination directory path
            progress_callback: Optional callback for progress updates

        Returns:
            Path to downloaded file
        """
        if not self.enabled:
            raise RuntimeError("Mega.nz downloader is not available due to a login failure.")
            
        try:
            logger.info(f"Downloading Mega.nz file from: {url}")
            logger.info(f"Destination: {dest_path}")

            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)

            # Download the file using mega.py
            file_path = self.mega.download_url(url, dest_path)

            logger.info(f"Successfully downloaded file to: {file_path}")
            return file_path

        except Exception as e:
            logger.error(f"Failed to download Mega.nz file: {e}")
            raise

    def download_folder(self, url: str, dest_path: str, progress_callback=None) -> List[str]:
        """
        Download an entire folder from Mega.nz.

        Args:
            url: Mega.nz folder URL
            dest_path: Destination directory path
            progress_callback: Optional callback for progress updates

        Returns:
            List of paths to downloaded files
        """
        if not self.enabled:
            raise RuntimeError("Mega.nz downloader is not available due to a login failure.")
            
        try:
            logger.info(f"Downloading Mega.nz folder from: {url}")
            logger.info(f"Destination: {dest_path}")

            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)

            # For folders, mega.py might not support direct folder download
            # We'll try to use download_url which might handle it
            try:
                result = self.mega.download_url(url, dest_path)
                if isinstance(result, list):
                    return result
                else:
                    return [result]
            except Exception as e:
                logger.error(f"Folder download not fully supported: {e}")
                raise NotImplementedError(
                    "Folder downloads are not fully supported. "
                    "Please use individual file links or try a different method."
                )

        except Exception as e:
            logger.error(f"Failed to download Mega.nz folder: {e}")
            raise

    def download(self, url: str, dest_path: str, progress_callback=None) -> Dict:
        """
        Download file or folder from Mega.nz (auto-detect).

        Args:
            url: Mega.nz URL (file or folder)
            dest_path: Destination directory path
            progress_callback: Optional callback for progress updates

        Returns:
            Dict with download info
        """
        if not self.enabled:
            return {
                'success': False,
                'error': "Mega.nz downloader is not available due to a login failure."
            }
            
        try:
            link_info = self.parse_mega_link(url)

            if link_info['type'] == 'file':
                file_path = self.download_file(url, dest_path, progress_callback)
                return {
                    'success': True,
                    'type': 'file',
                    'files': [file_path],
                    'count': 1
                }
            else:
                files = self.download_folder(url, dest_path, progress_callback)
                return {
                    'success': True,
                    'type': 'folder',
                    'files': files,
                    'count': len(files)
                }

        except Exception as e:
            logger.error(f"Mega.nz download failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }


def test_mega_download():
    """Test function for Mega.nz downloader."""
    downloader = MegaDownloader()

    # Test file link
    test_file = "https://mega.nz/file/EXAMPLE#KEY"
    print(f"Testing file download: {test_file}")

    result = downloader.download(test_file, "./downloads")
    print(f"Result: {result}")


if __name__ == '__main__':
    test_mega_download()
