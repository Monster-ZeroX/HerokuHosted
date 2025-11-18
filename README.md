# DirectTorrent.me – Deployment Guide

DirectTorrent.me pairs a Flask JSON API with a Next.js frontend for torrent and Mega.nz transfers that land in Google Drive via rclone. This document explains how to run the stack locally and how to deploy the backend (Heroku) and frontend (Vercel) so they talk to the same database and session-aware API.

## Architecture at a glance
- **Backend:** Flask app factory (`webapp/app_factory.py`) exposing JSON-only routes under `/api/*` and using SQLAlchemy models in `webapp/models.py`. Business logic lives in `webapp/services/` (auth, torrents, billing, stats, etc.).
- **Frontend:** Single Next.js (app router) site in `frontend/` consuming the API via `frontend/lib/api.ts` with `credentials: 'include'` so browser sessions work.
- **Data/Storage:** External Postgres (via `DATABASE_URL`), libtorrent for downloads, and rclone for uploads to Google Drive. Jobs capture `app_role`/`app_instance` for free vs paid Heroku dynos.
- **Legacy:** Telegram bot and old templates live in `legacy/` for reference but are not used by the new stack.

## Prerequisites
- Python 3.9+ (matches `runtime.txt`)
- Node.js 18+ and npm or pnpm/yarn
- Postgres database URL
- rclone config that can write to your Google Drive remote
- Maileroo API key (for OTP email) or rely on console logging in dev
- Full config var reference: see [`CONFIG_VARS.md`](CONFIG_VARS.md) for every environment variable and where to set it (Heroku, Vercel, and local `.env`).

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
Use the **single codebase** to deploy two web apps that share one Postgres: one with `APP_ROLE=FREE` and one with `APP_ROLE=PAID` (optionally a backup). The Next.js frontend is shared by all users and simply points to whichever backend you want browsers to hit.

### One-click deploy buttons (no CLI required)
Click the button twice—once to spin up your free dyno (set `APP_ROLE=FREE`) and once for the paid dyno (`APP_ROLE=PAID`). The button below pins the working branch that already contains the root-level `app.json` Heroku requires.

