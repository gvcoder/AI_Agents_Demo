from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p01_prompt_chaining import run_prompt_chaining

router = APIRouter(prefix="/p01-prompt-chaining", tags=["01. Prompt Chaining"])

class PromptChainingRequest(BaseModel):
    input_text: str = Field(
        default=(
            "Acme Corp announced Q3 2026 earnings on November 5th. Revenue reached $4.2B, "
            "up 18% YoY. Operating profit expanded to $850M. Cloud ARR grew 42% reaching $1.1B. "
            "CEO Sarah Lin noted aggressive hiring in AI R&D with 350 new engineers in Munich."
        ),
        description="Source input text to process through the gated chain"
    )
    target_format: str = Field(default="Executive Brief", description="Format for the final output")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.2, ge=0.0, le=1.0)

@router.post("/run")
async def execute_prompt_chaining(req: PromptChainingRequest):
    """
    Run Pattern 01: Prompt Chaining with Gate Verification.
    Returns a Server-Sent Events (SSE) stream of pipeline events.
    """
    generator = run_prompt_chaining(
        input_text=req.input_text,
        target_format=req.target_format,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature
    )
    return EventSourceResponse(generator)

