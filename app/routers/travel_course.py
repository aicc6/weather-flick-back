from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Accommodation, Restaurant, TouristAttraction, TravelCourse

router = APIRouter(prefix="/travel-courses", tags=["travel_courses"])

@router.get("/")
async def get_travel_courses(
    page: int = Query(1, ge=1, description="페이지 번호"),
    page_size: int = Query(5, ge=1, le=50, description="페이지당 항목 수"),
    region_code: str | None = Query(None, description="지역 코드"),
    course_theme: str | None = Query(None, description="코스 테마"),
    group_by: str | None = Query(None, description="그룹화 기준 (region, theme)"),
    db: Session = Depends(get_db),
):
    # 데이터베이스에서 여행 코스 조회
    courses = []
    total = 0

    try:
        query = db.query(TravelCourse)
        if region_code:
            query = query.filter(TravelCourse.region_code == region_code)
        if course_theme:
            query = query.filter(TravelCourse.course_theme == course_theme)
        total = query.count()
        courses = query.offset((page-1)*page_size).limit(page_size).all()
    except Exception as e:
        print(f"Database query error: {e}")
        # 데이터베이스 오류 시 기본 데이터 생성으로 진행
        courses = []
        total = 0

    # 데이터베이스에 데이터가 없는 경우 기본 데이터 생성
    if not courses:
        # 더 많은 여행 코스 데이터 생성
        total_courses = 150  # 총 150개의 코스
        start_idx = (page - 1) * page_size + 1
        end_idx = min(start_idx + page_size - 1, total_courses)

        sample_courses = []
        for i in range(start_idx, end_idx + 1):
            sample_courses.append(generate_default_course_data(str(i)))

        # 지역별 그룹화
        if group_by == "region":
            return group_courses_by_region(sample_courses, total_courses, page, page_size)

        # 테마별 그룹화
        elif group_by == "theme":
            return group_courses_by_theme(sample_courses, total_courses, page, page_size)

        return {
            "total": total_courses,
            "page": page,
            "page_size": page_size,
            "courses": sample_courses,
            "has_more": end_idx < total_courses
        }

    # SQLAlchemy 객체를 dict로 변환
    def course_to_dict(course: TravelCourse) -> dict[str, Any]:
        return {c.name: getattr(course, c.name) for c in course.__table__.columns}

    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "courses": [course_to_dict(course) for course in courses],
        "has_more": (page * page_size) < total
    }

# Moved the /{course_id} route to the end of the file to prevent route conflicts

def generate_course_detail_data(course: TravelCourse, attractions: list[TouristAttraction],
                               _restaurants: list[Restaurant], _accommodations: list[Accommodation]) -> dict[str, Any]:
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
        "itinerary": generate_region_itinerary(course.region_code, [attr.attraction_name for attr in attractions[:5]]),
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

