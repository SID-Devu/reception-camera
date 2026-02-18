from fastapi.testclient import TestClient
from src.api.app import app

client = TestClient(app)

def test_enrollment_route():
    response = client.post("/api/enroll", json={"name": "John Doe", "image": "base64_image_string"})
    assert response.status_code == 200
    assert response.json() == {"message": "Enrollment successful", "name": "John Doe"}

def test_recognition_route():
    response = client.post("/api/recognize", json={"image": "base64_image_string"})
    assert response.status_code == 200
    assert "name" in response.json()

def test_person_route():
    response = client.get("/api/persons")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

def test_analytics_route():
    response = client.get("/api/analytics")
    assert response.status_code == 200
    assert "total_recognitions" in response.json()