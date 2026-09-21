import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Meeting
from app.models.base import Base
from app.schemas.ai import AIResponse
from app.schemas.common import ToolCall
from app.services.orchestrator import process_email
from app.ai.ollama_provider import OllamaProvider


class FakeProvider:
    name = "fake"
    model = "test-model"

    def __init__(self):
        self.calls = 0

    async def analyze_email(self, sender, subject, body):
        return AIResponse(provider=self.name, model=self.model, tool_calls=[ToolCall(id="1", name="actualizar_contacto_en_crm", arguments={"email": sender, "name": "Ana"})])

    async def continue_with_tool_results(self, response, results):
        self.calls += 1
        return AIResponse(provider=self.name, model=self.model, content=f"Herramienta: {results[0].action}")


class CalendarProvider(FakeProvider):
    async def analyze_email(self, sender, subject, body):
        return AIResponse(
            provider=self.name,
            model=self.model,
            tool_calls=[
                ToolCall(
                    id="calendar-1",
                    name="agendar_reunion_en_calendar",
                    arguments={"title": "Demo técnica", "date": "2026-09-25", "time": "10:00", "duration_minutes": 45},
                )
            ],
        )


class NoToolProvider:
    name = "fake"
    model = "test-model"

    async def analyze_email(self, sender, subject, body):
        return AIResponse(provider=self.name, model=self.model, content="La demo ha sido agendada.")

    async def continue_with_tool_results(self, response, results):
        return AIResponse(provider=self.name, model=self.model, content="La demo ha sido agendada.")


def test_orchestrator_persists_run_and_tool_execution():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    email, run = asyncio.run(process_email(db, "ana@example.com", "Hola", "Contenido", FakeProvider(), 5))

    assert email.processed is True
    assert run.status == "completed"
    assert run.final_response == "Herramienta: created"
    assert len(run.tool_executions) == 1


def test_orchestrator_persists_calendar_meeting():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    _, run = asyncio.run(process_email(db, "patricia@example.com", "Demo", "Viernes 25 a las 10:00", CalendarProvider(), 5))

    assert run.status == "completed"
    assert db.query(Meeting).count() == 1


def test_ollama_normalizes_textual_function_calls():
    provider = OllamaProvider("http://localhost:11434", "llama3.2:1b")
    response = provider._normalize(
        {
            "message": {
                "content": "```json\n{\"type\":\"function\",\"name\":\"agendar_reunion_en_calendar\",\"parameters\":{\"title\":\"Demo\",\"date\":\"2026-09-25\",\"time\":\"10:00 AM\"}}\n```"
            }
        },
        [],
    )

    assert len(response.tool_calls) == 1
    assert response.tool_calls[0].name == "agendar_reunion_en_calendar"
    assert response.tool_calls[0].arguments["time"] == "10:00 AM"


def test_policy_creates_calendar_when_model_omits_tool_call():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()

    _, run = asyncio.run(
        process_email(
            db,
            "patricia.velez@fintechlatam.com",
            "Confirmación de demo técnica",
            "Saludos cordiales,\nPatricia Vélez\nFinTech Latam\n\nQueremos agendar la demo el 25 de septiembre de 2026 a las 10:00 AM, duración 45 minutos.",
            NoToolProvider(),
            5,
        )
    )

    assert run.status == "completed"
    assert db.query(Meeting).count() == 1
    assert db.query(Meeting).one().time.hour == 10
    assert db.query(Meeting).one().date.isoformat() == "2026-09-25"
    assert len(run.tool_executions) == 2
