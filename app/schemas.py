from typing import List, Optional
from pydantic import BaseModel

class Activity(BaseModel):
    time: str
    type: str
    place: str
    description: str
    address: Optional[str] = None

class DayItinerary(BaseModel):
    day: int
    title: str
    activities: List[Activity]

class TravelCourseLikeCreate(BaseModel):
    user_id: int
    title: str
    subtitle: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    region: Optional[str] = None
    itinerary: List[DayItinerary]

class TravelCourseLikeResponse(TravelCourseLikeCreate):
    id: int

    class Config:
        from_attributes = True
