# Configuration Variables

This reference lists every environment variable used by DirectTorrent.me and where to set it for each deployment target.

- **Backend (Heroku apps)**: Set via the Heroku dashboard or CLI. The one-click Deploy button reads `app.json` and will prompt for required values.
- **Frontend (Vercel)**: Set under *Project Settings → Environment Variables*. Use **Production** scope for live deployments and **Preview** for test deployments.
- **Local development**: Create a `.env` file in the project root for Flask (or export variables in your shell) and a `.env.local` inside `frontend/` for Next.js.

## Backend variables (Heroku)
These match `app.json`. Required values are marked **(required)**.

| Variable | Scope | Purpose |
| --- | --- | --- |
| `SECRET_KEY` **(required)** | Backend | Flask session signing key. Generate a strong random value. |
| `DATABASE_URL` **(required)** | Backend | Postgres connection string. Heroku Postgres sets this automatically. |
| `APP_ROLE` **(required)** | Backend | `FREE` or `PAID` to tag jobs from each dyno. |
| `APP_INSTANCE` | Backend | Unique label for the dyno/app instance (e.g., `directtorrent-free-1`). Useful for Heroku usage stats. |
| `ALLOWED_ORIGINS` **(required)** | Backend | Comma-separated origins allowed for CORS (e.g., `https://directtorrent.me,https://directtorrent.vercel.app`). |
| `MAILEROO_API_KEY` | Backend | Maileroo API key for sending OTP emails. |
| `MAILEROO_SENDER` | Backend | From-address for OTP email (default: `noreply@directtorrent.me`). |
| `RCLONE_CONFIG` **(required)** | Backend | Full `rclone.conf` contents pasted as one value. |
| `RCLONE_CONFIG_PATH` | Backend | Where to write the rclone config inside the dyno (default `/app/rclone.conf`). |
| `RCLONE_REMOTE_NAME` **(required)** | Backend | Remote name defined in `rclone.conf` (e.g., `gdrive`). |
| `RCLONE_BASE_DIR` | Backend | Base directory on the remote for uploads (default `DirectTorrent`). |
| `INDEX_BASE_URL` | Backend | Optional public index base URL for streaming links. |
| `MEGA_EMAIL` / `MEGA_PASSWORD` | Backend | Optional Mega.nz credentials for Mega jobs. |
| `GENIE_API_KEY` / `GENIE_MERCHANT_ID` | Backend | Genie Business Connect credentials for billing. |
| `GENIE_API_BASE` | Backend | Genie API base URL (default `https://api.geniebiz.lk/public/v2`). |
| `GENIE_CREATE_PAYMENT_URL` | Backend | Override for the Genie create-payment endpoint. |
| `GENIE_PAYMENT_STATUS_URL` | Backend | Override template for Genie payment status checks. |
| `GENIE_CURRENCY` | Backend | Billing currency (default `LKR`). |
| `PLAN_100_PRICE_LKR` | Backend | Price override for 100GB/day plan (default `300`). |
| `PLAN_300_PRICE_LKR` | Backend | Price override for 300GB/day plan (default `600`). |
| `PLAN_UNLIMITED_PRICE_LKR` | Backend | Price override for unlimited plan (default `1200`). |

### Suggested per-app values
- **Free dyno(s)**: `APP_ROLE=FREE`, `APP_INSTANCE=directtorrent-free-1`, set `ALLOWED_ORIGINS` to your Vercel domain(s).
- **Paid dyno**: `APP_ROLE=PAID`, `APP_INSTANCE=directtorrent-paid-1`, same `ALLOWED_ORIGINS` values.

## Frontend variables (Vercel / `frontend/.env.local`)
| Variable | Purpose |
| --- | --- |
| `NEXT_PUBLIC_API_BASE` **(recommended)** | Full HTTPS base URL for the backend (e.g., `https://directtorrent-free-1-d466324d1d71.herokuapp.com`). Avoid HTTP to prevent mixed-content errors. |
| `NEXT_PUBLIC_API_BASE_URL` | Alternative name accepted by the client; use one or the other. |

> Tip: For preview environments, set `NEXT_PUBLIC_API_BASE` to the correct staging Heroku app so browser requests go to the right API.

## Local Flask development (`.env` or shell)
In addition to the backend variables above, configure:

| Variable | Purpose |
| --- | --- |
| `FLASK_APP=web_server.py` | Entry point for local Flask runs. |
| `FLASK_ENV=development` | Enables debug mode locally (optional). |

Use `pip install -r requirements.txt` then `python web_server.py` after exporting required variables.

## Local Next.js development (`frontend/.env.local`)
Set `NEXT_PUBLIC_API_BASE=http://localhost:5000` when running the Flask server locally.

