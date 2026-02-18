import pytest

@pytest.fixture(scope="module")
def sample_data():
    return {
        "name": "John Doe",
        "image_path": "path/to/image.jpg",
        "embedding": [0.1, 0.2, 0.3]  # Example embedding
    }