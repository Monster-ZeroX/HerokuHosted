# Move the frontend to Vercel and Postgres to Supabase

This guide walks through cutting over the stack so the Next.js frontend is hosted on Vercel, the database lives in Supabase Postgres, and two Heroku apps run the torrent/Mega workers with shared storage but separate rclone configs.

## Target architecture
- **Frontend:** Vercel (Next.js app in `/frontend`) calling your Flask API.
- **Database:** Supabase Postgres shared by all apps (frontend hits the API, API/worker read/write the DB directly).
- **Workers:** Two Heroku apps running the `worker` process. One of them also runs the `web` process to expose the API the frontend calls.
- **Storage:** Both workers use different `RCLONE_CONFIG` secrets to avoid rate limiting but point to the same `RCLONE_BASE_DIR` so uploads land in a shared folder.

## Prerequisites
- Heroku CLI, Vercel CLI (optional but handy), `psql`, and `pg_dump` installed locally.
- Access to your existing Heroku app and its Postgres database.
- A Supabase account and project.

## 1) Create Supabase Postgres and capture the connection string
1. In Supabase, create a new project and database.
2. In **Settings → Database → Connection Info**, copy the primary connection string (or the pooled connection string if you prefer). It will look like `postgresql://USER:PASSWORD@HOST:PORT/postgres`.
3. Under **Network**, allow external connections (or add Heroku’s IP ranges if you restrict IPs).

## 2) Export data from Heroku Postgres
Run a clean export of your current Heroku database:

```bash
heroku pg:backups:capture -a <heroku-app>
heroku pg:backups:download -a <heroku-app>
# This downloads latest.dump
```

Alternatively, use `pg_dump` if you prefer:

```bash
heroku config:get DATABASE_URL -a <heroku-app> > heroku.db.url
pg_dump "$(cat heroku.db.url)" --format=custom --no-owner --no-acl --verbose -f latest.dump
```

## 3) Import the dump into Supabase
Using the Supabase connection string from step 1:

```bash
pg_restore --no-owner --no-acl --verbose -d "postgresql://USER:PASSWORD@HOST:5432/postgres" latest.dump
```

If you get SSL errors, append `?sslmode=require` to the Supabase connection string.

## 4) Point both Heroku apps to Supabase
1. On each Heroku app (primary and secondary worker), set:
   - `DATABASE_URL` = your Supabase connection string (include `?sslmode=require`).
   - `ALLOWED_ORIGINS` = your Vercel domain(s) so cookies/session calls work from the new frontend.
   - `PRIMARY_API_BASE` and `WORKER_API_TOKEN` should match on both apps if you use API-bridged worker callbacks.
2. Run migrations against Supabase to ensure the schema is up-to-date:

```bash
heroku run "python migrate_db.py" -a <heroku-app>
```

3. Scale processes so you have one API entry point and two workers:

```bash
# Primary app exposes API + worker
heroku ps:scale web=1 worker=1 -a <primary-app>

# Secondary app is worker-only
heroku ps:scale web=0 worker=1 -a <secondary-app>
```

## 5) Configure separate rclone configs but shared folder
- Set a unique `RCLONE_CONFIG` value on each Heroku app (e.g., different client IDs or service accounts) to spread Drive API usage.
- Use the same `RCLONE_REMOTE_NAME` and `RCLONE_BASE_DIR` so both workers upload to the identical target folder.
- Keep `INDEX_BASE_URL` identical on both apps so generated links stay consistent.

## 6) Deploy the frontend to Vercel
1. In Vercel, create a new project and import this repository. Set **Root Directory** to `frontend`.
2. Set environment variables in Vercel:
   - `NEXT_PUBLIC_API_BASE` = `https://<primary-app>.herokuapp.com` (the API host from step 4).
   - Any other public keys you need (e.g., `NEXT_PUBLIC_TMBD_KEY` if you expose TMDB from the frontend).
3. Deploy; Vercel will build the Next.js app and serve it globally.

## 7) Verify end-to-end
- Login via the Vercel URL, start a torrent/Mega job, and confirm it appears in the queue.
- Watch the two worker logs to ensure both pick up jobs: `heroku logs -t -a <primary-app>` and `heroku logs -t -a <secondary-app>`.
- Confirm uploads land in the shared Drive folder and that Supabase records reflect progress.

## 8) Optional: load-balance API traffic
If you want to spread HTTP API traffic as well, front the two Heroku apps with a simple Vercel rewrite/edge middleware or a DNS load balancer (e.g., Cloudflare) and set `NEXT_PUBLIC_API_BASE` to that balanced URL. Ensure both apps share the same `DATABASE_URL`, `WORKER_API_TOKEN`, and CORS settings.

## 9) Keep backups
- Enable automated backups in Supabase or run `pg_dump` regularly.
- Before switching DNS to Vercel, take one final Heroku backup and restore it to Supabase to avoid drift.

Following these steps moves the datastore to Supabase, hosts the UI on Vercel, and uses two Heroku workers with distinct rclone configs uploading into the same folder for better throughput.
