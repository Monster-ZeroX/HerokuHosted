# Torrent to Google Drive Bot

A powerful Telegram bot that downloads torrents and automatically uploads them to Google Drive with direct streaming links. Perfect for managing your media library in the cloud!

## Features

### Telegram Bot
- **Magnet Link & .torrent File Support** - Send magnet links or upload .torrent files directly
- **Smart File Selection** - Choose specific files to download or grab everything
- **Interactive UI** - Paginated inline keyboards for easy file browsing and selection
- **Progress Tracking** - Real-time download/upload progress with speed and ETA
- **Google Drive Integration** - Automatic upload via rclone with shareable links
- **Direct Streaming Links** - Generate direct streaming URLs via Google Drive index
- **Concurrent Downloads** - Queue system for handling multiple users simultaneously

### Web Application
- **User Authentication** - Secure login with username, password, and invite code system
- **Invite Code Access** - Controlled registration with customizable invite codes
- **Admin Panel** - Comprehensive admin interface for managing users and invite codes
- **Torrent Management** - Add torrents via web interface and track downloads
- **Online Video Player** - Built-in Video.js player for streaming videos directly in browser
- **External Player Support** - One-click integration with VLC, MX Player, PotPlayer, and more
- **Responsive Design** - Modern Bootstrap UI that works on desktop and mobile
- **Database Integration** - PostgreSQL-backed system for reliable data persistence

### General
- **Clean & Modular** - Well-organized codebase for easy customization
- **Heroku Ready** - One-click deployment with included app.json
- **Dual Process** - Web server and bot worker running simultaneously on same app

## Demo

### Telegram Bot Workflow
1. Send a magnet link → Bot fetches metadata
2. Choose "Download All" or "Select Files"
3. If selecting, use paginated keyboard to pick files
4. Bot downloads torrent → uploads to Google Drive
5. Receive Google Drive link + Direct streaming link buttons

### Web Application Workflow
1. Visit your app URL (e.g., `https://your-app.herokuapp.com`)
2. Register with username, password, and invite code: **Kaveesha**
3. Login to your dashboard
4. Add magnet link or browse existing torrents
5. Watch online with built-in player or use external players
6. Copy direct streaming links for sharing

### Admin Access
- **Username**: MonsterZeroX
- **Password**: Kaveesha@2005
- Access admin panel at `/admin` to manage users and invite codes

## Architecture

```
HerokuHosted/
├── bot/                    # Telegram bot handlers
│   ├── __init__.py
│   └── handlers.py         # Command and callback handlers
├── torrent/                # Torrent client wrapper
│   ├── __init__.py
│   └── client.py           # libtorrent integration
├── drive/                  # Google Drive integration
│   ├── __init__.py
│   └── rclone.py           # rclone wrapper
├── utils/                  # Utilities
│   ├── __init__.py
│   ├── keyboards.py        # Inline keyboard builders
│   └── queue.py            # Job queue system
├── config/                 # Configuration
│   ├── __init__.py
│   └── settings.py         # Environment-based settings
├── webapp/                 # Web application (NEW!)
│   ├── __init__.py
│   ├── app.py              # Flask routes and logic
│   ├── models.py           # Database models
│   ├── static/
│   │   └── style.css       # Custom CSS
│   └── templates/          # HTML templates
│       ├── base.html       # Base template
│       ├── login.html      # Login page
│       ├── register.html   # Registration page
│       ├── dashboard.html  # User dashboard
│       ├── add_torrent.html
│       ├── torrent_detail.html
│       ├── player.html     # Video player
│       └── admin.html      # Admin panel
├── bin/                    # Build scripts
│   └── pre_compile         # Heroku buildpack hooks
├── main.py                 # Bot entry point (worker)
├── web_server.py           # Web app entry point (web)
├── requirements.txt        # Python dependencies
├── Procfile                # Heroku process definition
├── runtime.txt             # Python version
├── .python-version         # Python version (new format)
├── Aptfile                 # System packages
├── app.json                # Heroku deployment manifest
└── README.md               # This file
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

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/Monster-ZeroX/HerokuHosted)


1. Click the "Deploy to Heroku" button above
2. Fill in the required environment variables:
   - **BOT_TOKEN**: Your Telegram bot token
   - **RCLONE_CONFIG**: Paste your entire rclone.conf file content
   - **RCLONE_REMOTE_NAME**: The remote name from your rclone.conf (e.g., `gdrive`)
   - **RCLONE_BASE_DIR**: Folder name on Google Drive (e.g., `TorrentBot`)
   - **INDEX_BASE_URL**: Your Google Drive index URL (optional)
3. Click "Deploy app"
4. Wait for deployment to complete
5. **Access the web app**: Visit `https://your-app-name.herokuapp.com`
6. **Register**: Use invite code **Kaveesha** to create your account
7. **Use Telegram bot**: Open your Telegram bot and send `/start`

