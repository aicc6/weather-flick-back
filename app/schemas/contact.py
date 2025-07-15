from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class ContactCreate(BaseModel):
    category: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    content: str
    name: str = Field(..., max_length=50)
    email: EmailStr
    is_public: bool = False

class ContactResponse(ContactCreate):
    id: int
    created_at: datetime
    approval_status: str

    class Config:
        from_attributes = True

class PasswordVerifyRequest(BaseModel):
    password: str
