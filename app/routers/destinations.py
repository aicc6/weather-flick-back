from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.services.destination_service import destination_service
from app.models import DestinationCreate, DestinationResponse
import httpx
import os

router = APIRouter(
    prefix="/destinations",
    tags=["destinations"]
)

GOOGLE_API_KEY = os.getenv("GCP_API_KEY")

@router.post("/", response_model=DestinationResponse)
def create_destination(
    destination: DestinationCreate,
    db: Session = Depends(get_db)
):
    """새로운 여행지 정보를 생성합니다."""
    return destination_service.create_destination(db=db, destination=destination)

@router.get("/", response_model=List[DestinationResponse])
def read_all_destinations(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """모든 여행지 목록을 조회합니다."""
    destinations = destination_service.get_all_destinations(db, skip=skip, limit=limit)
    return destinations

@router.get("/{province}", response_model=List[DestinationResponse])
def read_destinations_by_province(
    province: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """특정 도/광역시의 여행지 목록을 조회합니다."""
    destinations = destination_service.get_destinations_by_province(db, province=province, skip=skip, limit=limit)
    if not destinations:
        raise HTTPException(status_code=404, detail="해당 지역의 여행지를 찾을 수 없습니다.")
    return destinations

@router.get("/search")
async def search_destination(query: str = Query(...)):
    url = (
        f"https://maps.googleapis.com/maps/api/place/autocomplete/json"
        f"?input={query}&key={GOOGLE_API_KEY}&language=ko"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
    suggestions = [item["description"] for item in data.get("predictions", [])]
    return suggestions
