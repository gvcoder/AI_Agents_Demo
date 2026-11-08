from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p02_routing import run_routing

router = APIRouter(prefix="/p02-routing", tags=["02. Routing"])

class RoutingRequest(BaseModel):
    user_query: str = Field(
        default="We received an unexpected $4,500 charge on invoice #INV-9821 this morning. Our contracted seat count hasn't changed. Could you clarify and issue a credit memo?",
        description="Incoming user message to classify and route"
    )
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

@router.post("/run")
async def execute_routing(req: RoutingRequest):
    """
    Run Pattern 02: Intent Classification & Specialist Routing (Pydantic AI).
    Returns a Server-Sent Events (SSE) stream of routing events.
    """
    generator = run_routing(
        user_query=req.user_query,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature
    )
    return EventSourceResponse(generator)

