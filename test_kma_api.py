#!/usr/bin/env python3
"""
기상청 API 테스트 스크립트
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

# 환경 변수 로드
load_dotenv()

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.kma_weather_service import kma_weather_service
from app.utils.kma_utils import get_city_coordinates, get_supported_cities


async def test_kma_api():
    """기상청 API 테스트"""
    print("=== 기상청 API 테스트 ===\n")

    # 1. 지원되는 도시 목록 확인
    print("1. 지원되는 도시 목록:")
    cities = get_supported_cities()
    for i, city in enumerate(cities, 1):
        coords = get_city_coordinates(city)
        print(f"   {i:2d}. {city} (nx={coords['nx']}, ny={coords['ny']})")
    print()

    # 2. 서울 현재 날씨 조회
    print("2. 서울 현재 날씨 조회:")
    try:
        seoul_weather = await kma_weather_service.get_current_weather(60, 127)
        print(f"   기온: {seoul_weather['temperature']}°C")
        print(f"   습도: {seoul_weather['humidity']}%")
        print(f"   강수량: {seoul_weather['rainfall']}mm")
        print(f"   풍속: {seoul_weather['wind_speed']}m/s")
        print(f"   풍향: {seoul_weather['wind_direction']}")
        print(f"   강수형태: {seoul_weather.get('precipitation_type', 'N/A')}")
    except Exception as e:
        print(f"   오류: {e}")
    print()

    # 3. 서울 단기예보 조회
    print("3. 서울 단기예보 조회:")
    try:
        seoul_forecast = await kma_weather_service.get_short_forecast(60, 127)
        print(f"   예보 일수: {len(seoul_forecast['forecast'])}일")
        for day in seoul_forecast['forecast'][:3]:  # 처음 3일만
            print(f"   {day['date']}: 최고 {day['max_temp']}°C, 최저 {day['min_temp']}°C, 강수확률 {day['rainfall_probability']}%")
    except Exception as e:
        print(f"   오류: {e}")
    print()

    # 4. 서울 중기예보 조회
    print("4. 서울 중기예보 조회:")
    try:
        seoul_mid_forecast = await kma_weather_service.get_mid_forecast("11B10101")
        print(f"   예보 일수: {len(seoul_mid_forecast['forecast'])}일")
        for day in seoul_mid_forecast['forecast'][:3]:  # 처음 3일만
            print(f"   {day['date']}: {day['weather']}, 최고 {day['max_temp']}°C, 최저 {day['min_temp']}°C, 강수확률 {day['rainfall_probability']}%")
    except Exception as e:
        print(f"   오류: {e}")
    print()

    # 5. 기상특보 조회
    print("5. 서울 기상특보 조회:")
    try:
        seoul_warning = await kma_weather_service.get_weather_warning("서울")
        if seoul_warning['warnings']:
            for warning in seoul_warning['warnings']:
                print(f"   {warning['warning_type']}: {warning['warning_message']}")
        else:
            print("   현재 발표된 특보가 없습니다.")
    except Exception as e:
        print(f"   오류: {e}")
    print()

if __name__ == "__main__":
    # API 키 확인
    if not os.getenv("KMA_API_KEY") or os.getenv("KMA_API_KEY") == "your_kma_api_key_here":
        print("❌ KMA_API_KEY가 설정되지 않았습니다.")
        print("   .env 파일에 기상청 API 키를 설정해주세요.")
        print("   공공데이터포털(https://www.data.go.kr/)에서 API 키를 발급받으세요.")
        sys.exit(1)

    print("✅ KMA_API_KEY가 설정되었습니다.")
    print()

    # 테스트 실행
    asyncio.run(test_kma_api())
