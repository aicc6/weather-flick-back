import httpx
from typing import Optional, Dict, Any
from fastapi import HTTPException
from google.oauth2 import id_token
from google.auth.transport import requests
from app.config import settings
from app.models import User, UserRole
from sqlalchemy.orm import Session
from app.auth import get_password_hash, create_access_token, log_user_activity
from datetime import timedelta

class GoogleOAuthService:
    """구글 OAuth 인증 서비스"""

    def __init__(self):
        self.client_id = settings.google_client_id
        self.client_secret = settings.google_client_secret
        self.redirect_uri = settings.google_redirect_uri

    async def verify_google_token(self, token: str) -> Dict[str, Any]:
        """구글 ID 토큰 검증"""
        try:
            # 구글 ID 토큰 검증
            idinfo = id_token.verify_oauth2_token(
                token,
                requests.Request(),
                self.client_id
            )

            # 토큰이 유효한지 확인
            if idinfo['aud'] != self.client_id:
                raise ValueError('Wrong audience.')

            if idinfo['iss'] not in ['accounts.google.com', 'https://accounts.google.com']:
                raise ValueError('Wrong issuer.')

            return {
                'google_id': idinfo['sub'],
                'email': idinfo['email'],
                'name': idinfo.get('name', ''),
                'picture': idinfo.get('picture', ''),
                'email_verified': idinfo.get('email_verified', False)
            }

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid token: {str(e)}")
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Token verification failed: {str(e)}")

    async def get_google_user_info(self, access_token: str) -> Dict[str, Any]:
        """구글 액세스 토큰으로 사용자 정보 조회"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.googleapis.com/oauth2/v2/userinfo",
                    headers={"Authorization": f"Bearer {access_token}"}
                )

                if response.status_code == 200:
                    user_data = response.json()
                    # google_id 필드 추가 (OAuth callback에서 사용)
                    return {
                        'google_id': user_data.get('id'),
                        'email': user_data.get('email'),
                        'name': user_data.get('name', ''),
                        'picture': user_data.get('picture', ''),
                        'email_verified': user_data.get('verified_email', False)
                    }
                else:
                    raise HTTPException(status_code=400, detail="Failed to get user info from Google")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")

    async def create_or_update_user(self, db: Session, google_data: Dict[str, Any], request=None) -> User:
        """구글 사용자 정보로 사용자 생성 또는 업데이트"""
        google_id = google_data['google_id']
        email = google_data['email']

        # 기존 사용자 확인
        user = db.query(User).filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()

        if user:
            # 기존 사용자 업데이트
            user.google_id = google_id
            user.is_email_verified = google_data.get('email_verified', False)
            user.profile_image = google_data.get('picture', user.profile_image)
            user.auth_provider = "google"

            # 로그인 정보 업데이트
            if request:
                from app.auth import update_user_login_info
                update_user_login_info(db, user, request)

        else:
            # 새 사용자 생성
            nickname = self._generate_username(db, google_data.get('name', ''))

            user = User(
                email=email,
                nickname=nickname,
                google_id=google_id,
                auth_provider="google",
                is_email_verified=google_data.get('email_verified', False),
                profile_image=google_data.get('picture'),
                is_active=True,
                login_count=0
            )

            db.add(user)

            # 로그인 정보 업데이트
            if request:
                from app.auth import update_user_login_info
                update_user_login_info(db, user, request)

        db.commit()
        db.refresh(user)

        # 활동 로깅
        if request:
            log_user_activity(
                db=db,
                user_id=user.id,
                activity_type="google_login",
                description=f"User logged in via Google OAuth",
                ip_address=request.client.host if request else None,
                user_agent=request.headers.get("User-Agent") if request else None
            )

        return user

    def _generate_username(self, db: Session, name: str) -> str:
        """고유한 사용자명 생성"""
        import re

        # 이름에서 사용자명 생성
        base_username = re.sub(r'[^a-zA-Z0-9가-힣]', '', name.lower())
        if not base_username:
            base_username = "user"

        username = base_username
        counter = 1

        # 중복 확인
        while db.query(User).filter(User.nickname == username).first():
            username = f"{base_username}{counter}"
            counter += 1

        return username

    def create_access_token_for_user(self, user: User) -> str:
        """사용자를 위한 액세스 토큰 생성"""
        token_data = {
            "sub": user.email,
            "role": user.role.value,
            "user_id": str(user.id)
        }

        return create_access_token(
            data=token_data,
            expires_delta=timedelta(minutes=settings.access_token_expire_minutes)
        )

# 서비스 인스턴스
google_oauth_service = GoogleOAuthService()
