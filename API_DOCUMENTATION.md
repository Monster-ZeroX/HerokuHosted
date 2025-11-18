# DirectTorrent.me API Documentation

All endpoints are JSON-only and live under the `/api` prefix. Cookies are used for sessions, so clients must send `credentials: include` and the backend must be configured with `SESSION_COOKIE_SAMESITE=None` and `SESSION_COOKIE_SECURE=true` for cross-domain access (for example, Vercel frontend to Heroku API).

Base URL examples:
- Local development: `http://localhost:5000`
- Heroku free app: `https://directtorrent-free-1-d466324d1d71.herokuapp.com`
- Heroku paid app: `https://<your-paid-app>.herokuapp.com`

## Authentication

### POST `/api/auth/register/start`
Begin email OTP registration.
- **Body:** `{ "username": string, "email": string, "password": string }`
- **Response:** `{ "ok": true, "message": "OTP sent to email" }`

### POST `/api/auth/register/verify`
Confirm OTP and create the account with a default free plan.
- **Body:** `{ "email": string, "code": string }`
- **Response:** `{ "ok": true, "user": { id, username, email, is_admin, plan } }`

### POST `/api/auth/login`
Login with email or username.
- **Body:** `{ "email_or_username": string, "password": string }`
- **Response:** `{ "ok": true, "user": { ... , plan } }` or `{ "ok": false, "error": "INVALID_CREDENTIALS" }`

### POST `/api/auth/logout`
- **Response:** `{ "ok": true }`

### GET `/api/auth/me`
- **Response (unauthenticated):** `{ "authenticated": false }`
- **Response (authenticated):** `{ "authenticated": true, "user": { id, username, email, is_admin, plan } }`

### Password reset
- **Start:** `POST /api/auth/password-reset/start` with `{ "email": string }`
- **Complete:** `POST /api/auth/password-reset/complete` with `{ "email": string, "code": string, "new_password": string }`
- **Response:** `{ "ok": true }` or `{ "ok": false, "error": "INVALID_OTP" }`

## Torrent & Mega jobs

Job shape:
```
{
  "id": number,
  "user_id": number,
  "name": string,
  "source_type": "torrent" | "mega",
  "magnet_link": string | null,
  "source_url": string | null,
  "status": "queued" | "downloading" | "uploading" | "completed" | "failed" | "canceled",
  "progress": number,
  "size_bytes": number,
  "bytes_downloaded": number,
  "download_speed": number,
  "upload_speed": number,
  "eta_seconds": number | null,
  "drive_folder_url": string | null,
  "stream_url": string | null,
  "created_at": string,
  "completed_at": string | null,
  "app_role": "FREE" | "PAID",
  "app_instance": string
}
```

### GET `/api/torrents`
List jobs with optional filters.
- **Query params:** `status`, `source_type`, `page`, `page_size`
- **Response:** `{ "items": [job...], "pagination": { page, page_size, total_items, total_pages } }`

### POST `/api/torrents`
Create a new transfer.
- **Body (torrent):** `{ "source_type": "torrent", "magnet_link": string, "save_folder": string }`
- **Body (mega):** `{ "source_type": "mega", "source_url": string, "save_folder": string }`
- **Response:** `{ "ok": true, "job": job }` or `{ "ok": false, "error": "DAILY_LIMIT_EXCEEDED" }`

### GET `/api/torrents/{id}`
- **Response:** `{ "job": job }` or `{ "ok": false, "error": "NOT_FOUND" }`

### POST `/api/torrents/{id}/cancel`
Cancel an active job.
- **Response:** `{ "ok": true, "job": { ... status: "canceled" } }`

## Admin (requires `is_admin`)

### GET `/api/admin/overview`
- **Response:** `{ "user_counts": { total, free, paid }, "active_jobs": { free, paid }, "bandwidth_today_gb": { total, free, paid } }`

### GET `/api/admin/users`
- **Query params:** `plan_type`, `search`, `page`, `page_size`
- **Response:** `{ "items": [ { id, username, email, plan_type, plan_expires_at, created_at, is_active, usage_today_gb } ], "pagination": { ... } }`

### GET `/api/admin/users/{id}`
Full user details including plan, daily usage, total bandwidth, and last login.

### PATCH `/api/admin/users/{id}`
- **Body (any subset):** `plan_type`, `plan_expires_at`, `is_active`, `daily_limit_gb`
- **Response:** `{ "ok": true, "user": { ... } }`

### POST `/api/admin/users/{id}/reset-usage`
- **Response:** `{ "ok": true, "user": { "id", "usage_today_gb": 0 } }`

### GET `/api/admin/transactions`
- **Response:** `{ "items": [ { id, user_id, user_email, amount, currency, status, provider, provider_transaction_id, created_at, updated_at } ], "pagination": { ... } }`

### GET `/api/admin/usage/heroku`
- **Response:** `{ "free_apps": [ { app_instance, jobs_completed_today, bandwidth_today_gb }, ... ], "paid_app": { app_instance, jobs_completed_today, bandwidth_today_gb }, "total_bandwidth_today_gb" }`

### GET `/api/admin/usage/bandwidth`
- **Query params:** `from`, `to`, optional `group_by`
- **Response:** `{ "points": [ { "date", "total_gb", "free_gb", "paid_gb" } ... ] }`

## Error handling
- Authentication-required endpoints return 401 with `{ "ok": false, "error": "UNAUTHORIZED" }` when sessions are missing.
- Not-found resources return 404 with `{ "ok": false, "error": "NOT_FOUND" }`.
- Validation or limit errors return 400 with a descriptive `error` code (e.g., `DAILY_LIMIT_EXCEEDED`).

## Tips for clients
- Always send `credentials: 'include'` so session cookies persist across requests.
- Use HTTPS API URLs when the frontend is served over HTTPS to avoid mixed-content network errors reported as "Failed to fetch".
- Free apps and paid apps are deployed separately; the single frontend can target whichever backend URL you set via `NEXT_PUBLIC_API_BASE`.
