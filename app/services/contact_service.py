from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Contact
from app.schemas.contact import ContactCreate, ContactResponse
import bcrypt


def create_contact(db: Session, contact_data: ContactCreate):
    data = contact_data.model_dump()
    password = data.pop('password', None)

    # is_private가 True이고 password가 있을 때만 해시 저장
    if data.get('is_private', False) and password:
        # 비공개 문의: 비밀번호 해시 저장
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        data['password_hash'] = hashed.decode('utf-8')
    contact = Contact(**data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    contacts = db.query(Contact).order_by(Contact.id.desc()).offset(skip).limit(limit).all()
    # created_at이 naive면 UTC로 보정
    for c in contacts:
        if hasattr(c, 'created_at') and isinstance(c.created_at, datetime) and c.created_at.tzinfo is None:
            c.created_at = c.created_at.replace(tzinfo=UTC)
    return contacts

def verify_contact_password(db: Session, contact_id: int, password: str) -> bool:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")

    return bcrypt.checkpw(password.encode('utf-8'), contact.password_hash.encode('utf-8'))

def get_contact(db: Session, contact_id: int, increment_view: bool = True):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")

    # 공개 글인 경우에만 조회수 증가 (비공개 글은 비밀번호 확인 후 증가)
    if increment_view and not bool(getattr(contact, 'is_private', False)):
        # 실제 값만 증가
        object.__setattr__(contact, 'views', (getattr(contact, 'views', 0) or 0) + 1)
        db.commit()
        db.refresh(contact)

    return ContactResponse.model_validate(contact)

def increment_contact_view(db: Session, contact_id: int):
    """비공개 글의 비밀번호 확인 후 조회수 증가"""
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        raise HTTPException(status_code=404, detail="문의글을 찾을 수 없습니다.")

    object.__setattr__(contact, 'views', (getattr(contact, 'views', 0) or 0) + 1)
    db.commit()
    db.refresh(contact)

    return contact
