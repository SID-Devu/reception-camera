from sqlalchemy.orm import Session
from .models import Person
from typing import List, Optional

class Repository:
    def __init__(self, db: Session):
        self.db = db

    def get_person(self, person_id: int) -> Optional[Person]:
        return self.db.query(Person).filter(Person.id == person_id).first()

    def get_person_by_name(self, name: str) -> Optional[Person]:
        return self.db.query(Person).filter(Person.name == name).first()

    def get_all_persons(self) -> List[Person]:
        return self.db.query(Person).all()

    def add_person(self, person: Person) -> Person:
        self.db.add(person)
        self.db.commit()
        self.db.refresh(person)
        return person

    def update_person(self, person: Person) -> Person:
        self.db.commit()
        self.db.refresh(person)
        return person

    def delete_person(self, person_id: int) -> None:
        person = self.get_person(person_id)
        if person:
            self.db.delete(person)
            self.db.commit()