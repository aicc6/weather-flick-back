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
