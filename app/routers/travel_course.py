from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelCourse, TouristAttraction, Restaurant, Accommodation
from typing import Any, Dict, List
import json
from datetime import datetime, timedelta

router = APIRouter(prefix="/travel-courses", tags=["travel_courses"])

@router.get("/")
async def get_travel_courses(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(20, ge=1, le=100, description="페이지당 항목 수"),
    region_code: str | None = Query(None, description="지역 코드"),
    course_theme: str | None = Query(None, description="코스 테마"),
    db: Session = Depends(get_db),
):
    query = db.query(TravelCourse)
    if region_code:
        query = query.filter(TravelCourse.region_code == region_code)
    if course_theme:
        query = query.filter(TravelCourse.course_theme == course_theme)
    total = query.count()
    courses = query.offset((page-1)*page_size).limit(page_size).all()
    # SQLAlchemy 객체를 dict로 변환
    def course_to_dict(course: TravelCourse) -> dict[str, Any]:
        return {c.name: getattr(course, c.name) for c in course.__table__.columns}
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "courses": [course_to_dict(course) for course in courses]
    }

@router.get("/{course_id}")
async def get_travel_course_detail(
    course_id: str,
    db: Session = Depends(get_db),
):
    """여행 코스 상세 정보 조회 - 프론트엔드 하드코딩 데이터 구조와 호환"""

    try:
        # 기본 코스 정보 조회
        course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()

        if not course:
            # 데이터베이스에 해당 코스가 없는 경우 기본 데이터 반환
            return generate_default_course_data(course_id)

        # 해당 지역의 관광지, 맛집, 숙박 정보 조회
        attractions = db.query(TouristAttraction).filter(
            TouristAttraction.region_code == course.region_code
        ).limit(20).all()

        restaurants = db.query(Restaurant).filter(
            Restaurant.region_code == course.region_code
        ).limit(10).all()

        accommodations = db.query(Accommodation).filter(
            Accommodation.region_code == course.region_code
        ).limit(5).all()

        # 프론트엔드 호환 데이터 구조 생성
        course_data = generate_course_detail_data(course, attractions, restaurants, accommodations)

        return course_data

    except Exception as e:
        # 데이터베이스 오류 시 기본 데이터 반환
        print(f"Database error: {e}")
        return generate_default_course_data(course_id)

def generate_course_detail_data(course: TravelCourse, attractions: List[TouristAttraction],
                               restaurants: List[Restaurant], accommodations: List[Accommodation]) -> Dict[str, Any]:
    """하드코딩된 courseData 구조와 호환되는 데이터 생성"""

    # 기본 정보 설정
    course_data = {
        "id": course.content_id,
        "title": course.course_name,
        "subtitle": course.overview or f"{course.course_theme} 여행 코스",
        "region": course.region_code,
        "duration": course.required_time or "2박 3일",
        "theme": [course.course_theme] if course.course_theme else ["관광"],
        "mainImage": course.first_image or "default-image.jpg",
        "images": [course.first_image, course.first_image_small] if course.first_image else [],
        "rating": 4.5,  # 기본값
        "reviewCount": 100,  # 기본값
        "likeCount": 200,  # 기본값
        "viewCount": 1000,  # 기본값
        "price": "250,000원",  # 기본값
        "bestMonths": [3, 4, 5, 9, 10, 11],  # 기본값
        "summary": course.overview or "아름다운 여행 코스입니다.",
        "description": course.overview or "상세한 여행 코스 설명입니다.",
        "highlights": [attr.attraction_name for attr in attractions[:5]],
        "itinerary": generate_itinerary(attractions, restaurants, accommodations),
        "tips": [
            "편안한 신발을 착용하세요",
            "날씨를 확인하고 적절한 옷차림을 준비하세요",
            "현지 맛집을 미리 검색해보세요"
        ],
        "includes": [
            "주요 관광지 정보",
            "맛집 추천",
            "숙박 정보",
            "여행 가이드"
        ],
        "excludes": [
            "교통비",
            "식사비",
            "숙박비",
            "개인 경비"
        ],
        "tags": [course.course_theme, "실제데이터", "추천코스"] if course.course_theme else ["추천코스"]
    }

    return course_data