**Payment (Genie Business Connect) config vars:**
- `GENIE_API_KEY` and `GENIE_MERCHANT_ID` – required to create checkout sessions (set `GENIE_API_KEY` to the exact Authorization value your Genie dashboard provides, e.g., `Bearer abc123` or the raw key)
- `GENIE_API_BASE` – defaults to `https://api.geniebiz.lk/public/v2` (override if your merchant uses a different host/path)
- `GENIE_CURRENCY` – defaults to `LKR`
- `PLAN_100_PRICE_LKR`, `PLAN_300_PRICE_LKR`, `PLAN_UNLIMITED_PRICE_LKR` – override default plan prices (300/600/1200 LKR for 30 days)
- **Webhook:** point your Genie Business Connect webhook URL to `https://<your-app>/webhook/genie` so paid/failed statuses are pushed instantly (the app also polls if webhooks are delayed).

**Default Credentials:**
- **Admin**: Username: `MonsterZeroX` | Password: `Kaveesha@2005`
- **Invite Code**: `Kaveesha` (required for registration)

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

# Scale both dynos
heroku ps:scale web=1 worker=1

# Check logs
heroku logs --tail
```

**After deployment:**
- Web app: `https://your-app-name.herokuapp.com`
- Admin panel: `https://your-app-name.herokuapp.com/admin`
- Login with **MonsterZeroX** / **Kaveesha@2005**

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

# Run bot (in one terminal)
python main.py

# Run web server (in another terminal)
python web_server.py
```

**Local access:**
- Web app: `http://localhost:5000`
- Use invite code **Kaveesha** to register
- Admin login: **MonsterZeroX** / **Kaveesha@2005**

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

### Telegram Bot

#### Commands

- `/start` - Show welcome message and instructions
- `/status` - Check your active download jobs
- `/cancel` - Cancel an ongoing job

#### Workflow

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

### Web Application

#### Registration & Login

1. **Register a new account**
   - Visit `https://your-app.herokuapp.com/register`
   - Enter username and password
   - Use invite code: **Kaveesha**
   - Submit to create account

2. **Login**
   - Visit `https://your-app.herokuapp.com/login`
   - Enter your username and password
   - Access your personal dashboard

#### Adding Torrents

1. From your dashboard, click **"Add New Torrent"**
2. Paste magnet link or upload .torrent file
3. Submit and the bot will process it automatically
4. Track progress in your dashboard

#### Watching Videos

**Option 1: Online Player (Built-in)**
1. Click on any torrent from your dashboard
2. Select a video file
3. Click **"Watch Online"**
4. Video.js player loads with:
   - Play/pause controls
   - Volume control
   - Fullscreen mode
   - Quality selection
   - Playback speed control
   - Resume from last position

**Option 2: External Players**
1. From the player page, choose your preferred player:
   - **VLC** - Best for desktop streaming
   - **MX Player** - Android video player
   - **PotPlayer** - Windows media player
   - **Copy Link** - For any other player
2. Click the button to open in external app
3. Link opens directly in the player

#### Admin Panel

Access: `https://your-app.herokuapp.com/admin` (Admin login required)

**User Management:**
- View all registered users
- Delete user accounts
- Reset user passwords
- See user statistics

**Invite Code Management:**
- Create new invite codes
- Set usage limits (single-use or unlimited)
- Activate/deactivate codes
- View invite code usage stats

