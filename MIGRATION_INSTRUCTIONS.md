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
- `users.base_daily_limit`
- `users.subscription_plan`
- `users.subscription_expires_at`
- `payment_transactions` table (for paid plan purchases)

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
3. Creates the `payment_transactions` table if it does not exist
4. Sets default values for existing rows (0 for numeric columns, CURRENT_DATE for date columns)
5. Commits the changes

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

## Moving data from your old Heroku app to this branch

If you want the new production app to keep all users/torrents from the old Heroku Postgres database, copy the data over once the schemas match.

1. **Make sure schemas match**: Deploy this branch to the new app and run `heroku run python migrate_db.py --app NEW_APP` (or let the startup migration run once) so the destination database has all required columns.
2. **Create a fresh backup of the old app**: `heroku pg:backups:capture --app OLD_APP`. Optionally download a local copy with `heroku pg:backups:download --app OLD_APP`.
3. **Copy data directly between apps** (fastest path):
   ```bash
   # Puts the NEW_APP in maintenance to avoid writes during the copy
   heroku maintenance:on --app NEW_APP

   # Copies the old database into the new app's DATABASE_URL
   heroku pg:copy OLD_APP::DATABASE_URL DATABASE_URL --app NEW_APP --confirm NEW_APP

   # Turn maintenance back off once the copy finishes
   heroku maintenance:off --app NEW_APP
   ```
   This preserves users, torrents, invite codes, and usage history exactly as they were in the old app.
4. **Alternative restore from a backup file** (if you need a local staging step):
   ```bash
   # From a downloaded *.dump file (e.g., latest.dump)
   heroku pg:backups:restore 'https://path-to-backup' DATABASE_URL --app NEW_APP --confirm NEW_APP
   ```
5. **Verify the data**: Run `heroku pg:psql --app NEW_APP` and check tables (e.g., `SELECT COUNT(*) FROM users;`).
6. **Restart dynos**: `heroku restart --app NEW_APP` to ensure the worker/web picks up the migrated data and environment variables.

Tips:
- Perform the copy during a low-traffic window so no writes occur on the old app while you cut over.
- Keep the old app around until you confirm the new app works with the migrated data.
