from sqlalchemy.orm import Session
from app.models import Contact
from app.schemas.contact import ContactCreate
from datetime import timezone, datetime

def create_contact(db: Session, contact_data: ContactCreate):
    contact = Contact(**contact_data.model_dump())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_contacts(db: Session, skip: int = 0, limit: int = 100):
    contacts = db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()
    # created_at이 naive면 UTC로 보정
    for c in contacts:
        if hasattr(c, 'created_at') and isinstance(c.created_at, datetime) and c.created_at.tzinfo is None:
            c.created_at = c.created_at.replace(tzinfo=timezone.utc)
    return contacts
