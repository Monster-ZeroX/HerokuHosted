# DirectTorrent.me – Deployment Guide

DirectTorrent.me pairs a Flask JSON API with a Next.js frontend for torrent and Mega.nz transfers that land in Google Drive via rclone. This document explains how to run the stack locally and how to deploy the backend (Heroku) and frontend (Vercel) so they talk to the same database and session-aware API.

## Architecture at a glance
- **Backend:** Flask app factory (`webapp/app_factory.py`) exposing JSON-only routes under `/api/*` and using SQLAlchemy models in `webapp/models.py`. Business logic lives in `webapp/services/` (auth, torrents, billing, stats, etc.).
- **Frontend:** Next.js (app router) in `frontend/` consuming the API via `frontend/lib/api.ts` with `credentials: 'include'` so browser sessions work.
- **Data/Storage:** External Postgres (via `DATABASE_URL`), libtorrent for downloads, and rclone for uploads to Google Drive. Jobs capture `app_role`/`app_instance` for free vs paid Heroku dynos.
- **Legacy:** Telegram bot and old templates live in `legacy/` for reference but are not used by the new stack.

## Prerequisites
- Python 3.9+ (matches `runtime.txt`)
- Node.js 18+ and npm or pnpm/yarn
- Postgres database URL
- rclone config that can write to your Google Drive remote
- Maileroo API key (for OTP email) or rely on console logging in dev

## Backend setup (local)
1. Create a virtualenv and install dependencies:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```
2. Set environment variables (example):
   ```bash
   export FLASK_ENV=development
   export SECRET_KEY="change-me"
   export DATABASE_URL="postgresql://user:pass@host:5432/directtorrent"
   export APP_ROLE="FREE"            # FREE or PAID depending on dyno role
   export APP_INSTANCE="directtorrent-free-local"
   export ALLOWED_ORIGINS="http://localhost:3000"
   export MAILEROO_API_KEY="your-maileroo-key"   # omit to log emails locally
   export MAILEROO_SENDER="noreply@directtorrent.me"
   export RCLONE_CONFIG_PATH="$PWD/rclone.conf"  # path to your rclone.conf
   export RCLONE_REMOTE_NAME="gdrive"
   export RCLONE_BASE_DIR="DirectTorrent"
   ```
   > Tip: set `RCLONE_CONFIG` with the file contents in env-only deployments; `drive/rclone.py` will write it to `RCLONE_CONFIG_PATH` when present.
3. Ensure the database exists and run the server:
   ```bash
   flask --app web_server run --port 5000
   ```
   The API will create tables on startup via `db.create_all()`.

## Frontend setup (local)
1. Install dependencies:
   ```bash
   cd frontend
   npm install
   ```
2. Point the frontend to your backend and run dev mode:
   ```bash
   export NEXT_PUBLIC_API_BASE="http://localhost:5000"
   npm run dev
   ```
   Visit http://localhost:3000. Cookies will flow because the API sets `Access-Control-Allow-Credentials` and the frontend uses `credentials: 'include'`.

## Deploying the backend to Heroku
1. Create separate apps for free and paid processing (plus an optional backup) all pointing to the same managed Postgres:
   ```bash
   heroku create directtorrent-free-1
   heroku create directtorrent-paid-1
   heroku addons:create heroku-postgresql:standard-0 --app directtorrent-paid-1
   heroku addons:attach directtorrent-paid-1::DATABASE --app directtorrent-free-1
   ```
2. Configure shared settings on each app:
   ```bash
   heroku config:set SECRET_KEY="<strong-secret>" --app directtorrent-free-1
   heroku config:set SECRET_KEY="<strong-secret>" --app directtorrent-paid-1

   heroku config:set APP_ROLE=FREE APP_INSTANCE=directtorrent-free-1 --app directtorrent-free-1
   heroku config:set APP_ROLE=PAID APP_INSTANCE=directtorrent-paid-1 --app directtorrent-paid-1

   heroku config:set RCLONE_REMOTE_NAME=gdrive RCLONE_BASE_DIR=DirectTorrent --app directtorrent-free-1
   heroku config:set RCLONE_REMOTE_NAME=gdrive RCLONE_BASE_DIR=DirectTorrent --app directtorrent-paid-1

   # Paste the full rclone.conf content
   heroku config:set RCLONE_CONFIG="$(cat ~/.config/rclone/rclone.conf)" --app directtorrent-free-1
   heroku config:set RCLONE_CONFIG="$(cat ~/.config/rclone/rclone.conf)" --app directtorrent-paid-1

   # Maileroo (or skip to log-only)
   heroku config:set MAILEROO_API_KEY="<api-key>" MAILEROO_SENDER="noreply@directtorrent.me" --app directtorrent-free-1
   heroku config:set MAILEROO_API_KEY="<api-key>" MAILEROO_SENDER="noreply@directtorrent.me" --app directtorrent-paid-1

   # CORS for your Vercel domain
   heroku config:set ALLOWED_ORIGINS="https://directtorrent.vercel.app" --app directtorrent-free-1
   heroku config:set ALLOWED_ORIGINS="https://directtorrent.vercel.app" --app directtorrent-paid-1
   ```
3. Deploy the code (push the same branch to both apps):
   ```bash
   git push https://git.heroku.com/directtorrent-free-1.git HEAD:main
   git push https://git.heroku.com/directtorrent-paid-1.git HEAD:main
   ```
4. Verify dynos are web-only (Procfile: `web: gunicorn web_server:app ...`) and that each app reports its role via `/api/admin/usage/heroku` stats.

## Deploying the frontend to Vercel
1. From the `frontend/` directory run `vercel` (or use the Vercel dashboard) and connect the project.
2. Set environment variables in Vercel:
   - `NEXT_PUBLIC_API_BASE` = URL of the preferred backend (e.g., `https://directtorrent-free-1.herokuapp.com` if you route all browser traffic through the free app, or a load balancer if present).
3. Build and deploy:
   ```bash
   npm run build
   ```
   Vercel will run the build automatically during deployment.

## Connecting frontend and backend
- **CORS:** Ensure the backend `ALLOWED_ORIGINS` includes your Vercel domain so cookies are accepted.
- **Sessions:** The API uses Flask sessions; keep `credentials: 'include'` (already set in `frontend/lib/api.ts`).
- **Plan-aware behavior:** The backend enforces daily limits and marks jobs with `app_role`/`app_instance`; paid frontends should point to a backend with `APP_ROLE=PAID` to unlock higher limits and priority flags in responses.

## Running tests
From the repo root:
```bash
pytest -q
```
This covers OTP flows, daily limit enforcement, and torrent status transitions.

## Useful paths
- Backend entrypoint: `web_server.py`
- App factory: `webapp/app_factory.py`
- API blueprints: `webapp/api/`
- Services: `webapp/services/`
- Models: `webapp/models.py`
- Frontend API wrapper: `frontend/lib/api.ts`
- Legacy bot/templates (unused): `legacy/`
