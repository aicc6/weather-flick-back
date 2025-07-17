#!/usr/bin/env python3
"""
ODsay API 키 테스트 스크립트
새로 발급받은 API 키로 ODsay API 호출 테스트
"""

import asyncio
import httpx
import json
from datetime import datetime

# 서버 API 키로 변경
API_KEY = "2dpumXwMVIafymXG/9ZvBFppzH1KWH3lQMG80AaPzgU"
BASE_URL = "https://api.odsay.com/v1/api"

# 테스트 좌표
TEST_COORDINATES = {
    "가산디지털단지역": {"x": 126.8821, "y": 37.4816},
    "강남역": {"x": 127.0276, "y": 37.4979},
    "서울역": {"x": 126.9720, "y": 37.5547},
    "홍대입구역": {"x": 126.9244, "y": 37.5571}
}

async def test_api_key_basic():
    """기본 API 키 유효성 테스트"""
    print("=" * 60)
    print("1. ODsay API 키 기본 유효성 테스트")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 간단한 역 검색으로 API 키 테스트
        url = f"{BASE_URL}/searchStation"
        params = {
            "stationName": "강남",
            "CID": 1000,  # 서울
            "apiKey": API_KEY
        }
        
        try:
            response = await client.get(url, params=params)
            print(f"📍 요청 URL: {response.url}")
            print(f"📊 응답 상태: {response.status_code}")
            print(f"📄 응답 헤더: {dict(response.headers)}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ API 키 유효성: 성공")
                print(f"📝 응답 데이터 구조:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get("result"):
                    stations = data["result"].get("station", [])
                    print(f"🚇 검색된 역 수: {len(stations)}")
                    if stations:
                        for i, station in enumerate(stations[:3]):  # 최대 3개만 표시
                            print(f"   {i+1}. {station.get('stationName', 'N/A')} ({station.get('stationID', 'N/A')})")
                    return True
                else:
                    print(f"❌ API 응답 오류: {data}")
                    return False
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"응답 내용: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
            return False

async def test_public_transport_search():
    """대중교통 경로 검색 테스트"""
    print("\n" + "=" * 60)
    print("2. 대중교통 경로 검색 테스트")
    print("=" * 60)
    
    start = TEST_COORDINATES["가산디지털단지역"]
    end = TEST_COORDINATES["강남역"]
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        url = f"{BASE_URL}/searchPubTransPathT"
        params = {
            "SX": start["x"],
            "SY": start["y"],
            "EX": end["x"],
            "EY": end["y"],
            "apiKey": API_KEY
        }
        
        try:
            print(f"🚀 출발지: 가산디지털단지역 ({start['x']}, {start['y']})")
            print(f"🎯 도착지: 강남역 ({end['x']}, {end['y']})")
            
            response = await client.get(url, params=params)
            print(f"📍 요청 URL: {response.url}")
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ 대중교통 경로 검색: 성공")
                
                if data.get("result"):
                    result = data["result"]
                    paths = result.get("path", [])
                    
                    print(f"🛤️  검색된 경로 수: {len(paths)}")
                    
                    if paths:
                        for i, path in enumerate(paths[:2]):  # 최대 2개 경로만 표시
                            path_info = path.get("info", {})
                            print(f"\n📋 경로 {i+1}:")
                            print(f"   ⏱️  총 소요시간: {path_info.get('totalTime', 0)}분")
                            print(f"   📏 총 거리: {path_info.get('totalDistance', 0)}m")
                            print(f"   💰 비용: {path_info.get('payment', 0)}원")
                            print(f"   🔄 버스 환승: {path_info.get('busTransitCount', 0)}회")
                            print(f"   🚇 지하철 환승: {path_info.get('subwayTransitCount', 0)}회")
                            print(f"   🚶 총 도보시간: {path_info.get('totalWalk', 0)}분")
                            
                            # 세부 경로 정보
                            sub_paths = path.get("subPath", [])
                            if sub_paths:
                                print(f"   📍 세부 경로:")
                                for j, sub_path in enumerate(sub_paths):
                                    traffic_type = sub_path.get("trafficType")
                                    if traffic_type == 1:  # 지하철
                                        lane_info = sub_path.get("lane", [{}])[0]
                                        print(f"      {j+1}. 🚇 {lane_info.get('name', '지하철')} "
                                              f"({sub_path.get('startName', '')} → {sub_path.get('endName', '')})")
                                    elif traffic_type == 2:  # 버스
                                        lane_info = sub_path.get("lane", [{}])[0]
                                        print(f"      {j+1}. 🚌 {lane_info.get('busNo', '버스')} "
                                              f"({sub_path.get('startName', '')} → {sub_path.get('endName', '')})")
                                    elif traffic_type == 3:  # 도보
                                        print(f"      {j+1}. 🚶 도보 {sub_path.get('distance', 0)}m, "
                                              f"{sub_path.get('sectionTime', 0)}분")
                    
                    return True
                else:
                    print(f"❌ 경로 검색 실패: {data}")
                    return False
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                print(f"응답 내용: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 예외 발생: {e}")
            return False

async def test_multiple_routes():
    """여러 경로 테스트"""
    print("\n" + "=" * 60)
    print("3. 여러 경로 테스트")
    print("=" * 60)
    
    test_routes = [
        ("가산디지털단지역", "서울역"),
        ("홍대입구역", "강남역"),
        ("서울역", "홍대입구역")
    ]
    
    success_count = 0
    total_count = len(test_routes)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        for start_name, end_name in test_routes:
            start = TEST_COORDINATES[start_name]
            end = TEST_COORDINATES[end_name]
            
            print(f"\n🚀 {start_name} → {end_name}")
            
            url = f"{BASE_URL}/searchPubTransPathT"
            params = {
                "SX": start["x"],
                "SY": start["y"],
                "EX": end["x"],
                "EY": end["y"],
                "apiKey": API_KEY
            }
            
            try:
                response = await client.get(url, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    if data.get("result") and data["result"].get("path"):
                        paths = data["result"]["path"]
                        best_path = min(paths, key=lambda x: x.get("info", {}).get("totalTime", float('inf')))
                        path_info = best_path.get("info", {})
                        
                        print(f"   ✅ 성공 - 소요시간: {path_info.get('totalTime', 0)}분, "
                              f"비용: {path_info.get('payment', 0)}원")
                        success_count += 1
                    else:
                        print(f"   ❌ 경로 없음")
                else:
                    print(f"   ❌ HTTP 오류: {response.status_code}")
                    
            except Exception as e:
                print(f"   ❌ 예외: {e}")
    
    print(f"\n📊 테스트 결과: {success_count}/{total_count} 성공")
    return success_count == total_count

async def test_error_handling():
    """오류 처리 테스트"""
    print("\n" + "=" * 60)
    print("4. 오류 처리 테스트")
    print("=" * 60)
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        # 잘못된 좌표로 테스트
        url = f"{BASE_URL}/searchPubTransPathT"
        params = {
            "SX": 999,  # 잘못된 좌표
            "SY": 999,
            "EX": 127.0276,
            "EY": 37.4979,
            "apiKey": API_KEY
        }
        
        try:
            response = await client.get(url, params=params)
            print(f"📍 잘못된 좌표 테스트")
            print(f"📊 응답 상태: {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                print(f"📄 응답 데이터:")
                print(json.dumps(data, indent=2, ensure_ascii=False))
                
                if data.get("error"):
                    print(f"✅ 오류 처리 정상: {data['error']}")
                else:
                    print(f"⚠️  예상과 다른 응답")
            else:
                print(f"❌ HTTP 오류: {response.status_code}")
                
        except Exception as e:
            print(f"❌ 예외 발생: {e}")

async def main():
    """메인 테스트 실행"""
    print("🚀 ODsay API 키 테스트 시작")
    print(f"⏰ 테스트 시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔑 API 키: {API_KEY[:10]}...")
    print(f"🌐 기본 URL: {BASE_URL}")
    
    # 각 테스트 실행
    results = []
    
    # 1. 기본 API 키 테스트
    results.append(await test_api_key_basic())
    
    # 2. 대중교통 경로 검색 테스트
    results.append(await test_public_transport_search())
    
    # 3. 여러 경로 테스트
    results.append(await test_multiple_routes())
    
    # 4. 오류 처리 테스트
    await test_error_handling()
    
    # 최종 결과
    print("\n" + "=" * 60)
    print("📊 최종 테스트 결과")
    print("=" * 60)
    
    passed = sum(results)
    total = len(results)
    
    print(f"✅ 통과: {passed}/{total} 테스트")
    print(f"⏰ 테스트 완료 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    if passed == total:
        print("🎉 모든 테스트 성공! ODsay API 키가 정상 작동합니다.")
    else:
        print("⚠️  일부 테스트 실패. API 키나 설정을 확인해주세요.")
    
    return passed == total

if __name__ == "__main__":
    asyncio.run(main())