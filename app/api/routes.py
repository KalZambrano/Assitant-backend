import json

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.config import Settings, get_settings
from app.database.database import get_db
from app.models import Contact, Email, Meeting, Run
from app.schemas.ai import AIAnalysis, ProviderInfo
from app.schemas.contact import ContactResponse
from app.schemas.email import EmailProcessRequest, EmailResponse, ProcessEmailResponse, ToolExecutionResponse
from app.schemas.meeting import MeetingResponse
from app.schemas.run import RunSummaryResponse
from app.services.orchestrator import process_email
from app.services.provider_service import get_provider

router = APIRouter(prefix="/api")


@router.get("/health", summary="Verifica la salud del backend")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ai/providers", response_model=list[ProviderInfo], summary="Lista proveedores configurados")
def providers(settings: Settings = Depends(get_settings)) -> list[ProviderInfo]:
    return [
        ProviderInfo(name="gemini", model=settings.gemini_model, configured=bool(settings.gemini_api_key)),
        ProviderInfo(name="ollama", model=settings.ollama_model, configured=True),
    ]


@router.post("/emails/process", response_model=ProcessEmailResponse, status_code=status.HTTP_201_CREATED, summary="Procesa un correo con IA")
async def process(request: EmailProcessRequest, db: Session = Depends(get_db), settings: Settings = Depends(get_settings)) -> ProcessEmailResponse:
    try:
        provider = get_provider(settings)
        email, run = await process_email(db, request.sender, request.subject, request.body, provider, settings.max_tool_iterations)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail={"code": "CONFIGURATION_ERROR", "message": str(exc)}) from exc
    if request.received_at is not None:
        email.received_at = request.received_at
        db.commit()
    db.refresh(run)
    analysis = AIAnalysis.model_validate(json.loads(run.analysis_json)) if run.analysis_json else None
    return ProcessEmailResponse(
        run_id=run.id,
        email=email,
        status=run.status,
        provider=run.provider,
        model=run.model,
        analysis=analysis,
        tool_executions=run.tool_executions,
        final_response=run.final_response,
        error_message=run.error_message,
    )


@router.get("/emails", response_model=list[EmailResponse], summary="Lista correos")
def list_emails(db: Session = Depends(get_db)) -> list[Email]:
    return list(db.scalars(select(Email).order_by(Email.id.desc())))


@router.get("/emails/{email_id}", response_model=EmailResponse, summary="Obtiene un correo")
def get_email(email_id: int, db: Session = Depends(get_db)) -> Email:
    email = db.get(Email, email_id)
    if not email:
        raise HTTPException(404, "Correo no encontrado")
    return email


@router.get("/contacts", response_model=list[ContactResponse], summary="Lista contactos")
def list_contacts(db: Session = Depends(get_db)) -> list[Contact]:
    return list(db.scalars(select(Contact).order_by(Contact.id.desc())))


@router.get("/contacts/{contact_id}", response_model=ContactResponse, summary="Obtiene un contacto")
def get_contact(contact_id: int, db: Session = Depends(get_db)) -> Contact:
    contact = db.get(Contact, contact_id)
    if not contact:
        raise HTTPException(404, "Contacto no encontrado")
    return contact


@router.get("/meetings", response_model=list[MeetingResponse], summary="Lista reuniones")
def list_meetings(db: Session = Depends(get_db)) -> list[Meeting]:
    return list(db.scalars(select(Meeting).order_by(Meeting.date, Meeting.time)))


@router.get("/meetings/{meeting_id}", response_model=MeetingResponse, summary="Obtiene una reunión")
def get_meeting(meeting_id: int, db: Session = Depends(get_db)) -> Meeting:
    meeting = db.get(Meeting, meeting_id)
    if not meeting:
        raise HTTPException(404, "Reunión no encontrada")
    return meeting


@router.get("/runs", response_model=list[RunSummaryResponse], summary="Lista ejecuciones")
def list_runs(db: Session = Depends(get_db)) -> list[Run]:
    return list(db.scalars(select(Run).order_by(Run.id.desc())))


@router.get("/runs/{run_id}", response_model=ProcessEmailResponse, summary="Obtiene una ejecución completa")
def get_run(run_id: int, db: Session = Depends(get_db)) -> ProcessEmailResponse:
    run = db.scalar(select(Run).options(selectinload(Run.email), selectinload(Run.tool_executions)).where(Run.id == run_id))
    if not run:
        raise HTTPException(404, "Run no encontrado")
    analysis = AIAnalysis.model_validate(json.loads(run.analysis_json)) if run.analysis_json else None
    return ProcessEmailResponse(
        run_id=run.id,
        email=run.email,
        status=run.status,
        provider=run.provider,
        model=run.model,
        analysis=analysis,
        tool_executions=run.tool_executions,
        final_response=run.final_response,
        error_message=run.error_message,
    )
