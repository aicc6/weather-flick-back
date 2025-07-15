from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactResponse, PasswordVerifyRequest
from app.services.contact_service import create_contact, get_contacts
from app.models import Contact, User
from app.auth import verify_password

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    return create_contact(db, contact)

@router.get("/", response_model=List[ContactResponse])
def list_contacts(db: Session = Depends(get_db)):
    return get_contacts(db)

@router.post("/{contact_id}/verify-password", response_model=dict)
def verify_contact_password(contact_id: int, data: PasswordVerifyRequest, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")
    user = db.query(User).filter(User.email == contact.email).first()
    hashed_pw = getattr(user, 'hashed_password', None) if user else None
    if not user or not hashed_pw or not verify_password(data.password, hashed_pw):
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    return {"success": True}
