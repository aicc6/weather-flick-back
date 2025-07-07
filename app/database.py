from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings


# PostgreSQL 데이터베이스 URL
SQLALCHEMY_DATABASE_URL = settings.database_url

# 엔진 생성
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=20,  # 기본 연결 수 증가
    max_overflow=30,  # 추가 연결 수 설정
    pool_timeout=30,  # 연결 대기 시간
    pool_pre_ping=True,  # 연결 상태 확인
    pool_recycle=3600,  # 1시간마다 연결 재생성
    echo=settings.debug,  # 디버그 모드에서 SQL 로그 출력
)

# SQLAlchemy 메타데이터 캐시 강제 새로고침
from sqlalchemy import MetaData

metadata = MetaData()
try:
    metadata.reflect(bind=engine)
    # Clear any cached metadata
    metadata.clear()
except Exception as e:
    print(f"Metadata reflection warning: {e}")

# 세션 팩토리 생성
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Base 클래스
Base = declarative_base()


# 데이터베이스 의존성
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 트랜잭션 관리 컨텍스트 매니저
from contextlib import contextmanager


@contextmanager
def db_transaction(db: Session):
    """트랜잭션 관리를 위한 컨텍스트 매니저"""
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
