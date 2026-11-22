"""
Pattern 07: Plan-and-Execute (Macro Planner + Step Executor + Dynamic Replanner)
Flow: Planner -> Step List -> Executor (Step 1...N) -> (Replan if step fails) -> Synthesizer -> out
Framework: LangGraph
"""

import json
import operator
from typing import Annotated, Any, AsyncGenerator, Dict, List, Optional, Tuple, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from backend.app.core.events import AgentEvent
from backend.app.core.llm_factory import extract_text, get_chat_model


# -------------------------------------------------------------------------
# Structured Schemas
# -------------------------------------------------------------------------
class Plan(BaseModel):
    steps: List[str] = Field(
        description="Ordered list of 3 to 5 concise, actionable steps to accomplish the goal.",
        min_length=2,
        max_length=5,
    )


class StepExecutionResult(BaseModel):
    success: bool = Field(
        description="True if the step completed cleanly; False if a blocker/failure requires replanning."
    )
    output: str = Field(description="Detailed result or deliverable produced by executing this step.")
    blocker_reason: str = Field(
        default="",
        description="If success=False, explain the blocker or new constraint discovered.",
    )


class ReplanDecision(BaseModel):
    updated_steps: List[str] = Field(
        description="Revised list of remaining steps to work around the blocker and finish the goal."
    )
    rationale: str = Field(description="Why the plan was adjusted.")


# -------------------------------------------------------------------------
# LangGraph State Definition
# -------------------------------------------------------------------------
class PlanExecuteState(TypedDict):
    input_text: str
    target_format: str
    plan: List[str]
    past_steps: Annotated[List[Tuple[str, str]], operator.add]
    last_step_ok: bool
    last_blocker: str
    replan_count: int
    steps_executed: int
    max_steps: int
    final_response: str


# -------------------------------------------------------------------------
# Graph Builder
# -------------------------------------------------------------------------
def _build_plan_execute_graph(llm):
    async def planner_node(state: PlanExecuteState) -> Dict[str, Any]:
        prompt = [
            SystemMessage(
                content=(
                    "You are a Strategic Macro Planner. Given a user objective, write a clear, "
                    "ordered plan of 3 to 5 concrete, sequential steps. Each step should build on "
                    "the previous ones and be executable independently."
                )
            ),
            HumanMessage(content=f"Objective:\n{state['input_text']}"),
        ]

        plan_obj: Optional[Plan] = None
        try:
            structured_llm = llm.with_structured_output(Plan)
            plan_obj = await structured_llm.ainvoke(prompt)
        except Exception:
            fallback_prompt = [
                SystemMessage(
                    content=(
                        "You are a Strategic Macro Planner. Respond ONLY with valid JSON matching:\n"
                        '{"steps": ["Step 1...", "Step 2...", "Step 3..."]}'
                    )
                ),
                prompt[1],
            ]
            raw = extract_text((await llm.ainvoke(fallback_prompt)).content).strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            plan_obj = Plan.model_validate(json.loads(raw))

        return {"plan": plan_obj.steps}

    async def executor_node(state: PlanExecuteState) -> Dict[str, Any]:
        current_step = state["plan"][0]
        remaining = state["plan"][1:]
        history_text = (
            "\n".join(f"- **{s}**: {r}" for s, r in state["past_steps"])
            if state["past_steps"]
            else "None yet."
        )

        exec_prompt = [
            SystemMessage(
                content=(
                    "You are a Precise Step Executor. Execute ONLY the current step using the "
                    "overall objective and completed steps as context.\n"
                    "If the step is feasible, set `success=true` and provide a thorough `output`. "
                    "If the step hits an impossible constraint or missing prerequisite explicitly "
                    "present in the objective, set `success=false` and explain `blocker_reason`."
                )
            ),
            HumanMessage(
                content=(
                    f"Overall Objective:\n{state['input_text']}\n\n"
                    f"Completed Steps:\n{history_text}\n\n"
                    f"Current Step to Execute:\n{current_step}"
                )
            ),
        ]

        result: Optional[StepExecutionResult] = None
        try:
            structured_llm = llm.with_structured_output(StepExecutionResult)
            result = await structured_llm.ainvoke(exec_prompt)
        except Exception:
            res = await llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "Execute the current step concisely and thoroughly. "
                            "Provide the actionable result."
                        )
                    ),
                    exec_prompt[1],
                ]
            )
            result = StepExecutionResult(
                success=True,
                output=extract_text(res.content),
                blocker_reason="",
            )

        return {
            "plan": remaining,
            "past_steps": [(current_step, result.output)],
            "last_step_ok": result.success,
            "last_blocker": result.blocker_reason,
            "steps_executed": state["steps_executed"] + 1,
        }

    async def replanner_node(state: PlanExecuteState) -> Dict[str, Any]:
        history_text = "\n".join(f"- **{s}**: {r}" for s, r in state["past_steps"])
        replan_prompt = [
            SystemMessage(
                content=(
                    "You are a Dynamic Replanner. The previous step encountered a blocker. "
                    "Adjust the remaining steps so the overall objective can still be completed safely."
                )
            ),
            HumanMessage(
                content=(
                    f"Objective:\n{state['input_text']}\n\n"
                    f"Completed Steps:\n{history_text}\n\n"
                    f"Blocker:\n{state['last_blocker']}\n\n"
                    f"Original Remaining Steps:\n{state['plan']}"
                )
            ),
        ]

        decision: Optional[ReplanDecision] = None
        try:
            structured_llm = llm.with_structured_output(ReplanDecision)
            decision = await structured_llm.ainvoke(replan_prompt)
        except Exception:
            decision = ReplanDecision(
                updated_steps=state["plan"],
                rationale="Continuing with remaining steps after logging blocker.",
            )

        return {
            "plan": decision.updated_steps,
            "replan_count": state["replan_count"] + 1,
            "last_blocker": decision.rationale,
        }

    async def synthesizer_node(state: PlanExecuteState) -> Dict[str, Any]:
        history_text = "\n\n".join(
            f"### Step {i + 1}: {step}\n{output}"
            for i, (step, output) in enumerate(state["past_steps"])
        )
        synth_prompt = [
            SystemMessage(
                content=(
                    f"You are an Executive Synthesizer. Combine all executed plan steps into a "
                    f"polished, cohesive **{state['target_format']}**."
                )
            ),
            HumanMessage(
                content=(
                    f"Original Objective:\n{state['input_text']}\n\n"
                    f"Executed Steps & Results:\n{history_text}"
                )
            ),
        ]
        res = await llm.ainvoke(synth_prompt)
        return {"final_response": extract_text(res.content)}

    def route_after_executor(state: PlanExecuteState) -> str:
        if state["steps_executed"] >= state["max_steps"]:
            return "synthesizer"
        if not state["last_step_ok"] and state["replan_count"] < 2:
            return "replanner"
        if not state["plan"]:
            return "synthesizer"
        return "executor"

    def route_after_replanner(state: PlanExecuteState) -> str:
        if not state["plan"] or state["steps_executed"] >= state["max_steps"]:
            return "synthesizer"
        return "executor"

    builder = StateGraph(PlanExecuteState)
    builder.add_node("planner", planner_node)
    builder.add_node("executor", executor_node)
    builder.add_node("replanner", replanner_node)
    builder.add_node("synthesizer", synthesizer_node)

    builder.add_edge(START, "planner")
    builder.add_edge("planner", "executor")
    builder.add_conditional_edges(
        "executor", route_after_executor, ["executor", "replanner", "synthesizer"]
    )
    builder.add_conditional_edges(
        "replanner", route_after_replanner, ["executor", "synthesizer"]
    )
    builder.add_edge("synthesizer", END)

    return builder.compile()


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_plan_and_execute(
    input_text: str,
    target_format: str = "Executive Brief",
    max_steps: int = 8,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 07 (Plan-and-Execute) using LangGraph and streams
    Planner -> Executor steps -> (Replanner if needed) -> Synthesizer as SSE.
    """
    yield AgentEvent(
        step="start",
        node="Plan-and-Execute Input",
        content=(
            f"Received objective ({len(input_text)} chars). Target format: **{target_format}**.\n"
            "Invoking Macro Planner to generate the step list..."
        ),
        data={"target_format": target_format, "max_steps": max_steps},
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)
    graph = _build_plan_execute_graph(llm)

    initial_state: PlanExecuteState = {
        "input_text": input_text,
        "target_format": target_format,
        "plan": [],
        "past_steps": [],
        "last_step_ok": True,
        "last_blocker": "",
        "replan_count": 0,
        "steps_executed": 0,
        "max_steps": max_steps,
        "final_response": "",
    }

    try:
        async for update in graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                if node_name == "planner":
                    steps = node_output.get("plan", [])
                    formatted = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(steps))
                    yield AgentEvent(
                        step="plan_created",
                        node="Macro Planner",
                        content=f"🗺️ **Generated {len(steps)}-Step Plan:**\n\n{formatted}",
                        data={"plan": steps},
                    ).to_sse()

                elif node_name == "executor":
                    step_num = node_output.get("steps_executed", 0)
                    past = node_output.get("past_steps", [])
                    step_title, step_out = past[-1] if past else ("Step", "")
                    ok = node_output.get("last_step_ok", True)
                    blocker = node_output.get("last_blocker", "")
                    prefix = "✅" if ok else f"⚠️ **Blocker detected:** {blocker}\n\n"
                    yield AgentEvent(
                        step="step_complete",
                        node=f"Executor — Step {step_num}",
                        content=f"{prefix} **{step_title}**\n\n{step_out}",
                        data={"step_number": step_num, "success": ok},
                    ).to_sse()

                elif node_name == "replanner":
                    new_steps = node_output.get("plan", [])
                    rationale = node_output.get("last_blocker", "")
                    formatted = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(new_steps))
                    yield AgentEvent(
                        step="replan",
                        node=f"Replanner (#{node_output.get('replan_count', 1)})",
                        content=f"🔄 **Plan Revised:** {rationale}\n\n{formatted}",
                        data={"plan": new_steps},
                    ).to_sse()

                elif node_name == "synthesizer":
                    final_output = node_output.get("final_response", "")
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
            node="Plan-and-Execute Graph",
            content=f"Execution failed: {str(e)}",
            status="failed",
        ).to_sse()
