import json
from typing import Any

from app.ai.prompts import SYSTEM_PROMPT
from app.ai.tool_definitions import TOOL_DEFINITIONS
from app.schemas.ai import AIAnalysis, AIContext, AIResponse
from app.schemas.common import ToolCall, ToolResult


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("GEMINI_API_KEY no está configurada")
        from google import genai

        self.model = model
        self.client = genai.Client(api_key=api_key)

    def _config(self):
        from google.genai import types

        declarations = [
            types.FunctionDeclaration(
                name=tool["name"],
                description=tool["description"],
                parameters_json_schema=tool["parameters"],
            )
            for tool in TOOL_DEFINITIONS
        ]
        return types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT,
            tools=[types.Tool(function_declarations=declarations)],
            temperature=0.1,
        )

    def _normalize(self, response: Any, context: list[dict[str, Any]]) -> AIResponse:
        calls: list[ToolCall] = []
        text_parts: list[str] = []
        analysis = None
        candidate = response.candidates[0] if response.candidates else None
        parts = candidate.content.parts if candidate and candidate.content else []
        for index, part in enumerate(parts):
            if getattr(part, "text", None):
                text_parts.append(part.text)
            function_call = getattr(part, "function_call", None)
            if function_call:
                calls.append(ToolCall(id=f"gemini-call-{index}", name=function_call.name, arguments=dict(function_call.args or {})))
        content = "\n".join(text_parts).strip() or None
        if content:
            try:
                parsed = json.loads(content)
                if isinstance(parsed, dict) and "intent" in parsed:
                    analysis = AIAnalysis.model_validate(parsed)
            except (json.JSONDecodeError, ValueError):
                pass
        return AIResponse(content=content, tool_calls=calls, analysis=analysis, provider=self.name, model=self.model, context=AIContext(messages=context))

    async def analyze_email(self, sender: str, subject: str, body: str) -> AIResponse:
        prompt = f"Correo recibido\nRemitente: {sender}\nAsunto: {subject}\nCuerpo:\n{body}\n\nAnaliza el correo y usa herramientas solo si corresponde."
        response = await self.client.aio.models.generate_content(model=self.model, contents=prompt, config=self._config())
        return self._normalize(response, [{"role": "user", "parts": [{"text": prompt}]}])

    async def continue_with_tool_results(self, response: AIResponse, results: list[ToolResult]) -> AIResponse:
        from google.genai import types

        contents = list(response.context.messages)
        contents.append(types.Content(role="model", parts=[types.Part(function_call={"name": call.name, "args": call.arguments}) for call in response.tool_calls]))
        contents.append(types.Content(role="tool", parts=[types.Part.from_function_response(name=result.tool_name, response=result.model_dump()) for result in results]))
        generated = await self.client.aio.models.generate_content(model=self.model, contents=contents, config=self._config())
        return self._normalize(generated, contents)
