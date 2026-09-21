import json
import logging
import re
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.ai.provider import AIProvider
from app.models import Email, Run, ToolExecution
from app.schemas.common import ToolCall, ToolResult
from app.services.email_analysis import extract_email_facts
from app.services import tool_execution_service

logger = logging.getLogger(__name__)


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def process_email(db: Session, sender: str, subject: str, body: str, provider: AIProvider, max_iterations: int) -> tuple[Email, Run]:
    email = Email(sender=sender, subject=subject, body=body)
    db.add(email)
    db.flush()
    run = Run(email_id=email.id, status="created", provider=provider.name, model=provider.model)
    db.add(run)
    db.commit()
    db.refresh(run)
    logger.info("Run %s started with provider %s", run.id, provider.name)
    try:
        fallback_analysis, calendar_arguments = extract_email_facts(sender, subject, body)
        run.status = "analyzing"
        db.commit()
        response = await provider.analyze_email(sender, subject, body)
        analysis = response.analysis or fallback_analysis
        if response.analysis and fallback_analysis.meeting_request.requested:
            analysis.meeting_request = fallback_analysis.meeting_request
            analysis.missing_information = fallback_analysis.missing_information
        run.analysis_json = analysis.model_dump_json()
        db.commit()
        all_results: list[ToolResult] = []
        for iteration in range(max_iterations):
            calls = list(response.tool_calls)
            if iteration == 0:
                tool_names = {call.name for call in calls}
                if "actualizar_contacto_en_crm" not in tool_names:
                    calls.insert(0, ToolCall(id="policy-crm-0", name="actualizar_contacto_en_crm", arguments=fallback_analysis.contact.model_dump(exclude_none=True)))
                if calendar_arguments and "agendar_reunion_en_calendar" not in tool_names:
                    calls.append(ToolCall(id="policy-calendar-0", name="agendar_reunion_en_calendar", arguments=calendar_arguments))

            if not calls:
                run.status = "completing"
                run.final_response = _truthful_response(response.content, fallback_analysis, all_results)
                run.status = "completed"
                run.finished_at = _now()
                email.processed = True
                db.commit()
                return email, run
            run.status = "requires_action"
            db.commit()
            run.status = "executing_tools"
            db.commit()
            results: list[ToolResult] = []
            calls.sort(key=lambda call: 0 if call.name == "actualizar_contacto_en_crm" else 1)
            contact_id = None
            for call in calls:
                if call.name == "agendar_reunion_en_calendar" and contact_id is not None:
                    call.arguments.setdefault("contact_id", contact_id)
                execution = ToolExecution(run_id=run.id, tool_name=call.name, arguments=json.dumps(call.arguments, ensure_ascii=False), status="running")
                db.add(execution)
                db.flush()
                result = tool_execution_service.execute_tool(db, call)
                execution.result = result.model_dump_json()
                execution.status = "success" if result.success else result.action
                execution.completed_at = _now()
                db.commit()
                results.append(result)
                if result.tool_name == "actualizar_contacto_en_crm" and result.success:
                    contact_id = result.data.get("contact_id")

            all_results.extend(results)
            calendar_succeeded = any(result.tool_name == "agendar_reunion_en_calendar" and result.success for result in results)
            if iteration == 0 and calendar_arguments and not calendar_succeeded:
                corrected_call = ToolCall(id="policy-calendar-correction", name="agendar_reunion_en_calendar", arguments=dict(calendar_arguments))
                if contact_id is not None:
                    corrected_call.arguments["contact_id"] = contact_id
                execution = ToolExecution(run_id=run.id, tool_name=corrected_call.name, arguments=json.dumps(corrected_call.arguments, ensure_ascii=False), status="running")
                db.add(execution)
                db.flush()
                corrected_result = tool_execution_service.execute_tool(db, corrected_call)
                execution.result = corrected_result.model_dump_json()
                execution.status = "success" if corrected_result.success else corrected_result.action
                execution.completed_at = _now()
                db.commit()
                results.append(corrected_result)
                all_results.append(corrected_result)
            run.status = "completing"
            db.commit()
            response = await provider.continue_with_tool_results(response.model_copy(update={"tool_calls": calls}), results)
        raise RuntimeError("Maximum tool execution iterations exceeded.")
    except Exception as exc:
        db.rollback()
        run.status = "failed"
        run.error_message = str(exc)
        run.finished_at = _now()
        db.commit()
        logger.exception("Run %s failed", run.id)
        return email, run


def _truthful_response(content: str | None, analysis, results: list[ToolResult]) -> str:
    text = content or "No se generó una respuesta final."
    requested_meeting = analysis.meeting_request.requested
    scheduled = any(result.tool_name == "agendar_reunion_en_calendar" and result.success for result in results)
    claims_scheduled = bool(re.search(r"agendad[ao]|programad[ao]|scheduled", text, re.IGNORECASE))
    if requested_meeting and analysis.meeting_request.date and analysis.meeting_request.time and not scheduled and claims_scheduled:
        return "La reunión no pudo agendarse porque la herramienta de Calendar no confirmó una ejecución exitosa."
    if requested_meeting and not analysis.meeting_request.date and claims_scheduled:
        return "La reunión quedó pendiente porque todavía faltan la fecha y la hora exactas."
    return text
