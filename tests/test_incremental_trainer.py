from src.learning.incremental_trainer import IncrementalTrainer
import pytest

@pytest.fixture
def incremental_trainer():
    return IncrementalTrainer()

def test_initialization(incremental_trainer):
    assert incremental_trainer is not None

def test_add_embedding(incremental_trainer):
    sample_embedding = [0.1, 0.2, 0.3, 0.4]
    name = "John Doe"
    incremental_trainer.add_embedding(name, sample_embedding)
    assert name in incremental_trainer.embeddings
    assert incremental_trainer.embeddings[name] == sample_embedding

def test_train_model(incremental_trainer):
    sample_embedding_1 = [0.1, 0.2, 0.3, 0.4]
    sample_embedding_2 = [0.5, 0.6, 0.7, 0.8]
    incremental_trainer.add_embedding("John Doe", sample_embedding_1)
    incremental_trainer.add_embedding("Jane Doe", sample_embedding_2)
    
    initial_model = incremental_trainer.model
    incremental_trainer.train_model()
    assert incremental_trainer.model is not initial_model

def test_recognition_accuracy(incremental_trainer):
    sample_embedding = [0.1, 0.2, 0.3, 0.4]
    incremental_trainer.add_embedding("John Doe", sample_embedding)
    recognized_name = incremental_trainer.recognize(sample_embedding)
    assert recognized_name == "John Doe"

def test_feedback_loop(incremental_trainer):
    sample_embedding = [0.1, 0.2, 0.3, 0.4]
    incremental_trainer.add_embedding("John Doe", sample_embedding)
    incremental_trainer.train_model()
    
    # Simulate feedback
    feedback = {"John Doe": True}
    incremental_trainer.update_with_feedback(feedback)
    
    assert incremental_trainer.feedback_received == feedback