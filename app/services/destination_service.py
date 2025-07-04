import uuid

from sqlalchemy.orm import Session

from app.models import Destination, DestinationCreate


class DestinationService:
    def create_destination(
        self, db: Session, destination: DestinationCreate
    ) -> Destination:
        """새로운 여행지 생성"""
        db_destination = Destination(
            name=destination.name,
            province=destination.province,
            region=destination.region,
            category=destination.category,
            is_indoor=destination.is_indoor,
            tags=destination.tags,
            latitude=destination.latitude,
            longitude=destination.longitude,
            amenities=destination.amenities,
            image_url=destination.image_url,
        )
        db.add(db_destination)
        db.commit()
        db.refresh(db_destination)
        return db_destination

    def get_destination_by_id(
        self, db: Session, destination_id: uuid.UUID
    ) -> Destination | None:
        """ID로 여행지 조회"""
        return (
            db.query(Destination)
            .filter(Destination.destination_id == destination_id)
            .first()
        )

    def get_destinations_by_province(
        self, db: Session, province: str, skip: int = 0, limit: int = 100
    ) -> list[Destination]:
        """도/광역시별 여행지 목록 조회"""
        return (
            db.query(Destination)
            .filter(Destination.province == province)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_all_destinations(
        self, db: Session, skip: int = 0, limit: int = 100
    ) -> list[Destination]:
        """모든 여행지 목록 조회"""
        return db.query(Destination).offset(skip).limit(limit).all()

    def get_destinations_by_tags(
        self, db: Session, tags: list[str], skip: int = 0, limit: int = 100
    ) -> list[Destination]:
        """태그로 여행지 목록 조회"""
        query = db.query(Destination)
        for tag in tags:
            query = query.filter(Destination.tags.contains([tag]))
        return query.offset(skip).limit(limit).all()


destination_service = DestinationService()
