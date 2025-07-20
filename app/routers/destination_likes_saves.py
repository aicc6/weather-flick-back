"""
여행지 좋아요 및 저장 관련 API 엔드포인트
"""
from typing import List, Optional
from uuid import UUID, uuid4
import re

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.auth import get_current_active_user
from app.database import get_db
from app.models import (
    Destination,
    DestinationLike,
    DestinationLikeCreate,
    DestinationLikeResponse,
    DestinationResponse,
    DestinationSave,
    DestinationSaveCreate,
    DestinationSaveResponse,
    TravelCourse,
    User,
)

router = APIRouter(
    prefix="/destinations",
    tags=["destination-likes-saves"],
    responses={404: {"description": "Not found"}},
)


def get_destination_with_stats(
    db: Session, destination_id: UUID, current_user_id: Optional[UUID] = None
) -> Optional[dict]:
    """여행지 정보와 좋아요/저장 통계를 함께 가져오는 헬퍼 함수"""
    destination = db.query(Destination).filter(
        Destination.destination_id == destination_id
    ).first()
    
    if not destination:
        return None
    
    # 좋아요 수 계산
    likes_count = db.query(func.count(DestinationLike.id)).filter(
        DestinationLike.destination_id == destination_id
    ).scalar()
    
    # 저장 수 계산
    saves_count = db.query(func.count(DestinationSave.id)).filter(
        DestinationSave.destination_id == destination_id
    ).scalar()
    
    result = {
        "destination_id": destination.destination_id,
        "name": destination.name,
        "province": destination.province,
        "region": destination.region,
        "category": destination.category,
        "is_indoor": destination.is_indoor,
        "tags": destination.tags,
        "latitude": float(destination.latitude) if destination.latitude else None,
        "longitude": float(destination.longitude) if destination.longitude else None,
        "image_url": destination.image_url,
        "rating": destination.rating,
        "likes_count": likes_count,
        "saves_count": saves_count,
        "is_liked": False,
        "is_saved": False,
    }
    
    # 현재 사용자의 좋아요/저장 여부 확인
    if current_user_id:
        is_liked = db.query(DestinationLike).filter(
            and_(
                DestinationLike.user_id == current_user_id,
                DestinationLike.destination_id == destination_id
            )
        ).first() is not None
        
        is_saved = db.query(DestinationSave).filter(
            and_(
                DestinationSave.user_id == current_user_id,
                DestinationSave.destination_id == destination_id
            )
        ).first() is not None
        
        result["is_liked"] = is_liked
        result["is_saved"] = is_saved
    
    return result


