# app/schema_models/travel_course.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List
from datetime import datetime

class TravelCourseResponse(BaseModel):
    content_id: str
    region_code: str
    course_name: str
    course_theme: Optional[str]
    required_time: Optional[str]
    difficulty_level: Optional[str]
    schedule: Optional[str]
    course_distance: Optional[str]
    address: Optional[str]
    overview: Optional[str]
    first_image: Optional[str]
    created_at: Optional[datetime]
    place_id: str | None = None
    # 필요에 따라 필드 추가
    class Config:
        orm_mode = True

class TravelCourseListResponse(BaseModel):
    courses: List[TravelCourseResponse]
    totalCount: int
    model_config = ConfigDict(from_attributes=True)

class TravelCourseDetailResponse(BaseModel):
    """여행 코스 상세 정보 응답 스키마"""
    content_id: str
    region_code: str
    course_name: str
    course_theme: Optional[str]
    required_time: Optional[str]
    difficulty_level: Optional[str]
    schedule: Optional[str]
    course_distance: Optional[str]
    address: Optional[str]
    detail_address: Optional[str]
    tel: Optional[str]
    homepage: Optional[str]
    overview: Optional[str]
    first_image: Optional[str]
    first_image_small: Optional[str]
    latitude: Optional[float]
    longitude: Optional[float]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    detail_intro_info: Optional[dict]
    detail_additional_info: Optional[dict]

    model_config = ConfigDict(from_attributes=True)
