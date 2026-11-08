import json
from typing import Any, Dict, Optional
from pydantic import BaseModel

class AgentEvent(BaseModel):
    step: str                  # e.g., "input", "thought", "gate_check", "tool_call", "output", "error"
    node: str                  # Active node name in graph/pattern
    content: str               # Human-readable markdown or message
    data: Optional[Dict[str, Any]] = None # Optional payload (metrics, intermediate state)
    status: str = "running"    # "running" | "completed" | "failed" | "gated"

    def to_sse(self) -> str:
        return f"data: {json.dumps(self.model_dump())}\n\n"

