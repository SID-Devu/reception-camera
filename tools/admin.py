"""
Reception Greeter – Admin CLI tool.

Manage enrolled persons: list, delete, info, re-enroll, view events.

Usage:
    python -m tools.admin --config app/config.yaml list
    python -m tools.admin --config app/config.yaml info --name "Sudheer"
    python -m tools.admin --config app/config.yaml delete --name "Sudheer"
    python -m tools.admin --config app/config.yaml events [--limit 50]
    python -m tools.admin --config app/config.yaml stats
"""

from __future__ import annotations

import argparse
import os
import sys

import yaml

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.db.storage import FaceDB


def load_db(config_path: str) -> FaceDB:
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(config_path)), db_path)
    return FaceDB(db_path)


def cmd_list(db: FaceDB) -> None:
    persons = db.list_persons()
    if not persons:
        print("No enrolled persons.")
        return
    print(f"\n{'ID':>4}  {'Name':<25}  {'Role':<15}  {'Embeddings':>10}  {'Created'}")
    print("-" * 80)
    for p in persons:
        count = db.count_embeddings(p["person_id"])
        print(
            f"{p['person_id']:>4}  {p['name']:<25}  {p.get('role', ''):<15}  "
            f"{count:>10}  {p['created_at']}"
        )
    print(f"\nTotal: {len(persons)} persons")


def cmd_info(db: FaceDB, name: str) -> None:
    person = db.get_person_by_name(name)
    if not person:
        print(f"Person '{name}' not found.")
        return
    count = db.count_embeddings(person["person_id"])
    print(f"\n  Person ID:   {person['person_id']}")
    print(f"  Name:        {person['name']}")
    print(f"  Role:        {person.get('role', 'N/A')}")
    print(f"  Embeddings:  {count}")
    print(f"  Created:     {person['created_at']}")
    print(f"  Updated:     {person['updated_at']}")


def cmd_delete(db: FaceDB, name: str) -> None:
    person = db.get_person_by_name(name)
    if not person:
        print(f"Person '{name}' not found.")
        return
    confirm = input(f"Delete '{name}' and all embeddings? [y/N]: ").strip().lower()
    if confirm == "y":
        db.delete_person(person["person_id"])
        print(f"Deleted '{name}' (person_id={person['person_id']})")
    else:
        print("Cancelled.")


def cmd_events(db: FaceDB, limit: int, event_type: str | None) -> None:
    events = db.get_events(limit=limit, event_type=event_type)
    if not events:
        print("No events found.")
        return
    print(f"\n{'ID':>6}  {'Type':<6}  {'Name':<20}  {'Confidence':>10}  {'Timestamp'}")
    print("-" * 75)
    for e in events:
        print(
            f"{e['event_id']:>6}  {e['event_type']:<6}  {e['person_name']:<20}  "
            f"{e['confidence']:>10.3f}  {e['timestamp']}"
        )
    print(f"\nShowing {len(events)} events")


def cmd_stats(db: FaceDB) -> None:
    persons = db.list_persons()
    total_emb = sum(db.count_embeddings(p["person_id"]) for p in persons)
    entries = db.get_events(limit=100000, event_type="entry")
    exits = db.get_events(limit=100000, event_type="exit")
    print(f"\n  Enrolled persons:    {len(persons)}")
    print(f"  Total embeddings:    {total_emb}")
    print(f"  Total entry events:  {len(entries)}")
    print(f"  Total exit events:   {len(exits)}")


def main():
    parser = argparse.ArgumentParser(description="Reception Greeter – Admin Tool")
    parser.add_argument("--config", default="app/config.yaml", help="Config file")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("list", help="List all enrolled persons")

    info_p = sub.add_parser("info", help="Show info for a person")
    info_p.add_argument("--name", required=True)

    del_p = sub.add_parser("delete", help="Delete a person")
    del_p.add_argument("--name", required=True)

    ev_p = sub.add_parser("events", help="Show recent events")
    ev_p.add_argument("--limit", type=int, default=50)
    ev_p.add_argument("--type", choices=["entry", "exit"], default=None)

    sub.add_parser("stats", help="Show system statistics")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = load_db(args.config)

    try:
        if args.command == "list":
            cmd_list(db)
        elif args.command == "info":
            cmd_info(db, args.name)
        elif args.command == "delete":
            cmd_delete(db, args.name)
        elif args.command == "events":
            cmd_events(db, args.limit, args.type)
        elif args.command == "stats":
            cmd_stats(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
