from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p06_react import run_react

router = APIRouter(prefix="/p06-react", tags=["06. ReAct"])


class ReActRequest(BaseModel):
    input_text: str = Field(
        default=(
            "A customer in EU wants to buy 15 units of EdgeGateway X1 and 8 licenses of "
            "CloudSync Pro. Check their unit prices and stock, apply any eligible volume "
            "discount tier, add EU shipping, and calculate the final total in USD."
        ),
        description="Multi-step reasoning + tool-use task for the ReAct agent",
    )
    max_steps: int = Field(default=8, ge=2, le=12, description="Maximum Thought-Action-Observation cycles")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)


@router.post("/run")
async def execute_react(req: ReActRequest):
    """
    Run Pattern 06: ReAct (Smolagents ToolCallingAgent).
    Returns a Server-Sent Events (SSE) stream of Thought, Action, Observation, and Final Answer.
    """
    generator = run_react(
        input_text=req.input_text,
        max_steps=req.max_steps,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
