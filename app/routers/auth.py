from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from app.database import get_db
from app.models import (
    User, UserCreate, UserResponse, UserListResponse, Token, UserUpdate,
    UserAdminUpdate, PasswordChange, PasswordReset, PasswordResetConfirm,
    AdminStats, UserActivityResponse, UserRole
)
from app.auth import (
    authenticate_user, create_access_token, get_password_hash,
    get_current_active_user, get_current_admin_user, get_current_super_admin_user,
    update_user_login_info, log_user_activity, check_password_strength,
    ACCESS_TOKEN_EXPIRE_MINUTES
)
import requests

router = APIRouter(
    prefix="/auth",
    tags=["authentication"]
)

@router.post("/register", response_model=UserResponse)
async def register(user: UserCreate, db: Session = Depends(get_db)):
    """회원가입"""
    # 이메일 중복 확인
    db_user = db.query(User).filter(User.email == user.email).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # 사용자명 중복 확인
    db_user = db.query(User).filter(User.username == user.username).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken"
        )

    # 비밀번호 강도 검사
    password_check = check_password_strength(user.password)
    if not password_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too weak: {', '.join(password_check['errors'])}"
        )

    # 새 사용자 생성
    hashed_password = get_password_hash(user.password)
    db_user = User(
        email=user.email,
        username=user.username,
        hashed_password=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user

@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
    request: Request = None
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
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user_info": user
    }

@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    request: Request = None
):
    """로그아웃"""
    if request:
        log_user_activity(
            db=db,
            user_id=current_user.id,
            activity_type="logout",
            description="User logged out",
            ip_address=request.client.host,
            user_agent=request.headers.get("User-Agent")
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
    db: Session = Depends(get_db)
):
    """사용자 프로필 업데이트"""
    if user_update.username:
        # 사용자명 중복 확인
        existing_user = db.query(User).filter(
            User.username == user_update.username,
            User.id != current_user.id
        ).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        current_user.username = user_update.username

    if user_update.bio is not None:
        current_user.bio = user_update.bio

    if user_update.profile_image is not None:
        current_user.profile_image = user_update.profile_image

    db.commit()
    db.refresh(current_user)
    return current_user

@router.post("/change-password")
async def change_password(
    password_change: PasswordChange,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """비밀번호 변경"""
    # 현재 비밀번호 확인
    from app.auth import verify_password
    if not verify_password(password_change.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect"
        )

    # 새 비밀번호 강도 검사
    password_check = check_password_strength(password_change.new_password)
    if not password_check["is_valid"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password is too weak: {', '.join(password_check['errors'])}"
        )

    # 비밀번호 변경
    current_user.hashed_password = get_password_hash(password_change.new_password)
    db.commit()

    return {"message": "Password changed successfully"}

# 관리자 전용 엔드포인트
@router.get("/admin/users", response_model=List[UserListResponse])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role: Optional[UserRole] = None,
    is_active: Optional[bool] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """모든 사용자 목록 조회 (관리자 전용)"""
    query = db.query(User)

    if search:
        query = query.filter(
            (User.email.contains(search)) |
            (User.username.contains(search))
        )

    if role:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    users = query.offset(skip).limit(limit).all()
    return users

@router.get("/admin/users/{user_id}", response_model=UserResponse)
async def get_user_by_id(
    user_id: int,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """특정 사용자 정보 조회 (관리자 전용)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    return user

@router.put("/admin/users/{user_id}", response_model=UserResponse)
async def update_user_by_admin(
    user_id: int,
    user_update: UserAdminUpdate,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 정보 관리자 수정 (슈퍼 관리자 전용)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 이메일 변경 시 중복 확인
    if user_update.email and user_update.email != user.email:
        existing_user = db.query(User).filter(User.email == user_update.email).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        user.email = user_update.email

    # 사용자명 변경 시 중복 확인
    if user_update.username and user_update.username != user.username:
        existing_user = db.query(User).filter(User.username == user_update.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already taken"
            )
        user.username = user_update.username

    # 다른 필드들 업데이트
    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    if user_update.is_verified is not None:
        user.is_verified = user_update.is_verified

    if user_update.role is not None:
        user.role = user_update.role

    if user_update.bio is not None:
        user.bio = user_update.bio

    if user_update.profile_image is not None:
        user.profile_image = user_update.profile_image

    db.commit()
    db.refresh(user)
    return user

@router.delete("/admin/users/{user_id}")
async def delete_user_by_admin(
    user_id: int,
    current_admin: User = Depends(get_current_super_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 삭제 (슈퍼 관리자 전용)"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    # 자기 자신은 삭제할 수 없음
    if user.id == current_admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself"
        )

    db.delete(user)
    db.commit()

    return {"message": "User deleted successfully"}

@router.get("/admin/stats", response_model=AdminStats)
async def get_admin_stats(
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """관리자 통계 조회"""
    from datetime import datetime, timedelta

    now = datetime.utcnow()
    today = now.date()
    week_ago = now - timedelta(days=7)
    month_ago = now - timedelta(days=30)

    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    verified_users = db.query(User).filter(User.is_verified == True).count()
    admin_users = db.query(User).filter(User.role == UserRole.ADMIN).count()
    moderator_users = db.query(User).filter(User.role == UserRole.MODERATOR).count()

    today_logins = db.query(User).filter(
        User.last_login >= today
    ).count()

    this_week_logins = db.query(User).filter(
        User.last_login >= week_ago
    ).count()

    this_month_logins = db.query(User).filter(
        User.last_login >= month_ago
    ).count()

    return AdminStats(
        total_users=total_users,
        active_users=active_users,
        verified_users=verified_users,
        admin_users=admin_users,
        moderator_users=moderator_users,
        today_logins=today_logins,
        this_week_logins=this_week_logins,
        this_month_logins=this_month_logins
    )

@router.get("/admin/activities", response_model=List[UserActivityResponse])
async def get_user_activities(
    skip: int = 0,
    limit: int = 100,
    user_id: Optional[int] = None,
    activity_type: Optional[str] = None,
    current_admin: User = Depends(get_current_admin_user),
    db: Session = Depends(get_db)
):
    """사용자 활동 로그 조회 (관리자 전용)"""
    from app.models import UserActivity

    query = db.query(UserActivity)

    if user_id:
        query = query.filter(UserActivity.user_id == user_id)

    if activity_type:
        query = query.filter(UserActivity.activity_type == activity_type)

    activities = query.order_by(desc(UserActivity.created_at)).offset(skip).limit(limit).all()
    return activities

@router.post("/google", response_model=Token)
def google_login(data: dict, db: Session = Depends(get_db)):
    """구글 소셜 로그인/회원가입"""
    access_token = data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="No access token provided")

    # 구글에서 사용자 정보 가져오기
    userinfo_response = requests.get(
        "https://www.googleapis.com/oauth2/v3/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    if not userinfo_response.ok:
        raise HTTPException(status_code=400, detail="Invalid Google token")

    userinfo = userinfo_response.json()
    email = userinfo["email"]
    username = userinfo.get("name", email.split("@")[0])

    # 이미 가입된 사용자면 로그인, 아니면 회원가입
    user = db.query(User).filter(User.email == email).first()
    if not user:
        from app.auth import get_password_hash
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(access_token),  # 소셜 로그인은 access_token 등으로 대체
            is_verified=True,
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
        "user_info": user
    }
