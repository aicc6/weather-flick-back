"""
여행지 관련 서비스 모듈
여행지 조회, 검색, 추천 등의 비즈니스 로직을 처리합니다.
"""

from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from app.models import Destination


class DestinationService:
    """여행지 관련 비즈니스 로직을 처리하는 서비스 클래스"""

    def get_destinations_by_tags(
        self, db: Session, tags: List[str], limit: Optional[int] = None
    ) -> List[Destination]:
        """
        태그를 기반으로 여행지를 조회합니다.

        Args:
            db: 데이터베이스 세션
            tags: 검색할 태그 목록
            limit: 반환할 최대 개수 (기본값: None = 전체)

        Returns:
            매칭되는 여행지 목록
        """
        query = db.query(Destination)

        # 태그가 제공된 경우, JSONB 컬럼에서 태그 검색
        if tags:
            # PostgreSQL의 JSONB 연산자를 사용하여 태그 검색
            # tags 컬럼이 제공된 태그 중 하나라도 포함하는 경우 반환
            tag_conditions = []
            for tag in tags:
                # JSONB 배열에 특정 값이 포함되어 있는지 확인
                tag_conditions.append(Destination.tags.op("@>")([tag]))

            query = query.filter(or_(*tag_conditions))

        # 결과 개수 제한
        if limit:
            query = query.limit(limit)

        return query.all()

    def get_destination_by_id(
        self, db: Session, destination_id: str
    ) -> Optional[Destination]:
        """
        ID로 특정 여행지를 조회합니다.

        Args:
            db: 데이터베이스 세션
            destination_id: 여행지 ID

        Returns:
            여행지 정보 또는 None
        """
        return (
            db.query(Destination)
            .filter(Destination.destination_id == destination_id)
            .first()
        )

    def get_destinations_by_province(
        self, db: Session, province: str, is_indoor: Optional[bool] = None
    ) -> List[Destination]:
        """
        지역별 여행지를 조회합니다.

        Args:
            db: 데이터베이스 세션
            province: 도/광역시 이름
            is_indoor: 실내/실외 필터 (선택사항)

        Returns:
            해당 지역의 여행지 목록
        """
        query = db.query(Destination).filter(Destination.province == province)

        if is_indoor is not None:
            query = query.filter(Destination.is_indoor == is_indoor)

        return query.all()

    def search_destinations(
        self,
        db: Session,
        keyword: Optional[str] = None,
        category: Optional[str] = None,
        province: Optional[str] = None,
        is_indoor: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        limit: int = 50,
    ) -> List[Destination]:
        """
        다양한 조건으로 여행지를 검색합니다.

        Args:
            db: 데이터베이스 세션
            keyword: 검색 키워드 (이름에서 검색)
            category: 카테고리 필터
            province: 지역 필터
            is_indoor: 실내/실외 필터
            tags: 태그 필터
            limit: 최대 반환 개수

        Returns:
            검색 조건에 맞는 여행지 목록
        """
        query = db.query(Destination)

        # 키워드 검색 (이름에서 검색)
        if keyword:
            query = query.filter(Destination.name.ilike(f"%{keyword}%"))

        # 카테고리 필터
        if category:
            query = query.filter(Destination.category == category)

        # 지역 필터
        if province:
            query = query.filter(Destination.province == province)

        # 실내/실외 필터
        if is_indoor is not None:
            query = query.filter(Destination.is_indoor == is_indoor)

        # 태그 필터
        if tags:
            tag_conditions = []
            for tag in tags:
                tag_conditions.append(Destination.tags.op("@>")([tag]))
            query = query.filter(or_(*tag_conditions))

        return query.limit(limit).all()


# 서비스 인스턴스 생성 (싱글톤 패턴)
destination_service = DestinationService()