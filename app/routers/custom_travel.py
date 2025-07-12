"""맞춤 여행 추천 라우터"""

import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    Accommodation,
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

        # 여행지 검색을 위한 기본 쿼리
        attractions = (
            db.query(TouristAttraction)
            .filter(TouristAttraction.region_code == request.region_code)
            .all()
        )

        cultural_facilities = (
            db.query(CulturalFacility)
            .filter(CulturalFacility.region_code == request.region_code)
            .all()
        )

        restaurants = (
            db.query(Restaurant)
            .filter(Restaurant.region_code == request.region_code)
            .limit(50)
            .all()
        )

        shopping_places = (
            db.query(Shopping).filter(Shopping.region_code == request.region_code).all()
        )

        # 숙박시설 조회 추가
        accommodations = (
            db.query(Accommodation)
            .filter(Accommodation.region_code == request.region_code)
            .limit(30)
            .all()
        )

        # 모든 장소를 하나의 리스트로 통합
        all_places = []

        # 디버그 정보를 파일에 기록
        with open("/tmp/custom_travel_debug.log", "a") as f:
            f.write("\n=== 새로운 요청 ===\n")
            f.write(
                f"DB 조회 결과: 관광지 {len(attractions)}개, 문화시설 {len(cultural_facilities)}개, 음식점 {len(restaurants)}개, 쇼핑 {len(shopping_places)}개, 숙박 {len(accommodations)}개\n"
            )
            f.write(f"요청 정보: {request.who}, {request.styles}\n")

        # 관광지 추가
        for place in attractions:
            tags = []
            if place.category_code:
                tags.append(place.category_code)
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

        # 태그 매칭 점수 계산
        for place in all_places:
            score = 0
            place_tags_lower = [tag.lower() for tag in place["tags"]]

            for selected_tag in selected_tags:
                for place_tag in place_tags_lower:
                    if selected_tag in place_tag or place_tag in selected_tag:
                        score += 1

            # 이름이나 설명에 태그가 포함된 경우 추가 점수
            name_desc = (place["name"] + place["description"]).lower()
            for selected_tag in selected_tags:
                if selected_tag in name_desc:
                    score += 0.5

            # 장소 타입별 보너스 점수 (다양성 확보)
            # 태그 매칭 점수가 0인 경우에도 최소한의 타입 보너스 부여
            type_bonus = {
                "attraction": 1.0,  # 관광지 우선
                "cultural": 0.8,  # 문화시설
                "shopping": 0.6,  # 쇼핑
                "restaurant": 0.3,  # 음식점 (점심시간에 자동 선택되므로 낮은 점수)
                "accommodation": 0.4,  # 숙박시설 (매일 필요하므로 적당한 점수)
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
        use_ai = os.getenv("OPENAI_API_KEY") and len(all_places) > 0

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

        return response

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}") from e


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
        while len(non_accommodation_places) < places_per_day and len(used_places) < len(other_places):
            for place in other_places:
                if place["id"] not in used_places:
                    # 숙박시설 시간대를 제외한 시간대 선택
                    time_slot_index = len(non_accommodation_places)
                    if time_slot_index < len(time_slots) - 1:  # 마지막(숙박) 시간대 제외
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
