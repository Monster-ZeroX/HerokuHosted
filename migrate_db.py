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

        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS base_daily_limit BIGINT DEFAULT 0
            """))
            print("  ✓ Added base_daily_limit column")
        except Exception as e:
            print(f"  - base_daily_limit: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50)
            """))
            print("  ✓ Added subscription_plan column")
        except Exception as e:
            print(f"  - subscription_plan: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP
            """))
            print("  ✓ Added subscription_expires_at column")
        except Exception as e:
            print(f"  - subscription_expires_at: {e}")

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

        try:
            conn.execute(text("""
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS selection_mode VARCHAR(20) DEFAULT 'all'
            """))
            print("  ✓ Added selection_mode column")
        except Exception as e:
            print(f"  - selection_mode: {e}")

        try:
            conn.execute(text("""
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS selected_file_indices TEXT
            """))
            print("  ✓ Added selected_file_indices column")
        except Exception as e:
            print(f"  - selected_file_indices: {e}")

        print("\nEnsuring payment_transactions table exists...")
        try:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS payment_transactions (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    plan_key VARCHAR(50) NOT NULL,
                    amount_cents INTEGER NOT NULL,
                    currency VARCHAR(10) DEFAULT 'USD',
                    status VARCHAR(20) DEFAULT 'pending',
                    reference VARCHAR(100) UNIQUE NOT NULL,
                    gateway_payment_id VARCHAR(100),
                    raw_response TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            print("  ✓ payment_transactions table ready")
        except Exception as e:
            print(f"  - payment_transactions: {e}")

        conn.commit()
        print("\n✓ Migration completed successfully!")

if __name__ == '__main__':
    run_migration()