[![Deploy to Heroku](https://www.herokucdn.com/deploy/button.svg)](https://dashboard.heroku.com/new?template=https://github.com/Monster-ZeroX/HerokuHosted/tree/codex/refactor-project-to-flask-api-and-next.js-frontend)

Heroku clones that branch and reads `/app.json` directly, so you should no longer see the "No app.json located" error when launching from the button.

After deploy, open each app’s Settings → Config Vars and fill the checklist below (match `APP_ROLE`/`APP_INSTANCE` to the dyno).

### Manual CLI alternative (optional)
If you prefer the CLI, you can still create apps and push the same branch to both dynos, then set config vars as shown above. Verify dynos are web-only (Procfile: `web: gunicorn web_server:app ...`) and that each app reports its role via `/api/admin/usage/heroku`.

### Heroku config vars (copy/paste checklist)
Set these on **every** DirectTorrent.me Heroku app unless marked optional. Values that differ between free/paid apps are noted.

| Variable | Required? | Suggested value / notes |
| --- | --- | --- |
| `SECRET_KEY` | Yes | Strong random string for Flask sessions. |
| `DATABASE_URL` | Yes | Provided automatically when you attach Heroku Postgres; share the same database across free/paid apps. |
| `APP_ROLE` | Yes | `FREE` for free dynos, `PAID` for paid dynos. |
| `APP_INSTANCE` | Yes | Unique label for the dyno/app (e.g., `directtorrent-free-1`, `directtorrent-paid-1`). Falls back to `HEROKU_APP_NAME`. |
| `ALLOWED_ORIGINS` | Yes | Comma-separated list of frontend origins (`https://<your-vercel-domain>`). |
| `MAILEROO_API_KEY` | Optional | Needed to send OTP emails in production. Leave unset to log OTPs only. |
| `MAILEROO_SENDER` | Optional | Sender email for OTPs (e.g., `noreply@directtorrent.me`). Defaults to `noreply@directtorrent.me`. |
| `RCLONE_CONFIG` | Yes | Full contents of your `rclone.conf` file (paste as a single value). |
| `RCLONE_CONFIG_PATH` | Optional | Path where the config is written. Default `/app/rclone.conf`. |
| `RCLONE_REMOTE_NAME` | Yes | Remote name from your rclone config (e.g., `gdrive`). |
| `RCLONE_BASE_DIR` | Optional | Base folder on the remote for uploads (e.g., `DirectTorrent`). |
| `INDEX_BASE_URL` | Optional | Base URL of a public Drive index if you expose streaming links. |
| `MEGA_EMAIL` | Optional | Mega.nz account email for premium transfers. |
| `MEGA_PASSWORD` | Optional | Mega.nz account password. |
| `GENIE_API_KEY` | Optional | Genie Business Connect API key for billing/transactions. |
| `GENIE_MERCHANT_ID` | Optional | Genie merchant ID. |
| `GENIE_API_BASE` | Optional | Genie API base (default `https://api.geniebiz.lk/public/v2`). |
| `GENIE_CREATE_PAYMENT_URL` | Optional | Override for Genie create-payment endpoint. |
| `GENIE_PAYMENT_STATUS_URL` | Optional | Override template for Genie payment status checks. |
| `GENIE_CURRENCY` | Optional | Currency code for payments (default `LKR`). |
| `PLAN_100_PRICE_LKR` | Optional | Price override for 100GB/day plan (default `300`). |
| `PLAN_300_PRICE_LKR` | Optional | Price override for 300GB/day plan (default `600`). |
| `PLAN_UNLIMITED_PRICE_LKR` | Optional | Price override for unlimited plan (default `1200`). |
| `PORT` | No | Heroku sets this automatically for web dynos. |

## Deploying the frontend to Vercel
1. From the `frontend/` directory run `vercel` (or use the Vercel dashboard) and connect the project.
2. Set environment variables in Vercel:
   - `NEXT_PUBLIC_API_BASE` = URL of the preferred backend (e.g., `https://directtorrent-free-1.herokuapp.com` if you route all browser traffic through the free app, or a load balancer if present). **Use an HTTPS URL**; browsers block mixed-content requests from the HTTPS Vercel frontend to an HTTP API and will surface a generic "Failed to fetch" error.
3. Build and deploy:
   ```bash
   npm run build
   ```
   Vercel will run the build automatically during deployment.

## Connecting frontend and backend
- **CORS:** Ensure the backend `ALLOWED_ORIGINS` includes your Vercel domain so cookies are accepted.
- **Sessions:** The API uses Flask sessions; keep `credentials: 'include'` (already set in `frontend/lib/api.ts`). For cross-domain deployments, set `SESSION_COOKIE_SAMESITE=None` and `SESSION_COOKIE_SECURE=true` in Heroku config so browsers will send cookies to the API from the Vercel origin.
- **Plan-aware behavior:** The backend enforces daily limits and marks jobs with `app_role`/`app_instance`; the single Next.js frontend can target either backend. Use the paid backend URL for paid users (priority speed/support) and the free backend for free users.
- **API reference:** A full endpoint-by-endpoint guide lives in [`API_DOCUMENTATION.md`](API_DOCUMENTATION.md) for quick troubleshooting or testing.

## Running tests
From the repo root:
```bash
pytest -q
```
This covers OTP flows, daily limit enforcement, and torrent status transitions.

## Quick API smoke test from your laptop
A small helper script lives at `tools/check_api.py` to verify the deployed API responds as expected without opening the browser. Example:

```bash
python tools/check_api.py --base https://your-backend.herokuapp.com --email demo@example.com --password hunter2
```

It hits `/api/auth/me`, `/api/auth/login`, `/api/torrents`, and (optionally with `--admin`) `/api/admin/overview`, printing the JSON responses.

## Useful paths
- Backend entrypoint: `web_server.py`
- App factory: `webapp/app_factory.py`
- API blueprints: `webapp/api/`
- Services: `webapp/services/`
- Models: `webapp/models.py`
- Frontend API wrapper: `frontend/lib/api.ts`
- Legacy bot/templates (unused): `legacy/`
