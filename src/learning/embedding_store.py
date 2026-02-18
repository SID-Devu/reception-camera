from typing import Dict, Any
import json

class EmbeddingStore:
    def __init__(self, db_connection):
        self.db_connection = db_connection

    def save_embedding(self, person_id: str, embedding: Any) -> None:
        query = "INSERT INTO embeddings (person_id, embedding) VALUES (%s, %s)"
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (person_id, json.dumps(embedding)))
        self.db_connection.commit()

    def get_embedding(self, person_id: str) -> Any:
        query = "SELECT embedding FROM embeddings WHERE person_id = %s"
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (person_id,))
            result = cursor.fetchone()
            if result:
                return json.loads(result[0])
            return None

    def update_embedding(self, person_id: str, embedding: Any) -> None:
        query = "UPDATE embeddings SET embedding = %s WHERE person_id = %s"
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (json.dumps(embedding), person_id))
        self.db_connection.commit()

    def delete_embedding(self, person_id: str) -> None:
        query = "DELETE FROM embeddings WHERE person_id = %s"
        with self.db_connection.cursor() as cursor:
            cursor.execute(query, (person_id,))
        self.db_connection.commit()

    def list_embeddings(self) -> Dict[str, Any]:
        query = "SELECT person_id, embedding FROM embeddings"
        with self.db_connection.cursor() as cursor:
            cursor.execute(query)
            results = cursor.fetchall()
            return {person_id: json.loads(embedding) for person_id, embedding in results}