def generate_default_course_data(course_id: str) -> Dict[str, Any]:
    """코스 ID에 따라 다양한 지역의 기본 데이터 반환"""

    # 코스 ID를 숫자로 변환하여 지역 결정
    try:
        id_num = int(course_id)
        region_index = id_num % 6  # 6개 지역을 순환
    except:
        region_index = 0

    courses = [
        # 1. 제주도
        {
            "id": course_id,
            "title": "제주도 자연 힐링 여행 코스",
            "subtitle": "한라산부터 바다까지, 제주의 아름다운 자연을 만나보세요",
            "region": "제주도",
            "duration": "2박 3일",
            "theme": ["자연", "힐링", "관광"],
            "mainImage": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop"
            ],
            "highlights": ["한라산 국립공원", "성산일출봉", "우도", "애월 카페거리", "협재해수욕장"],
            "summary": "제주도의 대표적인 자연 명소들을 둘러보며 힐링할 수 있는 여행 코스입니다."
        },
        # 2. 서울
        {
            "id": course_id,
            "title": "서울 전통과 현대의 만남",
            "subtitle": "경복궁부터 강남까지, 서울의 과거와 현재를 체험하세요",
            "region": "서울",
            "duration": "2박 3일",
            "theme": ["문화", "역사", "도시탐방"],
            "mainImage": "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1540959733332-eab4deabeeaf?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1598212680973-2471c9becd79?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1553654685-78b84d7b9974?w=800&h=600&fit=crop"
            ],
            "highlights": ["경복궁", "북촌한옥마을", "명동", "홍대", "동대문"],
            "summary": "전통 궁궐부터 현대적인 쇼핑가까지, 서울의 다양한 매력을 만끽하는 코스입니다."
        },
        # 3. 부산
        {
            "id": course_id,
            "title": "부산 바다와 문화 여행",
            "subtitle": "해운대부터 감천문화마을까지, 부산의 바다와 문화를 즐기세요",
            "region": "부산",
            "duration": "2박 3일",
            "theme": ["해양", "문화", "맛집"],
            "mainImage": "https://images.unsplash.com/photo-1561022470-509098e4dd5e?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1561022470-509098e4dd5e?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1580656449195-2cb5d9b80a76?w=800&h=600&fit=crop"
            ],
            "highlights": ["해운대 해수욕장", "감천문화마을", "태종대", "광안리", "자갈치시장"],
            "summary": "푸른 바다와 알록달록한 문화마을, 신선한 해산물까지 부산의 모든 매력을 담은 코스입니다."
        },
        # 4. 경주
        {
            "id": course_id,
            "title": "경주 천년 고도 역사 탐방",
            "subtitle": "불국사부터 첨성대까지, 신라의 찬란한 역사를 만나보세요",
            "region": "경주",
            "duration": "2박 3일",
            "theme": ["역사", "문화", "유적"],
            "mainImage": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1504595403659-9088ce801e29?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=800&h=600&fit=crop"
            ],
            "highlights": ["불국사", "석굴암", "첨성대", "안압지", "대릉원"],
            "summary": "신라 천년의 역사가 살아 숨 쉬는 경주에서 우리나라의 찬란한 문화유산을 체험하는 코스입니다."
        },
        # 5. 강릉
        {
            "id": course_id,
            "title": "강릉 바다와 커피 여행",
            "subtitle": "경포대부터 안목해변까지, 강릉의 바다와 커피 문화를 즐기세요",
            "region": "강릉",
            "duration": "2박 3일",
            "theme": ["해양", "커피", "자연"],
            "mainImage": "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1484300681262-5ceb8242ea1c?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop"
            ],
            "highlights": ["경포대", "안목해변", "정동진", "오죽헌", "강릉커피거리"],
            "summary": "동해의 푸른 바다와 향긋한 커피 향이 어우러지는 강릉의 낭만적인 여행 코스입니다."
        },
        # 6. 여수
        {
            "id": course_id,
            "title": "여수 밤바다와 섬 여행",
            "subtitle": "오동도부터 향일암까지, 여수의 아름다운 바다를 만나보세요",
            "region": "여수",
            "duration": "2박 3일",
            "theme": ["해양", "섬", "야경"],
            "mainImage": "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop",
            "images": [
                "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop",
                "https://images.unsplash.com/photo-1587139223877-04cb899fa3e8?w=800&h=600&fit=crop"
            ],
            "highlights": ["오동도", "향일암", "여수 밤바다", "돌산대교", "만성리해수욕장"],
            "summary": "아름다운 밤바다와 신비로운 섬들이 어우러진 여수에서 로맨틱한 바다 여행을 즐기는 코스입니다."
        }
    ]

    base_course = courses[region_index]

    # 공통 필드 추가
    base_course.update({
        "rating": 4.5 + (region_index * 0.1),
        "reviewCount": 100 + (region_index * 20),
        "likeCount": 200 + (region_index * 50),
        "viewCount": 1000 + (region_index * 300),
        "price": f"{250 + (region_index * 50)},000원",
        "bestMonths": [3, 4, 5, 9, 10, 11],
        "description": f"{base_course['summary']} 이 코스는 {base_course['region']}의 대표적인 명소들을 효율적으로 둘러볼 수 있도록 구성되었습니다.",
        "itinerary": generate_region_itinerary(base_course['region'], base_course['highlights']),
        "tips": [
            "편안한 신발을 착용하세요",
            "날씨를 확인하고 적절한 옷차림을 준비하세요",
            "현지 맛집을 미리 검색해보세요",
            f"{base_course['region']} 특산품을 꼭 맛보세요"
        ],
        "includes": [
            "주요 관광지 정보",
            "맛집 추천",
            "숙박 정보",
            "여행 가이드북",
            "24시간 고객 지원"
        ],
        "excludes": [
            "교통비",
            "식사비",
            "숙박비",
            "개인 경비",
            "여행자 보험"
        ],
        "tags": base_course['theme'] + [base_course['region'], "추천코스"]
    })

    return base_course

