# app/routers/travel_courses.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelCourse
from app.schema_models.travel_course import TravelCourseListResponse, TravelCourseDetailResponse
from app.schema_models.travel_course import TravelCourseResponse

router = APIRouter(prefix="/travel-courses", tags=["travel-courses"])

@router.get("/", response_model=TravelCourseListResponse)
async def get_travel_courses(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 항목 수 (최대 50)"),
    regionCode: str = Query(None, description="광역시도 코드(예: seoul, busan 등)")
) -> TravelCourseListResponse:
    offset = (page - 1) * limit
    query = db.query(TravelCourse)
    if regionCode:
        # 지역명 매핑 (예: 'seoul' -> '서울', 'busan' -> '부산')
        region_name_map = {
            'seoul': ('서울', 1), 'busan': ('부산', 6), 'daegu': ('대구', 4), 'incheon': ('인천', 2),
            'gwangju': ('광주', 5), 'daejeon': ('대전', 3), 'ulsan': ('울산', 7), 'sejong': ('세종', 8),
            'gyeonggi': ('경기', 31), 'gangwon': ('강원', 32), 'chungbuk': ('충청북도', 33), 'chungnam': ('충청남도', 34),
            'gyeongbuk': ('경상북도', 35), 'gyeongnam': ('경상남도', 36), 'jeonbuk': ('전라북도', 37), 'jeonnam': ('전라남도', 38), 'jeju': ('제주', 39)
        }
        region_info = region_name_map.get(regionCode, (regionCode, None))
        region_name, region_code = region_info
        print('regionCode:', regionCode, 'region_name:', region_name, 'region_code:', region_code)
        if region_code is not None:
            query = query.filter(TravelCourse.region_code == str(region_code))
        else:
            query = query.filter(TravelCourse.address.contains(region_name))
    total_count = query.count()  # 전체 개수
    courses = query.offset(offset).limit(limit).all()
    # ORM 객체를 Pydantic 모델로 변환
    course_models = []
    for course in courses:
        try:
            course_models.append(TravelCourseResponse.model_validate(course, from_attributes=True))
        except Exception as e:
            print('Pydantic 변환 에러:', e)
            print('문제 course:', course.__dict__)
            raise
    return TravelCourseListResponse(courses=course_models, totalCount=total_count)

@router.get("/{course_id}", response_model=TravelCourseDetailResponse)
async def get_travel_course_detail(
    course_id: str,
    db: Session = Depends(get_db)
) -> TravelCourseDetailResponse:
    """여행 코스 상세 정보 조회"""
    # 복합 기본키 대응: content_id로만 조회하되 첫 번째 결과 사용
    course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="여행 코스를 찾을 수 없습니다")

    # ORM 객체를 Pydantic 모델로 변환
    return TravelCourseDetailResponse.model_validate(course, from_attributes=True)

@router.get("/{course_id}/google-review")
async def get_google_review_for_course(course_id: str, db: Session = Depends(get_db)):
    course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()
    if not course or not course.place_id:
        raise HTTPException(status_code=404, detail="place_id가 없습니다")
    from app.services.google_places_service import GooglePlacesService
    service = GooglePlacesService()
    return await service.get_place_reviews_and_rating(course.place_id)
