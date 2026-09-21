from __future__ import annotations

from datetime import date as DateType, datetime, time as TimeType

from pydantic import BaseModel, ConfigDict


class MeetingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    contact_id: int | None
    date: DateType
    time: TimeType
    duration_minutes: int
    description: str | None
    status: str
    created_at: datetime
