from typing import Any, Dict
import os
import joblib

class ModelManager:
    def __init__(self, model_path: str):
        self.model_path = model_path
        self.model = self.load_model()

    def load_model(self) -> Any:
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        else:
            raise FileNotFoundError(f"Model file not found at {self.model_path}")

    def save_model(self, model: Any) -> None:
        joblib.dump(model, self.model_path)

    def update_model(self, new_model: Any) -> None:
        self.save_model(new_model)

    def get_model(self) -> Any:
        return self.model