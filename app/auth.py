from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import TokenData, User, UserRole

# 비밀번호 해싱 설정
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer 스키마
bearer_scheme = HTTPBearer()

# Optional Bearer 스키마 (인증 선택적)
optional_bearer_scheme = HTTPBearer(auto_error=False)

# JWT 설정
SECRET_KEY = settings.secret_key
ALGORITHM = settings.algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.access_token_expire_minutes


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """비밀번호 검증"""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """비밀번호 해싱"""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """JWT 액세스 토큰 생성"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict):
    """JWT 리프레시 토큰 생성"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=7)  # 7일 유효
    to_encode.update({"exp": expire, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str, credentials_exception):
    """토큰 검증"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        role: str = payload.get("role")
        if email is None:
            raise credentials_exception
        token_data = TokenData(email=email, role=role)
    except JWTError as e:
        raise credentials_exception from e
    return token_data


def authenticate_user(db: Session, email: str, password: str):
    """사용자 인증"""
    user = db.query(User).filter(User.email == email).first()
    if not user:
        return False
    if not user.is_active:
        return False
    if not verify_password(password, user.hashed_password):
        return False
    return user


def log_user_activity(
    db: Session,
    user_id,
    activity_type: str,
    description: str = None,
    ip_address: str = None,
    user_agent: str = None,
):
    """사용자 활동 로깅 - UserActivity 테이블이 삭제되어 비활성화됨"""
    # TODO: 필요시 다른 로깅 방식으로 대체
    pass


def get_client_ip(request: Request) -> str:
    """클라이언트 IP 주소 가져오기"""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0]
    return request.client.host


def get_current_user(token=Depends(bearer_scheme), db: Session = Depends(get_db)):
    """현재 사용자 조회"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    token_data = verify_token(token.credentials, credentials_exception)
    user = db.query(User).filter(User.email == token_data.email).first()
    if user is None:
        raise credentials_exception
    return user


def get_current_user_optional(
    token=Depends(optional_bearer_scheme),
    db: Session = Depends(get_db)
) -> User | None:
    """
    현재 사용자 조회 (선택적)
    토큰이 없거나 유효하지 않으면 None을 반환합니다.
    """
    if token is None:
        return None

    try:
        credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
        token_data = verify_token(token.credentials, credentials_exception)
        user = db.query(User).filter(User.email == token_data.email).first()
        return user
    except (HTTPException, JWTError):
        # 토큰이 유효하지 않으면 None 반환 (에러 발생시키지 않음)
        return None


def get_current_active_user(current_user: User = Depends(get_current_user)):
    """현재 활성 사용자 조회"""
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


def get_current_admin_user(current_user: User = Depends(get_current_active_user)):
    """현재 관리자 사용자 조회"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions"
        )
    return current_user


def get_current_super_admin_user(current_user: User = Depends(get_current_active_user)):
    """현재 슈퍼 관리자 사용자 조회"""
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required"
        )
    return current_user


def update_user_login_info(db: Session, user: User, request: Request):
    """사용자 로그인 정보 업데이트"""
    user.last_login = datetime.utcnow()
    user.login_count = (user.login_count or 0) + 1
    db.commit()

    # 로그인 활동 로깅
    log_user_activity(
        db=db,
        user_id=user.id,
        activity_type="login",
        description=f"User logged in from {get_client_ip(request)}",
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )


def check_password_strength(password: str) -> dict:
    """비밀번호 강도 검사"""
    errors = []
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        errors.append("Password must contain at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("Password must contain at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("Password must contain at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        errors.append("Password must contain at least one special character")

    return {
        "is_valid": len(errors) == 0,
        "errors": errors,
        "strength": "strong" if len(errors) == 0 else "weak",
    }


def generate_temporary_password(length: int = 12) -> str:
    """
    보안 강화된 임시 비밀번호 생성

    Args:
        length: 비밀번호 길이 (기본값: 12)

    Returns:
        str: 생성된 임시 비밀번호
    """
    import secrets
    import string

    # 각 문자 유형별로 최소 1개씩 포함
    lowercase = string.ascii_lowercase
    uppercase = string.ascii_uppercase
    digits = string.digits
    special_chars = "!@#$%^&*"  # 호환성을 위해 제한된 특수문자 사용

    # 각 유형에서 최소 1개씩 선택
    password_chars = [
        secrets.choice(lowercase),
        secrets.choice(uppercase),
        secrets.choice(digits),
        secrets.choice(special_chars)
    ]

    # 나머지 자리는 모든 문자에서 랜덤 선택
    all_chars = lowercase + uppercase + digits + special_chars
    for _ in range(length - 4):
        password_chars.append(secrets.choice(all_chars))

    # 문자 순서 섞기 (패턴 예측 방지)
    secrets.SystemRandom().shuffle(password_chars)

    return ''.join(password_chars)
