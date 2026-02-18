from sklearn.linear_model import SGDClassifier
from sklearn.metrics import accuracy_score
import numpy as np
import joblib
import os

class IncrementalTrainer:
    def __init__(self, model_path='model.pkl'):
        self.model_path = model_path
        self.model = self.load_model()

    def load_model(self):
        if os.path.exists(self.model_path):
            return joblib.load(self.model_path)
        else:
            return SGDClassifier()

    def train(self, X, y):
        self.model.partial_fit(X, y, classes=np.unique(y))
        self.save_model()

    def save_model(self):
        joblib.dump(self.model, self.model_path)

    def evaluate(self, X, y):
        predictions = self.model.predict(X)
        return accuracy_score(y, predictions)

    def add_new_data(self, new_X, new_y):
        self.train(new_X, new_y)