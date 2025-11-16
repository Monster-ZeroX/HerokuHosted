# Setup Guide

This guide will walk you through setting up the Torrent to Google Drive Bot step by step.

## Step 1: Create a Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Choose a name for your bot (e.g., "My Torrent Bot")
4. Choose a username (must end in 'bot', e.g., "mytorrent_bot")
5. BotFather will give you a token like: `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz`
6. Save this token securely

## Step 2: Set Up Rclone with Google Drive

### Install Rclone

**Linux/Mac:**
```bash
curl https://rclone.org/install.sh | sudo bash
```

**Windows:**
Download from [https://rclone.org/downloads/](https://rclone.org/downloads/)

### Configure Google Drive

```bash
rclone config
```

Follow these steps:
1. Press `n` for new remote
2. Name it `gdrive` (or your preferred name)
3. Choose `drive` for Google Drive
4. Leave client_id and client_secret blank (or use your own)
5. Choose full access scope (1)
6. Leave root_folder_id blank
7. Leave service_account_file blank
8. Choose `n` for advanced config
9. Choose `y` to auto config (opens browser)
10. Authorize in browser
11. Choose `n` for team drive
12. Confirm with `y`

### Verify Configuration

```bash
rclone ls gdrive:
```

Should list your Google Drive files.

### Get Config File

```bash
# Linux/Mac
cat ~/.config/rclone/rclone.conf

# Windows
type %USERPROFILE%\.config\rclone\rclone.conf
```

Copy this entire file's content. You'll need it for deployment.

## Step 3: Set Up Google Drive Index (Optional but Recommended)

A Google Drive index allows direct streaming/downloading of files.

### Option A: Deploy goindex to Cloudflare Workers

1. Fork [goindex repository](https://github.com/alx-xlx/goindex)
2. Follow their deployment guide
3. Deploy to Cloudflare Workers (free tier available)
4. Get your worker URL (e.g., `https://index.yourname.workers.dev`)

### Option B: Use GDIndex

1. Fork [GDIndex](https://github.com/maple3142/GDIndex)
2. Deploy to Vercel or Cloudflare Pages
3. Configure with your Google Drive credentials
4. Get your deployment URL

### Option C: Skip Index

You can skip this step, but you won't get direct streaming links. Only Google Drive web interface links will be available.

## Step 4: Deploy to Heroku

### Option A: One-Click Deploy (Easiest)

1. Click the Deploy to Heroku button in README.md
2. Enter your app name
3. Fill in environment variables:

   **Required:**
   - `BOT_TOKEN`: Your token from Step 1
   - `RCLONE_CONFIG`: Paste entire content from Step 2
   - `RCLONE_REMOTE_NAME`: `gdrive` (or whatever you named it)

   **Optional:**
   - `RCLONE_BASE_DIR`: `TorrentBot` (folder name on Google Drive)
   - `INDEX_BASE_URL`: Your index URL from Step 3
   - Keep other defaults

4. Click "Deploy app"
5. Wait 2-3 minutes for deployment

### Option B: Manual Heroku Deployment

```bash
# Install Heroku CLI
# https://devcenter.heroku.com/articles/heroku-cli

# Login
heroku login

# Clone your repository
git clone <your-repo>
cd HerokuHosted

# Create Heroku app
heroku create my-torrent-bot

# Set environment variables
heroku config:set BOT_TOKEN="your_token_here"
heroku config:set RCLONE_REMOTE_NAME="gdrive"
heroku config:set RCLONE_BASE_DIR="TorrentBot"
heroku config:set INDEX_BASE_URL="https://your-index.com"

# Set rclone config (entire file)
heroku config:set RCLONE_CONFIG="$(cat ~/.config/rclone/rclone.conf)"

# Deploy
git push heroku main

# Scale worker
heroku ps:scale worker=1

# Check status
heroku ps
```

## Step 5: Test Your Bot

1. Open Telegram
2. Search for your bot by username
3. Send `/start`
4. You should see a welcome message

## Step 6: Test Downloading

1. Find a test magnet link (use a small, legal torrent)
2. Send it to your bot
3. Choose "Download All" or "Select Files"
4. Wait for download and upload to complete
5. Click the provided links to verify

## Common Issues

### "Bot doesn't respond"

**Check if bot is running:**
```bash
heroku ps
```

**View logs:**
```bash
heroku logs --tail
```

**Restart bot:**
```bash
heroku ps:restart
```

### "Rclone upload failed"

**Test rclone config locally:**
```bash
echo "test" > test.txt
rclone copy test.txt gdrive:TorrentBot/
rclone ls gdrive:TorrentBot/
```

**Check Google Drive API quota:**
- Go to Google Cloud Console
- Check Drive API usage
- May need to wait if quota exceeded

### "Torrent download stuck"

**Check if magnet has seeders:**
- Use a torrent client to verify
- Try a different torrent

**Increase timeout:**
```bash
heroku config:set TORRENT_TIMEOUT="7200"  # 2 hours
```

### "Out of disk space"

**Reduce download size limit:**
```bash
heroku config:set MAX_DOWNLOAD_SIZE="524288000"  # 500MB
```

**Upgrade to paid dyno:**
- Hobby dyno ($7/month) has more resources
- Standard dyno ($25/month) for heavy usage

## Getting Your Telegram User ID

To restrict bot to specific users:

1. Send any message to [@userinfobot](https://t.me/userinfobot)
2. It will reply with your user ID
3. Set it in Heroku:
```bash
heroku config:set OWNER_IDS="123456789,987654321"
```

## Monitoring

**View logs in real-time:**
```bash
heroku logs --tail
```

**Check dyno status:**
```bash
heroku ps
```

**Check config:**
```bash
heroku config
```

**View app info:**
```bash
heroku apps:info
```

## Updating the Bot

```bash
# Pull latest changes
git pull origin main

# Deploy updates
git push heroku main

# Restart
heroku ps:restart
```

## Cost Estimates

**Free Tier:**
- Eco dynos: 1000 hours/month free
- Good for personal use
- ~500MB storage in /tmp
- 512MB RAM

**Paid Options:**
- Basic ($5/month): More reliable
- Standard 1X ($25/month): 512MB RAM
- Standard 2X ($50/month): 1GB RAM

## Next Steps

- Join Telegram groups for support
- Customize the bot to your needs
- Set up monitoring/alerts
- Consider backup strategies

## Security Tips

1. **Never share your bot token**
2. **Use OWNER_IDS to restrict access**
3. **Keep your rclone.conf secure**
4. **Monitor your Google Drive storage**
5. **Be aware of copyright laws**

## Need Help?

- Check logs: `heroku logs --tail`
- Review README.md for troubleshooting
- Open GitHub issue with:
  - Error message
  - Steps to reproduce
  - Relevant logs (remove sensitive info)

Happy torrenting! 🚀
