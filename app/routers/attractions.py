from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.logging_config import get_logger
from app.models import TouristAttraction
from app.database import get_db

# 로거 설정
logger = get_logger()

router = APIRouter(prefix="/attractions", tags=["attractions"])

@router.get("/by-region", response_model=list[str])
async def get_attractions_by_region(
    region_code: str = Query(..., description="지역 코드"),
    db: Session = Depends(get_db)
):
    logger.info(region_code)
    # region_code 컬럼에서 region_code 값이 일치하는 관광지 이름 조회
    attractions = (
        db.query(TouristAttraction.attraction_name)
        .filter(TouristAttraction.region_code == region_code)
        .all()
    )
    # [(name1,), (name2,), ...] → [name1, name2, ...]
    return [a[0] for a in attractions]
