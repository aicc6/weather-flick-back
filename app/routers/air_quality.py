from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import List, Optional
from app.models import User
from app.auth import get_current_active_user
from app.services.air_quality_service import air_quality_service

router = APIRouter(
    prefix="/air-quality",
    tags=["air_quality"]
)

@router.get("/current/{city}")
async def get_current_air_quality(
    city: str,
    current_user: User = Depends(get_current_active_user)
):
    """현재 대기질 정보 조회"""
    air_quality = await air_quality_service.get_current_air_quality(city)
    if not air_quality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Air quality data for city '{city}' not found"
        )
    return air_quality

@router.get("/forecast/{city}")
async def get_air_quality_forecast(
    city: str,
    current_user: User = Depends(get_current_active_user)
):
    """대기질 예보 조회"""
    forecast = await air_quality_service.get_air_quality_forecast(city)
    if not forecast:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Air quality forecast for city '{city}' not found"
        )
    return forecast

@router.get("/stations/nearby")
async def get_nearby_stations(
    latitude: float = Query(..., description="위도"),
    longitude: float = Query(..., description="경도"),
    radius: float = Query(5000, description="반경 (미터)", ge=1000, le=50000),
    current_user: User = Depends(get_current_active_user)
):
    """주변 측정소 조회"""
    stations = await air_quality_service.get_nearby_stations(latitude, longitude, radius)
    return {
        "stations": stations,
        "total": len(stations),
        "center": {"latitude": latitude, "longitude": longitude},
        "radius": radius
    }

@router.get("/cities")
async def get_supported_cities():
    """지원되는 도시 목록"""
    cities = await air_quality_service.get_supported_cities()
    return {"cities": cities}

@router.get("/info")
async def get_air_quality_info():
    """대기질 정보 안내"""
    return {
        "description": "대기질 정보 API",
        "sources": [
            {
                "name": "미세미세",
                "description": "미세미세 API를 통한 실시간 대기질 정보",
                "priority": 1
            },
            {
                "name": "공공데이터포털",
                "description": "환경부 대기질 정보 API",
                "priority": 2
            },
            {
                "name": "내장 데이터",
                "description": "기본 대기질 정보 (API 키 없을 때)",
                "priority": 3
            }
        ],
        "pollutants": {
            "pm10": {
                "name": "미세먼지 (PM10)",
                "unit": "㎍/㎥",
                "description": "지름 10마이크로미터 이하의 미세먼지"
            },
            "pm25": {
                "name": "초미세먼지 (PM2.5)",
                "unit": "㎍/㎥",
                "description": "지름 2.5마이크로미터 이하의 초미세먼지"
            },
            "o3": {
                "name": "오존 (O3)",
                "unit": "ppm",
                "description": "지표면 오존 농도"
            },
            "no2": {
                "name": "이산화질소 (NO2)",
                "unit": "ppm",
                "description": "이산화질소 농도"
            },
            "co": {
                "name": "일산화탄소 (CO)",
                "unit": "ppm",
                "description": "일산화탄소 농도"
            },
            "so2": {
                "name": "이산화황 (SO2)",
                "unit": "ppm",
                "description": "이산화황 농도"
            }
        },
        "grades": {
            "좋음": {
                "color": "#00E400",
                "description": "대기질이 양호한 상태"
            },
            "보통": {
                "color": "#FFFF00",
                "description": "대기질이 보통인 상태"
            },
            "나쁨": {
                "color": "#FF7E00",
                "description": "대기질이 나쁜 상태"
            },
            "매우나쁨": {
                "color": "#FF0000",
                "description": "대기질이 매우 나쁜 상태"
            }
        }
    }

