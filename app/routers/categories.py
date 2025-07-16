"""
카테고리 API 라우터
한국관광공사 카테고리 데이터 조회 API
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.category_service import get_category_service
from app.utils.cache import clear_category_cache

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.get("/content-types")
async def get_content_types(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """컨텐츠 타입 목록 조회"""
    try:
        category_service = get_category_service(db)
        content_types = category_service.get_content_type_mapping()
        
        return {
            "content_types": [
                {
                    "content_type_id": type_id,
                    "content_type_name": type_name
                }
                for type_id, type_name in content_types.items()
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"컨텐츠 타입 조회 실패: {str(e)}")


@router.get("/by-content-type/{content_type_id}")
async def get_categories_by_content_type(
    content_type_id: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """컨텐츠 타입별 카테고리 조회"""
    try:
        category_service = get_category_service(db)
        categories = category_service.get_categories_by_content_type(content_type_id)
        
        return {
            "content_type_id": content_type_id,
            "categories": categories,
            "total_count": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 조회 실패: {str(e)}")


@router.get("/hierarchy")
async def get_category_hierarchy(
    content_type_id: Optional[str] = Query(None, description="컨텐츠 타입 ID (선택사항)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """카테고리 계층 구조 조회"""
    try:
        category_service = get_category_service(db)
        hierarchy = category_service.get_category_hierarchy(content_type_id)
        
        return {
            "content_type_id": content_type_id,
            "hierarchy": hierarchy
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 계층 조회 실패: {str(e)}")


@router.get("/code/{category_code}")
async def get_category_by_code(
    category_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """카테고리 코드로 카테고리 정보 조회"""
    try:
        category_service = get_category_service(db)
        category = category_service.get_category_by_code(category_code)
        
        if not category:
            raise HTTPException(status_code=404, detail="카테고리를 찾을 수 없습니다")
        
        return {"category": category}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 조회 실패: {str(e)}")


@router.get("/parent/{parent_code}")
async def get_categories_by_parent(
    parent_code: str,
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """부모 카테고리 코드로 하위 카테고리 조회"""
    try:
        category_service = get_category_service(db)
        categories = category_service.get_categories_by_parent(parent_code)
        
        return {
            "parent_code": parent_code,
            "categories": categories,
            "total_count": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"하위 카테고리 조회 실패: {str(e)}")


@router.get("/search")
async def search_categories(
    keyword: str = Query(..., description="검색 키워드"),
    content_type_id: Optional[str] = Query(None, description="컨텐츠 타입 ID (선택사항)"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """키워드로 카테고리 검색"""
    try:
        category_service = get_category_service(db)
        categories = category_service.search_categories(keyword, content_type_id)
        
        return {
            "keyword": keyword,
            "content_type_id": content_type_id,
            "categories": categories,
            "total_count": len(categories)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 검색 실패: {str(e)}")


@router.get("/stats")
async def get_category_stats(
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """카테고리 통계 조회"""
    try:
        category_service = get_category_service(db)
        stats = category_service.get_category_stats()
        
        return {"stats": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 통계 조회 실패: {str(e)}")


@router.post("/cache/clear")
async def clear_cache():
    """카테고리 캐시 초기화"""
    try:
        cleared_count = clear_category_cache()
        return {
            "message": "카테고리 캐시가 초기화되었습니다",
            "cleared_count": cleared_count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"캐시 초기화 실패: {str(e)}")


@router.post("/categorize/restaurant")
async def categorize_restaurant(
    category_name: str = Query(..., description="카테고리명"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """카테고리명을 기반으로 맛집 분류"""
    try:
        category_service = get_category_service(db)
        result = category_service.categorize_restaurant_by_name(category_name)
        
        return {
            "original_category": category_name,
            "categorized_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"맛집 분류 실패: {str(e)}")


@router.post("/categorize/accommodation")
async def categorize_accommodation(
    category_name: str = Query(..., description="카테고리명"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """카테고리명을 기반으로 숙소 분류"""
    try:
        category_service = get_category_service(db)
        result = category_service.categorize_accommodation_by_name(category_name)
        
        return {
            "original_category": category_name,
            "categorized_result": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"숙소 분류 실패: {str(e)}")


@router.get("/")
async def get_all_categories(
    content_type_id: Optional[str] = Query(None, description="컨텐츠 타입 ID"),
    category_level: Optional[int] = Query(None, description="카테고리 레벨"),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """전체 카테고리 목록 조회 (필터링 가능)"""
    try:
        category_service = get_category_service(db)
        
        if content_type_id:
            categories = category_service.get_categories_by_content_type(content_type_id)
            if category_level:
                categories = [cat for cat in categories if cat['category_level'] == category_level]
        else:
            # 모든 카테고리 조회 (간단한 구현)
            from app.models import CategoryCode
            query = db.query(CategoryCode)
            
            if category_level:
                query = query.filter(CategoryCode.category_level == category_level)
            
            categories_db = query.order_by(CategoryCode.category_code).all()
            categories = [
                {
                    'category_code': cat.category_code,
                    'category_name': cat.category_name,
                    'content_type_id': cat.content_type_id,
                    'parent_category_code': cat.parent_category_code,
                    'category_level': cat.category_level
                }
                for cat in categories_db
            ]
        
        return {
            "categories": categories,
            "total_count": len(categories),
            "filters": {
                "content_type_id": content_type_id,
                "category_level": category_level
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"카테고리 목록 조회 실패: {str(e)}")