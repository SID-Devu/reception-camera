"""
Reception Greeter – Export embeddings to JSON.

Exports all persons and their embeddings from the SQLite database
to a human-readable JSON file for inspection or migration.

Usage:
    python scripts/export_embeddings.py [--output embeddings.json] [--config app/config.yaml]
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys

import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.db.storage import FaceDB


def export_embeddings(db: FaceDB, output_file: str) -> None:
    persons = db.get_all_persons()
    if not persons:
        print("No enrolled persons found.")
        return

    data = []
    for p in persons:
        pid = p["person_id"]
        conn = db._get_conn()
        rows = conn.execute(
            "SELECT embedding, dim FROM embeddings WHERE person_id = ?", (pid,)
        ).fetchall()

        embeddings_b64 = []
        for row in rows:
            emb_bytes = row[0]  # BLOB
            dim = row[1]
            arr = np.frombuffer(emb_bytes, dtype=np.float32).reshape(dim)
            embeddings_b64.append(base64.b64encode(arr.tobytes()).decode("ascii"))

        data.append({
            "person_id": pid,
            "name": p["name"],
            "role": p.get("role", ""),
            "embedding_dim": dim if rows else 512,
            "num_embeddings": len(embeddings_b64),
            "embeddings": embeddings_b64,
        })

    with open(output_file, "w") as f:
        json.dump(data, f, indent=2)

    print(f"Exported {len(data)} persons ({sum(d['num_embeddings'] for d in data)} "
          f"embeddings) to {output_file}")


def main():
    import yaml

    parser = argparse.ArgumentParser(description="Export embeddings to JSON")
    parser.add_argument("--output", default="embeddings.json", help="Output file")
    parser.add_argument("--config", default="app/config.yaml", help="Config file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(args.config)), db_path)

    db = FaceDB(db_path)
    export_embeddings(db, args.output)
    db.close()


if __name__ == "__main__":
    main()