from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.database.models import Base, Person
from faker import Faker

def seed_database():
    engine = create_engine('sqlite:///./database.db')  # Update with your database URL
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    fake = Faker()
    
    for _ in range(10):  # Seed 10 fake individuals
        person = Person(
            name=fake.name(),
            embedding=fake.md5()  # Replace with actual embedding logic
        )
        session.add(person)
    
    session.commit()
    session.close()

if __name__ == "__main__":
    seed_database()