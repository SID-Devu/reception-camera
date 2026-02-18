from src.database.repository import Repository
import pytest

@pytest.fixture
def repository():
    return Repository()

def test_add_person(repository):
    person_data = {
        'name': 'John Doe',
        'embedding': [0.1, 0.2, 0.3]  # Example embedding
    }
    person_id = repository.add_person(person_data)
    assert person_id is not None

def test_get_person(repository):
    person_data = {
        'name': 'Jane Doe',
        'embedding': [0.4, 0.5, 0.6]  # Example embedding
    }
    person_id = repository.add_person(person_data)
    retrieved_person = repository.get_person(person_id)
    assert retrieved_person['name'] == 'Jane Doe'

def test_update_person(repository):
    person_data = {
        'name': 'John Smith',
        'embedding': [0.7, 0.8, 0.9]  # Example embedding
    }
    person_id = repository.add_person(person_data)
    updated_data = {
        'name': 'John Doe Updated',
        'embedding': [0.1, 0.2, 0.3]
    }
    repository.update_person(person_id, updated_data)
    updated_person = repository.get_person(person_id)
    assert updated_person['name'] == 'John Doe Updated'

def test_delete_person(repository):
    person_data = {
        'name': 'Alice',
        'embedding': [0.1, 0.2, 0.3]  # Example embedding
    }
    person_id = repository.add_person(person_data)
    repository.delete_person(person_id)
    assert repository.get_person(person_id) is None

def test_get_all_persons(repository):
    person_data1 = {
        'name': 'Bob',
        'embedding': [0.1, 0.2, 0.3]
    }
    person_data2 = {
        'name': 'Charlie',
        'embedding': [0.4, 0.5, 0.6]
    }
    repository.add_person(person_data1)
    repository.add_person(person_data2)
    all_persons = repository.get_all_persons()
    assert len(all_persons) >= 2