"""맞춤 여행 추천 라우터"""

import asyncio
import hashlib
import json
import os
from datetime import datetime, timedelta
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Accommodation,
    CategoryCode,
    CulturalFacility,
    CustomTravelRecommendationRequest,
    CustomTravelRecommendationResponse,
    DayItinerary,
    PlaceRecommendation,
    Restaurant,
    Shopping,
    TouristAttraction,
)
from app.services.ai_recommendation import AIRecommendationService

router = APIRouter(
    prefix="/custom-travel",
    tags=["custom-travel"],
)

# 인메모리 캐시 (실제 프로덕션에서는 Redis 사용 권장)
recommendation_cache: Dict[str, Dict[str, Any]] = {}
CACHE_DURATION = timedelta(minutes=30)  # 30분 캐시

# 카테고리 코드 캐시 (데이터베이스 조회 최소화)
category_code_cache = {}

def get_category_name(code: str, db: Session) -> str:
    """카테고리 코드를 한글 이름으로 변환 (데이터베이스 사용)"""
    if not code:
        return None
    
    # 캐시 확인
    if code in category_code_cache:
        return category_code_cache[code]
    
    # 데이터베이스에서 조회
    category = db.query(CategoryCode).filter(CategoryCode.category_code == code).first()
    
    if category:
        category_name = category.category_name
        category_code_cache[code] = category_name
        print(f"Category code {code} converted to: {category_name}")
        return category_name
    
    print(f"Category code {code} not found in database")
    # 데이터베이스에 없으면 코드 그대로 반환
    return code  # None 대신 코드를 반환하여 태그에 포함되도록 함


def get_cache_key(request: CustomTravelRecommendationRequest) -> str:
    """요청 데이터를 기반으로 캐시 키 생성"""
    key_data = f"{request.region_code}:{request.days}:{request.who}:{','.join(sorted(request.styles))}:{request.schedule}"
    return hashlib.md5(key_data.encode()).hexdigest()


def clean_expired_cache():
    """만료된 캐시 항목 제거"""
    now = datetime.now()
    expired_keys = [
        key
        for key, value in recommendation_cache.items()
        if now - value["timestamp"] > CACHE_DURATION
    ]
    for key in expired_keys:
        del recommendation_cache[key]


