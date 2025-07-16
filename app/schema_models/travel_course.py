# app/schema_models/travel_course.py
from pydantic import BaseModel, ConfigDict
from typing import Optional, List

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
    created_at: Optional[str]
    # 필요에 따라 필드 추가
    class Config:
        orm_mode = True

class TravelCourseListResponse(BaseModel):
    courses: List[TravelCourseResponse]
    totalCount: int
    model_config = ConfigDict(from_attributes=True)