**Creating New Invite Codes:**
1. Scroll to "Create New Invite Code" section
2. Enter the code (e.g., "NEWCODE2024")
3. Set max uses (0 = unlimited)
4. Check "Active" to enable immediately
5. Click "Create Code"

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

### Web Application Architecture

**Frontend:**
- Bootstrap 5 responsive design
- Video.js for HTML5 video playback
- AJAX for real-time torrent status updates
- LocalStorage for resume playback position

**Backend:**
- Flask web framework
- SQLAlchemy ORM with PostgreSQL
- Flask-Login for session management
- Password hashing with werkzeug.security

**Database Models:**
- **User**: Authentication and authorization
- **Torrent**: Torrent metadata and tracking
- **TorrentFile**: Individual files within torrents
- **InviteCode**: Registration access control

**Security:**
- Password hashing (pbkdf2:sha256)
- Session-based authentication
- CSRF protection via Flask-WTF
- Admin-only route protection
- Invite code validation

## Limitations on Heroku

### Free/Eco Dynos
- **Ephemeral filesystem**: All downloads are temporary and deleted on restart
- **Storage limit**: ~500MB available in `/tmp`
- **Memory**: 512MB RAM per dyno (web + worker = 2 dynos)
- **Monthly hours**: Limited free dyno hours
- **Database**: PostgreSQL essential-0 addon included

### Recommendations
- Keep `MAX_DOWNLOAD_SIZE` under 500MB for free dynos
- Use paid dynos for larger files
- Set `CONCURRENT_DOWNLOADS` to 1-2 on free dynos
- Consider upgrading to Hobby dynos ($7/month each) for better performance
- Monitor dyno hours to avoid service interruptions

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

### Web app issues

**Can't access web app:**
- Check web dyno is running: `heroku ps`
- Verify app URL is correct
- Check logs: `heroku logs --tail --dyno web`

**Can't login/register:**
- Verify invite code "Kaveesha" is active
- Check database is connected (PostgreSQL addon)
- Clear browser cookies and try again
- Check logs for database errors

**Admin panel not accessible:**
- Ensure using admin credentials: **MonsterZeroX** / **Kaveesha@2005**
- Try logging out and logging in again
- Check if `/admin` route is accessible

**Video player not working:**
- Verify `INDEX_BASE_URL` is set correctly
- Check if index URL returns video file
- Try external player instead
- Check browser console for errors

**Database errors:**
- Run migrations: Check Heroku logs for database initialization
- Verify PostgreSQL addon is provisioned
- Check `DATABASE_URL` environment variable

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

### Web Application Customization

**Change default invite code:**
1. Login as admin
2. Go to `/admin`
3. Deactivate "Kaveesha" code
4. Create new invite code with your preferred name

**Create multiple admin accounts:**
- Currently requires database modification
- Use admin panel to reset any user's password
- Manually set `is_admin=True` via database console

**Customize branding:**
- Edit `webapp/templates/base.html` - Update title and navbar
- Edit `webapp/static/style.css` - Modify colors and styling
- Redeploy to Heroku

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

## Technology Stack

**Backend:**
- Python 3.11
- Flask (Web framework)
- python-telegram-bot (Bot framework)
- SQLAlchemy (ORM)
- Flask-Login (Authentication)
- libtorrent (Torrent client)
- rclone (Cloud storage sync)

**Frontend:**
- Bootstrap 5 (UI framework)
- Video.js (Video player)
- JavaScript (AJAX, LocalStorage)

**Database:**
- PostgreSQL (Production - Heroku)
- SQLite (Local development)

**Deployment:**
- Heroku (Platform)
- Gunicorn (WSGI server)
- heroku-buildpack-apt (System packages)

## Credits

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [libtorrent](https://www.libtorrent.org/) - BitTorrent library
- [rclone](https://rclone.org/) - Cloud storage sync tool
- [Flask](https://flask.palletsprojects.com/) - Web framework
- [Bootstrap](https://getbootstrap.com/) - Frontend framework
- [Video.js](https://videojs.com/) - HTML5 video player
- Inspired by [TorToolkit-Telegram](https://github.com/yash-dk/TorToolkit-Telegram)

---

Made with ❤️ for the community
