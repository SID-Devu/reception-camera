from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from src.enrollment.enroll_service import EnrollService

router = APIRouter()
enroll_service = EnrollService()

class EnrollmentRequest(BaseModel):
    name: str
    image: UploadFile = File(...)

@router.post("/enroll")
async def enroll_person(enrollment_request: EnrollmentRequest):
    try:
        image_data = await enrollment_request.image.read()
        result = enroll_service.enroll(enrollment_request.name, image_data)
        return {"message": "Enrollment successful", "person_id": result}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))