"""
Database migration script to add usage tracking columns.
Run this script once to update the database schema.
"""
import os
import sys
from sqlalchemy import create_engine, text
from datetime import datetime

def run_migration():
    """Add new columns to existing tables."""
    database_url = os.environ.get('DATABASE_URL')

    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        sys.exit(1)

    # Fix Heroku postgres:// URL
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    print(f"Connecting to database...")
    engine = create_engine(database_url)

    with engine.connect() as conn:
        print("Starting migration...")

        # Add columns to users table
        print("Adding columns to users table...")

        try:
            # Add total_downloaded column
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS total_downloaded BIGINT DEFAULT 0
            """))
            print("  ✓ Added total_downloaded column")
        except Exception as e:
            print(f"  - total_downloaded: {e}")

        try:
            # Add daily_downloaded column
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS daily_downloaded BIGINT DEFAULT 0
            """))
            print("  ✓ Added daily_downloaded column")
        except Exception as e:
            print(f"  - daily_downloaded: {e}")

        try:
            # Add last_reset_date column
            conn.execute(text(f"""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_reset_date DATE DEFAULT CURRENT_DATE
            """))
            print("  ✓ Added last_reset_date column")
        except Exception as e:
            print(f"  - last_reset_date: {e}")

        try:
            # Add daily_limit column
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS daily_limit BIGINT DEFAULT 0
            """))
            print("  ✓ Added daily_limit column")
        except Exception as e:
            print(f"  - daily_limit: {e}")

        # Add columns to invite_codes table
        print("\nAdding columns to invite_codes table...")

        try:
            # Add daily_download_limit column
            conn.execute(text("""
                ALTER TABLE invite_codes
                ADD COLUMN IF NOT EXISTS daily_download_limit BIGINT DEFAULT 0
            """))
            print("  ✓ Added daily_download_limit column")
        except Exception as e:
            print(f"  - daily_download_limit: {e}")

        print("\nAdding columns to torrents table...")

        try:
            conn.execute(text("""
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS download_rate FLOAT DEFAULT 0
            """))
            print("  ✓ Added download_rate column")
        except Exception as e:
            print(f"  - download_rate: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS eta_seconds INTEGER
            """))
            print("  ✓ Added eta_seconds column")
        except Exception as e:
            print(f"  - eta_seconds: {e}")

        conn.commit()
        print("\n✓ Migration completed successfully!")

if __name__ == '__main__':
    run_migration()