@router.post("/recommendations", response_model=CustomTravelRecommendationResponse)
async def get_custom_travel_recommendations(
    request: CustomTravelRecommendationRequest,
    db: Session = Depends(get_db),
):
    """
    맞춤형 여행 일정 추천 API

    사용자가 선택한 지역, 기간, 동행자, 여행 스타일 등을 기반으로
    AI가 최적화된 여행 일정을 생성합니다.
    """
    try:
        # 캐시 확인
        clean_expired_cache()
        cache_key = get_cache_key(request)

        if cache_key in recommendation_cache:
            cached_data = recommendation_cache[cache_key]
            return CustomTravelRecommendationResponse(**cached_data["response"])
        # 동행자 유형별 태그 매핑
        who_tags = {
            "solo": ["혼자", "자유로운", "개인적인", "조용한"],
            "couple": ["연인", "로맨틱한", "분위기", "데이트"],
            "family": ["가족", "안전한", "교육적", "놀이공원", "체험"],
            "friends": ["친구들", "액티비티", "SNS", "핫플레이스"],
            "colleagues": ["동료", "회식", "편의시설", "교통편리"],
            "group": ["단체", "넓은", "주차편리", "대형"],
        }

        # 여행 스타일별 태그 매핑
        style_tags = {
            "activity": ["액티비티", "체험", "스포츠", "모험"],
            "hotplace": ["핫플레이스", "인기", "SNS", "트렌디"],
            "nature": ["자연", "경치", "산책", "힐링"],
            "landmark": ["랜드마크", "역사", "문화재", "박물관"],
            "healing": ["힐링", "휴식", "온천", "스파"],
            "culture": ["문화", "예술", "전시", "공연"],
            "local": ["로컬", "맛집", "재래시장", "전통"],
            "shopping": ["쇼핑", "면세점", "백화점", "아울렛"],
            "food": ["맛집", "카페", "디저트", "특산물"],
            "pet": ["반려동물", "펫카페", "공원", "동반가능"],
        }

        # 사용자 선택에 따른 태그 수집
        selected_tags = []
        if request.who in who_tags:
            selected_tags.extend(who_tags[request.who])

        for style in request.styles:
            if style in style_tags:
                selected_tags.extend(style_tags[style])
        
        # region_code 매핑 (프론트엔드 코드와 DB 코드 차이 해결)
        region_code_mapping = {
            "11": "1",    # 서울
            "26": "6",    # 부산
            "27": "4",    # 대구
            "28": "2",    # 인천
            "29": "5",    # 광주
            "30": "3",    # 대전
            "31": "7",    # 울산
            "36": "8",    # 세종
            "41": "31",   # 경기
            "43": "33",   # 충북
            "44": "34",   # 충남
            "46": "36",   # 전남
            "47": "35",   # 경북
            "48": "38",   # 경남
            "50": "39",   # 제주
            "51": "32",   # 강원
            "52": "37",   # 전북
        }
        
        # 실제 DB에서 사용할 region_code
        db_region_code = region_code_mapping.get(request.region_code, request.region_code)

        # 순차적 DB 쿼리 실행 (안정성 우선)
        import logging
        logger = logging.getLogger(__name__)
        
        try:
            # 관광지 조회
            attractions = (
                db.query(TouristAttraction)
                .filter(TouristAttraction.region_code == db_region_code)
                .limit(500)  # 성능 개선을 위해 제한
                .all()
            )
            logger.info(f"Found {len(attractions)} attractions")
            
            # 문화시설 조회
            cultural_facilities = (
                db.query(CulturalFacility)
                .filter(CulturalFacility.region_code == db_region_code)
                .limit(200)
                .all()
            )
            logger.info(f"Found {len(cultural_facilities)} cultural facilities")
            
            # 음식점 조회
            restaurants = (
                db.query(Restaurant)
                .filter(Restaurant.region_code == db_region_code)
                .limit(100)
                .all()
            )
            logger.info(f"Found {len(restaurants)} restaurants")
            
            # 쇼핑 장소 조회
            shopping_places = (
                db.query(Shopping)
                .filter(Shopping.region_code == db_region_code)
                .limit(300)
                .all()
            )
            logger.info(f"Found {len(shopping_places)} shopping places")
            
            # 숙박시설 조회
            accommodations = (
                db.query(Accommodation)
                .filter(Accommodation.region_code == db_region_code)
                .limit(50)
                .all()
            )
            logger.info(f"Found {len(accommodations)} accommodations")
            
        except Exception as e:
            logger.error(f"Database query error: {str(e)}")
            raise HTTPException(
                status_code=500, 
                detail=f"데이터베이스 조회 중 오류 발생: {str(e)}"
            )

        # 모든 장소를 하나의 리스트로 통합
        all_places = []

        # 디버그 정보를 파일에 기록
        with open("/tmp/custom_travel_debug.log", "a") as f:
            f.write("\n=== 새로운 요청 ===\n")
            f.write(f"원본 region_code: {request.region_code}, 변환된 region_code: {db_region_code}\n")
            f.write(
                f"DB 조회 결과: 관광지 {len(attractions)}개, 문화시설 {len(cultural_facilities)}개, 음식점 {len(restaurants)}개, 쇼핑 {len(shopping_places)}개, 숙박 {len(accommodations)}개\n"
            )
            f.write(f"요청 정보: {request.who}, {request.styles}\n")
            f.write(f"선택된 태그: {selected_tags}\n")

        # 관광지 추가
        for place in attractions:
            tags = ["관광지"]  # 기본 태그 추가
            if place.category_code:
                category_name = get_category_name(place.category_code, db)
                if category_name:
                    tags.append(category_name)
                else:
                    # 카테고리 이름을 찾지 못한 경우 코드를 그대로 추가
                    tags.append(place.category_code)
                    print(f"Category code {place.category_code} not converted, using raw code")
            if hasattr(place, "tags") and place.tags:
                tags.extend(place.tags)

            all_places.append(
                {
                    "id": place.content_id,
                    "name": place.attraction_name,
                    "type": "attraction",
                    "tags": tags,
                    "description": (
                        place.overview[:100]
                        if hasattr(place, "overview") and place.overview
                        else ""
                    ),
                    "rating": 4.2,  # 임시 평점
                    "image": (
                        place.first_image if hasattr(place, "first_image") else None
                    ),
                    "address": place.address,
                    "latitude": float(place.latitude) if place.latitude else None,
                    "longitude": float(place.longitude) if place.longitude else None,
                }
            )

        # 문화시설 추가
        for place in cultural_facilities:
            tags = ["문화", "전시"]
            if place.category_code:
                category_name = get_category_name(place.category_code, db)
                if category_name:
                    tags.append(category_name)
                else:
                    # 카테고리 이름을 찾지 못한 경우 코드를 그대로 추가
                    tags.append(place.category_code)

            all_places.append(
                {
                    "id": place.content_id,
                    "name": place.facility_name,
                    "type": "cultural",
                    "tags": tags,
                    "description": (
                        place.overview[:100]
                        if hasattr(place, "overview") and place.overview
                        else ""
                    ),
                    "rating": 4.0,
                    "image": (
                        place.first_image if hasattr(place, "first_image") else None
                    ),
                    "address": place.address,
                    "latitude": float(place.latitude) if place.latitude else None,
                    "longitude": float(place.longitude) if place.longitude else None,
                }
            )

        # 음식점 추가
        for place in restaurants:
            tags = ["맛집", "음식"]
            if place.cuisine_type:
                tags.append(place.cuisine_type)

            all_places.append(
                {
                    "id": place.content_id,
                    "name": place.restaurant_name,
                    "type": "restaurant",
                    "tags": tags,
                    "description": (
                        place.overview[:100]
                        if hasattr(place, "overview") and place.overview
                        else ""
                    ),
                    "rating": 4.1,
                    "image": (
                        place.first_image if hasattr(place, "first_image") else None
                    ),
                    "address": place.address,
                    "latitude": float(place.latitude) if place.latitude else None,
                    "longitude": float(place.longitude) if place.longitude else None,
                }
            )

        # 쇼핑 장소 추가
        for place in shopping_places:
            tags = ["쇼핑"]
            if place.category_code:
                category_name = get_category_name(place.category_code, db)
                if category_name:
                    tags.append(category_name)
                else:
                    # 카테고리 이름을 찾지 못한 경우 코드를 그대로 추가
                    tags.append(place.category_code)

            all_places.append(
                {
                    "id": place.content_id,
                    "name": place.shop_name,  # shopping_name이 아니라 shop_name
                    "type": "shopping",
                    "tags": tags,
                    "description": (
                        place.overview[:100]
                        if hasattr(place, "overview") and place.overview
                        else ""
                    ),
                    "rating": 3.9,
                    "image": (
                        place.first_image if hasattr(place, "first_image") else None
                    ),
                    "address": place.address,
                    "latitude": float(place.latitude) if place.latitude else None,
                    "longitude": float(place.longitude) if place.longitude else None,
                }
            )

        # 숙박시설 추가
        for place in accommodations:
            tags = ["숙박"]
            if place.category_code:
                category_name = get_category_name(place.category_code, db)
                if category_name:
                    tags.append(category_name)
                else:
                    # 카테고리 이름을 찾지 못한 경우 코드를 그대로 추가
                    tags.append(place.category_code)
            if hasattr(place, "accommodation_type") and place.accommodation_type:
                # 숙박 타입에 따른 태그 추가
                type_tags = {
                    "호텔": ["호텔", "비즈니스"],
                    "펜션": ["펜션", "가족", "자연"],
                    "게스트하우스": ["게스트하우스", "저렴한"],
                    "모텔": ["모텔", "편리한"],
                    "리조트": ["리조트", "럭셔리", "휴양"],
                }
                if place.accommodation_type in type_tags:
                    tags.extend(type_tags[place.accommodation_type])

            # 가격대 정보가 있으면 태그에 추가
            if hasattr(place, "price_range") and place.price_range:
                tags.append(place.price_range)

            all_places.append(
                {
                    "id": place.content_id,
                    "name": place.accommodation_name,
                    "type": "accommodation",
                    "tags": tags,
                    "description": (
                        place.overview[:100]
                        if hasattr(place, "overview") and place.overview
                        else ""
                    ),
                    "rating": 4.3,  # 임시 평점
                    "image": (
                        place.first_image if hasattr(place, "first_image") else None
                    ),
                    "address": place.address,
                    "latitude": float(place.latitude) if place.latitude else None,
                    "longitude": float(place.longitude) if place.longitude else None,
                    "accommodation_type": (
                        place.accommodation_type
                        if hasattr(place, "accommodation_type")
                        else None
                    ),
                    "price_range": (
                        place.price_range if hasattr(place, "price_range") else None
                    ),
                }
            )

        # 태그 매칭 점수 계산 (최적화)
        selected_tags_set = set(tag.lower() for tag in selected_tags)

        for place in all_places:
            score = 0
            place_tags_lower = [tag.lower() for tag in place["tags"]]
            place_tags_set = set(place_tags_lower)

            # 태그 매칭 최적화
            for selected_tag in selected_tags_set:
                for place_tag in place_tags_set:
                    if selected_tag in place_tag or place_tag in selected_tag:
                        score += 1
                        break  # 중복 점수 방지

            # 이름이나 설명에 태그가 포함된 경우 추가 점수
            if place["description"]:  # 설명이 있는 경우만 체크
                name_desc = (place["name"] + place["description"]).lower()
                for selected_tag in selected_tags_set:
                    if selected_tag in name_desc:
                        score += 0.5
                        break  # 첫 매칭에서 중단

            # 장소 타입별 보너스 점수 (다양성 확보)
            # 태그 매칭 점수가 0인 경우에도 최소한의 타입 보너스 부여
            type_bonus = {
                "attraction": 1.0,  # 관광지 우선
                "cultural": 0.8,  # 문화시설
                "shopping": 0.6,  # 쇼핑
                "restaurant": 0.5,  # 음식점
                "accommodation": 0.7,  # 숙박시설 (적당한 우선순위)
            }

            # 최종 점수: 태그 매칭 점수 + 타입 보너스
            # 태그 매칭이 없어도 타입 보너스로 포함될 수 있도록
            place["score"] = score + type_bonus.get(place["type"], 0)

            # 특정 스타일에 대한 추가 보너스
            if "shopping" in request.styles and place["type"] == "shopping":
                place["score"] += 2.0
            if "culture" in request.styles and place["type"] == "cultural":
                place["score"] += 2.0
            if "landmark" in request.styles and place["type"] in [
                "attraction",
                "cultural",
            ]:
                place["score"] += 1.0

        # 점수 기준으로 정렬
        all_places.sort(key=lambda x: x["score"], reverse=True)
        
        # 타입별로 최소한의 다양성을 보장하기 위해 재정렬
        # 각 타입별로 상위 N개씩 추출
        type_top_places = {
            "attraction": [],
            "cultural": [],
            "restaurant": [],
            "shopping": [],
            "accommodation": [],
        }
        
        for place in all_places:
            place_type = place.get("type")
            if place_type in type_top_places and len(type_top_places[place_type]) < 20:
                type_top_places[place_type].append(place)
        
        # 라운드 로빈 방식으로 다양한 타입 보장
        diversified_places = []
        max_per_type = max(len(places) for places in type_top_places.values())
        
        for i in range(max_per_type):
            for place_type in ["attraction", "cultural", "restaurant", "shopping", "accommodation"]:
                if i < len(type_top_places[place_type]):
                    diversified_places.append(type_top_places[place_type][i])
        
        # 나머지 장소들 추가
        remaining_places = [p for p in all_places if p not in diversified_places]
        all_places = diversified_places + remaining_places

        # 디버깅: 장소 타입별 개수 확인
        type_counts = {}
        for place in all_places[:50]:  # 상위 50개만 확인
            place_type = place.get("type", "unknown")
            type_counts[place_type] = type_counts.get(place_type, 0) + 1
        with open("/tmp/custom_travel_debug.log", "a") as f:
            f.write(f"장소 타입별 개수 (상위 50개): {type_counts}\n")
            f.write(f"전체 장소 수: {len(all_places)}\n")
            f.write("상위 10개 장소:\n")
            for i, place in enumerate(all_places[:10]):
                f.write(
                    f"  {i+1}. {place['name']} (타입: {place['type']}, 점수: {place['score']})\n"
                )

        # AI 추천 사용 여부 확인
        use_ai = False  # 임시로 AI 비활성화 (폴백 로직 사용)

        if use_ai:
            try:
                # AI 추천 서비스 사용
                ai_service = AIRecommendationService(db)
                days = await ai_service.generate_travel_itinerary(request, all_places)
            except Exception as e:
                print(f"AI 추천 실패, 폴백 사용: {str(e)}")
                # 폴백: 기존 로직 사용
                days = _generate_basic_itinerary(request, all_places)
        else:
            # 기존 로직 사용
            days = _generate_basic_itinerary(request, all_places)

        # 날씨 정보 가져오기 (AI 서비스가 사용된 경우 이미 포함됨)
        weather_summary = {
            "forecast": "대체로 맑음",
            "average_temperature": "15-22°C",
            "recommendation": "야외 활동하기 좋은 날씨입니다.",
        }

        # AI 추천이 사용된 경우 날씨 정보 업데이트
        if use_ai and days:
            # 각 날짜의 날씨 정보를 집계
            min_temp = 100
            max_temp = -100
            rain_days = 0

            for day in days:
                if day.weather and isinstance(day.weather, dict):
                    rain_prob = day.weather.get("rain_probability", 0)
                    if rain_prob > 60:
                        rain_days += 1

                    # 온도 범위 파싱
                    temp_range = day.weather.get("temperature", "15-22°C")
                    if "-" in temp_range:
                        temps = temp_range.replace("°C", "").split("-")
                        try:
                            min_temp = min(min_temp, int(temps[0]))
                            max_temp = max(max_temp, int(temps[1]))
                        except (ValueError, IndexError):
                            pass

            # 날씨 요약 업데이트
            if rain_days > 0:
                weather_summary["forecast"] = f"{rain_days}일간 비 예보"
                weather_summary["recommendation"] = (
                    "우산을 준비하세요. 실내 활동도 계획하세요."
                )
            else:
                weather_summary["forecast"] = "대체로 맑음"
                weather_summary["recommendation"] = "야외 활동하기 좋은 날씨입니다."

            if min_temp < 100 and max_temp > -100:
                weather_summary["average_temperature"] = f"{min_temp}-{max_temp}°C"

        # 응답 생성
        total_places = sum(len(day.places) for day in days)

        response = CustomTravelRecommendationResponse(
            days=days,
            weather_summary=weather_summary,
            total_places=total_places,
            recommendation_type="custom_ai" if use_ai else "custom_basic",
        )

        # 응답을 캐시에 저장
        recommendation_cache[cache_key] = {
            "response": response.dict(),
            "timestamp": datetime.now(),
        }

        return response

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}"
        ) from e


