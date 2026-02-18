from src.enrollment.enroll_service import EnrollService
import pytest

@pytest.fixture
def enroll_service():
    return EnrollService()

def test_enroll_new_individual(enroll_service):
    name = "John Doe"
    image_path = "path/to/image.jpg"
    result = enroll_service.enroll(name, image_path)
    assert result is True

def test_enroll_duplicate_individual(enroll_service):
    name = "Jane Doe"
    image_path = "path/to/image.jpg"
    enroll_service.enroll(name, image_path)
    result = enroll_service.enroll(name, image_path)
    assert result is False

def test_enroll_with_invalid_image(enroll_service):
    name = "Invalid User"
    image_path = "path/to/invalid_image.jpg"
    result = enroll_service.enroll(name, image_path)
    assert result is False

def test_enroll_service_updates_database(enroll_service):
    name = "Alice Smith"
    image_path = "path/to/image.jpg"
    enroll_service.enroll(name, image_path)
    # Assuming the service has a method to check if the individual is in the database
    assert enroll_service.is_enrolled(name) is True

def test_enroll_service_handles_multiple_enrollments(enroll_service):
    names = ["Bob Brown", "Charlie Black", "Diana White"]
    for name in names:
        image_path = "path/to/image.jpg"
        result = enroll_service.enroll(name, image_path)
        assert result is True
    assert len(enroll_service.get_all_enrolled()) == len(names)