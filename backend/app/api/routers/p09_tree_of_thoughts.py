from fastapi import APIRouter
from pydantic import BaseModel, Field
from typing import Optional
from sse_starlette.sse import EventSourceResponse

from backend.app.patterns.p09_tree_of_thoughts import run_tree_of_thoughts

router = APIRouter(prefix="/p09-tree-of-thoughts", tags=["09. Tree of Thoughts"])


class TreeOfThoughtsRequest(BaseModel):
    input_text: str = Field(
        default=(
            "You have 3 servers (2 CPUs each) and 5 microservices with CPU/memory/latency constraints: "
            "Auth (1 CPU, must be isolated or paired only with Gateway), Gateway (1 CPU, public-facing), "
            "Billing (1.5 CPU, PCI isolated from Gateway), Search (1.5 CPU), and Worker (1 CPU). "
            "Find a valid placement across the 3 servers minimizing cross-server network hops."
        ),
        description="Constraint-satisfaction, puzzle, or strategic planning problem for ToT search",
    )
    target_format: str = Field(default="Executive Brief", description="Format for the final solution")
    branching_factor: int = Field(default=3, ge=2, le=4, description="Candidate branches per frontier node")
    max_depth: int = Field(default=2, ge=1, le=3, description="Tree search depth")
    beam_width: int = Field(default=2, ge=1, le=3, description="Top-K branches kept at each level")
    provider: Optional[str] = Field(default=None, description="LLM provider: gemini | openai | anthropic | ollama")
    model_name: Optional[str] = Field(default=None, description="Specific model override")
    temperature: float = Field(default=0.5, ge=0.0, le=1.0)


@router.post("/run")
async def execute_tree_of_thoughts(req: TreeOfThoughtsRequest):
    """
    Run Pattern 09: Tree of Thoughts (Beam / BFS Algorithmic Search).
    Returns a Server-Sent Events (SSE) stream of branching, scoring, pruning, and best-path synthesis.
    """
    generator = run_tree_of_thoughts(
        input_text=req.input_text,
        target_format=req.target_format,
        branching_factor=req.branching_factor,
        max_depth=req.max_depth,
        beam_width=req.beam_width,
        provider=req.provider,
        model_name=req.model_name,
        temperature=req.temperature,
    )
    return EventSourceResponse(generator)
