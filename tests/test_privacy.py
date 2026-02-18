import pytest
from src.privacy.consent_manager import ConsentManager
from src.privacy.data_retention import DataRetention
from src.privacy.anonymizer import Anonymizer

@pytest.fixture
def consent_manager():
    return ConsentManager()

@pytest.fixture
def data_retention():
    return DataRetention()

@pytest.fixture
def anonymizer():
    return Anonymizer()

def test_consent_manager_initialization(consent_manager):
    assert consent_manager is not None

def test_data_retention_initialization(data_retention):
    assert data_retention is not None

def test_anonymizer_initialization(anonymizer):
    assert anonymizer is not None

def test_consent_management(consent_manager):
    consent_manager.give_consent("user@example.com")
    assert consent_manager.has_consent("user@example.com") is True
    consent_manager.withdraw_consent("user@example.com")
    assert consent_manager.has_consent("user@example.com") is False

def test_data_retention_policy(data_retention):
    data_retention.set_retention_period(30)
    assert data_retention.get_retention_period() == 30

def test_anonymization(anonymizer):
    original_data = {"name": "John Doe", "email": "john@example.com"}
    anonymized_data = anonymizer.anonymize(original_data)
    assert anonymized_data["name"] != original_data["name"]
    assert anonymized_data["email"] != original_data["email"]