# Database Migration Instructions

## Problem
Recent updates added new columns to the database for usage tracking and torrent file selection:
- `users.total_downloaded`
- `users.daily_downloaded`
- `users.last_reset_date`
- `users.daily_limit`
- `invite_codes.daily_download_limit`
- `torrents.download_rate`
- `torrents.eta_seconds`
- `torrents.selection_mode`
- `torrents.selected_file_indices`

These columns need to be added to the existing Heroku PostgreSQL database.

## Solution: Run the Migration Script

### Option 1: Run on Heroku (Recommended)

```bash
heroku run python migrate_db.py
```

This will connect to your Heroku PostgreSQL database and add the required columns.

### Option 2: Run Locally (if you have direct database access)

```bash
# Set the DATABASE_URL environment variable
export DATABASE_URL="your_heroku_postgres_url"

# Run the migration
python migrate_db.py
```

## What the Migration Does

The `migrate_db.py` script:
1. Connects to your PostgreSQL database
2. Adds new columns using `ALTER TABLE ... ADD COLUMN IF NOT EXISTS`
3. Sets default values for existing rows (0 for numeric columns, CURRENT_DATE for date columns)
4. Commits the changes

## After Migration

Once the migration is complete:
1. Restart your Heroku dynos: `heroku restart`
2. The application will start normally
3. All new features (usage tracking, download limits) will be enabled

## Verification

After migration, you can verify the columns were added:

```bash
heroku pg:psql
```

Then run:
```sql
\d users
\d invite_codes
```

You should see the new columns listed.

## Rollback (if needed)

If you need to remove the columns:

```sql
ALTER TABLE users DROP COLUMN IF EXISTS total_downloaded;
ALTER TABLE users DROP COLUMN IF EXISTS daily_downloaded;
ALTER TABLE users DROP COLUMN IF EXISTS last_reset_date;
ALTER TABLE users DROP COLUMN IF EXISTS daily_limit;
ALTER TABLE invite_codes DROP COLUMN IF EXISTS daily_download_limit;
ALTER TABLE torrents DROP COLUMN IF EXISTS download_rate;
ALTER TABLE torrents DROP COLUMN IF EXISTS eta_seconds;
ALTER TABLE torrents DROP COLUMN IF EXISTS selection_mode;
ALTER TABLE torrents DROP COLUMN IF EXISTS selected_file_indices;
```

## Notes

- The migration is safe and uses `IF NOT EXISTS` to prevent errors if columns already exist
- Existing user data is preserved
- All new columns have safe default values
- The app now also runs a lightweight, idempotent migration on startup to keep dynos from crashing if the script hasn't been run yet, but you should still run `migrate_db.py` to ensure the database is fully updated
