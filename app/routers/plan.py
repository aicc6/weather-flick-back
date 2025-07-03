from fastapi import APIRouter
from pydantic import BaseModel
from typing import List
from datetime import date

router = APIRouter(prefix="/plan", tags=["plan"])

class PlanRequest(BaseModel):
    origin: str
    destination: str
    startDate: date
    endDate: date

class PlanResponse(BaseModel):
    title: str
    description: str

@router.post("/recommend", response_model=dict)
async def recommend_plan(req: PlanRequest):
    if req.endDate < req.startDate:
        return {"error": "도착일이 출발일보다 빠를 수 없습니다."}
    days = (req.endDate - req.startDate).days + 1
    plans = [
        {"title": f"{req.destination} 여행 {i+1}일차", "description": f"{req.destination}에서 보내는 {i+1}일차 일정"}
        for i in range(days)
    ]
    return {"plans": plans}
