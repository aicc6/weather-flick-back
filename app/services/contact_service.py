from sqlalchemy.orm import Session
from app.models import Contact

def create_contact(db: Session, contact_data):
    contact = Contact(**contact_data.dict())
    db.add(contact)
    db.commit()
    db.refresh(contact)
    return contact

def get_contacts(db: Session, skip=0, limit=100):
    return db.query(Contact).order_by(Contact.created_at.desc()).offset(skip).limit(limit).all()