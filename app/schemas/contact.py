from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class ContactResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str | None
    company: str | None
    email: EmailStr
    phone: str | None
    status: str | None
    created_at: datetime
    updated_at: datetime
