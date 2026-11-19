from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p03_parallelization import run_parallelization

router = APIRouter(prefix="/p03-parallelization", tags=["03. Parallelization"])


class ParallelizationRequest(BaseModel):
    input_text: str = Field(
        default=(
            "We are considering adding an autonomous voice-to-SQL assistant inside our B2B SaaS "
            "analytics dashboard. Customers will speak natural-language questions, which transcribe "
            "via Whisper, translate into read-only PostgreSQL queries by an LLM, execute against "
            "multi-tenant customer tables, and render live charts."
        ),
        description="Scenario or proposal to evaluate across parallel specialist branches",
    )
    target_format: str = Field(default="Executive Brief", description="Format for the merged synthesis")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.3, ge=0.0, le=1.0)


@router.post("/run")
async def execute_parallelization(req: ParallelizationRequest):
    """
    Run Pattern 03: Parallelization (Asyncio Fan-Out / Fan-In).
    Returns a Server-Sent Events (SSE) stream of concurrent worker completions and merged output.
    """
    generator = run_parallelization(
        input_text=req.input_text,
        target_format=req.target_format,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
