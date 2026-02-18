"""
Reception Greeter – Export / import face database.

Export all persons + embeddings to a portable JSON file for backup
or transfer between machines.

Usage:
    python -m tools.export_db --config app/config.yaml --output backup.json
    python -m tools.import_db --config app/config.yaml --input backup.json
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

import numpy as np
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


def export_db(db: FaceDB, output_path: str) -> None:
    persons = db.list_persons()
    data = {"persons": []}

    for p in persons:
        pid = p["person_id"]
        embeddings = db.get_embeddings_for_person(pid)
        emb_list = [
            base64.b64encode(e.astype(np.float32).tobytes()).decode("ascii")
            for e in embeddings
        ]
        data["persons"].append({
            "name": p["name"],
            "role": p.get("role", ""),
            "created_at": p["created_at"],
            "embedding_dim": int(embeddings[0].shape[0]) if embeddings else 512,
            "embeddings": emb_list,
        })

    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)

    total_emb = sum(len(p["embeddings"]) for p in data["persons"])
    print(f"Exported {len(data['persons'])} persons, {total_emb} embeddings → {output_path}")


def import_db(db: FaceDB, input_path: str) -> None:
    with open(input_path, "r") as f:
        data = json.load(f)

    imported = 0
    skipped = 0
    for p in data["persons"]:
        name = p["name"]
        if db.person_exists(name):
            print(f"  SKIP: '{name}' already enrolled")
            skipped += 1
            continue

        person_id = db.add_person(name, p.get("role", ""))
        dim = p.get("embedding_dim", 512)
        embeddings = [
            np.frombuffer(base64.b64decode(e), dtype=np.float32).reshape(dim)
            for e in p["embeddings"]
        ]
        db.add_embeddings_bulk(person_id, embeddings)
        print(f"  OK: '{name}' → {len(embeddings)} embeddings")
        imported += 1

    print(f"\nImported {imported}, skipped {skipped}")


def main():
    parser = argparse.ArgumentParser(description="Export/import face database")
    parser.add_argument("--config", default="app/config.yaml")
    sub = parser.add_subparsers(dest="command")

    exp = sub.add_parser("export", help="Export DB to JSON")
    exp.add_argument("--output", default="backup.json")

    imp = sub.add_parser("import", help="Import DB from JSON")
    imp.add_argument("--input", required=True)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    db = load_db(args.config)
    try:
        if args.command == "export":
            export_db(db, args.output)
        elif args.command == "import":
            import_db(db, args.input)
    finally:
        db.close()


if __name__ == "__main__":
    main()
