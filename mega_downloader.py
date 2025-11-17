"""
Mega.nz downloader module with premium account support.
Downloads files and folders from Mega.nz links.
"""
import os
import logging
from typing import Optional, Dict, List
from mega import Mega

logger = logging.getLogger(__name__)


class MegaDownloader:
    """Handle Mega.nz downloads with premium account support."""

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Mega downloader.

        Args:
            email: Mega.nz account email (for premium features)
            password: Mega.nz account password
        """
        self.email = email or os.environ.get('MEGA_EMAIL')
        self.password = password or os.environ.get('MEGA_PASSWORD')
        self.mega = None
        self._login()

    def _login(self):
        """Login to Mega.nz account."""
        try:
            self.mega = Mega()
            if self.email and self.password:
                logger.info(f"Logging into Mega.nz with account: {self.email}")
                self.mega = self.mega.login(self.email, self.password)
                logger.info("Successfully logged into Mega.nz premium account")
            else:
                logger.warning("No Mega.nz credentials provided, using anonymous mode")
                # Anonymous mode has limited download speed
        except Exception as e:
            logger.error(f"Failed to login to Mega.nz: {e}")
            raise

    def parse_mega_link(self, url: str) -> Dict[str, str]:
        """
        Parse Mega.nz link to extract type and ID.

        Args:
            url: Mega.nz URL (file or folder)

        Returns:
            Dict with 'type' (file/folder) and 'id'
        """
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
        try:
            link_info = self.parse_mega_link(url)

            if link_info['type'] == 'file':
                # Get file details
                file = self.mega.get_public_url_info(url)
                return {
                    'name': file.get('name', 'Unknown'),
                    'size': file.get('size', 0),
                    'type': 'file'
                }
            else:
                # For folders, get folder info
                folder_files = self.mega.get_public_folder_info(url)
                total_size = sum(f.get('size', 0) for f in folder_files)
                return {
                    'name': f"Mega Folder ({len(folder_files)} files)",
                    'size': total_size,
                    'type': 'folder',
                    'file_count': len(folder_files)
                }

        except Exception as e:
            logger.error(f"Failed to get Mega.nz file info: {e}")
            raise

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
        try:
            logger.info(f"Downloading Mega.nz file from: {url}")
            logger.info(f"Destination: {dest_path}")

            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)

            # Download the file
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
        try:
            logger.info(f"Downloading Mega.nz folder from: {url}")
            logger.info(f"Destination: {dest_path}")

            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)

            # Get folder contents
            folder_files = self.mega.get_public_folder_info(url)
            logger.info(f"Found {len(folder_files)} files in folder")

            downloaded_files = []

            # Download each file in the folder
            for idx, file_info in enumerate(folder_files, 1):
                file_name = file_info.get('name', f'file_{idx}')
                file_size = file_info.get('size', 0)

                logger.info(f"Downloading file {idx}/{len(folder_files)}: {file_name} ({file_size} bytes)")

                if progress_callback:
                    progress_callback(idx, len(folder_files), file_name)

                # Download individual file
                try:
                    # Construct file URL from folder info
                    file_id = file_info.get('h')
                    if file_id:
                        # Download the file
                        file_path = self.mega.download(file_id, dest_path)
                        downloaded_files.append(file_path)
                        logger.info(f"Downloaded: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to download {file_name}: {e}")
                    continue

            logger.info(f"Successfully downloaded {len(downloaded_files)} files from folder")
            return downloaded_files

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
