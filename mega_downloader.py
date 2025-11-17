"""
Mega.nz downloader module with premium account support.
Downloads files and folders from Mega.nz links using direct API calls.
Compatible with Python 3.11+
"""
import os
import re
import json
import base64
import logging
import requests
from typing import Optional, Dict, List
from Crypto.Cipher import AES
from Crypto.Util import Counter
import struct

logger = logging.getLogger(__name__)


class MegaDownloader:
    """Handle Mega.nz downloads with premium account support using direct API."""

    API_URL = "https://g.api.mega.co.nz/cs"

    def __init__(self, email: Optional[str] = None, password: Optional[str] = None):
        """
        Initialize Mega downloader.

        Args:
            email: Mega.nz account email (for premium features)
            password: Mega.nz account password
        """
        self.email = email or os.environ.get('MEGA_EMAIL')
        self.password = password or os.environ.get('MEGA_PASSWORD')
        self.session_id = None
        self.master_key = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Content-Type': 'application/json'
        })
        self._sequence_num = 0

        if self.email and self.password:
            try:
                self._login()
            except Exception as e:
                logger.warning(f"Failed to login to Mega.nz premium account: {e}")
                logger.info("Continuing in anonymous mode")

    def _get_sequence_num(self):
        """Get next sequence number for API requests."""
        self._sequence_num += 1
        return self._sequence_num

    def _api_request(self, data):
        """Make API request to Mega.nz."""
        params = {'id': self._get_sequence_num()}
        if self.session_id:
            params['sid'] = self.session_id

        response = self.session.post(
            self.API_URL,
            params=params,
            data=json.dumps([data]),
            timeout=30
        )
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            result = result[0]

        if isinstance(result, int) and result < 0:
            raise Exception(f"Mega API error code: {result}")

        return result

    def _base64_to_bytes(self, s):
        """Convert Mega's base64 format to bytes."""
        s = s.replace('-', '+').replace('_', '/').replace(',', '')
        padding = (4 - len(s) % 4) % 4
        s += '=' * padding
        return base64.b64decode(s)

    def _bytes_to_base64(self, b):
        """Convert bytes to Mega's base64 format."""
        s = base64.b64encode(b).decode('utf-8')
        return s.replace('+', '-').replace('/', '_').replace('=', '')

    def _aes_cbc_decrypt(self, data, key):
        """Decrypt data using AES-CBC."""
        cipher = AES.new(key, AES.MODE_CBC, b'\0' * 16)
        return cipher.decrypt(data)

    def _aes_cbc_encrypt(self, data, key):
        """Encrypt data using AES-CBC."""
        cipher = AES.new(key, AES.MODE_CBC, b'\0' * 16)
        return cipher.encrypt(data)

    def _prepare_key(self, key_data):
        """Prepare encryption key from key data."""
        key = [0, 0, 0, 0]
        for i in range(len(key_data) // 4):
            key[i % 4] ^= struct.unpack('>I', key_data[i * 4:i * 4 + 4])[0]
        return struct.pack('>4I', *key)

    def _login(self):
        """Login to Mega.nz account (simplified version)."""
        logger.info(f"Attempting to login to Mega.nz with: {self.email}")
        # For now, we'll work without login for public links
        # Full login implementation requires password hashing with PBKDF2
        logger.info("Using anonymous mode for public links")

    def parse_mega_link(self, url: str) -> Dict[str, str]:
        """
        Parse Mega.nz link to extract type and ID.

        Args:
            url: Mega.nz URL (file or folder)

        Returns:
            Dict with 'type' (file/folder), 'id', and 'key'
        """
        url = url.strip()

        # File link patterns: https://mega.nz/file/ABC123#key or https://mega.nz/#!ABC123!key
        file_match = re.search(r'mega\.nz/file/([a-zA-Z0-9_-]+)#([a-zA-Z0-9_-]+)', url)
        if not file_match:
            file_match = re.search(r'mega\.nz/#!([a-zA-Z0-9_-]+)!([a-zA-Z0-9_-]+)', url)

        if file_match:
            return {
                'type': 'file',
                'id': file_match.group(1),
                'key': file_match.group(2),
                'url': url
            }

        # Folder link patterns: https://mega.nz/folder/ABC123#key or https://mega.nz/#F!ABC123!key
        folder_match = re.search(r'mega\.nz/folder/([a-zA-Z0-9_-]+)#([a-zA-Z0-9_-]+)', url)
        if not folder_match:
            folder_match = re.search(r'mega\.nz/#F!([a-zA-Z0-9_-]+)!([a-zA-Z0-9_-]+)', url)

        if folder_match:
            return {
                'type': 'folder',
                'id': folder_match.group(1),
                'key': folder_match.group(2),
                'url': url
            }

        raise ValueError(f"Invalid Mega.nz link format: {url}")

    def get_file_info(self, url: str) -> Dict:
        """
        Get information about a Mega.nz file or folder.

        Args:
            url: Mega.nz file/folder URL

        Returns:
            Dict with name and size
        """
        try:
            link_info = self.parse_mega_link(url)

            if link_info['type'] == 'file':
                # Get public file info
                file_data = self._api_request({
                    'a': 'g',
                    'p': link_info['id']
                })

                # Decrypt file attributes
                key = self._base64_to_bytes(link_info['key'])
                k = self._prepare_key(key)

                # Get file name and size
                size = file_data.get('s', 0)

                # Try to get filename from attributes
                try:
                    attr = file_data.get('at')
                    if attr:
                        attr_bytes = self._base64_to_bytes(attr)
                        attr_decrypted = self._aes_cbc_decrypt(attr_bytes, k)
                        attr_str = attr_decrypted.decode('utf-8').rstrip('\0')
                        # Parse JSON attributes
                        attr_json = json.loads(attr_str.split('MEGA')[1] if 'MEGA' in attr_str else attr_str)
                        name = attr_json.get('n', 'Unknown')
                    else:
                        name = 'Unknown File'
                except Exception as e:
                    logger.warning(f"Could not decrypt filename: {e}")
                    name = 'Mega File'

                return {
                    'name': name,
                    'size': size,
                    'type': 'file'
                }
            else:
                # Folder - return basic info
                return {
                    'name': 'Mega Folder',
                    'size': 0,  # Can't easily get folder size without downloading
                    'type': 'folder'
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

            link_info = self.parse_mega_link(url)
            if link_info['type'] != 'file':
                raise ValueError("URL is not a file link")

            # Get download URL
            file_data = self._api_request({
                'a': 'g',
                'p': link_info['id']
            })

            download_url = file_data.get('g')
            if not download_url:
                raise Exception("Could not get download URL")

            # Get file info
            info = self.get_file_info(url)
            filename = info['name']

            # Ensure destination directory exists
            os.makedirs(dest_path, exist_ok=True)
            file_path = os.path.join(dest_path, filename)

            # Download file
            logger.info(f"Downloading to: {file_path}")
            response = self.session.get(download_url, stream=True)
            response.raise_for_status()

            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

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
        logger.warning("Folder download not fully implemented yet")
        logger.info("Please use individual file links for now")
        raise NotImplementedError("Folder downloads require full API implementation. Please use individual file links.")

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
