from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p08_reflection import run_reflection

router = APIRouter(prefix="/p08-reflection", tags=["08. Reflection"])


class ReflectionRequest(BaseModel):
    input_text: str = Field(
        default=(
            "Draft a crisp customer incident post-mortem email explaining a 22-minute API "
            "latency spike caused by a misconfigured Redis connection pool during peak traffic, "
            "detailing root cause, customer impact, immediate fix, and long-term safeguards."
        ),
        description="Prompt or writing task for Draft -> Self-Critic -> Revise reflection",
    )
    target_format: str = Field(default="Executive Brief", description="Format for the reflected output")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


@router.post("/run")
async def execute_reflection(req: ReflectionRequest):
    """
    Run Pattern 08: Reflection (Pydantic AI Draft -> Self-Critic -> Revise).
    Returns a Server-Sent Events (SSE) stream of draft, self-critique rubric, and revised output.
    """
    generator = run_reflection(
        input_text=req.input_text,
        target_format=req.target_format,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
