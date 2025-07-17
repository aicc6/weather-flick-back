from fastapi import APIRouter, Query, HTTPException
import httpx
import os

router = APIRouter(prefix="/google", tags=["google"])

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

@router.get("/reviews")
async def get_google_reviews(place_id: str = Query(...)):
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Google API Key not set")
    url = (
        f"https://maps.googleapis.com/maps/api/place/details/json"
        f"?place_id={place_id}&fields=rating,reviews&language=ko&key={GOOGLE_API_KEY}"
    )
    async with httpx.AsyncClient() as client:
        resp = await client.get(url)
        data = resp.json()
        print("구글 API 응답:", data)  # <-- 이 줄 추가
        if data.get("status") != "OK":
            raise HTTPException(
                status_code=404,
                detail=f"Google Place not found: status={data.get('status')}, error_message={data.get('error_message')}"
            )
        result = data.get("result", {})
        return {
            "rating": result.get("rating"),
            "reviews": result.get("reviews", []),
        }