def generate_default_course_data(course_id: str) -> dict[str, Any]:
    """코스 ID에 따라 다양한 지역의 기본 데이터 반환"""

    # 코스 ID를 숫자로 변환하여 지역 결정 (1부터 시작하므로 -1)
    try:
        id_num = int(course_id)
        region_index = (id_num - 1) % 18  # 18개 지역으로 확장
    except ValueError:
        region_index = 0

    courses = [
        # 1. 제주도
        {
            "id": course_id,
            "title": "제주도 자연 힐링 여행 코스",
            "subtitle": "한라산부터 바다까지, 제주의 아름다운 자연을 만나보세요",
            "region": "jeju",
            "regionName": "제주도",
            "duration": "2박 3일",
            "theme": ["자연", "힐링", "관광"],
            "mainImage": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["한라산 국립공원", "성산일출봉", "우도", "애월 카페거리", "협재해수욕장"],
            "summary": "제주도의 대표적인 자연 명소들을 둘러보며 힐링할 수 있는 여행 코스입니다."
        },
        # 2. 전주
        {
            "id": course_id,
            "title": "전주 한옥마을 감성 여행",
            "subtitle": "한옥마을부터 비빔밥까지, 전주의 멋과 맛을 느껴보세요",
            "region": "jeonju",
            "regionName": "전주",
            "duration": "2박 3일",
            "theme": ["문화", "역사", "맛집"],
            "mainImage": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1464983953574-0892a716854b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["전주한옥마을", "경기전", "전동성당", "남부시장", "전주비빔밥"],
            "summary": "전통 한옥의 정취와 전주만의 맛을 모두 즐길 수 있는 감성 여행 코스입니다."
        },
        # 3. 부산
        {
            "id": course_id,
            "title": "부산 바다와 문화 여행",
            "subtitle": "해운대부터 감천문화마을까지, 부산의 바다와 문화를 즐기세요",
            "region": "busan",
            "regionName": "부산",
            "duration": "2박 3일",
            "theme": ["해양", "문화", "맛집"],
            "mainImage": "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1580656449195-2cb5d9b80a76?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["해운대 해수욕장", "감천문화마을", "태종대", "광안리", "자갈치시장"],
            "summary": "푸른 바다와 알록달록한 문화마을, 신선한 해산물까지 부산의 모든 매력을 담은 코스입니다."
        },
        # 4. 경주
        {
            "id": course_id,
            "title": "경주 천년 고도 역사 탐방",
            "subtitle": "불국사부터 첨성대까지, 신라의 찬란한 역사를 만나보세요",
            "region": "gyeongju",
            "regionName": "경주",
            "duration": "2박 3일",
            "theme": ["역사", "문화", "유적"],
            "mainImage": "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1504595403659-9088ce801e29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["불국사", "석굴암", "첨성대", "안압지", "대릉원"],
            "summary": "신라 천년의 역사가 살아 숨 쉬는 경주에서 우리나라의 찬란한 문화유산을 체험하는 코스입니다."
        },
        # 5. 강릉
        {
            "id": course_id,
            "title": "강릉 바다와 커피 여행",
            "subtitle": "경포대부터 안목해변까지, 강릉의 바다와 커피 문화를 즐기세요",
            "region": "gangneung",
            "regionName": "강릉",
            "duration": "2박 3일",
            "theme": ["해양", "커피", "자연"],
            "mainImage": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1484300681262-5ceb8242ea1c?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["경포대", "안목해변", "정동진", "오죽헌", "강릉커피거리"],
            "summary": "동해의 푸른 바다와 향긋한 커피 향이 어우러지는 강릉의 낭만적인 여행 코스입니다."
        },
        # 6. 여수
        {
            "id": course_id,
            "title": "여수 밤바다와 섬 여행",
            "subtitle": "오동도부터 향일암까지, 여수의 아름다운 바다를 만나보세요",
            "region": "yeosu",
            "regionName": "여수",
            "duration": "2박 3일",
            "theme": ["해양", "섬", "야경"],
            "mainImage": "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1587139223877-04cb899fa3e8?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["오동도", "향일암", "여수 밤바다", "돌산대교", "만성리해수욕장"],
            "summary": "아름다운 밤바다와 신비로운 섬들이 어우러진 여수에서 로맨틱한 바다 여행을 즐기는 코스입니다."
        },
        # 7. 인천
        {
            "id": course_id,
            "title": "인천 차이나타운과 송도 여행",
            "subtitle": "차이나타운부터 송도까지, 인천의 과거와 미래를 만나보세요",
            "region": "incheon",
            "regionName": "인천",
            "duration": "1박 2일",
            "theme": ["문화", "도시", "역사"],
            "mainImage": "https://images.unsplash.com/photo-1519640760746-95d1211e9c4e?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1519640760746-95d1211e9c4e?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1555400080-9893e0e4e10b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["차이나타운", "송도센트럴파크", "인천대교", "월미도", "자유공원"],
            "summary": "인천의 역사적 차이나타운과 현대적인 송도신도시를 함께 즐기는 코스입니다."
        },
        # 8. 대구
        {
            "id": course_id,
            "title": "대구 동성로와 팔공산 여행",
            "subtitle": "도심의 활력부터 산의 정취까지, 대구의 매력을 만끽하세요",
            "region": "daegu",
            "regionName": "대구",
            "duration": "1박 2일",
            "theme": ["도시", "자연", "쇼핑"],
            "mainImage": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["동성로", "팔공산", "서문시장", "국채보상운동기념공원", "대구타워"],
            "summary": "대구의 번화한 도심과 아름다운 자연을 함께 즐길 수 있는 코스입니다."
        },
        # 9. 광주
        {
            "id": course_id,
            "title": "광주 무등산과 국립아시아문화전당",
            "subtitle": "문화의 도시 광주에서 예술과 자연을 만나보세요",
            "region": "gwangju",
            "regionName": "광주",
            "duration": "1박 2일",
            "theme": ["문화", "자연", "예술"],
            "mainImage": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1464983953574-0892a716854b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["무등산", "국립아시아문화전당", "양림동", "충장로", "518기념공원"],
            "summary": "광주의 풍부한 문화유산과 아름다운 자연을 함께 체험하는 코스입니다."
        },
        # 10. 대전
        {
            "id": course_id,
            "title": "대전 엑스포공원과 유성온천",
            "subtitle": "과학과 휴양을 동시에 즐기는 대전 여행",
            "region": "daejeon",
            "regionName": "대전",
            "duration": "1박 2일",
            "theme": ["과학", "휴양", "온천"],
            "mainImage": "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1580656449195-2cb5d9b80a76?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["엑스포공원", "유성온천", "국립중앙과학관", "대전오월드", "한빛탑"],
            "summary": "대전의 과학기술과 온천 휴양을 함께 즐길 수 있는 코스입니다."
        },
        # 11. 울산
        {
            "id": course_id,
            "title": "울산 간절곶과 대왕암공원",
            "subtitle": "동해의 일출과 바다를 만끽하는 울산 여행",
            "region": "ulsan",
            "regionName": "울산",
            "duration": "1박 2일",
            "theme": ["바다", "일출", "자연"],
            "mainImage": "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1504595403659-9088ce801e29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["간절곶", "대왕암공원", "태화강", "울산대공원", "반구대암각화"],
            "summary": "울산의 아름다운 동해안과 일출 명소를 둘러보는 코스입니다."
        },
        # 12. 세종
        {
            "id": course_id,
            "title": "세종 호수공원과 정부세종청사",
            "subtitle": "대한민국의 행정수도 세종의 현재와 미래를 만나보세요",
            "region": "sejong",
            "regionName": "세종",
            "duration": "당일",
            "theme": ["도시", "공원", "행정"],
            "mainImage": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1484300681262-5ceb8242ea1c?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["호수공원", "정부세종청사", "세종호수공원", "베어트리파크", "세종문화예술회관"],
            "summary": "대한민국 행정수도의 현대적 면모와 아름다운 공원을 즐기는 코스입니다."
        },
        # 13. 수원 (경기)
        {
            "id": course_id,
            "title": "수원 화성과 행궁 역사 탐방",
            "subtitle": "조선시대 계획도시 수원의 역사를 따라 걷는 여행",
            "region": "gyeonggi",
            "regionName": "경기",
            "duration": "당일",
            "theme": ["역사", "문화", "유적"],
            "mainImage": "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1551918120-9739cb430c6d?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1587139223877-04cb899fa3e8?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["화성", "화성행궁", "수원화성박물관", "연무대", "방화수류정"],
            "summary": "유네스코 세계문화유산 수원 화성의 역사와 문화를 체험하는 코스입니다."
        },
        # 14. 춘천 (강원)
        {
            "id": course_id,
            "title": "춘천 남이섬과 소양강 레저",
            "subtitle": "낭만의 도시 춘천에서 자연과 레저를 즐기세요",
            "region": "gangwon",
            "regionName": "강원",
            "duration": "1박 2일",
            "theme": ["자연", "레저", "낭만"],
            "mainImage": "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1578662996442-48f60103fc96?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1544551763-46a013bb70d5?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["남이섬", "소양강", "춘천 닭갈비", "김유정문학촌", "애니메이션박물관"],
            "summary": "춘천의 아름다운 자연과 특색 있는 문화를 체험하는 코스입니다."
        },
        # 15. 청주 (충북)
        {
            "id": course_id,
            "title": "청주 직지와 상당산성 문화여행",
            "subtitle": "인쇄문화의 발상지 청주에서 역사와 문화를 만나보세요",
            "region": "chungbuk",
            "regionName": "충북",
            "duration": "1박 2일",
            "theme": ["문화", "역사", "전통"],
            "mainImage": "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506744038136-46273834b3fb?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1464983953574-0892a716854b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1501594907352-04cda38ebc29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["직지심체요절", "상당산성", "청주향교", "용두사지철당간", "청주 고인쇄박물관"],
            "summary": "세계 최초 금속활자본 직지의 고향 청주의 문화유산을 탐방하는 코스입니다."
        },
        # 16. 공주 (충남)
        {
            "id": course_id,
            "title": "공주 백제 역사유적지 탐방",
            "subtitle": "고대 백제의 수도 공주에서 찬란한 역사를 만나보세요",
            "region": "chungnam",
            "regionName": "충남",
            "duration": "1박 2일",
            "theme": ["역사", "문화", "유적"],
            "mainImage": "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1536431311719-398b6704d4cc?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1584646098378-0874589d76b1?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1580656449195-2cb5d9b80a76?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["공산성", "무령왕릉", "국립공주박물관", "공주 한옥마을", "금강"],
            "summary": "유네스코 세계문화유산 백제역사유적지구의 공주에서 고대사를 체험하는 코스입니다."
        },
        # 17. 군산 (전북)
        {
            "id": course_id,
            "title": "군산 시간여행과 근대문화유산",
            "subtitle": "일제강점기 아픈 역사부터 현재까지, 군산의 시간여행",
            "region": "jeonbuk",
            "regionName": "전북",
            "duration": "1박 2일",
            "theme": ["근대사", "문화", "역사"],
            "mainImage": "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1509909756405-be0199881695?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1504595403659-9088ce801e29?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1581833971358-2c8b550f87b3?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["군산 근대역사박물관", "군산 구 일본 제18은행", "신흥동 일본식 가옥", "군산 내항", "선유도"],
            "summary": "군산의 근대문화유산과 아름다운 섬을 함께 즐기는 역사문화 코스입니다."
        },
        # 18. 목포 (전남)
        {
            "id": course_id,
            "title": "목포 유달산과 다도해 섬여행",
            "subtitle": "서남해의 관문 목포에서 바다와 섬의 정취를 만끽하세요",
            "region": "jeonnam",
            "regionName": "전남",
            "duration": "2박 3일",
            "theme": ["바다", "섬", "자연"],
            "mainImage": "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
            "images": [
                "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1484300681262-5ceb8242ea1c?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3",
                "https://images.unsplash.com/photo-1571019613454-1cb2f99b2d8b?w=800&h=600&fit=crop&auto=format&q=80&ixlib=rb-4.0.3"
            ],
            "highlights": ["유달산", "홍도", "흑산도", "목포 근대역사관", "국립해양문화재연구소"],
            "summary": "목포의 상징인 유달산과 다도해의 아름다운 섬들을 탐방하는 코스입니다."
        }
    ]

    base_course = courses[region_index]

    # 공통 필드 추가
    # regionName, highlights, theme이 항상 str이 아닌 list[str]임을 보장
    if isinstance(base_course.get('theme'), str):
        base_course['theme'] = [base_course['theme']]
    if isinstance(base_course.get('highlights'), str):
        base_course['highlights'] = [base_course['highlights']]
    if not isinstance(base_course.get('regionName'), str):
        base_course['regionName'] = str(base_course.get('regionName', ''))

    base_course.update({
        "rating": 4.5 + (region_index * 0.1),
        "reviewCount": 100 + (region_index * 20),
        "likeCount": 200 + (region_index * 50),
        "viewCount": 1000 + (region_index * 300),
        "price": f"{250 + (region_index * 50)},000원",
        "bestMonths": [3, 4, 5, 9, 10, 11],
        "description": f"{base_course['summary']} 이 코스는 {base_course['regionName']}의 대표적인 명소들을 효율적으로 둘러볼 수 있도록 구성되었습니다.",
        "itinerary": generate_region_itinerary(base_course['regionName'], base_course['highlights']),
        "tips": [
            "편안한 신발을 착용하세요",
            "날씨를 확인하고 적절한 옷차림을 준비하세요",
            "현지 맛집을 미리 검색해보세요",
            f"{base_course['regionName']} 특산품을 꼭 맛보세요"
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
        "tags": list(base_course['theme']) + [base_course['regionName'], "추천코스"]
    })

    return base_course


def generate_region_itinerary(region: str, highlights: list[str]) -> list[dict[str, Any]]:
    """지역별 맞춤 일정 생성"""

    # 기본 2박 3일 일정 생성
    itinerary = []

    for day in range(1, 4):
        activities = []

        if day == 1:
            activities.append({
                "time": "09:00",
                "place": f"{region} 도착",
                "description": "여행 시작 및 숙소 체크인",
                "type": "transport",
                "address": f"{region} 중심가",
                "duration": 60
            })

            if len(highlights) > 0:
                activities.append({
                    "time": "11:00",
                    "place": highlights[0],
                    "description": f"{highlights[0]} 관광 및 둘러보기",
                    "type": "attraction",
                    "address": f"{region} {highlights[0]}",
                    "duration": 120
                })

            activities.append({
                "time": "18:00",
                "place": f"{region} 맛집",
                "description": "지역 특산물 저녁 식사",
                "type": "restaurant",
                "address": f"{region} 중심가",
                "duration": 90
            })

        elif day == 2:
            for i, highlight in enumerate(highlights[1:3]):
                time_hour = 9 + i * 3
                activities.append({
                    "time": f"{time_hour:02d}:00",
                    "place": highlight,
                    "description": f"{highlight} 관광",
                    "type": "attraction",
                    "address": f"{region} {highlight}",
                    "duration": 150
                })

        elif day == 3:
            if len(highlights) > 3:
                activities.append({
                    "time": "09:00",
                    "place": highlights[3],
                    "description": "마지막 관광 및 기념품 쇼핑",
                    "type": "attraction",
                    "address": f"{region} {highlights[3]}",
                    "duration": 120
                })

            activities.append({
                "time": "14:00",
                "place": "출발지",
                "description": "여행 마무리 및 출발",
                "type": "transport",
                "address": "-",
                "duration": 60
            })

        itinerary.append({
            "day": day,
            "title": f"Day {day}: {get_day_title(day)}",
            "activities": activities
        })

    return itinerary

def get_day_title(day: int) -> str:
    """일차별 제목 생성"""
    titles = {
        1: "도착 및 주요 관광지 탐방",
        2: "문화 체험 및 자연 감상",
        3: "마무리 및 출발"
    }
    return titles.get(day, f"{day}일차 여행")


def group_courses_by_region(courses: list[dict[str, Any]], total_courses: int, page: int, page_size: int) -> dict[str, Any]:
    """지역별로 여행 코스를 그룹화"""
    region_groups = {}

    for course in courses:
        region = course.get("regionName", "기타")
        if region not in region_groups:
            region_groups[region] = []
        region_groups[region].append(course)

    # 지역별 그룹 정렬
    sorted_regions = sorted(region_groups.keys())

    grouped_data = []
    for region in sorted_regions:
        grouped_data.append({
            "region": region,
            "courses": region_groups[region],
            "count": len(region_groups[region])
        })

    return {
        "total": total_courses,
        "page": page,
        "page_size": page_size,
        "group_by": "region",
        "groups": grouped_data,
        "has_more": (page * page_size) < total_courses
    }


def group_courses_by_theme(courses: list[dict[str, Any]], total_courses: int, page: int, page_size: int) -> dict[str, Any]:
    """테마별로 여행 코스를 그룹화"""
    theme_groups = {}

    for course in courses:
        themes = course.get("theme", ["기타"])
        if not isinstance(themes, list):
            themes = [themes]

        for theme in themes:
            if theme not in theme_groups:
                theme_groups[theme] = []
            theme_groups[theme].append(course)

    # 테마별 그룹 정렬
    sorted_themes = sorted(theme_groups.keys())

    grouped_data = []
    for theme in sorted_themes:
        grouped_data.append({
            "theme": theme,
            "courses": theme_groups[theme],
            "count": len(theme_groups[theme])
        })

    return {
        "total": total_courses,
        "page": page,
        "page_size": page_size,
        "group_by": "theme",
        "groups": grouped_data,
        "has_more": (page * page_size) < total_courses
    }


@router.get("/regions")
async def get_regions():
    """여행 지역 목록 조회"""
    regions = [
        {"code": "all", "name": "전체", "description": "모든 지역"},
        {"code": "seoul", "name": "서울", "description": "수도권 중심지"},
        {"code": "busan", "name": "부산", "description": "남부 해안도시"},
        {"code": "daegu", "name": "대구", "description": "영남권 중심지"},
        {"code": "incheon", "name": "인천", "description": "서해안 관문도시"},
        {"code": "gwangju", "name": "광주", "description": "호남권 중심지"},
        {"code": "daejeon", "name": "대전", "description": "중부권 중심지"},
        {"code": "ulsan", "name": "울산", "description": "동남권 공업도시"},
        {"code": "sejong", "name": "세종", "description": "행정중심복합도시"},
        {"code": "gyeonggi", "name": "경기", "description": "수도권 광역지역"},
        {"code": "gangwon", "name": "강원", "description": "동북부 산악지역"},
        {"code": "chungbuk", "name": "충북", "description": "중부 내륙지역"},
        {"code": "chungnam", "name": "충남", "description": "중서부 지역"},
        {"code": "jeonbuk", "name": "전북", "description": "서남부 지역"},
        {"code": "jeonnam", "name": "전남", "description": "남서부 지역"},
        {"code": "gyeongbuk", "name": "경북", "description": "동남부 내륙지역"},
        {"code": "gyeongnam", "name": "경남", "description": "남동부 지역"},
        {"code": "jeju", "name": "제주", "description": "남부 섬 지역"},
        {"code": "gangneung", "name": "강릉", "description": "동해안 관광도시"},
        {"code": "gyeongju", "name": "경주", "description": "천년 고도"},
        {"code": "jeonju", "name": "전주", "description": "한옥과 전통문화의 도시"},
        {"code": "yeosu", "name": "여수", "description": "남해안 해양관광도시"},
    ]

    return {
        "regions": regions,
        "total": len(regions)
    }

@router.get("/themes")
async def get_themes():
    """여행 테마 목록 조회"""
    themes = [
        {"code": "all", "name": "전체 테마", "description": "모든 테마"},
        {"code": "nature", "name": "자연", "description": "자연 경관과 야외 활동"},
        {"code": "city", "name": "도시", "description": "도시 관광과 문화"},
        {"code": "beach", "name": "바다", "description": "해변과 해양 활동"},
        {"code": "history", "name": "역사", "description": "역사 유적과 문화재"},
        {"code": "food", "name": "맛집", "description": "지역 특산물과 맛집"},
        {"code": "healing", "name": "힐링", "description": "휴양과 웰빙"},
        {"code": "activity", "name": "액티비티", "description": "체험과 레저 활동"},
        {"code": "culture", "name": "문화", "description": "문화 예술과 축제"},
        {"code": "shopping", "name": "쇼핑", "description": "쇼핑과 시장 탐방"},
        {"code": "family", "name": "가족", "description": "가족 단위 여행"},
        {"code": "couple", "name": "커플", "description": "연인과 함께하는 여행"},
    ]

    return {
        "themes": themes,
        "total": len(themes)
    }

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
