"""
여행지 좋아요 및 저장 관련 API 엔드포인트
"""
from typing import List, Optional
from uuid import UUID

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