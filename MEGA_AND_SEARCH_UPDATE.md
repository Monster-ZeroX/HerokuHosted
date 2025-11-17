# Mega.nz Download & Improved Search Update

## Changes Summary

This update adds two major features:
1. **Improved ThePirateBay Search** - Better search results using search.php API
2. **Mega.nz Download Support** - Download files and folders from Mega.nz with premium account

---

## 1. ThePirateBay Search Improvements

### Changed Files:
- `webapp/torrent_search.py` - Updated `search_thepiratebay()` method

### What Changed:
- Now uses `https://thepiratebay.org/search.php?q=` API endpoint
- Added multiple fallback selectors for different TPB layouts
- Improved parsing for size, seeders, and leechers
- Better error handling and logging
- More reliable results from all TPB mirrors

### Benefits:
- More accurate search results
- Better compatibility with TPB mirror sites
- Improved data extraction (size, seeds, peers)

---

## 2. Mega.nz Download Feature

### New Files Created:
- `mega_downloader.py` - Core Mega.nz download module
- `webapp/templates/add_mega.html` - UI for adding Mega.nz links

### Modified Files:
- `webapp/app.py` - Added Mega.nz routes
- `webapp/templates/base.html` - Added Mega.nz navigation link
- `requirements.txt` - Added mega.py library

### Features:
✅ Download single files from Mega.nz
✅ Download entire folders from Mega.nz
✅ Premium account support for high-speed downloads
✅ Automatic file size detection
✅ Download quota checking (respects user limits)
✅ Integration with existing torrent tracking system
✅ Beautiful Apple-style UI

### How It Works:

1. **User adds Mega.nz link** via `/add-mega` page
2. **System validates link** and checks file/folder info
3. **Quota check** ensures user has enough daily download allowance
4. **Creates download entry** in database (reuses Torrent model)
5. **Worker processes download** and uploads to Google Drive

### Configuration Required:

Add these to your Heroku Config Vars:

```bash
MEGA_EMAIL=your-mega-email@example.com
MEGA_PASSWORD=your-mega-password
```

**To set on Heroku:**
```bash
heroku config:set MEGA_EMAIL="your-mega-email@example.com"
heroku config:set MEGA_PASSWORD="your-mega-password"
```

---

## 3. Updated Dependencies

### Added to requirements.txt:
- `requests==2.31.0` - HTTP requests for torrent search
- `beautifulsoup4==4.12.2` - HTML parsing for search results
- `Pillow==10.1.0` - Image processing for favicons
- `mega.py==1.0.8` - Mega.nz API client

---

## 4. New Routes

### `/add-mega` (GET, POST)
- **Purpose**: Add Mega.nz file or folder download
- **Access**: Authenticated users only
- **Features**:
  - Validates Mega.nz links
  - Checks download quotas
  - Supports files and folders
  - Beautiful UI with examples

---

## 5. UI Updates

### Navigation Bar
Added new "Mega.nz" link in main navigation:
- Icon: Cloud download icon
- Position: After "Add Torrent"
- Accessible to all authenticated users

### Add Mega.nz Page
- Premium download info banner
- Link input with validation
- Examples for file and folder links
- Quick action cards for other features
- Apple-style design matching the rest of the app

---

## 6. Deployment Instructions

### Step 1: Commit and Push Changes
```bash
git add .
git commit -m "Add Mega.nz download support and improve TPB search

- Updated ThePirateBay search to use search.php API
- Added Mega.nz file and folder download support
- Created mega_downloader.py module
- Added /add-mega route and template
- Updated navigation with Mega.nz link
- Added required dependencies"

git push heroku main
```

### Step 2: Set Mega.nz Credentials
```bash
heroku config:set MEGA_EMAIL="your-email@example.com"
heroku config:set MEGA_PASSWORD="your-password"
```

### Step 3: Restart Dynos
```bash
heroku restart
```

### Step 4: Verify Deployment
```bash
heroku logs --tail
```

---

## 7. Testing

### Test ThePirateBay Search:
1. Navigate to "Search Torrents"
2. Search for any content
3. Verify results show from ThePirateBay with correct data

### Test Mega.nz Download:
1. Navigate to "Mega.nz" in navigation
2. Enter a Mega.nz file link (e.g., `https://mega.nz/file/...`)
3. Click "Add to Downloads"
4. Check dashboard for download status

---

## 8. Important Notes

### Mega.nz Credentials:
- **REQUIRED**: You must add your Mega.nz premium account credentials to Heroku config vars
- Without credentials, downloads will be limited to anonymous mode (slower speeds)
- Premium accounts have no speed limits and better reliability

### Download Limits:
- Mega.nz downloads respect user daily quotas
- Admins have unlimited downloads
- File size is checked before starting download

### Security:
- Credentials stored securely in Heroku config vars (not in code)
- Environment variables never exposed to users
- Each user's downloads are private and tracked

---

## 9. Architecture

### Mega.nz Download Flow:
```
User submits Mega link
    ↓
Validate link format
    ↓
Check Mega.nz file/folder info
    ↓
Verify user download quota
    ↓
Create database entry (Torrent model)
    ↓
Worker processes download
    ↓
Download to temp storage
    ↓
Upload to Google Drive
    ↓
Update database status
    ↓
Notify user (if enabled)
```

### Module Structure:
```
mega_downloader.py
├── MegaDownloader class
│   ├── __init__() - Initialize and login
│   ├── parse_mega_link() - Parse URL type
│   ├── get_file_info() - Get file/folder metadata
│   ├── download_file() - Download single file
│   ├── download_folder() - Download folder recursively
│   └── download() - Auto-detect and download
```

---

## 10. Future Enhancements

Potential improvements for future versions:
- [ ] Real-time download progress tracking
- [ ] Pause/resume for large downloads
- [ ] Download history and statistics
- [ ] Multiple Mega accounts for load balancing
- [ ] Direct streaming from Mega links
- [ ] Scheduled downloads
- [ ] Download speed limiting

---

## Support

For issues or questions:
1. Check Heroku logs: `heroku logs --tail`
2. Verify config vars are set: `heroku config`
3. Test Mega.nz credentials independently
4. Ensure all dependencies installed correctly

---

**Version**: 2.0
**Date**: 2025-11-17
**Author**: Claude Code
