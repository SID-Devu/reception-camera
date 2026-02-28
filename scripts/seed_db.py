"""
Reception Greeter – Seed database with test persons.

Creates test persons with random embeddings for development/testing.
These are NOT real face embeddings and won't match anyone.

Usage:
    python scripts/seed_db.py [--count 5] [--config app/config.yaml]
"""

from __future__ import annotations

import argparse
import os
import sys

import numpy as np

_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _PROJECT_ROOT)

from app.db.storage import FaceDB

# Test names (no external dependency needed)
TEST_NAMES = [
    "Alice Johnson", "Bob Smith", "Charlie Brown", "Diana Prince",
    "Eve Wilson", "Frank Castle", "Grace Hopper", "Hank Pym",
    "Iris West", "Jack Ryan", "Karen Page", "Leo Fitz",
    "Maya Lopez", "Nate Grey", "Olivia Pope", "Peter Parker",
]


def seed_database(db: FaceDB, count: int = 5, embeddings_per_person: int = 10) -> None:
    names = TEST_NAMES[:count]

    for name in names:
        if db.person_exists(name):
            print(f"  [skip] '{name}' already exists")
            continue

        person_id = db.add_person(name, role="test")

        # Generate random normalised 512-d embeddings
        embeddings = []
        quality_scores = []
        for _ in range(embeddings_per_person):
            emb = np.random.randn(512).astype(np.float32)
            emb = emb / (np.linalg.norm(emb) + 1e-10)
            embeddings.append(emb)
            quality_scores.append(float(np.random.uniform(0.7, 1.0)))

        db.add_embeddings_bulk(person_id, embeddings, quality_scores)
        print(f"  [OK] '{name}' -> {embeddings_per_person} embeddings (person_id={person_id})")

    print(f"\nSeeded {len(names)} test persons.")


def main():
    import yaml

    parser = argparse.ArgumentParser(description="Seed database with test data")
    parser.add_argument("--count", type=int, default=5, help="Number of test persons")
    parser.add_argument("--config", default="app/config.yaml", help="Config file")
    args = parser.parse_args()

    with open(args.config) as f:
        config = yaml.safe_load(f)

    db_path = config.get("database", {}).get("path", "../data/faces.db")
    if not os.path.isabs(db_path):
        db_path = os.path.join(os.path.dirname(os.path.abspath(args.config)), db_path)

    db = FaceDB(db_path)
    seed_database(db, args.count)
    db.close()


if __name__ == "__main__":
    main()