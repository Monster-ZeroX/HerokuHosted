"""
Database migration script to add usage tracking columns.
Run this script once to update the database schema.
"""
import os
import sys
from sqlalchemy import create_engine, inspect, text
from datetime import datetime

def _execute_step(conn, sql: str, label: str):
    """Execute a single SQL statement with its own transaction and error handling."""
    txn = conn.begin()
    try:
        conn.execute(text(sql))
        txn.commit()
        print(f"  ✓ {label}")
    except Exception as exc:  # pragma: no cover - defensive logging
        txn.rollback()
        print(f"  - {label}: {exc}")


def run_migration():
    """Add new columns to existing tables while tolerating missing legacy tables."""
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
        inspector = inspect(engine)
        print("Starting migration...")

        # Add columns to users table
        print("Adding columns to users table...")

        if inspector.has_table("users"):
            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS total_downloaded BIGINT DEFAULT 0
                """,
                "Added total_downloaded column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS daily_downloaded BIGINT DEFAULT 0
                """,
                "Added daily_downloaded column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS last_reset_date DATE DEFAULT CURRENT_DATE
                """,
                "Added last_reset_date column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS daily_limit BIGINT DEFAULT 0
                """,
                "Added daily_limit column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS base_daily_limit BIGINT DEFAULT 0
                """,
                "Added base_daily_limit column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS subscription_plan VARCHAR(50)
                """,
                "Added subscription_plan column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE users
                ADD COLUMN IF NOT EXISTS subscription_expires_at TIMESTAMP
                """,
                "Added subscription_expires_at column",
            )
        else:
            print("  - users table not found; skipping user column migrations")

        # Add columns to invite_codes table
        print("\nAdding columns to invite_codes table...")

        if inspector.has_table("invite_codes"):
            _execute_step(
                conn,
                """
                ALTER TABLE invite_codes
                ADD COLUMN IF NOT EXISTS daily_download_limit BIGINT DEFAULT 0
                """,
                "Added daily_download_limit column",
            )
        else:
            print("  - invite_codes table not found; skipping invite code migrations")

        print("\nAdding columns to torrents table...")

        if inspector.has_table("torrents"):
            _execute_step(
                conn,
                """
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS download_rate FLOAT DEFAULT 0
                """,
                "Added download_rate column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS eta_seconds INTEGER
                """,
                "Added eta_seconds column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS selection_mode VARCHAR(20) DEFAULT 'all'
                """,
                "Added selection_mode column",
            )

            _execute_step(
                conn,
                """
                ALTER TABLE torrents
                ADD COLUMN IF NOT EXISTS selected_file_indices TEXT
                """,
                "Added selected_file_indices column",
            )
        else:
            print("  - torrents table not found; skipping torrent column migrations")

        print("\nEnsuring payment_transactions table exists...")
        _execute_step(
            conn,
            """
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
            """,
            "payment_transactions table ready",
        )

        print("\n✓ Migration completed successfully!")

if __name__ == '__main__':
    run_migration()
