# Torrent to Google Drive Bot

A powerful Telegram bot that downloads torrents and automatically uploads them to Google Drive with direct streaming links. Perfect for managing your media library in the cloud!

## Features

- **Magnet Link & .torrent File Support** - Send magnet links or upload .torrent files directly
- **Smart File Selection** - Choose specific files to download or grab everything
- **Interactive UI** - Paginated inline keyboards for easy file browsing and selection
- **Progress Tracking** - Real-time download/upload progress with speed and ETA
- **Google Drive Integration** - Automatic upload via rclone with shareable links
- **Direct Streaming Links** - Generate direct streaming URLs via Google Drive index
- **Concurrent Downloads** - Queue system for handling multiple users simultaneously
- **Clean & Modular** - Well-organized codebase for easy customization
- **Heroku Ready** - One-click deployment with included app.json

## Demo

1. Send a magnet link → Bot fetches metadata
2. Choose "Download All" or "Select Files"
3. If selecting, use paginated keyboard to pick files
4. Bot downloads torrent → uploads to Google Drive
5. Receive Google Drive link + Direct streaming link buttons

## Architecture

```
HerokuHosted/
├── bot/              # Telegram bot handlers
│   ├── __init__.py
│   └── handlers.py   # Command and callback handlers
├── torrent/          # Torrent client wrapper
│   ├── __init__.py
│   └── client.py     # libtorrent integration
├── drive/            # Google Drive integration
│   ├── __init__.py
│   └── rclone.py     # rclone wrapper
├── utils/            # Utilities
│   ├── __init__.py
│   ├── keyboards.py  # Inline keyboard builders
│   └── queue.py      # Job queue system
├── config/           # Configuration
│   ├── __init__.py
│   └── settings.py   # Environment-based settings
├── bin/              # Build scripts
│   └── pre_compile   # Heroku buildpack hooks
├── main.py           # Application entry point
├── requirements.txt  # Python dependencies
├── Procfile          # Heroku process definition
├── runtime.txt       # Python version
├── app.json          # Heroku deployment manifest
└── README.md         # This file
```

## Prerequisites

