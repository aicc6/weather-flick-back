from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    category: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    content: str
    name: str = Field(..., max_length=50)
    email: EmailStr
    is_private: bool = False
    password: str | None = None  # 비공개 문의 비밀번호(plain, 입력용)


class ContactListResponse(BaseModel):
    id: int
    category: str
    title: str
    name: str
    email: str
    approval_status: str
    views: int
    created_at: datetime
    is_private: bool

    class Config:
        from_attributes = True


class ContactAnswerResponse(BaseModel):
    id: int
    content: str
    created_at: datetime
    admin_id: int
    
    class Config:
        from_attributes = True


class ContactResponse(ContactCreate):
    id: int
    created_at: datetime
    approval_status: str
    views: int
    password: str | None = None  # 응답에는 보통 포함하지 않지만, 일관성 위해 추가(실제 응답에선 제외 가능)
    answer: Optional[ContactAnswerResponse] = None  # 답변 정보 추가

    class Config:
        from_attributes = True

class PasswordVerifyRequest(BaseModel):
    password: str
