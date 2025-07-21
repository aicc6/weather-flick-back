from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

# PostgreSQL 데이터베이스 URL
SQLALCHEMY_DATABASE_URL = settings.database_url

# 엔진 생성 - 안정성 개선
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    pool_size=15,  # 연결 풀 크기 최적화
    max_overflow=25,  # 추가 연결 수 제한
    pool_timeout=60,  # 연결 대기 시간 증가
    pool_pre_ping=True,  # 연결 상태 확인 활성화
    pool_recycle=1800,  # 30분마다 연결 재생성 (안정성 향상)
    echo=settings.debug,  # 디버그 모드에서 SQL 로그 출력
    # 추가 안정성 옵션
    connect_args={
        "connect_timeout": 30,  # 연결 타임아웃
        "application_name": "weather_flick_backend",  # 애플리케이션 식별
        "options": "-c statement_timeout=30000",  # 쿼리 타임아웃 (30초)
    },
    # 연결 검증 강화
    pool_reset_on_return='commit',  # 연결 반환 시 커밋 상태로 리셋
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


# 데이터베이스 의존성 - 안정성 개선
def get_db():
    db = SessionLocal()
    try:
        # 연결 상태 확인
        db.execute(text("SELECT 1"))
        yield db
    except Exception as e:
        db.rollback()
        print(f"Database error: {e}")
        raise
    finally:
        db.close()


# 헬스체크용 데이터베이스 연결 함수
def check_db_connection():
    """데이터베이스 연결 상태 확인"""
    try:
        db = SessionLocal()
        result = db.execute(text("SELECT 1")).fetchone()
        db.close()
        return True, "Database connection successful"
    except Exception as e:
        return False, f"Database connection failed: {str(e)}"


# 연결 풀 상태 확인
def get_pool_status():
    """연결 풀 상태 정보 반환"""
    pool = engine.pool
    return {
        "pool_size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "invalid": pool.invalid(),
    }


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