def generate_itinerary(attractions: List[TouristAttraction], restaurants: List[Restaurant],
                      accommodations: List[Accommodation]) -> List[Dict[str, Any]]:
    """동적 일정 생성"""

    itinerary = []

    # 2박 3일 일정 생성 (예시)
    for day in range(1, 4):
        day_activities = []

        if day == 1:
            # 첫째 날: 도착 및 관광지 방문
            day_activities.extend([
                {
                    "time": "09:00",
                    "place": "출발지",
                    "description": "여행 시작",
                    "type": "transport",
                    "address": "",
                    "duration": 60
                }
            ])

            # 관광지 추가 (첫째 날)
            for i, attraction in enumerate(attractions[:3]):
                time_hour = 10 + i * 2
                day_activities.append({
                    "time": f"{time_hour:02d}:00",
                    "place": attraction.attraction_name,
                    "description": attraction.description or f"{attraction.attraction_name} 관광",
                    "type": "attraction",
                    "address": attraction.address or "",
                    "duration": 120
                })

            # 맛집 추가
            if restaurants:
                day_activities.append({
                    "time": "18:00",
                    "place": restaurants[0].restaurant_name,
                    "description": "저녁 식사",
                    "type": "restaurant",
                    "address": restaurants[0].address or "",
                    "duration": 60
                })

            # 숙박 추가
            if accommodations:
                day_activities.append({
                    "time": "20:00",
                    "place": accommodations[0].accommodation_name,
                    "description": "숙박",
                    "type": "accommodation",
                    "address": accommodations[0].address or "",
                    "duration": 600
                })

        elif day == 2:
            # 둘째 날: 더 많은 관광지 방문
            for i, attraction in enumerate(attractions[3:6]):
                time_hour = 9 + i * 2
                day_activities.append({
                    "time": f"{time_hour:02d}:00",
                    "place": attraction.attraction_name,
                    "description": attraction.description or f"{attraction.attraction_name} 관광",
                    "type": "attraction",
                    "address": attraction.address or "",
                    "duration": 120
                })

            # 점심 식사
            if len(restaurants) > 1:
                day_activities.append({
                    "time": "12:00",
                    "place": restaurants[1].restaurant_name,
                    "description": "점심 식사",
                    "type": "restaurant",
                    "address": restaurants[1].address or "",
                    "duration": 60
                })

        elif day == 3:
            # 셋째 날: 마무리 및 출발
            if len(attractions) > 6:
                day_activities.append({
                    "time": "09:00",
                    "place": attractions[6].attraction_name,
                    "description": "마지막 관광",
                    "type": "attraction",
                    "address": attractions[6].address or "",
                    "duration": 120
                })

            day_activities.append({
                "time": "14:00",
                "place": "출발지",
                "description": "여행 마무리 및 출발",
                "type": "transport",
                "address": "",
                "duration": 60
            })

        itinerary.append({
            "day": day,
            "title": f"Day {day}: {get_day_title(day)}",
            "activities": day_activities
        })

    return itinerary