@router.get("/health/{city}")
async def get_air_quality_health_advice(
    city: str,
    current_user: User = Depends(get_current_active_user)
):
    """대기질 건강 조언"""
    air_quality = await air_quality_service.get_current_air_quality(city)
    if not air_quality:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Air quality data for city '{city}' not found"
        )

    # 대기질 등급에 따른 건강 조언
    aqi_grade = air_quality.get("air_quality_index", {}).get("grade", "보통")

    health_advice = {
        "좋음": {
            "general": "대기질이 양호합니다. 정상적인 실외활동이 가능합니다.",
            "sensitive_groups": "민감군도 정상적인 실외활동이 가능합니다.",
            "activities": ["야외운동", "등산", "자전거", "산책"],
            "recommendations": ["정상적인 실외활동 권장", "창문 열기 가능"]
        },
        "보통": {
            "general": "대기질이 보통입니다. 대부분의 사람들에게는 영향이 없습니다.",
            "sensitive_groups": "민감군은 장시간 실외활동을 줄이는 것이 좋습니다.",
            "activities": ["야외운동", "등산", "자전거", "산책"],
            "recommendations": ["정상적인 실외활동 가능", "민감군은 주의"]
        },
        "나쁨": {
            "general": "대기질이 나쁩니다. 실외활동을 줄이는 것이 좋습니다.",
            "sensitive_groups": "민감군은 실외활동을 피해야 합니다.",
            "activities": ["가벼운 산책", "짧은 실외활동"],
            "recommendations": ["실외활동 줄이기", "마스크 착용 권장", "창문 닫기"]
        },
        "매우나쁨": {
            "general": "대기질이 매우 나쁩니다. 실외활동을 피해야 합니다.",
            "sensitive_groups": "민감군은 실외활동을 금지해야 합니다.",
            "activities": ["실내활동만"],
            "recommendations": ["실외활동 금지", "마스크 필수", "공기청정기 사용"]
        }
    }

    return {
        "city": city,
        "air_quality_grade": aqi_grade,
        "timestamp": air_quality.get("timestamp"),
        "health_advice": health_advice.get(aqi_grade, health_advice["보통"]),
        "current_data": air_quality
    }

@router.get("/compare/{city}")
async def compare_air_quality_sources(
    city: str,
    current_user: User = Depends(get_current_active_user)
):
    """여러 소스의 대기질 정보 비교"""
    # 미세미세 API 데이터
    misemise_data = None
    if air_quality_service.misemise_api_key:
        misemise_data = await air_quality_service._get_misemise_air_quality(city)

    # 공공데이터포털 API 데이터
    public_data = None
    if air_quality_service.public_data_api_key:
        public_data = await air_quality_service._get_public_data_air_quality(city)

    # 내장 데이터
    local_data = await air_quality_service._get_local_air_quality(city)

    return {
        "city": city,
        "timestamp": datetime.now().isoformat(),
        "sources": {
            "misemise": misemise_data,
            "public_data": public_data,
            "local_data": local_data
        },
        "summary": {
            "available_sources": len([d for d in [misemise_data, public_data, local_data] if d]),
            "primary_source": "misemise" if misemise_data else "public_data" if public_data else "local_data"
        }
    }

@router.get("/trends/{city}")
async def get_air_quality_trends(
    city: str,
    days: int = Query(7, description="조회할 일수", ge=1, le=30),
    current_user: User = Depends(get_current_active_user)
):
    """대기질 추세 분석"""
    # 실제로는 데이터베이스에서 히스토리 데이터를 조회해야 함
    # 여기서는 예시 데이터를 반환

    from datetime import datetime, timedelta

    trends = []
    base_date = datetime.now()

    for i in range(days):
        date = base_date - timedelta(days=i)
        # 실제 데이터가 없으므로 예시 데이터 생성
        pm10_value = 40 + (i % 3) * 10  # 40-60 범위에서 변동
        pm25_value = 20 + (i % 3) * 5   # 20-30 범위에서 변동

        trends.append({
            "date": date.strftime("%Y-%m-%d"),
            "pm10": {
                "value": pm10_value,
                "grade": "좋음" if pm10_value <= 30 else "보통" if pm10_value <= 80 else "나쁨"
            },
            "pm25": {
                "value": pm25_value,
                "grade": "좋음" if pm25_value <= 15 else "보통" if pm25_value <= 35 else "나쁨"
            }
        })

    return {
        "city": city,
        "period": f"{days}일",
        "trends": trends,
        "summary": {
            "avg_pm10": sum(t["pm10"]["value"] for t in trends) / len(trends),
            "avg_pm25": sum(t["pm25"]["value"] for t in trends) / len(trends),
            "best_day": min(trends, key=lambda x: x["pm10"]["value"])["date"],
            "worst_day": max(trends, key=lambda x: x["pm10"]["value"])["date"]
        }
    }
