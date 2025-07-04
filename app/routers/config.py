import re

from fastapi import APIRouter

from app.config import settings

router = APIRouter(
    prefix="/config",
    tags=["config"],
    responses={404: {"description": "Not found"}},
)


@router.get("/google-key")
async def get_google_api_key():
    """구글 API 키 반환"""
    # API 키에서 주석, 따옴표, 공백 제거 및 정리
    api_key = settings.google_api_key
    if api_key:
        # 주석 부분 제거
        if "#" in api_key:
            api_key = api_key.split("#")[0]

        # 따옴표, 공백, 특수문자 제거
        api_key = re.sub(r'["\'\s]', "", api_key.strip())

    # 유효하지 않은 기본값인 경우 빈 문자열 반환
    if not api_key or api_key in ["your-google-api-key-here", "None", ""]:
        api_key = ""

    # API 키 길이 검증 (Google API 키는 보통 39자)
    if api_key and len(api_key) < 20:
        api_key = ""

    return {"googleApiKey": api_key}
