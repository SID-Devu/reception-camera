from recognition.matcher import Matcher
import pytest

@pytest.fixture
def matcher():
    return Matcher()

def test_match_embeddings(matcher):
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.1, 0.2, 0.3]
    assert matcher.match(embedding1, embedding2) == True

def test_match_embeddings_different(matcher):
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.4, 0.5, 0.6]
    assert matcher.match(embedding1, embedding2) == False

def test_match_embeddings_threshold(matcher):
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.1, 0.2, 0.35]  # Slightly different
    matcher.set_threshold(0.05)
    assert matcher.match(embedding1, embedding2) == False

def test_match_embeddings_with_noise(matcher):
    embedding1 = [0.1, 0.2, 0.3]
    embedding2 = [0.1, 0.2, 0.299]  # Very close
    matcher.set_threshold(0.01)
    assert matcher.match(embedding1, embedding2) == True