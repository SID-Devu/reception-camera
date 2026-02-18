import os
import json
import sqlite3

def export_embeddings(db_path, output_file):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, embedding FROM persons")
    rows = cursor.fetchall()

    embeddings = []
    for row in rows:
        person_id, name, embedding = row
        embeddings.append({
            "id": person_id,
            "name": name,
            "embedding": json.loads(embedding)  # Assuming embedding is stored as a JSON string
        })

    with open(output_file, 'w') as f:
        json.dump(embeddings, f, indent=4)

    conn.close()

if __name__ == "__main__":
    DATABASE_PATH = os.getenv("DATABASE_PATH", "path/to/your/database.db")
    OUTPUT_FILE = os.getenv("OUTPUT_FILE", "embeddings.json")

    export_embeddings(DATABASE_PATH, OUTPUT_FILE)