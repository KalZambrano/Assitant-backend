from collections.abc import Callable
from typing import Any

from sqlalchemy.orm import Session

from app.schemas.common import ToolResult
from app.services.calendar_service import schedule_meeting
from app.services.crm_service import upsert_contact


def crm_tool(db: Session, arguments: dict[str, Any], call_id: str) -> ToolResult:
    contact, action = upsert_contact(db, arguments)
    return ToolResult(tool_call_id=call_id, tool_name="actualizar_contacto_en_crm", success=True, action=action, data={"contact_id": contact.id}, message=f"Contact {action} successfully")


def calendar_tool(db: Session, arguments: dict[str, Any], call_id: str) -> ToolResult:
    missing = [field for field in ("date", "time") if not arguments.get(field)]
    if missing:
        return ToolResult(tool_call_id=call_id, tool_name="agendar_reunion_en_calendar", success=False, action="skipped", reason="missing_information", missing_fields=missing, message="Meeting information is incomplete")
    meeting, action = schedule_meeting(db, arguments)
    return ToolResult(tool_call_id=call_id, tool_name="agendar_reunion_en_calendar", success=True, action=action, data={"meeting_id": meeting.id}, message="Meeting scheduled successfully")


TOOLS: dict[str, Callable[[Session, dict[str, Any], str], ToolResult]] = {
    "actualizar_contacto_en_crm": crm_tool,
    "agendar_reunion_en_calendar": calendar_tool,
}
