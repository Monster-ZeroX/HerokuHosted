# Web Application Documentation

This document provides detailed information about the web application component of the Torrent to Google Drive Bot.

## Overview

The web application provides a user-friendly interface for managing torrents, viewing downloads, and streaming videos directly in your browser. It runs alongside the Telegram bot on the same Heroku app, sharing the same database and torrent processing system.

## Features

### User Management
- **Invite Code System**: Control who can register
- **Password Authentication**: Secure login with hashed passwords
- **Session Management**: Persistent login sessions
- **User Dashboard**: Personal torrent library

### Admin Features
- **User Administration**: View, delete, and manage user accounts
- **Password Reset**: Reset passwords for any user
- **Invite Code Management**: Create, activate/deactivate invite codes
- **Usage Tracking**: Monitor invite code usage

### Torrent Features
- **Add Torrents**: Submit magnet links or .torrent files
- **Track Progress**: Real-time status updates
- **File Management**: View all files within a torrent
- **Direct Links**: Access Google Drive and streaming links

### Video Player
- **Built-in Player**: Video.js HTML5 player
- **External Player Support**: VLC, MX Player, PotPlayer integration
- **Resume Playback**: Auto-save playback position
- **Playlist**: Navigate between files in same torrent

## Default Credentials

### Admin Account
- **Username**: `MonsterZeroX`
- **Password**: `Kaveesha@2005`
- **Access Level**: Full admin privileges

### Default Invite Code
- **Code**: `Kaveesha`
- **Type**: Unlimited uses
- **Status**: Active by default

## Routes & Pages

### Public Routes (No Authentication Required)

#### `/` - Home/Landing Page
- Redirects to login if not authenticated
- Redirects to dashboard if authenticated

#### `/register` - Registration Page
- **Method**: GET, POST
- **Required Fields**: Username, Password, Invite Code
- **Validation**:
  - Username must be unique
  - Password minimum length: 6 characters
  - Invite code must be valid and active
- **Success**: Redirects to login page

#### `/login` - Login Page
- **Method**: GET, POST
- **Required Fields**: Username, Password
- **Success**: Redirects to dashboard
- **Error**: Shows error message

#### `/logout` - Logout
- **Method**: GET
- Clears session and redirects to login

### User Routes (Authentication Required)

#### `/dashboard` - User Dashboard
- **Method**: GET
- **Display**: List of all torrents added by user
- **Features**:
  - View torrent status (Queued, Downloading, Uploading, Completed)
  - Progress indicators
  - Quick actions (View details, Delete)
  - Add new torrent button

#### `/add-torrent` - Add New Torrent
- **Method**: GET, POST
- **Input**: Magnet link or .torrent file upload
- **Processing**: Creates torrent record and initiates download
- **Success**: Redirects to dashboard

#### `/torrent/<id>` - Torrent Details
- **Method**: GET
- **Display**:
  - Torrent metadata (name, size, status)
  - List of files
  - Google Drive link (if completed)
  - Individual file links
- **Actions**:
  - Watch video files
  - Copy direct links
  - Delete torrent

#### `/player/<file_id>` - Video Player
- **Method**: GET
- **Features**:
  - Video.js player with controls
  - External player buttons (VLC, MX Player, PotPlayer)
  - Playlist of other files
  - Copy link button
- **LocalStorage**: Saves playback position

### Admin Routes (Admin Authentication Required)

#### `/admin` - Admin Panel
- **Method**: GET, POST
- **Access**: Admin users only
- **Sections**:
  1. **User Management**
     - List all users
     - Delete user accounts
     - Reset passwords
  2. **Invite Code Management**
     - View all invite codes
     - Create new codes
     - Toggle activation
     - View usage statistics

### API Routes

#### `/api/torrent/<id>/status` - Get Torrent Status
- **Method**: GET
- **Returns**: JSON with current status and progress
- **Used by**: Dashboard auto-refresh

## Database Schema

### User Model
```python
class User(UserMixin, db.Model):
    id = Integer (Primary Key)
    username = String(80) (Unique, Required)
    password_hash = String(255) (Required)
    is_admin = Boolean (Default: False)
    created_at = DateTime (Default: now)
```

**Methods:**
- `set_password(password)`: Hash and store password
- `check_password(password)`: Verify password
- `torrents`: Relationship to user's torrents

### Torrent Model
```python
class Torrent(db.Model):
    id = Integer (Primary Key)
    user_id = Integer (Foreign Key -> User)
    info_hash = String(40) (Unique, Required)
    name = String(255)
    magnet_link = Text
    total_size = BigInteger
    status = String(20) (Default: 'queued')
    progress = Float (Default: 0.0)
    gdrive_link = Text
    created_at = DateTime (Default: now)
    completed_at = DateTime
```

