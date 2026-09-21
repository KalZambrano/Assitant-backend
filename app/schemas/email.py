from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.ai import AIAnalysis


class EmailProcessRequest(BaseModel):
    sender: str = Field(min_length=3, max_length=320)
    subject: str = Field(min_length=1, max_length=500)
    body: str = Field(min_length=1)
    received_at: datetime | None = None


class EmailResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    sender: str
    subject: str
    body: str
    received_at: datetime
    processed: bool


class ToolExecutionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    tool_name: str
    arguments: str
    result: str | None
    status: str
    error_message: str | None


class ProcessEmailResponse(BaseModel):
    run_id: int
    email: EmailResponse
    status: str
    provider: str
    model: str
    analysis: AIAnalysis | None
    tool_executions: list[ToolExecutionResponse]
    final_response: str | None
    error_message: str | None
