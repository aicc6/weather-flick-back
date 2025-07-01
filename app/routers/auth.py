from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import (
    User,
    UserCreate,
    UserResponse,
    Token,
    UserUpdate,
    PasswordChange,
    GoogleLoginRequest,
    GoogleLoginResponse,
    GoogleAuthUrlResponse,
    EmailVerificationRequest,
    EmailVerificationConfirm,
    EmailVerificationResponse,
    ResendVerificationRequest,
)
from app.auth import (
    authenticate_user,
    create_access_token,
    get_password_hash,
    get_current_active_user,
    update_user_login_info,
    log_user_activity,
    check_password_strength,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from app.services.google_oauth_service import google_oauth_service
from app.services.email_service import email_verification_service, email_service
import secrets
import httpx
import requests

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """회원가입 (이메일 인증 필요)"""
    # 이메일 중복 확인
    db_user = db.query(User.email).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered"
        )

    # 사용자명 중복 확인
    db_user = db.query(User.nickname).filter(User.nickname == user.nickname).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
        )

    # 비밀번호 강도 검사
    password_check = check_password_strength(user.password)
    if not password_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too weak: {', '.join(password_check['errors'])}",
        )

    # 이메일 인증 확인
    if not email_verification_service.is_email_verified(db, user.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email verification required. Please verify your email first.",
        )

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

    # 환영 이메일 발송
    await email_service.send_welcome_email(user.email, user.nickname)

    return db_user


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

    return {
        "access_token": access_token,
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
    if user_update.nickname:
        # 사용자명 중복 확인
        existing_user = (
            db.query(User)
            .filter(User.nickname == user_update.nickname, User.id != current_user.id)
            .first()
        )
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Username already taken"
            )
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

        # 새 사용자 여부 확인
        is_new_user = user.created_at == user.updated_at

        return GoogleLoginResponse(
            access_token=access_token,
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
async def google_callback(
    code: str, state: str, db: Session = Depends(get_db), request: Request = None
):
    """구글 OAuth 콜백 처리"""
    try:
        # 액세스 토큰 교환
        async with httpx.AsyncClient() as client:
            token_response = await client.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": google_oauth_service.client_id,
                    "client_secret": google_oauth_service.client_secret,
                    "code": code,
                    "grant_type": "authorization_code",
                    "redirect_uri": google_oauth_service.redirect_uri,
                },
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Failed to exchange token")

            token_data = token_response.json()
            access_token = token_data.get("access_token")

            if not access_token:
                raise HTTPException(status_code=400, detail="No access token received")

        # 사용자 정보 조회
        user_info = await google_oauth_service.get_google_user_info(access_token)

        # 사용자 생성 또는 업데이트
        user = await google_oauth_service.create_or_update_user(db, user_info, request)

        # 액세스 토큰 생성
        jwt_token = google_oauth_service.create_access_token_for_user(user)

        # 프론트엔드로 리다이렉트 (토큰 포함)
        redirect_url = f"/auth/success?token={jwt_token}&user_id={user.id}"
        return {"redirect_url": redirect_url}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Google callback failed: {str(e)}",
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
        # 이미 가입된 이메일인지 확인
        existing_user = db.query(User.email).filter(User.email == request.email).first()
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
        # 이미 가입된 이메일인지 확인
        existing_user = db.query(User.email).filter(User.email == request.email).first()
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


@router.post("/google", response_model=Token)
def google_login(data: dict, db: Session = Depends(get_db)):
    """구글 소셜 로그인/회원가입"""
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided")

    # 구글에서 사용자 정보 가져오기
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    if not userinfo_response.ok:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    userinfo = userinfo_response.json()
    email = userinfo["email"]
    username = userinfo.get("name", email.split("@")[0])

    # 이미 가입된 사용자면 로그인, 아니면 회원가입
    existing_user_check = db.query(User.email).filter(User.email == email).first()
    user = (
        db.query(User).filter(User.email == email).first()
        if existing_user_check
        else None
    )
    if not user:
        from app.auth import get_password_hash

        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(
                access_token
            ),  # 소셜 로그인은 access_token 등으로 대체
            is_email_verified=True,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    from app.auth import create_access_token

    token = create_access_token(data={"sub": user.email, "role": user.role.value})
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_info": user,
    }
