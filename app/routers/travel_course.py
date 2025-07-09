from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import TravelCourse
from typing import Any

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
