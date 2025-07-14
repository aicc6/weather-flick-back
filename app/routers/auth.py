import secrets
from datetime import datetime, timedelta

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    authenticate_user,
    check_password_strength,
    create_access_token,
    create_refresh_token,
    generate_temporary_password,
    get_current_active_user,
    get_password_hash,
    log_user_activity,
    update_user_login_info,
)
from app.database import get_db
from app.exceptions import (
    DatabaseError,
    ValidationError,
)
from app.logging_config import get_logger
from app.models import (
    EmailVerificationConfirm,
    EmailVerificationRequest,
    EmailVerificationResponse,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    GoogleAuthCodeRequest,
    GoogleAuthUrlResponse,
    GoogleLoginRequest,
    GoogleLoginResponse,
    PasswordChange,
    ResendVerificationRequest,
    User,
    UserCreate,
    UserResponse,
    UserUpdate,
    WithdrawRequest,
    WithdrawResponse,
)
from app.schemas import Token, RefreshTokenRequest, RefreshTokenResponse
from app.services.email_service import email_service, email_verification_service
from app.services.google_oauth_service import google_oauth_service

router = APIRouter(prefix="/auth", tags=["authentication"])

# 로거 설정
logger = get_logger("auth")

# 임시 인증 코드 저장소 (프로덕션에서는 Redis 사용 권장)
temp_auth_store: dict[str, dict] = {}


def store_temp_auth(code: str, data: dict, ttl_minutes: int = 10):
    """임시 인증 데이터 저장"""
    expire_time = datetime.now() + timedelta(minutes=ttl_minutes)
    temp_auth_store[code] = {"data": data, "expire_time": expire_time}


def get_temp_auth(code: str) -> dict:
    """임시 인증 데이터 조회 및 삭제"""
    logger.info(f"Looking for temp auth code: {code[:10]}...")
    logger.info(f"Available codes: {[k[:10] + '...' for k in temp_auth_store.keys()]}")

    if code not in temp_auth_store:
        logger.warning(f"Temp auth code not found: {code[:10]}...")
        return None

    stored = temp_auth_store[code]

    # 만료 확인
    if datetime.now() > stored["expire_time"]:
        logger.warning(f"Temp auth code expired: {code[:10]}...")
        del temp_auth_store[code]
        return None

    # 사용 후 삭제 (일회성)
    data = stored["data"]
    del temp_auth_store[code]
    logger.info(f"Temp auth code used successfully: {code[:10]}...")
    return data


