from typing import List
import numpy as np
from sklearn.metrics import accuracy_score
from src.learning.embedding_store import EmbeddingStore
from src.recognition.encoder import Encoder
from src.recognition.matcher import Matcher

class FeedbackLoop:
    def __init__(self, embedding_store: EmbeddingStore, encoder: Encoder, matcher: Matcher):
        self.embedding_store = embedding_store
        self.encoder = encoder
        self.matcher = matcher

    def collect_feedback(self, true_labels: List[str], predicted_labels: List[str]) -> None:
        accuracy = accuracy_score(true_labels, predicted_labels)
        print(f"Current accuracy: {accuracy:.2f}")

    def retrain_model(self) -> None:
        embeddings, labels = self.embedding_store.retrieve_all_embeddings()
        if embeddings:
            new_embeddings = self.encoder.encode(embeddings)
            self.embedding_store.update_embeddings(new_embeddings, labels)

    def run_feedback_loop(self, true_labels: List[str], predicted_labels: List[str]) -> None:
        self.collect_feedback(true_labels, predicted_labels)
        self.retrain_model()