def _generate_basic_itinerary(
    request: CustomTravelRecommendationRequest, all_places: list
) -> list[DayItinerary]:
    """기본 태그 기반 일정 생성 (폴백용)"""

    places_per_day = 4 if request.schedule == "packed" else 3
    days = []
    used_places = set()

    # 숙박시설만 별도로 분리 (매일 사용될 수 있도록)
    accommodations = [p for p in all_places if p["type"] == "accommodation"]
    other_places = [p for p in all_places if p["type"] != "accommodation"]

    for day in range(1, request.days + 1):
        day_places = []

        # 시간대 설정 (숙박시설 포함)
        if request.schedule == "packed":
            time_slots = [
                "09:00-11:00",
                "11:30-13:30",
                "14:00-16:00",
                "16:30-18:30",
                "20:00-다음날",
            ]
        else:
            time_slots = ["10:00-12:00", "14:00-16:00", "17:00-19:00", "20:00-다음날"]

        # 시간대별로 장소 선택
        for i, time_slot in enumerate(time_slots):  # 모든 시간대 처리
            # 숙박 시간대는 따로 처리
            if time_slot == "20:00-다음날":
                # 마지막에 숙박시설 추가
                break

            # 점심시간대에는 음식점 우선
            if i == 1 or (i == 2 and request.schedule == "relaxed"):
                for place in other_places:
                    if place["type"] == "restaurant" and place["id"] not in used_places:
                        place_rec = PlaceRecommendation(
                            id=place["id"],
                            name=place["name"],
                            time=time_slot,
                            tags=place["tags"][:3],
                            description=place["description"],
                            rating=place["rating"],
                            image=place["image"],
                            address=place["address"],
                            latitude=place["latitude"],
                            longitude=place["longitude"],
                        )
                        day_places.append(place_rec)
                        used_places.add(place["id"])
                        break

                if len(day_places) > i:
                    continue

            # 일반 장소 선택 (타입 다양성 고려)
            # 이미 선택된 타입 확인
            selected_types = [p.tags[0] for p in day_places if p.tags]

            # 다른 타입 우선 선택
            for place in other_places:
                if (
                    place["id"] not in used_places
                    and place["score"] > 0
                    and place["type"] not in selected_types
                ):
                    place_rec = PlaceRecommendation(
                        id=place["id"],
                        name=place["name"],
                        time=time_slot,
                        tags=place["tags"][:3],
                        description=place["description"],
                        rating=place["rating"],
                        image=place["image"],
                        address=place["address"],
                        latitude=place["latitude"],
                        longitude=place["longitude"],
                    )
                    day_places.append(place_rec)
                    used_places.add(place["id"])
                    selected_types.append(place["type"])
                    break

            # 다른 타입이 없으면 점수 순으로 선택
            if len(day_places) <= i:
                for place in other_places:
                    if place["id"] not in used_places and place["score"] > 0:
                        place_rec = PlaceRecommendation(
                            id=place["id"],
                            name=place["name"],
                            time=time_slot,
                            tags=place["tags"][:3],
                            description=place["description"],
                            rating=place["rating"],
                            image=place["image"],
                            address=place["address"],
                            latitude=place["latitude"],
                            longitude=place["longitude"],
                        )
                        day_places.append(place_rec)
                        used_places.add(place["id"])
                        break

        # 장소가 부족한 경우 추가 (숙박 제외)
        # 숙박시설을 제외한 day_places 수 계산
        non_accommodation_places = [p for p in day_places if p.time != "20:00-다음날"]
        while len(non_accommodation_places) < places_per_day and len(used_places) < len(
            other_places
        ):
            for place in other_places:
                if place["id"] not in used_places:
                    # 숙박시설 시간대를 제외한 시간대 선택
                    time_slot_index = len(non_accommodation_places)
                    if (
                        time_slot_index < len(time_slots) - 1
                    ):  # 마지막(숙박) 시간대 제외
                        time_slot = time_slots[time_slot_index]
                    else:
                        time_slot = "19:00-21:00"
                    place_rec = PlaceRecommendation(
                        id=place["id"],
                        name=place["name"],
                        time=time_slot,
                        tags=place["tags"][:3],
                        description=place["description"],
                        rating=place["rating"],
                        image=place["image"],
                        address=place["address"],
                        latitude=place["latitude"],
                        longitude=place["longitude"],
                    )
                    day_places.append(place_rec)
                    used_places.add(place["id"])
                    non_accommodation_places.append(place_rec)
                    break

            if len(non_accommodation_places) >= places_per_day:
                break

        # 마지막에 숙박시설 추가
        if accommodations:
            # 가장 평점이 높은 숙박시설 선택 (중복 가능)
            best_accommodation = None
            for place in accommodations:
                if (
                    best_accommodation is None
                    or place["score"] > best_accommodation["score"]
                ):
                    best_accommodation = place

            if best_accommodation:
                place_rec = PlaceRecommendation(
                    id=best_accommodation["id"],
                    name=best_accommodation["name"],
                    time="20:00-다음날",
                    tags=best_accommodation["tags"][:3],
                    description=best_accommodation["description"],
                    rating=best_accommodation["rating"],
                    image=best_accommodation["image"],
                    address=best_accommodation["address"],
                    latitude=best_accommodation["latitude"],
                    longitude=best_accommodation["longitude"],
                )
                day_places.append(place_rec)

        day_itinerary = DayItinerary(
            day=day,
            places=day_places,
            weather={"status": "맑음", "temperature": "15-22°C"},
        )
        days.append(day_itinerary)

    return days
