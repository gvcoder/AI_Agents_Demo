from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p05_evaluator_optimizer import run_evaluator_optimizer

router = APIRouter(prefix="/p05-evaluator-optimizer", tags=["05. Evaluator-Optimizer"])


class EvaluatorOptimizerRequest(BaseModel):
    input_text: str = Field(
        default=(
            "Write a Python rate-limiter class `TokenBucket` that is thread-safe, supports "
            "configurable refill rate and burst capacity, includes a `try_consume(tokens=1)` "
            "method, handles clock drift/monotonic time safely, and includes 3 concise unit test cases."
        ),
        description="Task or specification for the Generator-Evaluator refinement loop",
    )
    target_format: str = Field(default="JSON Specification", description="Format for the generated output")
    max_iterations: int = Field(default=3, ge=1, le=5, description="Maximum refinement iterations")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


@router.post("/run")
async def execute_evaluator_optimizer(req: EvaluatorOptimizerRequest):
    """
    Run Pattern 05: Evaluator-Optimizer (LangGraph Cyclic Refinement Loop).
    Returns a Server-Sent Events (SSE) stream of drafts, evaluations, and final output.
    """
    generator = run_evaluator_optimizer(
        input_text=req.input_text,
        target_format=req.target_format,
        max_iterations=req.max_iterations,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
