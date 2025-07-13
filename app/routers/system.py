import time
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any

import httpx
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/system", tags=["system"])


async def check_database_connection(db: Session) -> Dict[str, Any]:
    """데이터베이스 연결 상태를 확인합니다."""
    try:
        start_time = time.time()
        # 간단한 쿼리로 DB 연결 테스트
        result = db.execute(text("SELECT 1")).fetchone()
        response_time = round((time.time() - start_time) * 1000, 2)
        
        if result:
            return {
                "status": "연결됨",
                "response_time": f"{response_time}ms"
            }
        else:
            return {
                "status": "오류",
                "response_time": f"{response_time}ms"
            }
    except Exception as e:
        logger.error(f"Database connection check failed: {str(e)}")
        return {
            "status": f"오류({str(e)})",
            "response_time": "N/A"
        }


async def check_external_api(url: str, timeout: int = 5) -> Dict[str, Any]:
    """외부 API 상태를 확인합니다."""
    try:
        start_time = time.time()
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response_time = round((time.time() - start_time) * 1000, 2)
            
            if response.status_code == 200:
                return {
                    "status": "정상",
                    "response_time": f"{response_time}ms"
                }
            else:
                return {
                    "status": f"오류({response.status_code})",
                    "response_time": f"{response_time}ms"
                }
    except asyncio.TimeoutError:
        return {
            "status": "타임아웃",
            "response_time": "N/A"
        }
    except Exception as e:
        logger.error(f"External API check failed for {url}: {str(e)}")
        return {
            "status": f"오류({str(e)})",
            "response_time": "N/A"
        }


@router.get("/status")
async def get_system_status(db: Session = Depends(get_db)):
    """
    시스템 전체 상태를 확인합니다.
    데이터베이스 연결, 외부 API 상태 등을 종합적으로 체크합니다.
    """
    try:
        # 데이터베이스 상태 확인
        db_status = await check_database_connection(db)
        
        # 외부 API 상태 확인 (병렬 처리)
        api_checks = []
        
        # 기상청 API
        if hasattr(settings, 'KMA_API_URL') and settings.KMA_API_URL:
            api_checks.append(('weather_api', check_external_api(settings.KMA_API_URL)))
        
        # 한국관광공사 API
        if hasattr(settings, 'TOUR_API_BASE_URL') and settings.TOUR_API_BASE_URL:
            api_checks.append(('tourism_api', check_external_api(settings.TOUR_API_BASE_URL)))
        
        # Google Places API
        if hasattr(settings, 'GOOGLE_PLACES_API_URL') and settings.GOOGLE_PLACES_API_URL:
            api_checks.append(('google_places', check_external_api(settings.GOOGLE_PLACES_API_URL)))
        
        # Naver Map API (기본 상태 체크용 URL)
        if hasattr(settings, 'NAVER_MAP_API_URL') and settings.NAVER_MAP_API_URL:
            api_checks.append(('naver_map', check_external_api(settings.NAVER_MAP_API_URL)))
        
        # 병렬로 외부 API 체크 실행
        external_apis = {}
        if api_checks:
            api_results = await asyncio.gather(*[check for _, check in api_checks])
            external_apis = {name: result for (name, _), result in zip(api_checks, api_results)}
        
        # 전체 서비스 상태 판단
        service_status = "정상"
        
        # DB 연결 실패 시
        if db_status["status"] != "연결됨":
            service_status = "문제발생"
        
        # 외부 API 중 하나라도 문제가 있으면
        for api_name, api_info in external_apis.items():
            if not (api_info["status"] == "정상" or "200" in api_info["status"]):
                service_status = "문제발생"
                break
        
        return {
            "success": True,
            "data": {
                "service_status": service_status,
                "database": db_status,
                "external_apis": external_apis,
                "timestamp": datetime.now().isoformat(),
                "server_info": {
                    "name": "weather-flick-back",
                    "version": "1.0.0",
                    "port": 8000
                }
            }
        }
        
    except Exception as e:
        logger.error(f"System status check failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"시스템 상태 확인 중 오류가 발생했습니다: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """간단한 헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "weather-flick-back"
    }