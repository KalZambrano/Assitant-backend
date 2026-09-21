from typing import Any

from pydantic import BaseModel, Field


class ErrorBody(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorBody


class ToolCall(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_call_id: str
    tool_name: str
    success: bool
    action: str
    data: dict[str, Any] = Field(default_factory=dict)
    message: str | None = None
    reason: str | None = None
    missing_fields: list[str] = Field(default_factory=list)
