from pydantic import BaseModel
from typing import List, Optional

class PersonBase(BaseModel):
    name: str
    email: Optional[str] = None

class PersonCreate(PersonBase):
    pass

class Person(PersonBase):
    id: int

    class Config:
        orm_mode = True

class EnrollmentRequest(BaseModel):
    person_id: int
    images: List[str]  # List of image file paths or URLs

class RecognitionResponse(BaseModel):
    person_id: int
    confidence: float

class GreetingResponse(BaseModel):
    message: str
    person: Person