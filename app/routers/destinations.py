import httpx
from fastapi import APIRouter, Query

from app.config import settings

router = APIRouter(prefix="/destinations", tags=["destinations"])

GOOGLE_API_KEY = settings.google_api_key


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
            address = None
            category = None
            if place_id:
                # Place Details API 호출
                details_url = "https://maps.googleapis.com/maps/api/place/details/json"
                details_resp = await client.get(
                    details_url,
                    params={
                        "place_id": place_id,
                        "fields": "photo,formatted_address,types,name",
                        "key": GOOGLE_API_KEY,
                        "language": "ko",
                    },
                )
                details_data = details_resp.json()
                result = details_data.get("result", {})
                photos = result.get("photos", [])
                address = result.get("formatted_address")
                types = result.get("types", [])
                # 대표적인 카테고리 하나를 선택
                if types:
                    category = types[0]

                if photos:
                    # 대표 사진의 photo_reference로 실제 이미지 URL 생성
                    photo_reference = photos[0].get("photo_reference")
                    if photo_reference:
                        photo_url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=400&photo_reference={photo_reference}&key={GOOGLE_API_KEY}"

            suggestions.append({
                "description": description,
                "place_id": place_id,
                "photo_url": photo_url,
                "address": address,
                "category": category,
            })
    return {"suggestions": suggestions}