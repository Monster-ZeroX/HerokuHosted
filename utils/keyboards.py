"""
Utilities for Telegram inline keyboards and pagination.
"""
from typing import List, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from torrent import TorrentFile, format_size


class FileSelector:
    """Handles file selection UI with pagination."""

    ITEMS_PER_PAGE = 8

    @staticmethod
    def create_file_list_keyboard(
        files: List[TorrentFile],
        page: int = 0,
        torrent_hash: str = ""
    ) -> InlineKeyboardMarkup:
        """
        Create paginated inline keyboard for file selection.

        Args:
            files: List of torrent files
            page: Current page number
            torrent_hash: Torrent info hash for callback data

        Returns:
            InlineKeyboardMarkup
        """
        buttons = []
        start_idx = page * FileSelector.ITEMS_PER_PAGE
        end_idx = start_idx + FileSelector.ITEMS_PER_PAGE
        page_files = files[start_idx:end_idx]

        # File selection buttons
        for file in page_files:
            checkbox = "✅" if file.selected else "☐"
            file_name = file.path.split("/")[-1] if "/" in file.path else file.path
            button_text = f"{checkbox} {file_name} ({format_size(file.size)})"

            # Truncate if too long
            if len(button_text) > 60:
                file_name_short = file_name[:40] + "..."
                button_text = f"{checkbox} {file_name_short} ({format_size(file.size)})"

            callback_data = f"toggle:{torrent_hash}:{file.index}:{page}"
            buttons.append([InlineKeyboardButton(button_text, callback_data=callback_data)])

        # Pagination buttons
        nav_buttons = []
        total_pages = (len(files) + FileSelector.ITEMS_PER_PAGE - 1) // FileSelector.ITEMS_PER_PAGE

        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page:{torrent_hash}:{page-1}"))

        nav_buttons.append(InlineKeyboardButton(f"📄 {page+1}/{total_pages}", callback_data="noop"))

        if page < total_pages - 1:
            nav_buttons.append(InlineKeyboardButton("Next ➡️", callback_data=f"page:{torrent_hash}:{page+1}"))

        if nav_buttons:
            buttons.append(nav_buttons)

        # Action buttons
        action_buttons = [
            InlineKeyboardButton("✅ Select All", callback_data=f"selectall:{torrent_hash}:{page}"),
            InlineKeyboardButton("❌ Deselect All", callback_data=f"deselectall:{torrent_hash}:{page}")
        ]
        buttons.append(action_buttons)

        # Confirm button
        selected_count = sum(1 for f in files if f.selected)
        confirm_text = f"⬇️ Download Selected ({selected_count})" if selected_count > 0 else "⬇️ Download All"
        buttons.append([InlineKeyboardButton(confirm_text, callback_data=f"confirm:{torrent_hash}")])

        # Cancel button
        buttons.append([InlineKeyboardButton("🚫 Cancel", callback_data=f"cancel:{torrent_hash}")])

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def create_simple_choice_keyboard(torrent_hash: str) -> InlineKeyboardMarkup:
        """
        Create simple keyboard for download all or select files.

        Args:
            torrent_hash: Torrent info hash

        Returns:
            InlineKeyboardMarkup
        """
        buttons = [
            [InlineKeyboardButton("⬇️ Download All Files", callback_data=f"downloadall:{torrent_hash}")],
            [InlineKeyboardButton("📝 Select Files", callback_data=f"selectfiles:{torrent_hash}")],
            [InlineKeyboardButton("🚫 Cancel", callback_data=f"cancel:{torrent_hash}")]
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def create_completion_keyboard(
        gdrive_link: str = None,
        index_link: str = None
    ) -> InlineKeyboardMarkup:
        """
        Create keyboard with completion links.

        Args:
            gdrive_link: Google Drive link
            index_link: Direct index link

        Returns:
            InlineKeyboardMarkup
        """
        buttons = []

        if gdrive_link:
            buttons.append([InlineKeyboardButton("📂 Open in Google Drive", url=gdrive_link)])

        if index_link:
            buttons.append([InlineKeyboardButton("🎬 Direct Link (Stream)", url=index_link)])

        return InlineKeyboardMarkup(buttons) if buttons else None


def parse_callback_data(data: str) -> Tuple[str, ...]:
    """
    Parse callback data from inline keyboard.

    Args:
        data: Callback data string

    Returns:
        Tuple of parsed components
    """
    return tuple(data.split(":"))


def format_eta(seconds: int) -> str:
    """
    Format ETA in seconds to human-readable string.

    Args:
        seconds: ETA in seconds

    Returns:
        Formatted string (e.g., "1h 23m", "45s")
    """
    if seconds < 0:
        return "Unknown"

    if seconds < 60:
        return f"{seconds}s"

    minutes = seconds // 60
    if minutes < 60:
        return f"{minutes}m {seconds % 60}s"

    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes}m"
