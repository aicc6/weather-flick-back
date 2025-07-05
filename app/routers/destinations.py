import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import DestinationCreate, DestinationResponse
from app.services.destination_service import destination_service

router = APIRouter(prefix="/destinations", tags=["destinations"])

GOOGLE_API_KEY = settings.google_api_key


@router.post("/", response_model=DestinationResponse)
def create_destination(destination: DestinationCreate, db: Session = Depends(get_db)):
    """새로운 여행지 정보를 생성합니다."""
    return destination_service.create_destination(db=db, destination=destination)


@router.get("/", response_model=list[DestinationResponse])
def read_all_destinations(
    skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """모든 여행지 목록을 조회합니다."""
    destinations = destination_service.get_all_destinations(db, skip=skip, limit=limit)
    return destinations


@router.get("/search")
async def search_destination(query: str = Query(...)):
    url = "https://maps.googleapis.com/maps/api/place/autocomplete/json"
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            url,
            params={
                "language": "ko",
                "key": GOOGLE_API_KEY,
                "input": query,
            },
        )
        data = resp.json()

        # 각 prediction에서 place_id 추출 후, Details API로 대표 사진 얻기
        suggestions = []
        for item in data.get("predictions", []):
            description = item["description"]
            place_id = item.get("place_id")
            photo_url = None
            if place_id:
                # Place Details API 호출
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_resp = await client.get(
                    details_url,
                    params={
                        "place_id": place_id,
                        "fields": "photo",
                        "key": GOOGLE_API_KEY,
                        "language": "ko",
                    },
                )
                details_data = details_resp.json()
                photos = details_data.get("result", {}).get("photos", [])
                if photos:
                    # 대표 사진의 photo_reference로 실제 이미지 URL 생성
                    photo_reference = photos[0].get("photo_reference")
                    if photo_reference:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={GOOGLE_API_KEY}"
            suggestions.append({
                "description": description,
                "place_id": place_id,
                "photo_url": photo_url,
            })
    return {"suggestions": suggestions}


@router.get("/{province}", response_model=list[DestinationResponse])
def read_destinations_by_province(
    province: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)
):
    """특정 도/광역시의 여행지 목록을 조회합니다."""
    destinations = destination_service.get_destinations_by_province(
        db, province=province, skip=skip, limit=limit
    )
    if not destinations:
        raise HTTPException(
            status_code=404, detail="해당 지역의 여행지를 찾을 수 없습니다."
        )
    return destinations
