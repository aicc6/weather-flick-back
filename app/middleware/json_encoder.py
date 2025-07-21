"""
JSON 직렬화 미들웨어
타임존 정보가 포함된 datetime 객체를 일관되게 직렬화
"""

import json
from datetime import datetime, timezone
from typing import Any
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.utils.timezone_utils import TimezoneUtils


class DateTimeEncoder(json.JSONEncoder):
    """
    datetime 객체를 ISO 8601 형식으로 직렬화하는 JSON 인코더
    타임존 정보를 포함하여 클라이언트에서 정확한 시간 해석 가능
    """
    
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            if obj.tzinfo is None:
                # naive datetime을 UTC로 가정하고 타임존 정보 추가
                obj = obj.replace(tzinfo=timezone.utc)
            
            # ISO 8601 형식으로 직렬화 (타임존 정보 포함)
            return obj.isoformat()
        
        return super().default(obj)


class TimezoneJSONMiddleware(BaseHTTPMiddleware):
    """
    JSON 응답에서 datetime 객체를 타임존 정보와 함께 직렬화하는 미들웨어
    """
    
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        
        # JSON 응답이 아닌 경우 그대로 반환
        if not isinstance(response, JSONResponse):
            return response
        
        # 응답 헤더에 타임존 정보 추가
        response.headers['X-Server-Timezone'] = 'UTC'
        response.headers['X-Client-Recommended-Timezone'] = 'Asia/Seoul'
        
        return response


def setup_json_encoding(app):
    """
    FastAPI 앱에 JSON 인코딩 설정 적용
    """
    
    # 타임존 미들웨어 추가
    app.add_middleware(TimezoneJSONMiddleware)


# Pydantic 모델을 위한 JSON 인코더 설정
def pydantic_json_encoder():
    """
    Pydantic 모델에서 사용할 JSON 인코더 반환
    """
    return {
        datetime: lambda v: TimezoneUtils.format_for_api(v) if v else None
    }


# 응답 데이터 후처리 함수
def process_response_data(data: Any) -> Any:
    """
    응답 데이터에서 datetime 객체를 타임존 정보와 함께 포맷팅
    """
    if isinstance(data, dict):
        return {key: process_response_data(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [process_response_data(item) for item in data]
    elif isinstance(data, datetime):
        return TimezoneUtils.format_for_api(data)
    else:
        return data


# API 응답용 헬퍼 함수
def create_timezone_aware_response(data: Any, status_code: int = 200) -> JSONResponse:
    """
    타임존 정보가 포함된 JSON 응답 생성
    """
    processed_data = process_response_data(data)
    
    response = JSONResponse(
        content=processed_data,
        status_code=status_code
    )
    
    # 타임존 관련 헤더 추가
    response.headers['X-Server-Timezone'] = 'UTC'
    response.headers['X-Client-Recommended-Timezone'] = 'Asia/Seoul'
    response.headers['X-Datetime-Format'] = 'ISO8601'
    
    return response


# FastAPI 의존성 주입용 함수
def get_timezone_headers() -> dict:
    """
    타임존 관련 헤더를 반환하는 의존성 함수
    """
    return {
        'X-Server-Timezone': 'UTC',
        'X-Client-Recommended-Timezone': 'Asia/Seoul',
        'X-Datetime-Format': 'ISO8601'
    }