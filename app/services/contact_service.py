from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.models import Contact
from app.schemas.contact import ContactCreate
import bcrypt


def create_contact(db: Session, contact_data: ContactCreate):
    data = contact_data.model_dump()
    password = data.pop('password', None)
    if data.get('is_public') and password:
        # 비공개 문의: 비밀번호 해시 저장
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        data['password_hash'] = hashed.decode('utf-8')
    contact = Contact(**data)
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    contacts = db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
    # created_at이 naive면 UTC로 보정
    for c in contacts:
        if hasattr(c, 'created_at') and isinstance(c.created_at, datetime) and c.created_at.tzinfo is None:
            c.created_at = c.created_at.replace(tzinfo=UTC)
    return contacts

def verify_contact_password(db: Session, contact_id: int, password: str) -> bool:
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact or not contact.password_hash:
        return False
    return bcrypt.checkpw(password.encode('utf-8'), contact.password_hash.encode('utf-8'))