1. **Telegram Bot Token**
   - Create a bot via [@BotFather](https://t.me/BotFather)
   - Save the token for later

2. **Rclone Configuration**
   - Set up rclone with your Google Drive
   - Follow the [rclone Google Drive setup guide](https://rclone.org/drive/)
   - Get your `rclone.conf` file (usually at `~/.config/rclone/rclone.conf`)

3. **Google Drive Index (Optional)**
   - Deploy a Google Drive index (e.g., [goindex](https://github.com/alx-xlx/goindex), [gdindex](https://github.com/maple3142/GDIndex))
   - This enables direct streaming/download links
   - Not required but highly recommended

## Setup & Deployment

### Option 1: Deploy to Heroku (Recommended)

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://heroku.com/deploy)

1. Click the "Deploy to Heroku" button above
2. Fill in the required environment variables:
   - **BOT_TOKEN**: Your Telegram bot token
   - **RCLONE_CONFIG**: Paste your entire rclone.conf file content
   - **RCLONE_REMOTE_NAME**: The remote name from your rclone.conf (e.g., `gdrive`)
   - **RCLONE_BASE_DIR**: Folder name on Google Drive (e.g., `TorrentBot`)
   - **INDEX_BASE_URL**: Your Google Drive index URL (optional)
3. Click "Deploy app"
4. Wait for deployment to complete
5. Open your Telegram bot and send `/start`

### Option 2: Manual Heroku Deployment

```bash
# Clone the repository
git clone <your-repo-url>
cd HerokuHosted

# Login to Heroku
heroku login

# Create a new Heroku app
heroku create your-bot-name

# Set environment variables
heroku config:set BOT_TOKEN="your_bot_token_here"
heroku config:set RCLONE_REMOTE_NAME="gdrive"
heroku config:set RCLONE_BASE_DIR="TorrentBot"
heroku config:set INDEX_BASE_URL="https://your-index-url.com"

# Set rclone config (encode as single line or use heredoc)
heroku config:set RCLONE_CONFIG="$(cat ~/.config/rclone/rclone.conf)"

# Deploy
git push heroku main

# Scale worker dyno
heroku ps:scale worker=1

# Check logs
heroku logs --tail
```

### Option 3: Local Development

```bash
# Clone repository
git clone <your-repo-url>
cd HerokuHosted

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install rclone (if not installed)
# Linux/Mac: curl https://rclone.org/install.sh | sudo bash
# Windows: Download from https://rclone.org/downloads/

# Copy rclone config
mkdir -p /app
cp ~/.config/rclone/rclone.conf /app/rclone.conf

# Set environment variables
export BOT_TOKEN="your_bot_token"
export RCLONE_REMOTE_NAME="gdrive"
export RCLONE_BASE_DIR="TorrentBot"
export INDEX_BASE_URL="https://your-index.com"
export RCLONE_CONFIG_PATH="/app/rclone.conf"

# Run bot
python main.py
```

## Configuration

All configuration is done via environment variables:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `BOT_TOKEN` | Telegram bot token from @BotFather | - | ✅ |
| `RCLONE_CONFIG` | Content of rclone.conf file | - | ✅ |
| `RCLONE_REMOTE_NAME` | Rclone remote name (e.g., `gdrive`) | `gdrive` | ✅ |
| `RCLONE_BASE_DIR` | Base directory on Google Drive | `TorrentBot` | ❌ |
| `INDEX_BASE_URL` | Google Drive index base URL | - | ❌ |
| `OWNER_IDS` | Comma-separated user IDs allowed to use bot | - | ❌ |
| `DOWNLOAD_DIR` | Temporary download directory | `/tmp/downloads` | ❌ |
| `MAX_DOWNLOAD_SIZE` | Max download size in bytes | `1073741824` (1GB) | ❌ |
| `CONCURRENT_DOWNLOADS` | Max concurrent downloads | `3` | ❌ |
| `TORRENT_TIMEOUT` | Download timeout in seconds | `3600` | ❌ |
| `SEED_TIME` | Time to seed after download (seconds) | `0` | ❌ |
| `PROGRESS_UPDATE_INTERVAL` | Progress update interval (seconds) | `10` | ❌ |
| `LOG_LEVEL` | Logging level (DEBUG/INFO/WARNING/ERROR) | `INFO` | ❌ |

### Setting up Rclone Config

Your `rclone.conf` should look like this:

```ini
[gdrive]
type = drive
client_id = your_client_id
client_secret = your_client_secret
token = {"access_token":"xxx","token_type":"Bearer","refresh_token":"xxx","expiry":"xxx"}
team_drive =
```

**For Heroku deployment:**
- Copy the entire content of your rclone.conf file
- Paste it as the value for `RCLONE_CONFIG` environment variable
- Make sure to preserve all newlines and formatting

### Setting up Google Drive Index

The bot can generate direct streaming links if you have a Google Drive index deployed. Popular options:

1. **goindex** - [GitHub](https://github.com/alx-xlx/goindex)
2. **GDIndex** - [GitHub](https://github.com/maple3142/GDIndex)
3. **gdindex** - [GitHub](https://github.com/ParveenBhadooOfficial/Google-Drive-Index)

After deploying your index:
1. Get the base URL (e.g., `https://index.yourdomain.com`)
2. Set `INDEX_BASE_URL` environment variable
3. The bot will construct direct URLs like: `https://index.yourdomain.com/TorrentBot/filename.mp4`

## Usage

### Commands

- `/start` - Show welcome message and instructions
- `/status` - Check your active download jobs
- `/cancel` - Cancel an ongoing job

### Workflow

1. **Send a magnet link or .torrent file**
   ```
   magnet:?xt=urn:btih:...
   ```

2. **Choose download option**
   - "⬇️ Download All Files" - Download entire torrent
   - "📝 Select Files" - Choose specific files

3. **If selecting files:**
   - Browse paginated file list
   - Tap to select/deselect files
   - Use "✅ Select All" / "❌ Deselect All"
   - Press "⬇️ Download Selected"

4. **Monitor progress**
   - Bot shows download progress with speed and ETA
   - Updates every 10 seconds (configurable)

5. **Upload to Google Drive**
   - Automatic upload after download completes
   - Shows upload progress

6. **Get links**
   - "📂 Open in Google Drive" - View in GDrive web interface
   - "🎬 Direct Link (Stream)" - Direct streaming/download URL

## How It Works

### Torrent Download
- Uses **libtorrent** for robust torrent downloading
- Fetches metadata before downloading
- Supports magnet links and .torrent files
- Allows selective file downloading
- DHT, PEX, and tracker support

### File Selection UI
- Paginated inline keyboards (8 files per page)
- Shows file names and sizes
- Multi-select with checkboxes
- Select/deselect all buttons
- Responsive pagination

### Upload to Google Drive
- Uses **rclone** for reliable uploads
- Chunked uploads for large files
- Progress tracking
- Automatic folder creation

### Direct Links
- Constructs URLs using your GDrive index
- Format: `INDEX_BASE_URL/RCLONE_BASE_DIR/filename`
- Enables direct streaming in browsers and video players

### Job Queue
- Handles multiple users concurrently
- Configurable concurrent download limit
- Status tracking (Queued → Downloading → Uploading → Completed)
- Automatic cleanup of old jobs

## Limitations on Heroku

### Free/Eco Dynos
- **Ephemeral filesystem**: All downloads are temporary and deleted on restart
- **Storage limit**: ~500MB available in `/tmp`
- **Memory**: 512MB RAM on eco dynos
- **Monthly hours**: Limited free dyno hours

### Recommendations
- Keep `MAX_DOWNLOAD_SIZE` under 500MB for free dynos
- Use paid dynos for larger files
- Set `CONCURRENT_DOWNLOADS` to 1-2 on free dynos
- Consider alternative hosting for heavy usage

## Troubleshooting

### Bot doesn't respond
- Check Heroku logs: `heroku logs --tail`
- Verify `BOT_TOKEN` is correct
- Ensure worker dyno is running: `heroku ps`

### Rclone upload fails
- Verify `RCLONE_CONFIG` is properly set
- Check `RCLONE_REMOTE_NAME` matches your config
- Test rclone locally: `rclone ls gdrive:`
- Check Google Drive API quotas

### Torrent download fails
- Check if magnet link is valid
- Ensure torrent has seeders
- Increase `TORRENT_TIMEOUT`
- Check Heroku logs for errors

### Out of disk space
- Reduce `MAX_DOWNLOAD_SIZE`
- Lower `CONCURRENT_DOWNLOADS`
- Ensure cleanup is working (check logs)

### Direct links don't work
- Verify `INDEX_BASE_URL` is correct
- Check index deployment is working
- Ensure file paths match between bot and index

## Advanced Customization

### Restricting Access

Allow only specific users:

```bash
heroku config:set OWNER_IDS="123456789,987654321"
```

### Adjusting Performance

For larger files on paid dynos:

```bash
heroku config:set MAX_DOWNLOAD_SIZE="5368709120"  # 5GB
heroku config:set CONCURRENT_DOWNLOADS="5"
heroku config:set TORRENT_TIMEOUT="7200"  # 2 hours
```

### Custom Base Directory

Organize uploads by category:

```bash
heroku config:set RCLONE_BASE_DIR="Media/Torrents"
```

### Enable Seeding

Seed torrents after download:

```bash
heroku config:set SEED_TIME="300"  # 5 minutes
```

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Disclaimer

This bot is for educational purposes and personal use only. Users are responsible for complying with copyright laws and terms of service of all platforms involved. The developers assume no liability for misuse.

## Support

- Open an issue on GitHub for bugs/features
- Check Heroku logs for debugging: `heroku logs --tail`
- Refer to [libtorrent docs](https://www.libtorrent.org/reference.html) for torrent-related issues
- Check [rclone docs](https://rclone.org/docs/) for upload issues

## Credits

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [libtorrent](https://www.libtorrent.org/) - BitTorrent library
- [rclone](https://rclone.org/) - Cloud storage sync tool
- Inspired by [TorToolkit-Telegram](https://github.com/yash-dk/TorToolkit-Telegram)

---

Made with ❤️ for the community
