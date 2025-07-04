import httpx
from fastapi import APIRouter, Query

from app.config import settings

router = APIRouter(prefix="/location", tags=["location"])

GOOGLE_API_KEY = settings.google_api_key


@router.get("/reverse-geocode")
async def reverse_geocode(lat: float = Query(...), lng: float = Query(...)):
    url = (
        f"https://maps.googleapis.com/maps/api/geocode/json"
        f"?latlng={lat},{lng}&key={GOOGLE_API_KEY}&language=ko"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
    return {
        "address": (
            data["results"][0]["formatted_address"]
            if data.get("status") == "OK" and data.get("results")
            else None
        ),
        "status": data.get("status"),
        "error_message": data.get("error_message"),
        "raw": data,  # (디버깅용, 실제 배포시 삭제)
    }