**Status Values:**
- `queued`: Waiting to start
- `downloading`: Currently downloading
- `uploading`: Uploading to Google Drive
- `completed`: Finished and uploaded
- `failed`: Error occurred

### TorrentFile Model
```python
class TorrentFile(db.Model):
    id = Integer (Primary Key)
    torrent_id = Integer (Foreign Key -> Torrent)
    file_path = String(512) (Required)
    file_size = BigInteger
    index_link = Text
    created_at = DateTime (Default: now)
```

### InviteCode Model
```python
class InviteCode(db.Model):
    id = Integer (Primary Key)
    code = String(50) (Unique, Required)
    created_by = Integer (Foreign Key -> User)
    max_uses = Integer (Default: 0, 0 = unlimited)
    current_uses = Integer (Default: 0)
    is_active = Boolean (Default: True)
    created_at = DateTime (Default: now)
```

## Security Features

### Password Security
- **Hashing Algorithm**: PBKDF2-SHA256
- **Implementation**: werkzeug.security
- **Storage**: Only hashed passwords stored in database
- **Verification**: Constant-time comparison

### Session Security
- **Implementation**: Flask-Login
- **Storage**: Server-side sessions
- **Expiration**: Configurable via Flask config
- **CSRF Protection**: Enabled by default

### Access Control
- **Login Required**: Decorator for protected routes
- **Admin Required**: Custom decorator for admin routes
- **User Isolation**: Users can only access their own torrents

### Input Validation
- **Username**: Alphanumeric, 3-30 characters
- **Password**: Minimum 6 characters
- **Invite Code**: Must exist and be active
- **Magnet Links**: Basic format validation

## Video Player Integration

### Video.js Configuration
```javascript
var player = videojs('my-video', {
    controls: true,
    autoplay: false,
    preload: 'auto',
    fluid: true,
    playbackRates: [0.5, 1, 1.5, 2]
});
```

### Playback Position Saving
- **Storage**: localStorage
- **Key**: `videoPosition_<file_id>`
- **Trigger**: Every 5 seconds during playback
- **Resume**: Automatic on page load

### External Player Integration

#### VLC (Desktop)
```
vlc://{{ file.index_link }}
```

#### MX Player (Android)
```
intent:{{ file.index_link }}#Intent;package=com.mxtech.videoplayer.ad;end
```

#### PotPlayer (Windows)
```
potplayer://{{ file.index_link }}
```

## Environment Variables

Web app specific variables (in addition to bot variables):

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `SECRET_KEY` | Flask session secret key | Auto-generated | ❌ |
| `DATABASE_URL` | PostgreSQL connection string | Auto-set by Heroku | ✅ |
| `FLASK_ENV` | Environment (development/production) | `production` | ❌ |

## Database Initialization

The database is automatically initialized on first run with:

1. **Create all tables** from models
2. **Create admin user** (MonsterZeroX/Kaveesha@2005)
3. **Create default invite code** (Kaveesha)

**Manual initialization:**
```python
from webapp.app import app
from webapp.models import db, init_db

with app.app_context():
    init_db(app)
```

## Customization Guide

### Changing Admin Credentials

**Option 1: Via Database (Recommended)**
```python
# Heroku console
heroku run python

>>> from webapp.app import app
>>> from webapp.models import db, User
>>> with app.app_context():
...     admin = User.query.filter_by(username='MonsterZeroX').first()
...     admin.set_password('NewSecurePassword')
...     db.session.commit()
```

**Option 2: Via Admin Panel**
1. Login as current admin
2. Go to `/admin`
3. Reset password for MonsterZeroX user

### Creating Additional Admin Users

```python
# Heroku console
heroku run python

>>> from webapp.app import app
>>> from webapp.models import db, User
>>> with app.app_context():
...     new_admin = User(username='NewAdmin', is_admin=True)
...     new_admin.set_password('password123')
...     db.session.add(new_admin)
...     db.session.commit()
```

### Customizing Invite Codes

**Via Admin Panel:**
1. Login as admin
2. Navigate to `/admin`
3. Scroll to "Create New Invite Code"
4. Fill in:
   - **Code**: Your custom code (e.g., "WELCOME2024")
   - **Max Uses**: 0 for unlimited, or specific number
   - **Active**: Check to enable immediately
5. Click "Create Code"

**Via Database:**
```python
from webapp.models import db, InviteCode

with app.app_context():
    code = InviteCode(
        code='CUSTOM123',
        max_uses=100,  # 0 = unlimited
        is_active=True
    )
    db.session.add(code)
    db.session.commit()
```

