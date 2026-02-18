from sqlalchemy import Column, Integer, String, Float
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    embedding = Column(Float, nullable=False)  # Assuming embeddings are stored as a float array
    created_at = Column(String, nullable=False)  # Store creation timestamp
    updated_at = Column(String, nullable=False)  # Store last update timestamp

    def __repr__(self):
        return f"<Person(id={self.id}, name={self.name})>"