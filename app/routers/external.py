from fastapi import APIRouter
from app.services.external_service import fetch_external_data

router = APIRouter(prefix="/api/external", tags=["External API Integration"])

@router.get("/data")
async def get_external_api_data():
    return await fetch_external_data()
