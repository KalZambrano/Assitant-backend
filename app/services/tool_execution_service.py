from app.schemas.common import ToolCall, ToolResult
from app.tools.registry import TOOLS


def execute_tool(db, call: ToolCall) -> ToolResult:
    handler = TOOLS.get(call.name)
    if handler is None:
        return ToolResult(tool_call_id=call.id, tool_name=call.name, success=False, action="failed", reason="tool_not_found", message="Unknown tool")
    try:
        return handler(db, call.arguments, call.id)
    except (ValueError, TypeError, KeyError) as exc:
        return ToolResult(tool_call_id=call.id, tool_name=call.name, success=False, action="failed", reason="validation_error", message=str(exc))
