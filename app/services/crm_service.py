from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact


def upsert_contact(db: Session, data: dict) -> tuple[Contact, str]:
    email = str(data.get("email", "")).strip().lower()
    if not email or "@" not in email:
        raise ValueError("El email del contacto es obligatorio y debe ser válido")
    contact = db.scalar(select(Contact).where(Contact.email == email))
    action = "updated" if contact else "created"
    if contact is None:
        contact = Contact(email=email)
        db.add(contact)
    for field in ("name", "company", "phone", "status"):
        value = data.get(field)
        if value not in (None, ""):
            setattr(contact, field, value)
    db.flush()
    return contact, action