def cleanup_expired_auth():
    """만료된 임시 인증 데이터 정리"""
    now = datetime.now()
    expired_codes = [
        code for code, stored in temp_auth_store.items() if now > stored["expire_time"]
    ]
    for code in expired_codes:
        del temp_auth_store[code]


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """회원가입 (이메일 인증 필요)"""
    try:
        logger.info(f"회원가입 시도: {user.email}")

        # 입력값 전처리
        if user.nickname and user.nickname.strip():
            user.nickname = user.nickname.strip()
            
        # 이메일 중복 확인 (활성 사용자만)
        existing_email = (
            db.query(User)
            .filter(
                User.email == user.email,
                User.is_active == True
            )
            .first()
        )
        
        if existing_email:
            logger.warning(f"중복된 이메일로 회원가입 시도: {user.email}")
            raise ValidationError(
                message="이미 등록된 이메일입니다.",
                code="EMAIL_ALREADY_EXISTS",
                details=[
                    {"field": "email", "message": "이미 사용 중인 이메일입니다."}
                ],
            )
        
        # 닉네임 중복 확인 (대소문자 무시, 활성 사용자만)
        from sqlalchemy import func
        existing_nickname = (
            db.query(User)
            .filter(
                func.lower(User.nickname) == func.lower(user.nickname),
                User.is_active == True
            )
            .first()
        )
        
        if existing_nickname:
            logger.warning(f"중복된 닉네임으로 회원가입 시도: {user.nickname}")
            raise ValidationError(
                message="이미 등록된 닉네임입니다.",
                code="NICKNAME_ALREADY_EXISTS",
                details=[
                    {"field": "nickname", "message": "이미 사용 중인 닉네임입니다."}
                ],
            )

        # 비밀번호 강도 검사
        password_check = check_password_strength(user.password)
        if not password_check["is_valid"]:
            logger.warning(f"약한 비밀번호로 회원가입 시도: {user.email}")
            raise ValidationError(
                message="비밀번호가 보안 요구사항을 충족하지 않습니다.",
                code="WEAK_PASSWORD",
                details=[
                    {
                        "field": "password",
                        "message": f"비밀번호 오류: {', '.join(password_check['errors'])}",
                    }
                ],
            )

        # 이메일 인증 확인 (환경 설정에 따라)
        from app.config_email_verification import EMAIL_VERIFICATION_ENABLED
        
        if EMAIL_VERIFICATION_ENABLED:
            if not email_verification_service.is_email_verified(db, user.email):
                logger.warning(f"이메일 미인증 상태로 회원가입 시도: {user.email}")
                raise ValidationError(
                    message="이메일 인증이 필요합니다.",
                    code="EMAIL_NOT_VERIFIED",
                    details=[
                        {"field": "email", "message": "먼저 이메일 인증을 완료해주세요."}
                    ],
                )
        else:
            logger.info(f"이메일 인증이 비활성화되어 있어 건너뜁니다: {user.email}")

        # 새 사용자 생성
        hashed_password = get_password_hash(user.password)
        db_user = User(
            email=user.email,
            nickname=user.nickname,
            hashed_password=hashed_password,
            is_email_verified=True,
        )
        db.add(db_user)
        db.commit()
        db.refresh(db_user)

        logger.info(f"회원가입 완료: {user.email}")

        # 환영 이메일 발송 (에러가 발생해도 회원가입은 완료됨)
        try:
            await email_service.send_welcome_email(user.email, user.nickname)
            logger.info(f"환영 이메일 발송 완료: {user.email}")
        except Exception as e:
            logger.warning(
                f"환영 이메일 발송 실패 (회원가입은 완료됨): {user.email}, 오류: {str(e)}"
            )

        return db_user

    except ValidationError:
        # ValidationError는 그대로 전파
        raise
    except Exception as e:
        logger.error(f"회원가입 중 예상치 못한 오류 발생: {user.email}, 오류: {str(e)}")
        db.rollback()
        raise DatabaseError(
            message="회원가입 처리 중 오류가 발생했습니다.", code="REGISTRATION_FAILED"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """로그인"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 로그인 정보 업데이트
    if request:
        update_user_login_info(db, user, request)

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    
    # refresh token 생성
    refresh_token = create_refresh_token(
        data={"sub": user.email}
    )

    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_info": user,
    }


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None,
):
    """로그아웃"""
    if request:
        log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="logout",
            description="User logged out",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent"),
        )

    return {"message": "Successfully logged out"}


@router.post("/refresh", response_model=RefreshTokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    """Refresh token으로 새로운 access token 발급"""
    from jose import JWTError, jwt
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # refresh token 검증
        from app.auth import SECRET_KEY, ALGORITHM
        payload = jwt.decode(request.refresh_token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        token_type: str = payload.get("type")
        
        if email is None or token_type != "refresh":
            raise credentials_exception
            
        # 사용자 확인
        user = db.query(User).filter(User.email == email).first()
        if user is None or not user.is_active:
            raise credentials_exception
            
        # 새로운 access token 발급
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email, "role": user.role.value},
            expires_delta=access_token_expires,
        )
        
        return {
            "access_token": access_token,
            "token_type": "bearer"
        }
        
    except JWTError:
        raise credentials_exception


@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """현재 사용자 정보 조회"""
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """사용자 프로필 업데이트"""
    if user_update.nickname and user_update.nickname.strip():
        user_update.nickname = user_update.nickname.strip()  # 공백 제거
        logger.info(f"닉네임 업데이트 시도: {current_user.email} -> {user_update.nickname}")
        logger.info(f"현재 사용자 ID: {current_user.id} (type: {type(current_user.id)})")
        logger.info(f"현재 사용자 user_id: {current_user.user_id} (type: {type(current_user.user_id)})")
        
        # 현재 닉네임과 동일한 경우 스킵
        if current_user.nickname and current_user.nickname.lower() == user_update.nickname.lower():
            logger.info(f"동일한 닉네임으로 변경 시도, 스킵: {user_update.nickname}")
        else:
            # 사용자명 중복 확인 (활성 사용자만, 대소문자 구분 없이)
            from sqlalchemy import func
            existing_user = (
                db.query(User)
                .filter(
                    func.lower(User.nickname) == func.lower(user_update.nickname), 
                    User.user_id != current_user.user_id,  # user_id 사용으로 변경
                    User.is_active == True  # 활성 사용자만 중복 체크
                )
                .first()
            )
            
            if existing_user:
                logger.warning(f"닉네임 중복 발견: {user_update.nickname} - 기존 사용자 ID: {existing_user.user_id}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
                )
            
            logger.info(f"닉네임 중복 체크 통과: {user_update.nickname}")
            current_user.nickname = user_update.nickname

    if user_update.profile_image is not None:
        current_user.profile_image = user_update.profile_image

    if user_update.preferences is not None:
        current_user.preferences = user_update.preferences

    if user_update.preferred_region is not None:
        current_user.preferred_region = user_update.preferred_region

    if user_update.preferred_theme is not None:
        current_user.preferred_theme = user_update.preferred_theme

    if user_update.bio is not None:
        current_user.bio = user_update.bio

    db.commit()
    db.refresh(current_user)
    return current_user


@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """비밀번호 변경"""
    # 현재 비밀번호 확인
    from app.auth import verify_password

    if not verify_password(
        password_change.current_password, current_user.hashed_password
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    # 새 비밀번호 강도 검사
    password_check = check_password_strength(password_change.new_password)
    if not password_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too weak: {', '.join(password_check['errors'])}",
        )

    # 비밀번호 변경
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()

    return {"message": "Password changed successfully"}


# 구글 OAuth 엔드포인트들
@router.get("/google/auth-url", response_model=GoogleAuthUrlResponse)
async def get_google_auth_url():
    """구글 OAuth 인증 URL 생성"""
    state = secrets.token_urlsafe(32)

    auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={google_oauth_service.client_id}&"
        f"redirect_uri={google_oauth_service.redirect_uri}&"
        f"response_type=code&"
        f"scope=openid%20email%20profile&"
        f"state={state}"
    )

    return GoogleAuthUrlResponse(auth_url=auth_url, state=state)


@router.post("/google/login", response_model=GoogleLoginResponse)
async def google_login(
    request: GoogleLoginRequest,
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """구글 ID 토큰으로 로그인"""
    try:
        # 구글 ID 토큰 검증
        google_data = await google_oauth_service.verify_google_token(request.id_token)

        # 사용자 생성 또는 업데이트
        user = await google_oauth_service.create_or_update_user(
            db, google_data, http_request
        )

        # 액세스 토큰 생성
        access_token = google_oauth_service.create_access_token_for_user(user)
        
        # refresh token 생성
        refresh_token = create_refresh_token(
            data={"sub": user.email}
        )

        # 새 사용자 여부 확인
        is_new_user = user.created_at == user.updated_at

        return GoogleLoginResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info=user,
            is_new_user=is_new_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google login failed: {str(e)}",
        )


@router.get("/google/callback")
async def google_callback(code: str, state: str, request: Request = None):
    """구글 OAuth 콜백 처리 - 임시 코드 생성"""
    try:
        logger.info(
            f"Google OAuth callback received - code: {code[:10]}..., state: {state}"
        )

        # 만료된 임시 코드 정리
        cleanup_expired_auth()

        # 임시 인증 코드 생성
        temp_code = secrets.token_urlsafe(32)

        # 구글 인증 데이터를 임시 저장 (5분 TTL)
        store_temp_auth(
            temp_code,
            {
                "google_code": code,
                "state": state,
                "ip_address": request.client.host if request else None,
                "user_agent": request.headers.get("User-Agent") if request else None,
            },
        )

        logger.info(f"Temp auth code stored: {temp_code[:10]}... (expires in 10min)")
        logger.info(f"Current temp_auth_store size: {len(temp_auth_store)}")

        # 프론트엔드로 임시 코드와 함께 리다이렉트 (토큰 없이)
        from app.config import settings

        frontend_url = (
            f"{settings.frontend_url}/auth/google/callback?auth_code={temp_code}"
        )
        logger.info(
            f"Google OAuth callback - redirecting with temp code: {temp_code[:10]}..."
        )
        return RedirectResponse(url=frontend_url, status_code=302)

    except Exception as e:
        logger.error(f"Google callback failed: {str(e)}")
        # 에러 시에도 프론트엔드로 리다이렉트
        from app.config import settings

        error_url = f"{settings.frontend_url}/auth/google/callback?error=oauth_failed"
        return RedirectResponse(url=error_url, status_code=302)


@router.post("/google/exchange", response_model=GoogleLoginResponse)
async def exchange_google_auth_code(
    request_data: GoogleAuthCodeRequest,
    db: Session = Depends(get_db),
    request: Request = None,
):
    """임시 인증 코드를 JWT 토큰으로 교환"""
    try:
        auth_code = request_data.auth_code
        logger.info(f"Exchange request received - auth_code: {auth_code[:10]}...")

        if not auth_code:
            logger.error("No auth_code provided in request")
            raise HTTPException(status_code=400, detail="auth_code is required")

        # 임시 인증 데이터 조회
        temp_data = get_temp_auth(auth_code)
        if not temp_data:
            logger.error(f"Invalid or expired auth code: {auth_code[:10]}...")
            logger.info(f"Current temp_auth_store keys: {list(temp_auth_store.keys())}")
            raise HTTPException(status_code=400, detail="Invalid or expired auth code")

        logger.info(f"Temp auth data found for code: {auth_code[:10]}...")

        google_code = temp_data["google_code"]
        # state = temp_data["state"]  # 현재 사용하지 않음

        logger.info(f"Processing Google auth exchange for code: {google_code[:10]}...")

        # 구글 액세스 토큰 교환
        async with httpx.AsyncClient() as client:
            token_data = {
                "client_id": google_oauth_service.client_id,
                "client_secret": google_oauth_service.client_secret,
                "code": google_code,
                "grant_type": "authorization_code",
                "redirect_uri": google_oauth_service.redirect_uri,
            }

            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data=token_data,
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )

            if token_response.status_code != 200:
                logger.error(
                    f"Token exchange failed - Status: {token_response.status_code}"
                )
                raise HTTPException(
                    status_code=400,
                    detail="Failed to exchange Google authorization code",
                )

            token_response_data = token_response.json()
            access_token = token_response_data.get("access_token")

            if not access_token:
                raise HTTPException(
                    status_code=400, detail="No access token received from Google"
                )

        # 사용자 정보 조회
        user_info = await google_oauth_service.get_google_user_info(access_token)
        logger.info(f"User info retrieved: {user_info.get('email')}")

        # 사용자 생성 또는 업데이트
        user = await google_oauth_service.create_or_update_user(db, user_info, request)

        # JWT 토큰 생성
        jwt_token = google_oauth_service.create_access_token_for_user(user)
        
        # refresh token 생성
        refresh_token = create_refresh_token(
            data={"sub": user.email}
        )

        # 새 사용자 여부 확인
        is_new_user = user.created_at == user.updated_at

        logger.info(f"Google OAuth exchange successful for user: {user.email}")

        return GoogleLoginResponse(
            access_token=jwt_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user_info=user,
            is_new_user=is_new_user,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Google auth exchange failed: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google auth exchange failed: {str(e)}",
        )


@router.post("/google/link", response_model=UserResponse)
async def link_google_account(
    request: GoogleLoginRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
):
    """기존 계정에 구글 계정 연결"""
    try:
        # 구글 ID 토큰 검증
        google_data = await google_oauth_service.verify_google_token(request.id_token)

        # 이미 다른 사용자가 사용 중인지 확인
        existing_user = (
            db.query(User)
            .filter(
                (User.google_id == google_data["google_id"])
                | (User.email == google_data["email"])
            )
            .first()
        )

        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=400,
                detail="This Google account is already linked to another user",
            )

        # 현재 사용자에 구글 계정 연결
        current_user.google_id = google_data["google_id"]
        current_user.is_email_verified = google_data.get("email_verified", False)
        current_user.profile_image = google_data.get(
            "picture", current_user.profile_image
        )

        db.commit()
        db.refresh(current_user)

        return current_user

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to link Google account: {str(e)}",
        )


# 이메일 인증 관련 엔드포인트들
@router.post("/send-verification", response_model=EmailVerificationResponse)
async def send_email_verification(
    request: EmailVerificationRequest, db: Session = Depends(get_db)
):
    """이메일 인증 코드 발송"""
    try:
        # 이미 가입된 이메일인지 확인 (활성 사용자만)
        existing_user = db.query(User.email).filter(
            User.email == request.email,
            User.is_active == True  # 활성 사용자만 확인
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # 인증 코드 생성 및 이메일 발송
        verification_code = await email_verification_service.create_verification(
            db, request.email, request.nickname
        )

        if verification_code:
            return EmailVerificationResponse(
                message="Verification code sent successfully", success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to send verification email",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send verification: {str(e)}",
        )


@router.post("/verify-email", response_model=EmailVerificationResponse)
async def verify_email(
    request: EmailVerificationConfirm, db: Session = Depends(get_db)
):
    """이메일 인증 코드 확인"""
    try:
        # 인증 코드 검증
        is_valid = email_verification_service.verify_code(
            db, request.email, request.code
        )

        if is_valid:
            return EmailVerificationResponse(
                message="Email verified successfully", success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Verification failed: {str(e)}",
        )


@router.post("/resend-verification", response_model=EmailVerificationResponse)
async def resend_verification(
    request: ResendVerificationRequest, db: Session = Depends(get_db)
):
    """인증 코드 재발송"""
    try:
        # 이미 가입된 이메일인지 확인 (활성 사용자만)
        existing_user = db.query(User.email).filter(
            User.email == request.email,
            User.is_active == True  # 활성 사용자만 확인
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # 인증 코드 재발송
        verification_code = await email_verification_service.create_verification(
            db, request.email, request.nickname
        )

        if verification_code:
            return EmailVerificationResponse(
                message="Verification code resent successfully", success=True
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to resend verification email",
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to resend verification: {str(e)}",
        )


@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest, 
    db: Session = Depends(get_db),
    http_request: Request = None,
):
    """비밀번호 찾기 - 임시 비밀번호 발급"""
    try:
        logger.info(f"비밀번호 찾기 요청: {request.email}")
        
        # 이메일로 사용자 조회
        user = db.query(User).filter(User.email == request.email).first()
        if not user:
            logger.warning(f"존재하지 않는 이메일로 비밀번호 찾기 시도: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="해당 이메일로 등록된 계정을 찾을 수 없습니다.",
            )
        
        # 비활성화된 계정 확인
        if not user.is_active:
            logger.warning(f"비활성화된 계정으로 비밀번호 찾기 시도: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="비활성화된 계정입니다. 고객센터에 문의하세요.",
            )
        
        # OAuth 계정 확인 (구글 계정 등)
        if user.google_id and user.auth_provider != "local":
            logger.warning(f"OAuth 계정으로 비밀번호 찾기 시도: {request.email}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="소셜 로그인 계정입니다. 해당 서비스를 통해 로그인해주세요.",
            )
        
        # 임시 비밀번호 생성
        temp_password = generate_temporary_password()
        
        # 데이터베이스에 임시 비밀번호 저장
        user.hashed_password = get_password_hash(temp_password)
        db.commit()
        
        logger.info(f"임시 비밀번호 생성 완료: {request.email}")
        
        # 이메일로 임시 비밀번호 전송
        try:
            await email_service.send_temporary_password_email(
                email=request.email,
                temporary_password=temp_password,
                nickname=user.nickname
            )
            
            logger.info(f"임시 비밀번호 이메일 발송 완료: {request.email}")
            
            # 사용자 활동 로그 기록
            if http_request:
                log_user_activity(
                    db=db,
                    user_id=user.id,
                    activity_type="password_reset",
                    description="Temporary password issued",
                    ip_address=http_request.client.host if http_request.client else None,
                    user_agent=http_request.headers.get("User-Agent") if http_request else None,
                )
            
            return ForgotPasswordResponse(
                message="임시 비밀번호가 이메일로 전송되었습니다. 로그인 후 새로운 비밀번호로 변경해주세요.",
                success=True
            )
            
        except Exception as email_error:
            logger.error(f"임시 비밀번호 이메일 발송 실패: {request.email}, 오류: {str(email_error)}")
            
            # 이메일 발송 실패 시에도 임시 비밀번호는 이미 설정되었으므로
            # 사용자에게 알림 (실제 서비스에서는 다른 방식으로 전달)
            return ForgotPasswordResponse(
                message="임시 비밀번호가 발급되었으나 이메일 전송에 실패했습니다. 고객센터에 문의하세요.",
                success=False
            )
    
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        logger.error(f"비밀번호 찾기 중 예상치 못한 오류 발생: {request.email}, 오류: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="비밀번호 찾기 처리 중 오류가 발생했습니다.",
        )


@router.delete("/withdraw", response_model=WithdrawResponse)
async def withdraw_user(
    request: WithdrawRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    http_request: Request = None,
):
    """회원탈퇴"""
    try:
        logger.info(f"회원탈퇴 요청: {current_user.email}")
        
        # 소셜 로그인 사용자가 아닌 경우 비밀번호 확인
        if current_user.auth_provider == "local" and current_user.hashed_password:
            if not request.password:
                logger.warning(f"비밀번호 누락으로 회원탈퇴 실패: {current_user.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="비밀번호를 입력해주세요.",
                )
            
            # 비밀번호 확인
            if not authenticate_user(db, current_user.email, request.password):
                logger.warning(f"잘못된 비밀번호로 회원탈퇴 시도: {current_user.email}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="비밀번호가 일치하지 않습니다.",
                )
        
        # 사용자 계정 비활성화 (소프트 삭제) 및 이메일 마스킹
        current_user.is_active = False
        current_user.email = f"deleted_{current_user.user_id}_{current_user.email}"
        current_user.updated_at = datetime.utcnow()
        
        # 탈퇴 사유가 있는 경우 로그에 기록
        if request.reason:
            logger.info(f"회원탈퇴 사유: {current_user.email} - {request.reason}")
        
        # 사용자 활동 로그 기록
        if http_request:
            log_user_activity(
                db=db,
                user_id=current_user.id,
                activity_type="account_withdrawal",
                description=f"Account withdrawn. Reason: {request.reason or 'No reason provided'}",
                ip_address=http_request.client.host if http_request.client else None,
                user_agent=http_request.headers.get("User-Agent") if http_request else None,
            )
        
        db.commit()
        
        logger.info(f"회원탈퇴 완료: {current_user.email}")
        
        return WithdrawResponse(
            message="회원탈퇴가 완료되었습니다. 그동안 서비스를 이용해주셔서 감사합니다.",
            success=True
        )
        
    except HTTPException:
        # HTTPException은 그대로 전파
        raise
    except Exception as e:
        logger.error(f"회원탈퇴 중 예상치 못한 오류 발생: {current_user.email}, 오류: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="회원탈퇴 처리 중 오류가 발생했습니다.",
        )
