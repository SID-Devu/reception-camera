from fastapi import APIRouter, HTTPException
from typing import List
from src.database.repository import PersonRepository
from src.api.schemas import PersonCreate, PersonRead

router = APIRouter()
repository = PersonRepository()

@router.post("/persons/", response_model=PersonRead)
async def create_person(person: PersonCreate):
    existing_person = await repository.get_person_by_name(person.name)
    if existing_person:
        raise HTTPException(status_code=400, detail="Person already exists")
    return await repository.create_person(person)

@router.get("/persons/", response_model=List[PersonRead])
async def read_persons(skip: int = 0, limit: int = 10):
    return await repository.get_persons(skip=skip, limit=limit)

@router.get("/persons/{person_id}", response_model=PersonRead)
async def read_person(person_id: int):
    person = await repository.get_person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person

@router.delete("/persons/{person_id}", response_model=PersonRead)
async def delete_person(person_id: int):
    person = await repository.delete_person(person_id)
    if person is None:
        raise HTTPException(status_code=404, detail="Person not found")
    return person