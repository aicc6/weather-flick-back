
from datetime import datetime
from pydantic import BaseModel
from uuid import UUID


class Activity(BaseModel):
    time: str
    type: str
    place: str
    description: str
    address: str | None = None

class DayItinerary(BaseModel):
    day: int
    title: str
    activities: list[Activity]

class TravelCourseLikeCreate(BaseModel):
    content_id: str
    title: str
    subtitle: str | None = None
    summary: str | None = None
    description: str | None = None
    region: str | None = None
    itinerary: list[DayItinerary]

class TravelCourseLikeResponse(TravelCourseLikeCreate):
    id: int
    user_id: UUID
    created_at: datetime

    class Config:
        from_attributes = True
