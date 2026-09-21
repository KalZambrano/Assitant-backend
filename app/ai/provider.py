from typing import Protocol

from app.schemas.ai import AIResponse
from app.schemas.common import ToolResult


class AIProvider(Protocol):
    name: str
    model: str

    async def analyze_email(self, sender: str, subject: str, body: str) -> AIResponse:
        ...

    async def continue_with_tool_results(self, response: AIResponse, results: list[ToolResult]) -> AIResponse:
        ...
