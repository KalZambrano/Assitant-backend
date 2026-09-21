from datetime import date, datetime, time

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Contact, Meeting


def _parse_time(value: str) -> time:
    normalized = value.strip().lower().replace("a. m.", "am").replace("p. m.", "pm").replace("a.m.", "am").replace("p.m.", "pm")
    for pattern in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
        try:
            return datetime.strptime(normalized, pattern).time()
        except ValueError:
            continue
    raise ValueError("La hora debe ser HH:MM, HH:MM:SS o un formato AM/PM válido")


def schedule_meeting(db: Session, data: dict) -> tuple[Meeting, str]:
    missing = [field for field in ("title", "date", "time") if not data.get(field)]
    if missing:
        raise ValueError(f"Faltan campos obligatorios: {', '.join(missing)}")
    try:
        meeting_date = date.fromisoformat(str(data["date"]))
        meeting_time = _parse_time(str(data["time"]))
    except ValueError as exc:
        raise ValueError("La fecha debe ser YYYY-MM-DD y la hora HH:MM o HH:MM:SS") from exc
    duration = int(data.get("duration_minutes") or 30)
    if duration <= 0 or duration > 1440:
        raise ValueError("La duración debe estar entre 1 y 1440 minutos")
    contact_id = data.get("contact_id")
    if contact_id is not None and db.get(Contact, int(contact_id)) is None:
        raise ValueError("El contacto indicado no existe")
    duplicate = db.scalar(select(Meeting).where(Meeting.title == data["title"], Meeting.date == meeting_date, Meeting.time == meeting_time))
    if duplicate:
        return duplicate, "existing"
    meeting = Meeting(title=data["title"], contact_id=contact_id, date=meeting_date, time=meeting_time, duration_minutes=duration, description=data.get("description"))
    db.add(meeting)
    db.flush()
    return meeting, "scheduled"
