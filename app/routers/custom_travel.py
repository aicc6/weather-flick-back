"""맞춤 여행 추천 라우터"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models import (
    CustomTravelRecommendationRequest,
    CustomTravelRecommendationResponse,
    PlaceRecommendation,
    DayItinerary,
    TouristAttraction,
    CulturalFacility,
    Restaurant,
    Shopping,
)

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
            "group": ["단체", "넓은", "주차편리", "대형"]
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
            "pet": ["반려동물", "펫카페", "공원", "동반가능"]
        }
        
        # 사용자 선택에 따른 태그 수집
        selected_tags = []
        if request.who in who_tags:
            selected_tags.extend(who_tags[request.who])
        
        for style in request.styles:
            if style in style_tags:
                selected_tags.extend(style_tags[style])
        
        # 여행지 검색을 위한 기본 쿼리
        attractions = db.query(TouristAttraction).filter(
            TouristAttraction.region_code == request.region_code
        ).all()
        
        cultural_facilities = db.query(CulturalFacility).filter(
            CulturalFacility.region_code == request.region_code
        ).all()
        
        restaurants = db.query(Restaurant).filter(
            Restaurant.region_code == request.region_code
        ).limit(50).all()
        
        shopping_places = db.query(Shopping).filter(
            Shopping.region_code == request.region_code
        ).all()
        
        # 모든 장소를 하나의 리스트로 통합
        all_places = []
        
        # 관광지 추가
        for place in attractions:
            tags = []
            if place.category_code:
                tags.append(place.category_code)
            if hasattr(place, 'tags') and place.tags:
                tags.extend(place.tags)
            
            all_places.append({
                'id': place.content_id,
                'name': place.attraction_name,
                'type': 'attraction',
                'tags': tags,
                'description': place.overview[:100] if hasattr(place, 'overview') and place.overview else "",
                'rating': 4.2,  # 임시 평점
                'image': place.first_image if hasattr(place, 'first_image') else None,
                'address': place.address,
                'latitude': float(place.latitude) if place.latitude else None,
                'longitude': float(place.longitude) if place.longitude else None
            })
        
        # 문화시설 추가
        for place in cultural_facilities:
            tags = ["문화", "전시"]
            if place.category_code:
                tags.append(place.category_code)
                
            all_places.append({
                'id': place.content_id,
                'name': place.facility_name,
                'type': 'cultural',
                'tags': tags,
                'description': place.overview[:100] if hasattr(place, 'overview') and place.overview else "",
                'rating': 4.0,
                'image': place.first_image if hasattr(place, 'first_image') else None,
                'address': place.address,
                'latitude': float(place.latitude) if place.latitude else None,
                'longitude': float(place.longitude) if place.longitude else None
            })
        
        # 음식점 추가
        for place in restaurants:
            tags = ["맛집", "음식"]
            if place.cuisine_type:
                tags.append(place.cuisine_type)
                
            all_places.append({
                'id': place.content_id,
                'name': place.restaurant_name,
                'type': 'restaurant',
                'tags': tags,
                'description': place.overview[:100] if hasattr(place, 'overview') and place.overview else "",
                'rating': 4.1,
                'image': place.first_image if hasattr(place, 'first_image') else None,
                'address': place.address,
                'latitude': float(place.latitude) if place.latitude else None,
                'longitude': float(place.longitude) if place.longitude else None
            })
        
        # 쇼핑 장소 추가
        for place in shopping_places:
            tags = ["쇼핑"]
            if place.category_code:
                tags.append(place.category_code)
                
            all_places.append({
                'id': place.content_id,
                'name': place.shop_name,  # shopping_name이 아니라 shop_name
                'type': 'shopping',
                'tags': tags,
                'description': place.overview[:100] if hasattr(place, 'overview') and place.overview else "",
                'rating': 3.9,
                'image': place.first_image if hasattr(place, 'first_image') else None,
                'address': place.address,
                'latitude': float(place.latitude) if place.latitude else None,
                'longitude': float(place.longitude) if place.longitude else None
            })
        
        # 태그 매칭 점수 계산
        for place in all_places:
            score = 0
            place_tags_lower = [tag.lower() for tag in place['tags']]
            
            for selected_tag in selected_tags:
                for place_tag in place_tags_lower:
                    if selected_tag in place_tag or place_tag in selected_tag:
                        score += 1
            
            # 이름이나 설명에 태그가 포함된 경우 추가 점수
            name_desc = (place['name'] + place['description']).lower()
            for selected_tag in selected_tags:
                if selected_tag in name_desc:
                    score += 0.5
                    
            place['score'] = score
        
        # 점수 기준으로 정렬
        all_places.sort(key=lambda x: x['score'], reverse=True)
        
        # 일정 유형에 따른 하루 장소 수 결정
        places_per_day = 4 if request.schedule == "packed" else 3
        
        # 일별 일정 생성
        days = []
        used_places = set()
        
        for day in range(1, request.days + 1):
            day_places = []
            place_count = 0
            
            # 시간대 설정
            if request.schedule == "packed":
                time_slots = ["09:00-11:00", "11:30-13:30", "14:00-16:00", "16:30-18:30"]
            else:
                time_slots = ["10:00-12:00", "14:00-16:00", "17:00-19:00"]
            
            # 아침/점심/저녁 시간대별로 적절한 장소 선택
            for i, time_slot in enumerate(time_slots[:places_per_day]):
                # 점심시간대에는 음식점 우선
                if i == 1 or (i == 2 and request.schedule == "relaxed"):
                    restaurant_found = False
                    for place in all_places:
                        if place['type'] == 'restaurant' and place['id'] not in used_places:
                            place_rec = PlaceRecommendation(
                                id=place['id'],
                                name=place['name'],
                                time=time_slot,
                                tags=place['tags'][:3],
                                description=place['description'],
                                rating=place['rating'],
                                image=place['image'],
                                address=place['address'],
                                latitude=place['latitude'],
                                longitude=place['longitude']
                            )
                            day_places.append(place_rec)
                            used_places.add(place['id'])
                            restaurant_found = True
                            break
                    
                    if restaurant_found:
                        continue
                
                # 일반 장소 선택
                for place in all_places:
                    if place['id'] not in used_places and place['score'] > 0:
                        place_rec = PlaceRecommendation(
                            id=place['id'],
                            name=place['name'],
                            time=time_slot,
                            tags=place['tags'][:3],
                            description=place['description'],
                            rating=place['rating'],
                            image=place['image'],
                            address=place['address'],
                            latitude=place['latitude'],
                            longitude=place['longitude']
                        )
                        day_places.append(place_rec)
                        used_places.add(place['id'])
                        break
            
            # 장소가 부족한 경우 점수 상관없이 추가
            while len(day_places) < places_per_day and len(used_places) < len(all_places):
                for place in all_places:
                    if place['id'] not in used_places:
                        time_slot = time_slots[len(day_places)] if len(day_places) < len(time_slots) else "19:00-21:00"
                        place_rec = PlaceRecommendation(
                            id=place['id'],
                            name=place['name'],
                            time=time_slot,
                            tags=place['tags'][:3],
                            description=place['description'],
                            rating=place['rating'],
                            image=place['image'],
                            address=place['address'],
                            latitude=place['latitude'],
                            longitude=place['longitude']
                        )
                        day_places.append(place_rec)
                        used_places.add(place['id'])
                        break
                
                if len(day_places) >= places_per_day:
                    break
            
            day_itinerary = DayItinerary(
                day=day,
                places=day_places,
                weather={"status": "맑음", "temperature": "15-22°C"}  # 임시 날씨 정보
            )
            days.append(day_itinerary)
        
        # 응답 생성
        total_places = sum(len(day.places) for day in days)
        
        response = CustomTravelRecommendationResponse(
            days=days,
            weather_summary={
                "forecast": "대체로 맑음",
                "average_temperature": "15-22°C",
                "recommendation": "야외 활동하기 좋은 날씨입니다."
            },
            total_places=total_places,
            recommendation_type="custom_ai"
        )
        
        return response
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"추천 생성 중 오류 발생: {str(e)}")