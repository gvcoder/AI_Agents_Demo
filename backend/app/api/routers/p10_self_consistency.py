from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p10_self_consistency import run_self_consistency

router = APIRouter(prefix="/p10-self-consistency", tags=["10. Self-Consistency"])


class SelfConsistencyRequest(BaseModel):
    input_text: str = Field(
        default=(
            "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. "
            "If a store sells 12 balls at a 20% discount off the original ball price, "
            "how much do the 12 balls cost in total?"
        ),
        description="Reasoning or math/logic question to sample N times and vote on",
    )
    num_samples: int = Field(default=5, ge=3, le=7, description="Number of parallel reasoning samples")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)


@router.post("/run")
async def execute_self_consistency(req: SelfConsistencyRequest):
    """
    Run Pattern 10: Self-Consistency (Parallel Sampling + Majority Vote).
    Returns a Server-Sent Events (SSE) stream of N samples, vote tally, and consensus answer.
    """
    generator = run_self_consistency(
        input_text=req.input_text,
        num_samples=req.num_samples,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
