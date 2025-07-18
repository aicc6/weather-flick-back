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

    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(url)
            data = resp.json()
            print("구글 API 응답:", data)  # 디버깅용 로그

            status = data.get("status")
            if status != "OK":
                # 다양한 에러 상태에 따른 적절한 HTTP 상태 코드와 메시지
                if status == "REQUEST_DENIED":
                    error_message = data.get("error_message", "Request denied by Google Places API")
                    if "billing" in error_message.lower():
                        raise HTTPException(
                            status_code=503,
                            detail=f"Google Places API billing not enabled: {error_message}"
                        )
                    else:
                        raise HTTPException(
                            status_code=403,
                            detail=f"Google Places API access denied: {error_message}"
                        )
                elif status == "INVALID_REQUEST":
                    raise HTTPException(
                        status_code=400,
                        detail=f"Invalid request to Google Places API: {data.get('error_message', 'Invalid place_id or parameters')}"
                    )
                elif status == "NOT_FOUND":
                    raise HTTPException(
                        status_code=404,
                        detail=f"Place not found: {data.get('error_message', 'Place ID not found in Google Places API')}"
                    )
                elif status == "OVER_QUERY_LIMIT":
                    raise HTTPException(
                        status_code=429,
                        detail="Google Places API quota exceeded"
                    )
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Google Places API error: {status} - {data.get('error_message', 'Unknown error')}"
                    )

            result = data.get("result", {})
            return {
                "rating": result.get("rating"),
                "reviews": result.get("reviews", []),
            }

    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=503,
            detail=f"Failed to connect to Google Places API: {str(e)}"
        )
    except Exception as e:
        print(f"Unexpected error in get_google_reviews: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )
