"""
Pattern 04: Orchestrator-Workers (Dynamic Map-Reduce with LangGraph Send)
Flow: in -> Orchestrator (Dynamic Plan) -> [Send(Worker 1), Send(Worker 2), ...] -> Synthesizer -> out
Framework: LangGraph
"""

import json
import operator
import time
from typing import Annotated, Any, AsyncGenerator, Dict, List, Optional, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from langgraph.types import Send
from pydantic import BaseModel, Field

from backend.app.core.events import AgentEvent
from backend.app.core.llm_factory import extract_text, get_chat_model


# -------------------------------------------------------------------------
# Structured Plan Schema
# -------------------------------------------------------------------------
class Subtask(BaseModel):
    worker_id: str = Field(description="Short identifier such as W1, W2, W3.")
    role: str = Field(description="Specialist role title for this worker, e.g. 'Backend API Architect'.")
    focus: str = Field(description="Concise 1-line summary of what this worker owns.")
    instructions: str = Field(description="Detailed, actionable instructions for this worker.")


class OrchestratorPlan(BaseModel):
    analysis: str = Field(description="Brief reasoning for why the task was decomposed into these subtasks.")
    subtasks: List[Subtask] = Field(
        description="Between 2 and 5 independent subtasks to execute in parallel.",
        min_length=2,
        max_length=5,
    )


# -------------------------------------------------------------------------
# LangGraph State Definitions
# -------------------------------------------------------------------------
class OrchestratorState(TypedDict):
    input_text: str
    target_format: str
    analysis: str
    subtasks: List[Dict[str, Any]]
    completed_workers: Annotated[List[Dict[str, Any]], operator.add]
    final_output: str


class WorkerState(TypedDict):
    input_text: str
    subtask: Dict[str, Any]


# -------------------------------------------------------------------------
# Graph Builder
# -------------------------------------------------------------------------
def _build_orchestrator_graph(llm):
    async def orchestrator_node(state: OrchestratorState) -> Dict[str, Any]:
        prompt = [
            SystemMessage(
                content=(
                    "You are a Lead Orchestrator AI. Given a complex user request, dynamically "
                    "decompose it into 2 to 5 independent, non-overlapping specialist worker subtasks "
                    "that can be executed in parallel.\n"
                    "Tailor the number of workers and their roles specifically to the request."
                )
            ),
            HumanMessage(content=f"Task to decompose:\n{state['input_text']}"),
        ]

        plan: Optional[OrchestratorPlan] = None
        try:
            structured_llm = llm.with_structured_output(OrchestratorPlan)
            plan = await structured_llm.ainvoke(prompt)
        except Exception:
            # Fallback for providers/models without native structured output
            fallback_prompt = [
                SystemMessage(
                    content=(
                        "You are a Lead Orchestrator AI. Decompose the task into 2 to 4 parallel subtasks. "
                        "Respond ONLY with valid JSON matching:\n"
                        '{"analysis": "...", "subtasks": [{"worker_id": "W1", "role": "...", '
                        '"focus": "...", "instructions": "..."}]}'
                    )
                ),
                HumanMessage(content=state["input_text"]),
            ]
            raw = extract_text((await llm.ainvoke(fallback_prompt)).content).strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            plan = OrchestratorPlan.model_validate(json.loads(raw))

        return {
            "analysis": plan.analysis,
            "subtasks": [s.model_dump() for s in plan.subtasks],
        }

    def assign_workers(state: OrchestratorState):
        return [
            Send("worker", {"input_text": state["input_text"], "subtask": subtask})
            for subtask in state["subtasks"]
        ]

    async def worker_node(state: WorkerState) -> Dict[str, Any]:
        subtask = state["subtask"]
        t0 = time.perf_counter()
        messages = [
            SystemMessage(
                content=(
                    f"You are **{subtask['role']}** ({subtask['worker_id']}).\n"
                    f"Focus: {subtask['focus']}\n"
                    "Deliver a crisp, high-signal, actionable response for your assigned slice only."
                )
            ),
            HumanMessage(
                content=(
                    f"Overall Context:\n{state['input_text']}\n\n"
                    f"Your Specific Instructions:\n{subtask['instructions']}"
                )
            ),
        ]
        res = await llm.ainvoke(messages)
        elapsed = round(time.perf_counter() - t0, 2)
        return {
            "completed_workers": [
                {
                    "worker_id": subtask["worker_id"],
                    "role": subtask["role"],
                    "focus": subtask["focus"],
                    "output": extract_text(res.content),
                    "elapsed_s": elapsed,
                }
            ]
        }

    async def synthesizer_node(state: OrchestratorState) -> Dict[str, Any]:
        worker_sections = "\n\n".join(
            f"### {w['worker_id']} — {w['role']} ({w['focus']})\n{w['output']}"
            for w in state["completed_workers"]
        )
        messages = [
            SystemMessage(
                content=(
                    f"You are a Principal Synthesizer. Combine all worker deliverables into a single, "
                    f"cohesive **{state['target_format']}**. Resolve any overlaps and present clear next steps."
                )
            ),
            HumanMessage(
                content=(
                    f"Original Request:\n{state['input_text']}\n\n"
                    f"Orchestrator Plan:\n{state['analysis']}\n\n"
                    f"Worker Outputs:\n{worker_sections}"
                )
            ),
        ]
        res = await llm.ainvoke(messages)
        return {"final_output": extract_text(res.content)}

    builder = StateGraph(OrchestratorState)
    builder.add_node("orchestrator", orchestrator_node)
    builder.add_node("worker", worker_node)
    builder.add_node("synthesizer", synthesizer_node)

    builder.add_edge(START, "orchestrator")
    builder.add_conditional_edges("orchestrator", assign_workers, ["worker"])
    builder.add_edge("worker", "synthesizer")
    builder.add_edge("synthesizer", END)

    return builder.compile()


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_orchestrator_workers(
    input_text: str,
    target_format: str = "Executive Brief",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 04 (Orchestrator-Workers) using LangGraph Send map-reduce
    and streams real-time node updates as Server-Sent Events (SSE).
    """
    yield AgentEvent(
        step="start",
        node="Orchestrator Input",
        content=(
            f"Received task ({len(input_text)} chars). Target format: **{target_format}**.\n"
            "Invoking Lead Orchestrator to dynamically plan worker subtasks..."
        ),
        data={"target_format": target_format},
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)
    graph = _build_orchestrator_graph(llm)

    initial_state: OrchestratorState = {
        "input_text": input_text,
        "target_format": target_format,
        "analysis": "",
        "subtasks": [],
        "completed_workers": [],
        "final_output": "",
    }

    try:
        async for update in graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                if node_name == "orchestrator":
                    subtasks = node_output.get("subtasks", [])
                    plan_lines = "\n".join(
                        f"- **{s['worker_id']} ({s['role']})**: {s['focus']}"
                        for s in subtasks
                    )
                    yield AgentEvent(
                        step="plan_created",
                        node="Lead Orchestrator",
                        content=(
                            f"📋 **Dynamically Spawned {len(subtasks)} Workers via `Send()`**\n\n"
                            f"**Decomposition Strategy:** {node_output.get('analysis', '')}\n\n"
                            f"{plan_lines}"
                        ),
                        data={"subtasks": subtasks},
                    ).to_sse()

                elif node_name == "worker":
                    for w in node_output.get("completed_workers", []):
                        yield AgentEvent(
                            step="step_complete",
                            node=f"{w['worker_id']}: {w['role']}",
                            content=f"⏱️ *Completed in {w['elapsed_s']}s*\n\n{w['output']}",
                            data=w,
                        ).to_sse()

                elif node_name == "synthesizer":
                    final_output = node_output.get("final_output", "")
                    yield AgentEvent(
                        step="completed",
                        node="Synthesizer (Final Output)",
                        content=final_output,
                        data={"final_output": final_output},
                        status="completed",
                    ).to_sse()

    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Orchestrator-Workers Graph",
            content=f"Execution failed: {str(e)}",
            status="failed",
        ).to_sse()
