from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p04_orchestrator_workers import run_orchestrator_workers

router = APIRouter(prefix="/p04-orchestrator-workers", tags=["04. Orchestrator-Workers"])


class OrchestratorWorkersRequest(BaseModel):
    input_text: str = Field(
        default=(
            "We need to migrate our legacy monolithic Python/Flask e-commerce backend "
            "(handling user auth, product catalog, Stripe checkout, and order email notifications) "
            "to an event-driven FastAPI + Kafka microservices architecture with zero downtime."
        ),
        description="Complex task for the orchestrator to dynamically decompose into worker subtasks",
    )
    target_format: str = Field(default="Executive Brief", description="Format for the synthesized output")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


@router.post("/run")
async def execute_orchestrator_workers(req: OrchestratorWorkersRequest):
    """
    Run Pattern 04: Orchestrator-Workers (LangGraph Send Map-Reduce).
    Returns a Server-Sent Events (SSE) stream of dynamic planning, parallel worker completions, and synthesis.
    """
    generator = run_orchestrator_workers(
        input_text=req.input_text,
        target_format=req.target_format,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
