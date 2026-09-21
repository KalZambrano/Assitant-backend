import json
from typing import Any

import httpx

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.tool_definitions import TOOL_DEFINITIONS
from app.schemas.ai import AIContext, AIResponse
from app.schemas.common import ToolCall, ToolResult


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def _chat(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        tools = [{"type": "function", "function": tool} for tool in TOOL_DEFINITIONS]
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(f"{self.base_url}/api/chat", json={"model": self.model, "messages": messages, "tools": tools, "stream": False})
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _tool_names() -> set[str]:
        return {tool["name"] for tool in TOOL_DEFINITIONS}

    @classmethod
    def _extract_json_objects(cls, content: str) -> list[dict[str, Any]]:
        """Extract JSON objects from fenced or plain model text.

        Some small Ollama models emit a function call as JSON text instead of
        using Ollama's structured ``message.tool_calls`` field.
        """
        decoder = json.JSONDecoder()
        objects: list[dict[str, Any]] = []
        cursor = 0
        while cursor < len(content):
            start = content.find("{", cursor)
            if start < 0:
                break
            try:
                value, offset = decoder.raw_decode(content[start:])
            except json.JSONDecodeError:
                cursor = start + 1
                continue
            if isinstance(value, dict):
                objects.append(value)
            cursor = start + offset
        return objects

    @classmethod
    def _text_tool_calls(cls, content: str) -> list[ToolCall]:
        calls: list[ToolCall] = []
        known_tools = cls._tool_names()
        for index, value in enumerate(cls._extract_json_objects(content)):
            name = value.get("name")
            arguments = value.get("arguments") or value.get("parameters")

            # Typical fallback emitted by the model:
            # {"type":"function","name":"...","parameters":{...}}
            if isinstance(name, str) and name in known_tools and isinstance(arguments, dict):
                calls.append(ToolCall(id=f"ollama-text-call-{index}", name=name, arguments=arguments))
                continue

            # Also accept {"tool_name": {...}} style responses.
            for tool_name in known_tools:
                nested_arguments = value.get(tool_name)
                if isinstance(nested_arguments, dict):
                    calls.append(ToolCall(id=f"ollama-text-call-{index}", name=tool_name, arguments=nested_arguments))
                    break
        return calls

    def _normalize(self, payload: dict[str, Any], messages: list[dict[str, Any]]) -> AIResponse:
        message = payload.get("message", {})
        calls: list[ToolCall] = []
        for index, call in enumerate(message.get("tool_calls", [])):
            function = call.get("function", call)
            arguments = function.get("arguments", {})
            if isinstance(arguments, str):
                arguments = json.loads(arguments)
            calls.append(ToolCall(id=f"ollama-call-{index}", name=function.get("name", ""), arguments=arguments))
        content = message.get("content") or ""
        if not calls and content:
            calls = self._text_tool_calls(content)
        return AIResponse(content=content or None, tool_calls=calls, provider=self.name, model=self.model, context=AIContext(messages=messages + [message]))

    async def analyze_email(self, sender: str, subject: str, body: str) -> AIResponse:
        prompt = f"Correo recibido\nRemitente: {sender}\nAsunto: {subject}\nCuerpo:\n{body}\n\nAnaliza el correo y usa herramientas solo si corresponde."
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}]
        return self._normalize(await self._chat(messages), messages)

    async def continue_with_tool_results(self, response: AIResponse, results: list[ToolResult]) -> AIResponse:
        messages = list(response.context.messages)
        messages.append({"role": "tool", "content": "\n".join(result.model_dump_json() for result in results)})
        return self._normalize(await self._chat(messages), messages)