# 좋아요 관련 엔드포인트
@router.post("/likes", response_model=DestinationLikeResponse)
async def create_destination_like(
    like_data: DestinationLikeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행지에 좋아요 추가"""
    # 여행지 존재 확인
    destination = db.query(Destination).filter(
        Destination.destination_id == like_data.destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # 이미 좋아요했는지 확인
    existing_like = db.query(DestinationLike).filter(
        and_(
            DestinationLike.user_id == current_user.user_id,
            DestinationLike.destination_id == like_data.destination_id
        )
    ).first()
    
    if existing_like:
        raise HTTPException(status_code=400, detail="Already liked this destination")
    
    # 좋아요 생성
    new_like = DestinationLike(
        user_id=current_user.user_id,
        destination_id=like_data.destination_id
    )
    
    try:
        db.add(new_like)
        db.commit()
        db.refresh(new_like)
        
        # 응답에 여행지 정보 포함
        response = DestinationLikeResponse(
            id=new_like.id,
            destination_id=new_like.destination_id,
            user_id=new_like.user_id,
            created_at=new_like.created_at,
            destination=get_destination_with_stats(
                db, new_like.destination_id, current_user.user_id
            )
        )
        
        return response
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to create like")


@router.delete("/likes/{destination_id}")
async def delete_destination_like(
    destination_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행지 좋아요 취소"""
    like = db.query(DestinationLike).filter(
        and_(
            DestinationLike.user_id == current_user.user_id,
            DestinationLike.destination_id == destination_id
        )
    ).first()
    
    if not like:
        raise HTTPException(status_code=404, detail="Like not found")
    
    db.delete(like)
    db.commit()
    
    return {"message": "Like removed successfully"}


@router.get("/likes", response_model=List[DestinationLikeResponse])
async def get_my_destination_likes(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """내가 좋아요한 여행지 목록 조회"""
    likes = db.query(DestinationLike).filter(
        DestinationLike.user_id == current_user.user_id
    ).options(
        joinedload(DestinationLike.destination)
    ).order_by(
        DestinationLike.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for like in likes:
        destination_data = get_destination_with_stats(
            db, like.destination_id, current_user.user_id
        )
        result.append(
            DestinationLikeResponse(
                id=like.id,
                destination_id=like.destination_id,
                user_id=like.user_id,
                created_at=like.created_at,
                destination=destination_data
            )
        )
    
    return result


# 저장(북마크) 관련 엔드포인트
@router.post("/saves", response_model=DestinationSaveResponse)
async def create_destination_save(
    save_data: DestinationSaveCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행지 저장(북마크)"""
    # 여행지 존재 확인
    destination = db.query(Destination).filter(
        Destination.destination_id == save_data.destination_id
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    # 이미 저장했는지 확인
    existing_save = db.query(DestinationSave).filter(
        and_(
            DestinationSave.user_id == current_user.user_id,
            DestinationSave.destination_id == save_data.destination_id
        )
    ).first()
    
    if existing_save:
        raise HTTPException(status_code=400, detail="Already saved this destination")
    
    # 저장 생성
    new_save = DestinationSave(
        user_id=current_user.user_id,
        destination_id=save_data.destination_id,
        note=save_data.note
    )
    
    try:
        db.add(new_save)
        db.commit()
        db.refresh(new_save)
        
        # 응답에 여행지 정보 포함
        response = DestinationSaveResponse(
            id=new_save.id,
            destination_id=new_save.destination_id,
            user_id=new_save.user_id,
            note=new_save.note,
            created_at=new_save.created_at,
            destination=get_destination_with_stats(
                db, new_save.destination_id, current_user.user_id
            )
        )
        
        return response
        
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=400, detail="Failed to save destination")


@router.delete("/saves/{destination_id}")
async def delete_destination_save(
    destination_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행지 저장 취소"""
    save = db.query(DestinationSave).filter(
        and_(
            DestinationSave.user_id == current_user.user_id,
            DestinationSave.destination_id == destination_id
        )
    ).first()
    
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")
    
    db.delete(save)
    db.commit()
    
    return {"message": "Save removed successfully"}


@router.get("/saves", response_model=List[DestinationSaveResponse])
async def get_my_destination_saves(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """내가 저장한 여행지 목록 조회"""
    saves = db.query(DestinationSave).filter(
        DestinationSave.user_id == current_user.user_id
    ).options(
        joinedload(DestinationSave.destination)
    ).order_by(
        DestinationSave.created_at.desc()
    ).offset(skip).limit(limit).all()
    
    result = []
    for save in saves:
        destination_data = get_destination_with_stats(
            db, save.destination_id, current_user.user_id
        )
        result.append(
            DestinationSaveResponse(
                id=save.id,
                destination_id=save.destination_id,
                user_id=save.user_id,
                note=save.note,
                created_at=save.created_at,
                destination=destination_data
            )
        )
    
    return result


@router.put("/saves/{destination_id}", response_model=DestinationSaveResponse)
async def update_destination_save_note(
    destination_id: UUID,
    note: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """저장한 여행지의 메모 수정"""
    save = db.query(DestinationSave).filter(
        and_(
            DestinationSave.user_id == current_user.user_id,
            DestinationSave.destination_id == destination_id
        )
    ).first()
    
    if not save:
        raise HTTPException(status_code=404, detail="Save not found")
    
    save.note = note
    db.commit()
    db.refresh(save)
    
    # 응답에 여행지 정보 포함
    response = DestinationSaveResponse(
        id=save.id,
        destination_id=save.destination_id,
        user_id=save.user_id,
        note=save.note,
        created_at=save.created_at,
        destination=get_destination_with_stats(
            db, save.destination_id, current_user.user_id
        )
    )
    
    return response




def extract_province_from_address(address: str) -> str:
    """주소에서 광역시/도 추출"""
    if not address:
        return "알 수 없음"
    
    # 정규식으로 광역시/도 추출
    pattern = r'^([^시군구\s]+(?:특별시|광역시|특별자치시|도|특별자치도))'
    match = re.match(pattern, address.strip())
    
    if match:
        return match.group(1)
    
    # 기본적인 경우 처리
    if '서울' in address[:3]:
        return '서울특별시'
    elif '부산' in address[:3]:
        return '부산광역시'
    elif '대구' in address[:3]:
        return '대구광역시'
    elif '인천' in address[:3]:
        return '인천광역시'
    elif '광주' in address[:3]:
        return '광주광역시'
    elif '대전' in address[:3]:
        return '대전광역시'
    elif '울산' in address[:3]:
        return '울산광역시'
    elif '세종' in address[:3]:
        return '세종특별자치시'
    elif '경기도' in address[:4] or '경기' in address[:3]:
        return '경기도'
    elif '강원도' in address[:4] or '강원' in address[:3]:
        return '강원도'
    elif '충청북도' in address[:5] or '충북' in address[:3]:
        return '충청북도'
    elif '충청남도' in address[:5] or '충남' in address[:3]:
        return '충청남도'
    elif '전라북도' in address[:5] or '전북' in address[:3]:
        return '전라북도'
    elif '전라남도' in address[:5] or '전남' in address[:3]:
        return '전라남도'
    elif '경상북도' in address[:5] or '경북' in address[:3]:
        return '경상북도'
    elif '경상남도' in address[:5] or '경남' in address[:3]:
        return '경상남도'
    elif '제주' in address[:3]:
        return '제주특별자치도'
    
    return "알 수 없음"


def extract_region_from_address(address: str, province: str) -> Optional[str]:
    """주소에서 시/군/구 추출"""
    if not address:
        return None
    
    # 광역시/도 부분을 제거하고 시작
    cleaned_address = address
    if province in address:
        cleaned_address = address.replace(province, '').strip()
    
    # 시/군/구 추출
    pattern = r'^([^동면리로길\s]+(?:시|군|구))'
    match = re.match(pattern, cleaned_address)
    
    if match:
        return match.group(1)
    
    return None


@router.get("/search-by-name")
async def search_destination_by_name(
    name: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
):
    """여행지 이름으로 destinations 테이블에서 검색"""
    destination = db.query(Destination).filter(
        Destination.name == name
    ).first()
    
    if not destination:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    return {
        "destination_id": destination.destination_id,
        "name": destination.name,
        "province": destination.province,
        "region": destination.region,
        "category": destination.category,
        "is_indoor": destination.is_indoor,
        "tags": destination.tags,
        "latitude": float(destination.latitude) if destination.latitude else None,
        "longitude": float(destination.longitude) if destination.longitude else None,
        "image_url": destination.image_url,
        "rating": destination.rating,
    }


# 여행지 상세 정보 조회 (좋아요/저장 정보 포함)
@router.get("/{destination_id}", response_model=DestinationResponse)
async def get_destination_detail(
    destination_id: UUID,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user),
):
    """여행지 상세 정보 조회 (좋아요/저장 정보 포함)"""
    destination_data = get_destination_with_stats(
        db, 
        destination_id, 
        current_user.user_id if current_user else None
    )
    
    if not destination_data:
        raise HTTPException(status_code=404, detail="Destination not found")
    
    return destination_data


@router.post("/convert-from-courses")
async def convert_travel_courses_to_destinations(
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """여행 코스를 개별 여행지로 변환하여 destinations 테이블에 저장"""
    
    # 관리자 권한 확인 (실제 운영에서는 admin 권한 체크 필요)
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")
    
    try:
        # 제한된 수의 여행 코스 조회 (배치 처리)
        travel_courses = db.query(TravelCourse).limit(limit).all()
        
        converted_count = 0
        skipped_count = 0
        
        for course in travel_courses:
            # 이미 변환된 여행지인지 확인 (content_id 기반)
            existing_destination = db.query(Destination).filter(
                Destination.name == course.course_name,
                Destination.province == extract_province_from_address(course.address or "")
            ).first()
            
            if existing_destination:
                skipped_count += 1
                continue
            
            # 주소에서 광역시/도와 시/군/구 추출
            province = extract_province_from_address(course.address or "")
            region = extract_region_from_address(course.address or "", province)
            
            # 새로운 여행지 생성
            new_destination = Destination(
                destination_id=uuid4(),
                name=course.course_name,
                province=province,
                region=region,
                category="관광지",  # 기본 카테고리
                is_indoor=False,  # 기본값
                tags=["여행코스"] if not course.course_theme else [course.course_theme],
                latitude=course.latitude,
                longitude=course.longitude,
                image_url=course.first_image,
                rating=None,
                amenities={}
            )
            
            db.add(new_destination)
            converted_count += 1
        
        # 변경사항 커밋
        db.commit()
        
        return {
            "message": "Travel courses converted to destinations successfully",
            "converted_count": converted_count,
            "skipped_count": skipped_count,
            "processed_courses": len(travel_courses),
            "limit": limit
        }
        
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to convert travel courses: {str(e)}"
        )