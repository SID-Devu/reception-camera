from fastapi import APIRouter, HTTPException
from typing import List
from src.database.repository import get_analytics_data

router = APIRouter()

@router.get("/analytics", response_model=List[dict])
async def get_analytics():
    try:
        analytics_data = await get_analytics_data()
        return analytics_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))