
from pydantic import BaseModel


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
    user_id: int
    title: str
    subtitle: str | None = None
    summary: str | None = None
    description: str | None = None
    region: str | None = None
    itinerary: list[DayItinerary]

class TravelCourseLikeResponse(TravelCourseLikeCreate):
    id: int

    class Config:
        from_attributes = True
