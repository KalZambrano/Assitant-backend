import re
from datetime import date, time

from app.schemas.ai import AIAnalysis, ContactAnalysis, MeetingRequest

MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}


def _parse_date(text: str) -> date | None:
    iso_match = re.search(r"\b(20\d{2})-(\d{1,2})-(\d{1,2})\b", text)
    if iso_match:
        try:
            return date(int(iso_match.group(1)), int(iso_match.group(2)), int(iso_match.group(3)))
        except ValueError:
            return None

    spanish_match = re.search(
        r"\b(\d{1,2})\s+de\s+(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)(?:\s+de\s+(20\d{2}))?\b",
        text,
        re.IGNORECASE,
    )
    if not spanish_match or not spanish_match.group(3):
        return None
    try:
        return date(int(spanish_match.group(3)), MONTHS[spanish_match.group(2).lower()], int(spanish_match.group(1)))
    except ValueError:
        return None


def _parse_time(text: str) -> time | None:
    match = re.search(r"\b(\d{1,2}):(\d{2})\s*(a\.?\s*m\.?|p\.?\s*m\.?)?\b", text, re.IGNORECASE)
    if not match:
        return None
    hour = int(match.group(1))
    minute = int(match.group(2))
    meridiem = (match.group(3) or "").replace(".", "").replace(" ", "").lower()
    if meridiem == "pm" and hour < 12:
        hour += 12
    if meridiem == "am" and hour == 12:
        hour = 0
    try:
        return time(hour, minute)
    except ValueError:
        return None


def _parse_duration(text: str) -> int:
    match = re.search(r"duraci[oó]n\s+(?:de\s+)?(\d+)\s*(?:minutos|min)\b", text, re.IGNORECASE)
    return int(match.group(1)) if match else 30


def _contact_name(body: str, sender: str) -> str:
    signature = re.search(r"Saludos[^\n]*,?\s*\n\s*([^\n]+)", body, re.IGNORECASE)
    if signature and signature.group(1).strip():
        return signature.group(1).strip()
    local_part = sender.split("@", 1)[0].replace(".", " ").replace("_", " ")
    return local_part.title() or "Contacto"


def _contact_company(body: str, sender: str) -> str:
    signature = re.search(r"Saludos[^\n]*,?\s*\n\s*[^\n]+\s*\n\s*([^\n]+)", body, re.IGNORECASE)
    if signature and signature.group(1).strip():
        return signature.group(1).strip()
    return sender.split("@", 1)[1].split(".", 1)[0].replace("-", " ").title() if "@" in sender else "Empresa"


def extract_email_facts(sender: str, subject: str, body: str) -> tuple[AIAnalysis, dict | None]:
    text = f"{subject}\n{body}"
    lower_text = text.lower()
    meeting_requested = bool(re.search(r"reuni[oó]n|agendar|demo|reunirnos|juntarnos", lower_text))
    parsed_date = _parse_date(text)
    parsed_time = _parse_time(text)
    duration = _parse_duration(text)
    exact_schedule = meeting_requested and parsed_date is not None and parsed_time is not None
    missing_information: list[str] = []
    if meeting_requested and parsed_date is None:
        missing_information.append("Fecha exacta para la reunión")
    if meeting_requested and parsed_time is None:
        missing_information.append("Hora exacta para la reunión")

    contact = ContactAnalysis(name=_contact_name(body, sender), company=_contact_company(body, sender), email=sender)
    analysis = AIAnalysis(
        intent=f"Requerimiento sobre: {subject}",
        contact=contact,
        requirements=[subject],
        meeting_request=MeetingRequest(requested=meeting_requested, date=parsed_date, time=parsed_time),
        missing_information=missing_information,
        summary=f"Correo recibido de {contact.name}.",
    )
    calendar_arguments = None
    if exact_schedule:
        calendar_arguments = {
            "title": subject,
            "date": parsed_date.isoformat(),
            "time": parsed_time.strftime("%H:%M"),
            "duration_minutes": duration,
            "description": body[:1000],
        }
    return analysis, calendar_arguments
