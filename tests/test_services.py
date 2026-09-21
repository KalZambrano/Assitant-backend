from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.base import Base
from app.services.calendar_service import schedule_meeting
from app.services.crm_service import upsert_contact


def make_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def test_crm_creates_and_updates_by_email():
    db = make_db()
    contact, action = upsert_contact(db, {"email": "ANA@EXAMPLE.COM", "name": "Ana"})
    assert action == "created"
    same, action = upsert_contact(db, {"email": "ana@example.com", "company": "TechCorp"})
    assert action == "updated"
    assert same.id == contact.id
    assert same.name == "Ana"
    assert same.company == "TechCorp"


def test_calendar_rejects_missing_date_and_time():
    db = make_db()
    try:
        schedule_meeting(db, {"title": "Demo"})
    except ValueError as exc:
        assert "date" in str(exc)
        assert "time" in str(exc)
    else:
        raise AssertionError("Expected validation error")


def test_calendar_schedules_valid_meeting():
    db = make_db()
    meeting, action = schedule_meeting(db, {"title": "Demo", "date": "2026-10-01", "time": "10:30 AM"})
    assert action == "scheduled"
    assert meeting.duration_minutes == 30
    assert meeting.time.hour == 10
