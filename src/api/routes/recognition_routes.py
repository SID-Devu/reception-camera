from fastapi import APIRouter, HTTPException
from src.recognition.encoder import Encoder
from src.recognition.matcher import Matcher
from src.database.repository import Repository

router = APIRouter()
encoder = Encoder()
matcher = Matcher()
repository = Repository()

@router.post("/recognize")
async def recognize_face(image: bytes):
    try:
        embedding = encoder.encode(image)
        person_id = matcher.match(embedding)
        if person_id is not None:
            person = repository.get_person(person_id)
            return {"message": f"Hello, {person.name}!"}
        else:
            return {"message": "Face not recognized."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recognition-status")
async def recognition_status():
    return {"status": "Recognition service is running."}