from __future__ import annotations

from datetime import date as DateType, time as TimeType
from typing import Any

from pydantic import BaseModel, Field

from app.schemas.common import ToolCall


class ContactAnalysis(BaseModel):
    name: str | None = None
    company: str | None = None
    email: str | None = None
    phone: str | None = None


class MeetingRequest(BaseModel):
    requested: bool = False
    date: DateType | None = None
    time: TimeType | None = None


class AIAnalysis(BaseModel):
    intent: str | None = None
    contact: ContactAnalysis = Field(default_factory=ContactAnalysis)
    requirements: list[str] = Field(default_factory=list)
    meeting_request: MeetingRequest = Field(default_factory=MeetingRequest)
    missing_information: list[str] = Field(default_factory=list)
    summary: str | None = None


class AIContext(BaseModel):
    messages: list[dict[str, Any]] = Field(default_factory=list)


class AIResponse(BaseModel):
    content: str | None = None
    tool_calls: list[ToolCall] = Field(default_factory=list)
    analysis: AIAnalysis | None = None
    provider: str
    model: str
    context: AIContext = Field(default_factory=AIContext)


class ProviderInfo(BaseModel):
    name: str
    model: str
    configured: bool
