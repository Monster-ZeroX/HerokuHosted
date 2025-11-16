# Quick Start Guide

Get your Torrent to Google Drive Bot up and running in minutes!

## Prerequisites Checklist

Before deploying, make sure you have:

- [ ] Telegram Bot Token from [@BotFather](https://t.me/BotFather)
- [ ] Google Drive account
- [ ] Rclone configured with Google Drive (get `rclone.conf` file)
- [ ] (Optional) Google Drive Index deployed for direct streaming

## One-Click Heroku Deployment

### Step 1: Click Deploy Button

[![Deploy](https://www.herokucdn.com/deploy/button.svg)](https://www.heroku.com/deploy?template=https://github.com/Monster-ZeroX/HerokuHosted)

### Step 2: Fill Environment Variables

**Required:**
- `BOT_TOKEN`: Paste your bot token from BotFather
- `RCLONE_CONFIG`: Copy entire content of `~/.config/rclone/rclone.conf`
- `RCLONE_REMOTE_NAME`: Usually `gdrive` (check your rclone.conf)

**Optional:**
- `INDEX_BASE_URL`: Your Google Drive index URL (e.g., `https://index.example.com`)
- `RCLONE_BASE_DIR`: Folder name on GDrive (default: `TorrentBot`)

### Step 3: Deploy

Click **"Deploy app"** and wait 2-3 minutes.

### Step 4: Access Your Services

**Telegram Bot:**
1. Open your bot in Telegram
2. Send `/start`
3. Send a magnet link to test

**Web Application:**
1. Visit `https://your-app-name.herokuapp.com`
2. Click "Register"
3. Use invite code: **Kaveesha**
4. Create your account

**Admin Panel:**
1. Visit `https://your-app-name.herokuapp.com/login`
2. Username: `MonsterZeroX`
3. Password: `Kaveesha@2005`
4. Navigate to `/admin` to manage users

## Common First-Time Issues

### Issue: Bot doesn't respond
**Solution:**
```bash
heroku logs --tail --app your-app-name
```
Check for errors. Verify `BOT_TOKEN` is correct.

### Issue: Can't register on web app
**Solution:**
- Ensure you're using invite code: **Kaveesha**
- Check database is initialized: `heroku pg:info --app your-app-name`

### Issue: Rclone upload fails
**Solution:**
- Verify `RCLONE_CONFIG` contains full file content
- Test rclone locally: `rclone ls gdrive:`
- Check Google Drive quota

### Issue: Video player won't load
**Solution:**
- Set `INDEX_BASE_URL` environment variable
- Verify index is working (open URL in browser)

## Getting Rclone Config

### Quick Method
```bash
# View your rclone config
cat ~/.config/rclone/rclone.conf

# Copy to clipboard (Linux)
cat ~/.config/rclone/rclone.conf | xclip -selection clipboard

# Copy to clipboard (Mac)
cat ~/.config/rclone/rclone.conf | pbcopy

# Windows
type %USERPROFILE%\.config\rclone\rclone.conf
```

### If You Don't Have Rclone Configured

1. **Install rclone:**
   - Linux/Mac: `curl https://rclone.org/install.sh | sudo bash`
   - Windows: Download from [rclone.org/downloads](https://rclone.org/downloads/)

2. **Configure Google Drive:**
   ```bash
   rclone config
   ```
   - Choose `n` for new remote
   - Name: `gdrive`
   - Storage: Choose `Google Drive`
   - Follow prompts to authenticate

3. **Get config file:**
   ```bash
   cat ~/.config/rclone/rclone.conf
   ```

## Setting Up Google Drive Index (Optional)

For direct streaming links, deploy a Google Drive index:

### Option 1: GoIndex (Recommended)
1. Visit [goindex repository](https://github.com/alx-xlx/goindex)
2. Click "Deploy to Cloudflare Workers"
3. Follow setup instructions
4. Get your index URL (e.g., `https://example.workers.dev`)
5. Set as `INDEX_BASE_URL` in Heroku

### Option 2: GDIndex
1. Visit [GDIndex repository](https://github.com/maple3142/GDIndex)
2. Deploy to Vercel or Cloudflare
3. Configure with your Google Drive
4. Use the URL as `INDEX_BASE_URL`

## Default Credentials Reference

### Web App Admin
```
Username: MonsterZeroX
Password: Kaveesha@2005
URL: https://your-app.herokuapp.com/admin
```

### Registration Invite Code
```
Code: Kaveesha
Type: Unlimited uses
Status: Active by default
```

## Essential Commands

### Check App Status
```bash
heroku ps --app your-app-name
```

### View Logs
```bash
# All logs
heroku logs --tail --app your-app-name

# Web dyno only
heroku logs --tail --dyno web --app your-app-name

# Worker dyno only
heroku logs --tail --dyno worker --app your-app-name
```

### Restart App
```bash
heroku restart --app your-app-name
```

### Scale Dynos
```bash
# Start both
heroku ps:scale web=1 worker=1 --app your-app-name

# Stop both (saves dyno hours)
heroku ps:scale web=0 worker=0 --app your-app-name
```

### Check Database
```bash
heroku pg:info --app your-app-name
```

## First Test

### Test Telegram Bot
1. Open bot in Telegram
2. Send: `/start`
3. Send a small magnet link (test with a small file first)
4. Choose "Download All"
5. Wait for upload to complete
6. Click "Direct Link" button

### Test Web App
1. Register new user account
2. Login to dashboard
3. Click "Add New Torrent"
4. Paste same magnet link
5. Wait for completion
6. Click "Watch Online" on a video file
7. Verify player loads

### Test Admin Panel
1. Login as admin (MonsterZeroX)
2. Go to `/admin`
3. View registered users
4. Create new invite code
5. Test inviting a friend

## Next Steps

**Security:**
1. Change admin password immediately
2. Create new invite codes
3. Deactivate default "Kaveesha" code

**Customization:**
1. Read [WEBAPP.md](WEBAPP.md) for detailed web app documentation
2. Customize UI colors and branding
3. Configure external player preferences

**Optimization:**
1. Adjust `MAX_DOWNLOAD_SIZE` based on your dyno
2. Set `CONCURRENT_DOWNLOADS` appropriately
3. Monitor dyno usage and upgrade if needed

## Getting Help

**Documentation:**
- [README.md](README.md) - Complete project documentation
- [WEBAPP.md](WEBAPP.md) - Detailed web app guide
- [SETUP.md](SETUP.md) - Setup instructions

**Troubleshooting:**
```bash
# Check everything
heroku ps --app your-app-name
heroku config --app your-app-name
heroku logs --tail --app your-app-name
```

**Community:**
- Open GitHub issue for bugs
- Check existing issues for solutions
- Fork and contribute improvements

## Pro Tips

1. **Save Dyno Hours**: Scale down when not using
   ```bash
   heroku ps:scale web=0 worker=0
   ```

2. **Monitor Usage**: Check dyno hours monthly
   ```bash
   heroku ps --app your-app-name
   ```

3. **Backup Database**: Export data periodically
   ```bash
   heroku pg:backups:capture --app your-app-name
   heroku pg:backups:download --app your-app-name
   ```

4. **Test Locally First**: Run locally before deploying changes

5. **Use Environment Variables**: Never hardcode credentials

## Quick Reference URLs

Replace `your-app-name` with your actual Heroku app name:

- **Web App**: `https://your-app-name.herokuapp.com`
- **Register**: `https://your-app-name.herokuapp.com/register`
- **Login**: `https://your-app-name.herokuapp.com/login`
- **Dashboard**: `https://your-app-name.herokuapp.com/dashboard`
- **Admin Panel**: `https://your-app-name.herokuapp.com/admin`
- **Add Torrent**: `https://your-app-name.herokuapp.com/add-torrent`

---

**Ready to go?** Click the deploy button and start uploading! 🚀
