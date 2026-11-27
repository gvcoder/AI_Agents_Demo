from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p11_tool_use import run_tool_use

router = APIRouter(prefix="/p11-tool-use", tags=["11. Tool Use"])


class ToolUseRequest(BaseModel):
    input_text: str = Field(
        default=(
            "Check our 2026-11 cloud spend for `database` and `ai_inference`, identify which "
            "ones are over budget, forecast the 12-month total USD spend for `ai_inference` "
            "assuming 5% monthly growth, and convert that 12-month total to EUR."
        ),
        description="Query requiring deterministic structured tool calls",
    )
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.1, ge=0.0, le=1.0)


@router.post("/run")
async def execute_tool_use(req: ToolUseRequest):
    """
    Run Pattern 11: Tool Use (Pydantic AI Type-Safe Function Calling).
    Returns a Server-Sent Events (SSE) stream of JSON tool calls, results, and final answer.
    """
    generator = run_tool_use(
        input_text=req.input_text,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