def get_day_title(day: int) -> str:
    """일차별 제목 생성"""
    titles = {
        1: "여행 시작 및 주요 관광지 탐방",
        2: "문화 체험 및 자연 감상",
        3: "마무리 및 여행 정리"
    }
    return titles.get(day, f"{day}일차 여행")

def generate_region_itinerary(region: str, highlights: List[str]) -> List[Dict[str, Any]]:
    """지역별 맞춤 일정 생성"""

    itineraries = {
        "제주도": [
            {
                "day": 1,
                "title": "Day 1: 제주 도착 및 서부 지역 탐방",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "제주국제공항",
                        "description": "제주 도착 및 렌터카 인수",
                        "type": "transport",
                        "address": "제주특별자치도 제주시 공항로 2",
                        "duration": 60
                    },
                    {
                        "time": "11:00",
                        "place": "협재해수욕장",
                        "description": "제주 서부의 아름다운 해변 산책",
                        "type": "attraction",
                        "address": "제주특별자치도 제주시 한림읍 협재리",
                        "duration": 120
                    },
                    {
                        "time": "14:00",
                        "place": "애월 카페거리",
                        "description": "제주의 유명한 카페거리에서 점심 및 카페 투어",
                        "type": "cafe",
                        "address": "제주특별자치도 제주시 애월읍 애월해안로",
                        "duration": 180
                    }
                ]
            }
        ],
        "서울": [
            {
                "day": 1,
                "title": "Day 1: 전통 문화 체험",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "경복궁",
                        "description": "조선 왕조의 정궁에서 수문장 교대식 관람",
                        "type": "attraction",
                        "address": "서울특별시 종로구 사직로 161",
                        "duration": 120
                    },
                    {
                        "time": "11:30",
                        "place": "북촌한옥마을",
                        "description": "전통 한옥 마을 산책 및 사진 촬영",
                        "type": "attraction",
                        "address": "서울특별시 종로구 계동길 37",
                        "duration": 90
                    },
                    {
                        "time": "14:00",
                        "place": "인사동",
                        "description": "전통 찻집에서 점심 및 기념품 쇼핑",
                        "type": "restaurant",
                        "address": "서울특별시 종로구 인사동길",
                        "duration": 120
                    }
                ]
            }
        ],
        "부산": [
            {
                "day": 1,
                "title": "Day 1: 부산 바다와 문화 체험",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "해운대 해수욕장",
                        "description": "부산 대표 해수욕장에서 바다 산책",
                        "type": "attraction",
                        "address": "부산광역시 해운대구 우동",
                        "duration": 120
                    },
                    {
                        "time": "12:00",
                        "place": "감천문화마을",
                        "description": "알록달록한 마을 탐방 및 사진 촬영",
                        "type": "attraction",
                        "address": "부산광역시 사하구 감내2로 203",
                        "duration": 150
                    },
                    {
                        "time": "15:30",
                        "place": "자갈치시장",
                        "description": "신선한 해산물 시식 및 저녁 식사",
                        "type": "restaurant",
                        "address": "부산광역시 중구 자갈치해안로 52",
                        "duration": 120
                    }
                ]
            }
        ],
        "경주": [
            {
                "day": 1,
                "title": "Day 1: 신라 역사 탐방",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "불국사",
                        "description": "유네스코 세계문화유산 불국사 탐방",
                        "type": "attraction",
                        "address": "경상북도 경주시 진현동 15-1",
                        "duration": 120
                    },
                    {
                        "time": "12:00",
                        "place": "석굴암",
                        "description": "천년의 역사를 간직한 석굴암 방문",
                        "type": "attraction",
                        "address": "경상북도 경주시 진현동 999",
                        "duration": 90
                    },
                    {
                        "time": "15:00",
                        "place": "첨성대",
                        "description": "동양 최고의 천문관측대 견학",
                        "type": "attraction",
                        "address": "경상북도 경주시 인왕동",
                        "duration": 60
                    }
                ]
            }
        ],
        "강릉": [
            {
                "day": 1,
                "title": "Day 1: 강릉 바다와 커피",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "경포대",
                        "description": "강릉 대표 해변에서 바다 감상",
                        "type": "attraction",
                        "address": "강원도 강릉시 운정동",
                        "duration": 120
                    },
                    {
                        "time": "12:00",
                        "place": "안목해변 커피거리",
                        "description": "바다를 보며 즐기는 커피 타임",
                        "type": "cafe",
                        "address": "강원도 강릉시 견소동",
                        "duration": 150
                    },
                    {
                        "time": "15:30",
                        "place": "정동진",
                        "description": "세계에서 바다와 가장 가까운 기차역",
                        "type": "attraction",
                        "address": "강원도 강릉시 강동면 정동진리",
                        "duration": 120
                    }
                ]
            }
        ],
        "여수": [
            {
                "day": 1,
                "title": "Day 1: 여수 밤바다와 섬",
                "activities": [
                    {
                        "time": "09:00",
                        "place": "오동도",
                        "description": "동백꽃으로 유명한 아름다운 섬",
                        "type": "attraction",
                        "address": "전라남도 여수시 수정동",
                        "duration": 120
                    },
                    {
                        "time": "12:00",
                        "place": "향일암",
                        "description": "일출과 바다가 어우러진 명소",
                        "type": "attraction",
                        "address": "전라남도 여수시 돌산읍 율림리",
                        "duration": 90
                    },
                    {
                        "time": "19:00",
                        "place": "여수 밤바다",
                        "description": "아름다운 야경과 함께하는 저녁",
                        "type": "attraction",
                        "address": "전라남도 여수시 돌산로",
                        "duration": 120
                    }
                ]
            }
        ]
    }

    return itineraries.get(region, itineraries["제주도"])

@router.get("/regions/{region_code}/courses")
async def get_courses_by_region(
    region_code: str,
    limit: int = Query(10, ge=1, le=50, description="결과 개수"),
    db: Session = Depends(get_db),
):
    """지역별 여행 코스 목록 조회"""

    courses = db.query(TravelCourse).filter(
        TravelCourse.region_code == region_code
    ).limit(limit).all()

    course_list = []
    for course in courses:
        course_list.append({
            "id": course.content_id,
            "title": course.course_name,
            "theme": course.course_theme,
            "duration": course.required_time,
            "difficulty": course.difficulty_level,
            "distance": course.course_distance,
            "overview": course.overview,
            "image": course.first_image,
            "region_code": course.region_code
        })

    return {
        "region_code": region_code,
        "courses": course_list,
        "total": len(course_list)
    }
