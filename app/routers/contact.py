from typing import List
from fastapi import APIRouter, Depends, status, HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.contact import ContactCreate, ContactListResponse, ContactResponse, PasswordVerifyRequest
from app.services import contact_service
from app.models import Contact

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    return contact_service.create_contact(db, contact)

@router.get("/", response_model=list[ContactListResponse])
def list_contacts(db: Session = Depends(get_db)):
    return contact_service.get_contacts(db)

@router.post("/{contact_id}/verify-password", response_model=dict)
def verify_contact_password_route(contact_id: int, data: PasswordVerifyRequest, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")
    if not bool(contact.is_public) or not bool(contact.password_hash):
        raise HTTPException(status_code=400, detail="비공개 문의가 아니거나 비밀번호가 설정되지 않았습니다.")
    if not contact_service.verify_contact_password(db, contact_id, data.password):
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    return {"success": True}

@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(contact_id: int, db: Session = Depends(get_db)):
    return contact_service.get_contact(db, contact_id)
