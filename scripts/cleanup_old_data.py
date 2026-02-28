"""
Reception Greeter – Cleanup old event data.

Deletes event log entries older than a given number of days.
Does NOT delete enrolled persons or embeddings.

Usage:
    python scripts/cleanup_old_data.py [--days 30] [--config app/config.yaml]
"""

from __future__ import annotations

import argparse
import datetime
import os
import sys

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.db.storage import FaceDB


def cleanup_old_data(db: FaceDB, days_threshold: int = 30) -> None:
    cutoff = datetime.datetime.now() - datetime.timedelta(days=days_threshold)
    cutoff_str = cutoff.strftime("%Y-%m-%d %H:%M:%S")

    conn = db._get_conn()
    cursor = conn.execute(
        "SELECT COUNT(*) FROM events WHERE timestamp < ?", (cutoff_str,)
    )
    count = cursor.fetchone()[0]

    if count == 0:
        print(f"No events older than {days_threshold} days. Nothing to delete.")
        return

    confirm = input(f"Delete {count} events older than {cutoff_str}? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Cancelled.")
        return

    conn.execute("DELETE FROM events WHERE timestamp < ?", (cutoff_str,))
    conn.commit()
    print(f"Deleted {count} old event records.")


def main():
    import yaml

    parser = argparse.ArgumentParser(description="Cleanup old event data")
    parser.add_argument("--days", type=int, default=30, help="Delete events older than N days")
    parser.add_argument("--config", default="app/config.yaml", help="Config file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(args.config)), db_path)

    db = FaceDB(db_path)
    cleanup_old_data(db, args.days)
    db.close()


if __name__ == "__main__":
    main()