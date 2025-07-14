from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

class ContactCreate(BaseModel):
    category: str = Field(..., max_length=50)
    title: str = Field(..., max_length=200)
    content: str
    name: str = Field(..., max_length=50)
    email: EmailStr

class ContactResponse(ContactCreate):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True