### Customizing UI Theme

**Edit `webapp/static/style.css`:**
```css
/* Change primary color */
:root {
    --primary-color: #667eea;  /* Change this */
    --secondary-color: #764ba2;  /* And this */
}

/* Customize navbar */
.navbar {
    background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
}
```

**Edit `webapp/templates/base.html`:**
```html
<!-- Change site title -->
<title>{% block title %}Your Custom Title{% endblock %}</title>

<!-- Change navbar brand -->
<a class="navbar-brand" href="/">
    <i class="bi bi-cloud-download"></i> Your Brand Name
</a>
```

### Adding Custom Pages

1. **Create route in `webapp/app.py`:**
```python
@app.route('/custom-page')
@login_required
def custom_page():
    return render_template('custom_page.html')
```

2. **Create template `webapp/templates/custom_page.html`:**
```html
{% extends "base.html" %}

{% block title %}Custom Page{% endblock %}

{% block content %}
<div class="container mt-5">
    <h1>Your Custom Content</h1>
</div>
{% endblock %}
```

3. **Add to navbar (optional):**
```html
<!-- In base.html -->
<li class="nav-item">
    <a class="nav-link" href="/custom-page">Custom Page</a>
</li>
```

## Deployment Notes

### Heroku Dynos Configuration
- **Web Dyno**: Runs Flask app (web_server.py)
- **Worker Dyno**: Runs Telegram bot (main.py)
- Both dynos share the same database

### Scaling
```bash
# Scale up
heroku ps:scale web=1 worker=1

# Scale down (saves dyno hours)
heroku ps:scale web=0 worker=0
```

### Database Migrations

If you modify models, you may need to migrate:

```bash
# Connect to database
heroku pg:psql

# Drop and recreate tables (WARNING: Deletes all data)
DROP TABLE torrent_file;
DROP TABLE torrent;
DROP TABLE invite_code;
DROP TABLE user;

# Restart dyno to reinitialize
heroku restart
```

**For production, use Alembic for proper migrations.**

## Troubleshooting

### Database Issues

**Issue**: Tables not created
```bash
# Check if database exists
heroku pg:info

# Reinitialize database
heroku restart
```

**Issue**: Admin user doesn't exist
```python
# Create manually via console
heroku run python
>>> from webapp.app import app
>>> from webapp.models import init_db
>>> with app.app_context():
...     init_db(app)
```

### Login Issues

**Issue**: Can't login with correct credentials
- Clear browser cookies
- Check database connection
- Verify password hash in database
- Check session secret key is set

**Issue**: Session expires immediately
- Set `SECRET_KEY` environment variable
- Check `PERMANENT_SESSION_LIFETIME` config

### Video Player Issues

**Issue**: Videos won't play
- Verify `INDEX_BASE_URL` is set
- Check index URL is accessible
- Test direct link in browser
- Check CORS headers on index

**Issue**: External player doesn't open
- Check URL scheme is correct for your OS
- Verify player app is installed
- Try copying link manually

### Performance Issues

**Issue**: Slow page loads
- Enable browser caching
- Minimize database queries
- Consider upgrading dyno size

**Issue**: Database timeout
- Upgrade PostgreSQL plan
- Optimize queries
- Add database indexes

## Best Practices

### Security
1. Change default admin password immediately
2. Use strong invite codes
3. Regularly audit user accounts
4. Enable HTTPS (automatic on Heroku)
5. Set secure session cookie flags

### Performance
1. Use database indexes for large tables
2. Implement pagination for long lists
3. Cache frequently accessed data
4. Minimize external API calls

### Maintenance
1. Regularly check Heroku logs
2. Monitor database size
3. Clean up old/failed torrents
4. Backup database periodically

### User Experience
1. Provide clear error messages
2. Implement loading indicators
3. Add confirmation dialogs for destructive actions
4. Test on mobile devices

## API Documentation (Future)

The current implementation doesn't have a public API, but you could add:

### Example: RESTful API Endpoints

```python
# GET /api/v1/torrents
# Returns all user torrents

# POST /api/v1/torrents
# Add new torrent

# GET /api/v1/torrents/<id>
# Get torrent details

# DELETE /api/v1/torrents/<id>
# Delete torrent
```

**Implementation would require:**
- API key authentication
- Rate limiting
- CORS configuration
- JSON serialization

## Contributing

When contributing to the web app:

1. Test locally before deploying
2. Follow Flask best practices
3. Update this documentation
4. Maintain security standards
5. Write clear commit messages

## License

Same as main project (MIT License)

---

**Need help?** Check the main README.md or open an issue on GitHub.
