from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional

from ..validators import CommonValidators


class Token(BaseModel):
    """토큰 응답 스키마"""

    access_token: str = Field(..., description="액세스 토큰")
    refresh_token: str = Field(..., description="리프레시 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")


class TokenData(BaseModel):
    """토큰 데이터 스키마"""

    email: Optional[str] = Field(None, description="사용자 이메일")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        if v:
            return CommonValidators.validate_email(v)
        return v


class RefreshTokenRequest(BaseModel):
    """리프레시 토큰 요청 스키마"""

    refresh_token: str = Field(..., description="리프레시 토큰")


class RefreshTokenResponse(BaseModel):
    """리프레시 토큰 응답 스키마"""

    access_token: str = Field(..., description="새로운 액세스 토큰")
    token_type: str = Field(default="bearer", description="토큰 타입")


class LoginRequest(BaseModel):
    """로그인 요청 스키마"""

    email: str = Field(..., description="이메일")
    password: str = Field(..., description="비밀번호")
    fcm_token: Optional[str] = Field(None, description="FCM 푸시 알림 토큰")
    device_type: Optional[str] = Field(
        None, description="디바이스 타입 (android, ios, web)"
    )
    device_id: Optional[str] = Field(None, description="디바이스 고유 식별자")
    device_name: Optional[str] = Field(None, description="디바이스 이름")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        return CommonValidators.validate_email(v)


class RegisterRequest(BaseModel):
    """회원가입 요청 스키마"""

    email: str = Field(..., description="이메일")
    password: str = Field(..., description="비밀번호")
    nickname: str = Field(..., description="닉네임")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        return CommonValidators.validate_email(v)

    @field_validator("password", mode="before")
    @classmethod
    def validate_password(cls, v):
        return CommonValidators.validate_password(v)

    @field_validator("nickname", mode="before")
    @classmethod
    def validate_nickname(cls, v):
        return CommonValidators.validate_nickname(v)


class PasswordResetRequest(BaseModel):
    """비밀번호 재설정 요청 스키마"""

    email: str = Field(..., description="이메일")

    @field_validator("email", mode="before")
    @classmethod
    def validate_email(cls, v):
        return CommonValidators.validate_email(v)


class PasswordResetConfirm(BaseModel):
    """비밀번호 재설정 확인 스키마"""

    token: str = Field(..., description="재설정 토큰")
    new_password: str = Field(..., description="새 비밀번호")

    @field_validator("new_password", mode="before")
    @classmethod
    def validate_password(cls, v):
        return CommonValidators.validate_password(v)
