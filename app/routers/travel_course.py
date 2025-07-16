# app/routers/travel_courses.py
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelCourse
from app.schema_models.travel_course import TravelCourseListResponse, TravelCourseDetailResponse

router = APIRouter(prefix="/travel-courses", tags=["travel-courses"])

@router.get("/", response_model=TravelCourseListResponse)
async def get_travel_courses(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="페이지 번호 (1부터 시작)"),
    limit: int = Query(10, ge=1, le=50, description="페이지당 항목 수 (최대 50)"),
    regionCode: str = Query(None, description="광역시도 코드(예: seoul, busan 등)")
):
    offset = (page - 1) * limit
    query = db.query(TravelCourse)
    if regionCode:
        # 지역명 매핑 (예: 'seoul' -> '서울', 'busan' -> '부산')
        region_name_map = {
            'seoul': '서울', 'busan': '부산', 'daegu': '대구', 'incheon': '인천',
            'gwangju': '광주', 'daejeon': '대전', 'ulsan': '울산', 'sejong': '세종',
            'gyeonggi': '경기', 'gangwon': '강원', 'chungbuk': '충청북도', 'chungnam': '충청남도',
            'jeonbuk': '전라북도', 'jeonnam': '전라남도', 'gyeongbuk': '경상북도', 'gyeongnam': '경상남도', 'jeju': '제주'
        }
        region_name = region_name_map.get(regionCode, regionCode)
        query = query.filter(TravelCourse.address.contains(region_name))
    total_count = query.count()  # 전체 개수
    courses = query.offset(offset).limit(limit).all()
    return {"courses": courses, "totalCount": total_count}

@router.get("/{course_id}", response_model=TravelCourseDetailResponse)
async def get_travel_course_detail(
    course_id: str,
    db: Session = Depends(get_db)
):
    """여행 코스 상세 정보 조회"""
    course = db.query(TravelCourse).filter(TravelCourse.content_id == course_id).first()

    if not course:
        raise HTTPException(status_code=404, detail="여행 코스를 찾을 수 없습니다")

    # datetime 필드를 문자열로 변환
    course_dict = {}
    for key, value in course.__dict__.items():
        if key.startswith('_'):
            continue
        if hasattr(value, 'isoformat'):  # datetime 객체인 경우
            course_dict[key] = value.isoformat() if value else None
        else:
            course_dict[key] = value

    return course_dict
