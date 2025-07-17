#!/usr/bin/env python3
"""
ODsay API 키 상세 테스트 스크립트
API 키 인증 실패 원인 분석을 위한 상세 테스트
"""

import asyncio
import httpx
import json
import urllib.parse
from datetime import datetime

# 새로 발급받은 ODsay API 키
API_KEY = "vrSu2AoUX5Abn0xuqBJSGA"
BASE_URL = "https://api.odsay.com/v1/api"

async def test_api_key_encoding():
    """API 키 인코딩 테스트"""
    print("=" * 60)
    print("1. API 키 인코딩 분석")
    print("=" * 60)
    
    print(f"🔑 원본 API 키: {API_KEY}")
    print(f"🔑 URL 인코딩된 API 키: {urllib.parse.quote(API_KEY)}")
    print(f"🔑 키 길이: {len(API_KEY)} 문자")
    print(f"🔑 특수 문자 포함: {any(c in API_KEY for c in '!@#$%^&*()+=[]{}|;:,.<>?/')}")
    
    # 다양한 인코딩 방식으로 테스트
    encoding_tests = [
        ("원본 키", API_KEY),
        ("URL 인코딩", urllib.parse.quote(API_KEY)),
        ("Quote Plus", urllib.parse.quote_plus(API_KEY)),
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for encoding_name, encoded_key in encoding_tests:
            print(f"\n📝 {encoding_name} 테스트:")
            print(f"   키 값: {encoded_key}")
            
            url = f"{BASE_URL}/searchStation"
            params = {
                "stationName": "강남",
                "CID": 1000,
                "apiKey": encoded_key
            }
            
            try:
                response = await client.get(url, params=params)
                print(f"   📊 응답 상태: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("error"):
                        print(f"   ❌ 오류: {data['error'][0]['message']}")
                    else:
                        print(f"   ✅ 성공!")
                        return True
                else:
                    print(f"   ❌ HTTP 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 예외: {e}")
    
    return False

async def test_different_endpoints():
    """다양한 엔드포인트 테스트"""
    print("\n" + "=" * 60)
    print("2. 다양한 엔드포인트 테스트")
    print("=" * 60)
    
    endpoints = [
        {
            "name": "역 검색",
            "endpoint": "/searchStation",
            "params": {"stationName": "강남", "CID": 1000, "apiKey": API_KEY}
        },
        {
            "name": "대중교통 경로 검색",
            "endpoint": "/searchPubTransPathT",
            "params": {"SX": 126.8821, "SY": 37.4816, "EX": 127.0276, "EY": 37.4979, "apiKey": API_KEY}
        },
        {
            "name": "지하철 노선 검색",
            "endpoint": "/loadLane",
            "params": {"CID": 1000, "apiKey": API_KEY}
        }
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for endpoint_info in endpoints:
            print(f"\n🚀 {endpoint_info['name']} 테스트:")
            
            url = f"{BASE_URL}{endpoint_info['endpoint']}"
            
            try:
                response = await client.get(url, params=endpoint_info["params"])
                print(f"   📍 요청 URL: {response.url}")
                print(f"   📊 응답 상태: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"   📄 응답 데이터:")
                    print(json.dumps(data, indent=4, ensure_ascii=False)[:500] + "..." if len(json.dumps(data, indent=4, ensure_ascii=False)) > 500 else json.dumps(data, indent=4, ensure_ascii=False))
                    
                    if data.get("error"):
                        print(f"   ❌ API 오류: {data['error'][0]['message']}")
                    else:
                        print(f"   ✅ 성공!")
                else:
                    print(f"   ❌ HTTP 오류: {response.status_code}")
                    print(f"   응답 내용: {response.text}")
                    
            except Exception as e:
                print(f"   ❌ 예외: {e}")

async def test_headers_and_methods():
    """헤더 및 HTTP 메서드 테스트"""
    print("\n" + "=" * 60)
    print("3. 헤더 및 HTTP 메서드 테스트")
    print("=" * 60)
    
    headers_tests = [
        ("기본 헤더", {}),
        ("Content-Type 추가", {"Content-Type": "application/json"}),
        ("User-Agent 추가", {"User-Agent": "WeatherFlick/1.0"}),
        ("Accept 추가", {"Accept": "application/json"}),
        ("전체 헤더", {
            "Content-Type": "application/json",
            "User-Agent": "WeatherFlick/1.0",
            "Accept": "application/json"
        })
    ]
    
    url = f"{BASE_URL}/searchStation"
    params = {"stationName": "강남", "CID": 1000, "apiKey": API_KEY}
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for header_name, headers in headers_tests:
            print(f"\n📝 {header_name} 테스트:")
            
            try:
                response = await client.get(url, params=params, headers=headers)
                print(f"   📊 응답 상태: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    if data.get("error"):
                        print(f"   ❌ 오류: {data['error'][0]['message']}")
                    else:
                        print(f"   ✅ 성공!")
                        return True
                else:
                    print(f"   ❌ HTTP 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 예외: {e}")
    
    return False

async def test_api_key_validation():
    """API 키 유효성 검증"""
    print("\n" + "=" * 60)
    print("4. API 키 유효성 검증")
    print("=" * 60)
    
    # 가짜 API 키로 테스트
    fake_keys = [
        "invalid_key_123",
        "test_key_456",
        "",  # 빈 키
        "a" * 22,  # 길이만 맞춘 키
    ]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        print(f"🔑 실제 API 키 테스트:")
        url = f"{BASE_URL}/searchStation"
        params = {"stationName": "강남", "CID": 1000, "apiKey": API_KEY}
        
        try:
            response = await client.get(url, params=params)
            data = response.json()
            print(f"   실제 키 응답: {data}")
        except Exception as e:
            print(f"   실제 키 오류: {e}")
        
        print(f"\n🔑 가짜 API 키 테스트:")
        for fake_key in fake_keys:
            params = {"stationName": "강남", "CID": 1000, "apiKey": fake_key}
            
            try:
                response = await client.get(url, params=params)
                data = response.json()
                print(f"   가짜 키 '{fake_key[:10]}...' 응답: {data}")
            except Exception as e:
                print(f"   가짜 키 오류: {e}")

async def test_request_debugging():
    """요청 디버깅"""
    print("\n" + "=" * 60)
    print("5. 요청 디버깅")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/searchStation"
        params = {"stationName": "강남", "CID": 1000, "apiKey": API_KEY}
        
        try:
            response = await client.get(url, params=params)
            
            print(f"🔍 요청 분석:")
            print(f"   URL: {response.url}")
            print(f"   메서드: {response.request.method}")
            print(f"   헤더: {dict(response.request.headers)}")
            print(f"   파라미터: {params}")
            
            print(f"\n🔍 응답 분석:")
            print(f"   상태 코드: {response.status_code}")
            print(f"   응답 헤더: {dict(response.headers)}")
            print(f"   응답 크기: {len(response.content)} bytes")
            
            if response.status_code == 200:
                data = response.json()
                print(f"   응답 데이터:")
                print(json.dumps(data, indent=4, ensure_ascii=False))
                
                if data.get("error"):
                    error_info = data["error"][0]
                    print(f"\n❌ 오류 상세:")
                    print(f"   코드: {error_info.get('code')}")
                    print(f"   메시지: {error_info.get('message')}")
                    
                    # 오류 메시지 분석
                    if "ApiKeyAuthFailed" in error_info.get('message', ''):
                        print(f"\n💡 ApiKeyAuthFailed 오류 분석:")
                        print(f"   - API 키가 올바르지 않음")
                        print(f"   - 플랫폼 설정이 잘못됨")
                        print(f"   - 승인 대기 중일 수 있음")
                        print(f"   - 사용 한도 초과")
                        print(f"   - 서비스 중단")
                        
        except Exception as e:
            print(f"❌ 요청 실패: {e}")

async def main():
    """메인 테스트 실행"""
    print("🚀 ODsay API 키 상세 테스트 시작")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API 키: {API_KEY}")
    print(f"🌐 기본 URL: {BASE_URL}")
    
    # 각 테스트 실행
    await test_api_key_encoding()
    await test_different_endpoints()
    await test_headers_and_methods()
    await test_api_key_validation()
    await test_request_debugging()
    
    print("\n" + "=" * 60)
    print("📊 테스트 완료")
    print("=" * 60)
    print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\n💡 추천 해결 방안:")
    print("1. ODsay LAB 사이트에서 API 키 재발급")
    print("2. 애플리케이션 등록 상태 확인")
    print("3. 플랫폼 설정 (서버/URI) 확인")
    print("4. 사용 승인 상태 확인")
    print("5. 고객 지원 문의")

if __name__ == "__main__":
    asyncio.run(main())