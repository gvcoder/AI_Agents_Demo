from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p07_plan_and_execute import run_plan_and_execute

router = APIRouter(prefix="/p07-plan-and-execute", tags=["07. Plan-and-Execute"])


class PlanAndExecuteRequest(BaseModel):
    input_text: str = Field(
        default=(
            "Design a zero-downtime database migration plan to move a 500GB PostgreSQL "
            "multi-tenant production database from AWS RDS to Cloud SQL, including schema "
            "validation, dual-write/CDC replication, cutover verification, and rollback."
        ),
        description="Long-horizon objective for the Planner + Executor + Replanner graph",
    )
    target_format: str = Field(default="Executive Brief", description="Format for the final synthesized plan")
    max_steps: int = Field(default=8, ge=2, le=12, description="Maximum execution steps")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


@router.post("/run")
async def execute_plan_and_execute(req: PlanAndExecuteRequest):
    """
    Run Pattern 07: Plan-and-Execute (LangGraph).
    Returns a Server-Sent Events (SSE) stream of planning, step execution, replanning, and synthesis.
    """
    generator = run_plan_and_execute(
        input_text=req.input_text,
        target_format=req.target_format,
        max_steps=req.max_steps,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
