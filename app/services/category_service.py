"""
카테고리 서비스 계층
한국관광공사 카테고리 데이터베이스 기반 서비스
"""

from typing import List, Dict, Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import and_
from app.models import CategoryCode
from app.utils.cache import cache_result


class CategoryService:
    """카테고리 관련 서비스 클래스"""
    
    def __init__(self, db: Session):
        self.db = db
    
    @cache_result(ttl=3600)  # 1시간 캐싱
    def get_content_type_mapping(self) -> Dict[str, str]:
        """컨텐츠 타입 ID와 이름 매핑 반환"""
        return {
            '12': '관광지',
            '14': '문화시설',
            '15': '축제공연행사',
            '25': '여행코스',
            '28': '레포츠',
            '32': '숙박',
            '38': '쇼핑',
            '39': '음식점'
        }
    
    @cache_result(ttl=3600)
    def get_categories_by_content_type(self, content_type_id: str) -> List[Dict[str, Any]]:
        """컨텐츠 타입별 카테고리 조회"""
        categories = self.db.query(CategoryCode)\
            .filter(CategoryCode.content_type_id == content_type_id)\
            .order_by(CategoryCode.category_code)\
            .all()
        
        return [
            {
                'category_code': cat.category_code,
                'category_name': cat.category_name,
                'parent_category_code': cat.parent_category_code,
                'category_level': cat.category_level
            }
            for cat in categories
        ]
    
    @cache_result(ttl=3600)
    def get_category_hierarchy(self, content_type_id: str = None) -> List[Dict[str, Any]]:
        """카테고리 계층 구조 조회"""
        # 1차 카테고리 조회
        level1_categories = self.db.query(CategoryCode)\
            .filter(CategoryCode.category_level == 1)\
            .order_by(CategoryCode.category_code)\
            .all()
        
        # 2차 카테고리 조회
        level2_query = self.db.query(CategoryCode)\
            .filter(CategoryCode.category_level == 2)
        
        if content_type_id:
            level2_query = level2_query.filter(CategoryCode.content_type_id == content_type_id)
        
        level2_categories = level2_query.all()
        
        # 계층 구조 구성
        hierarchy = []
        for level1 in level1_categories:
            children = [
                {
                    'category_code': child.category_code,
                    'category_name': child.category_name,
                    'content_type_id': child.content_type_id,
                }
                for child in level2_categories
                if child.parent_category_code == level1.category_code
            ]
            
            # 해당 컨텐츠 타입 필터링 시 자식이 있는 경우만 포함
            if content_type_id is None or children:
                hierarchy.append({
                    'category_code': level1.category_code,
                    'category_name': level1.category_name,
                    'children': children
                })
        
        return hierarchy
    
    @cache_result(ttl=3600)
    def get_category_by_code(self, category_code: str) -> Optional[Dict[str, Any]]:
        """카테고리 코드로 카테고리 정보 조회"""
        category = self.db.query(CategoryCode)\
            .filter(CategoryCode.category_code == category_code)\
            .first()
        
        if not category:
            return None
        
        return {
            'category_code': category.category_code,
            'category_name': category.category_name,
            'content_type_id': category.content_type_id,
            'parent_category_code': category.parent_category_code,
            'category_level': category.category_level
        }
    
    @cache_result(ttl=3600)
    def get_categories_by_parent(self, parent_code: str) -> List[Dict[str, Any]]:
        """부모 카테고리 코드로 하위 카테고리 조회"""
        categories = self.db.query(CategoryCode)\
            .filter(CategoryCode.parent_category_code == parent_code)\
            .order_by(CategoryCode.category_code)\
            .all()
        
        return [
            {
                'category_code': cat.category_code,
                'category_name': cat.category_name,
                'content_type_id': cat.content_type_id,
                'parent_category_code': cat.parent_category_code,
                'category_level': cat.category_level
            }
            for cat in categories
        ]
    
    def categorize_restaurant_by_name(self, category_name: str) -> str:
        """카테고리명을 기반으로 맛집 분류 (데이터베이스 기반으로 향후 개선 가능)"""
        # 음식점(39) 카테고리에서 매칭 시도
        restaurant_categories = self.get_categories_by_content_type('39')
        
        category_name_lower = category_name.lower()
        
        # 데이터베이스의 카테고리와 매칭
        for cat in restaurant_categories:
            cat_name = cat['category_name'].lower()
            if cat_name in category_name_lower:
                return cat['category_name']
        
        # 기존 로직 유지 (향후 데이터베이스 기반으로 변경 예정)
        if any(keyword in category_name_lower for keyword in ["한식", "국밥", "김치", "비빔밥"]):
            return "한식"
        elif any(keyword in category_name_lower for keyword in ["중식", "짜장면", "탕수육", "마파두부"]):
            return "중식"
        elif any(keyword in category_name_lower for keyword in ["일식", "초밥", "라멘", "우동"]):
            return "일식"
        elif any(keyword in category_name_lower for keyword in ["양식", "파스타", "피자", "스테이크"]):
            return "서양식"
        elif any(keyword in category_name_lower for keyword in ["카페", "커피", "디저트"]):
            return "카페/디저트"
        else:
            return "음식점"
    
    def categorize_accommodation_by_name(self, category_name: str) -> str:
        """카테고리명을 기반으로 숙소 분류 (데이터베이스 기반으로 향후 개선 가능)"""
        # 숙박(32) 카테고리에서 매칭 시도
        accommodation_categories = self.get_categories_by_content_type('32')
        
        category_name_lower = category_name.lower()
        
        # 데이터베이스의 카테고리와 매칭
        for cat in accommodation_categories:
            cat_name = cat['category_name'].lower()
            if cat_name in category_name_lower:
                return cat['category_name']
        
        # 기존 로직 유지 (향후 데이터베이스 기반으로 변경 예정)
        if "호텔" in category_name_lower:
            return "관광호텔"
        elif "펜션" in category_name_lower:
            return "펜션"
        elif "게스트" in category_name_lower:
            return "게스트하우스"
        elif "모텔" in category_name_lower:
            return "모텔"
        elif "리조트" in category_name_lower:
            return "관광호텔"
        else:
            return "관광호텔"
    
    @cache_result(ttl=3600)
    def get_content_type_by_code(self, category_code: str) -> Optional[str]:
        """카테고리 코드로 컨텐츠 타입 조회"""
        category = self.get_category_by_code(category_code)
        if category:
            return category.get('content_type_id')
        return None
    
    @cache_result(ttl=3600)
    def search_categories(self, keyword: str, content_type_id: str = None) -> List[Dict[str, Any]]:
        """키워드로 카테고리 검색"""
        query = self.db.query(CategoryCode)\
            .filter(CategoryCode.category_name.like(f'%{keyword}%'))
        
        if content_type_id:
            query = query.filter(CategoryCode.content_type_id == content_type_id)
        
        categories = query.order_by(CategoryCode.category_code).all()
        
        return [
            {
                'category_code': cat.category_code,
                'category_name': cat.category_name,
                'content_type_id': cat.content_type_id,
                'parent_category_code': cat.parent_category_code,
                'category_level': cat.category_level
            }
            for cat in categories
        ]
    
    @cache_result(ttl=3600)
    def get_category_stats(self) -> Dict[str, Any]:
        """카테고리 통계 조회"""
        content_type_mapping = self.get_content_type_mapping()
        
        stats = {
            'total_categories': self.db.query(CategoryCode).count(),
            'by_content_type': {},
            'by_level': {}
        }
        
        # 컨텐츠 타입별 통계
        for content_type_id, content_type_name in content_type_mapping.items():
            count = self.db.query(CategoryCode)\
                .filter(CategoryCode.content_type_id == content_type_id)\
                .count()
            stats['by_content_type'][content_type_name] = count
        
        # 레벨별 통계
        for level in [1, 2]:
            count = self.db.query(CategoryCode)\
                .filter(CategoryCode.category_level == level)\
                .count()
            stats['by_level'][f'level_{level}'] = count
        
        return stats


def get_category_service(db: Session) -> CategoryService:
    """카테고리 서비스 팩토리 함수"""
    return CategoryService(db)