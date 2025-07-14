from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.schemas.contact import ContactCreate, ContactResponse
from app.services.contact_service import create_contact, get_contacts

router = APIRouter(prefix="/contact", tags=["contact"])

@router.post("/", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def submit_contact(contact: ContactCreate, db: Session = Depends(get_db)):
    return create_contact(db, contact)

@router.get("/", response_model=List[ContactResponse])
def list_contacts(db: Session = Depends(get_db)):
    return get_contacts(db)