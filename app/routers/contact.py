from typing import List
from fastapi import APIRouter, Depends, status, HTTPException

from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.contact import ContactCreate, ContactListResponse, ContactResponse, PasswordVerifyRequest
from app.services.contact_service import create_contact, get_contacts, verify_contact_password, increment_contact_views
from app.models import Contact

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    return create_contact(db, contact)

@router.get("/", response_model=list[ContactListResponse])
def list_contacts(db: Session = Depends(get_db)):
    return get_contacts(db)

@router.post("/{contact_id}/verify-password", response_model=dict)
def verify_contact_password_route(contact_id: int, data: PasswordVerifyRequest, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")
    if not bool(contact.is_public) or not bool(contact.password_hash):
        raise HTTPException(status_code=400, detail="비공개 문의가 아니거나 비밀번호가 설정되지 않았습니다.")
    if not verify_contact_password(db, contact_id, data.password):
        raise HTTPException(status_code=403, detail="비밀번호가 일치하지 않습니다.")
    return {"success": True}

@router.post("/{contact_id}/increment-views", response_model=dict)
def increment_views_route(contact_id: int, db: Session = Depends(get_db)):
    try:
        views = increment_contact_views(db, contact_id)
        return {"views": views}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
