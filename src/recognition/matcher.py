from typing import List
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

class Matcher:
    def __init__(self, threshold: float = 0.5):
        self.threshold = threshold
        self.embeddings_db = {}  # Dictionary to store embeddings with associated names

    def add_embedding(self, name: str, embedding: np.ndarray):
        self.embeddings_db[name] = embedding

    def match(self, query_embedding: np.ndarray) -> str:
        best_match = None
        highest_similarity = -1

        for name, embedding in self.embeddings_db.items():
            similarity = cosine_similarity([query_embedding], [embedding])[0][0]
            if similarity > highest_similarity:
                highest_similarity = similarity
                best_match = name

        if highest_similarity >= self.threshold:
            return best_match
        else:
            return "Unknown"

    def update_threshold(self, new_threshold: float):
        self.threshold = new_threshold

    def get_all_embeddings(self) -> List[str]:
        return list(self.embeddings_db.keys())