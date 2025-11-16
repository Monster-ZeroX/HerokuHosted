# Quick Reference

## Environment Variables

```bash
# Required
BOT_TOKEN=              # From @BotFather
RCLONE_CONFIG=          # Full rclone.conf content
RCLONE_REMOTE_NAME=     # e.g., "gdrive"

# Optional
RCLONE_BASE_DIR=        # Default: "TorrentBot"
INDEX_BASE_URL=         # Your GDrive index URL
OWNER_IDS=              # Comma-separated user IDs
DOWNLOAD_DIR=           # Default: "/tmp/downloads"
MAX_DOWNLOAD_SIZE=      # Default: 1073741824 (1GB)
CONCURRENT_DOWNLOADS=   # Default: 3
TORRENT_TIMEOUT=        # Default: 3600 (1 hour)
SEED_TIME=              # Default: 0 (no seeding)
PROGRESS_UPDATE_INTERVAL= # Default: 10 seconds
LOG_LEVEL=              # Default: "INFO"
```

## Heroku Commands

```bash
# Deploy
git push heroku main

# View logs
heroku logs --tail

# Restart
heroku ps:restart

# Scale worker
heroku ps:scale worker=1

# Set config
heroku config:set KEY=value

# View config
heroku config

# Open dashboard
heroku open

# SSH into dyno
heroku run bash
```

## Local Development

```bash
# Quick start
./start.sh

# Manual start
source venv/bin/activate
python main.py

# Test rclone
rclone ls gdrive:

# Check config
cat .env
```

## Bot Commands

```
/start   - Show welcome message
/status  - Check active jobs
/cancel  - Cancel a job
```

## File Structure

```
HerokuHosted/
├── bot/              # Bot handlers
├── torrent/          # Torrent client
├── drive/            # Google Drive
├── utils/            # Utilities
├── config/           # Settings
├── main.py           # Entry point
├── requirements.txt  # Dependencies
├── Procfile          # Heroku config
├── app.json          # Deploy manifest
└── README.md         # Documentation
```

## Common Issues

| Issue | Solution |
|-------|----------|
| Bot not responding | Check `heroku ps` and `heroku logs` |
| Rclone fails | Verify RCLONE_CONFIG and remote name |
| Out of space | Reduce MAX_DOWNLOAD_SIZE |
| Slow downloads | Check seeders, increase timeout |
| No direct links | Set INDEX_BASE_URL |

## Useful Links

- [Heroku CLI Docs](https://devcenter.heroku.com/articles/heroku-cli)
- [Rclone Docs](https://rclone.org/docs/)
- [python-telegram-bot](https://docs.python-telegram-bot.org/)
- [libtorrent](https://www.libtorrent.org/)

## Size Limits

Free Heroku:
- Ephemeral storage: ~500MB
- RAM: 512MB
- Keep downloads under 500MB

Paid Dynos:
- More resources available
- Can handle larger files
- See Heroku pricing page

## Tips

1. Use magnet links instead of .torrent files
2. Select only needed files to save space
3. Monitor logs during first few downloads
4. Set OWNER_IDS for security
5. Use INDEX_BASE_URL for streaming
6. Keep MAX_DOWNLOAD_SIZE reasonable
7. Clean up old jobs periodically

## Testing Checklist

- [ ] Bot responds to /start
- [ ] Magnet link handling
- [ ] .torrent file upload
- [ ] File selection UI
- [ ] Pagination works
- [ ] Download progress updates
- [ ] Upload to Google Drive
- [ ] Links work (GDrive + Index)
- [ ] Error handling
- [ ] Cleanup after completion

## Support

- GitHub Issues: Report bugs
- Heroku Logs: Debug issues
- README.md: Full documentation
- SETUP.md: Step-by-step guide
