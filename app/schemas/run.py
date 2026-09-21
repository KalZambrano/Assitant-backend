from datetime import datetime

from pydantic import BaseModel, ConfigDict


class RunSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email_id: int
    status: str
    provider: str
    model: str
    started_at: datetime
    finished_at: datetime | None
    final_response: str | None
    error_message: str | None
