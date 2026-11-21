"""
Pattern 05: Evaluator-Optimizer (Cyclic Generator <-> Evaluator Feedback Loop)
Flow: in -> Generator -> Draft -> Evaluator -> (Feedback Loop if fail) -> Out (Pass or Max Retries)
Framework: LangGraph
"""

import json
from typing import Any, AsyncGenerator, Dict, Optional, TypedDict
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, Field

from backend.app.core.events import AgentEvent
from backend.app.core.llm_factory import extract_text, get_chat_model


# -------------------------------------------------------------------------
# Structured Evaluation Schema
# -------------------------------------------------------------------------
class EvaluationResult(BaseModel):
    passed: bool = Field(
        description="True ONLY if the draft satisfies all requirements, handles edge cases, and scores >= 8/10."
    )
    score: int = Field(
        description="Quality score from 1 to 10.",
        ge=1,
        le=10,
    )
    feedback: str = Field(
        description="Specific, actionable critique for improving the draft, or praise if passed."
    )


# -------------------------------------------------------------------------
# LangGraph State Definition
# -------------------------------------------------------------------------
class EvalOptState(TypedDict):
    input_text: str
    target_format: str
    iteration: int
    max_iterations: int
    draft: str
    feedback: str
    score: int
    passed: bool


# -------------------------------------------------------------------------
# Graph Builder
# -------------------------------------------------------------------------
def _build_eval_opt_graph(llm):
    async def generator_node(state: EvalOptState) -> Dict[str, Any]:
        next_iter = state["iteration"] + 1
        if state["iteration"] == 0:
            messages = [
                SystemMessage(
                    content=(
                        f"You are an expert Solution Generator. Produce a thorough, production-grade "
                        f"response in **{state['target_format']}** format that satisfies every requirement "
                        "and edge case in the user's request."
                    )
                ),
                HumanMessage(content=state["input_text"]),
            ]
        else:
            messages = [
                SystemMessage(
                    content=(
                        f"You are an expert Solution Generator revising a previous draft (Attempt #{next_iter}). "
                        f"Address EVERY point in the evaluator's feedback while keeping the **{state['target_format']}** format."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Original Request:\n{state['input_text']}\n\n"
                        f"Previous Draft:\n{state['draft']}\n\n"
                        f"Evaluator Feedback (Score {state['score']}/10):\n{state['feedback']}\n\n"
                        "Produce the improved draft:"
                    )
                ),
            ]

        res = await llm.ainvoke(messages)
        return {
            "draft": extract_text(res.content),
            "iteration": next_iter,
        }

    async def evaluator_node(state: EvalOptState) -> Dict[str, Any]:
        eval_prompt = [
            SystemMessage(
                content=(
                    "You are a strict Quality Evaluator. Grade the draft against the original request "
                    "on completeness, technical accuracy, edge-case handling, and clarity.\n"
                    "Be genuinely critical on early drafts if anything is missing or vague; only set "
                    "`passed=true` when the draft is truly complete and scores 8/10 or higher."
                )
            ),
            HumanMessage(
                content=(
                    f"Original Request:\n{state['input_text']}\n\n"
                    f"Target Format: {state['target_format']}\n\n"
                    f"Draft (Iteration {state['iteration']}):\n{state['draft']}"
                )
            ),
        ]

        evaluation: Optional[EvaluationResult] = None
        try:
            structured_llm = llm.with_structured_output(EvaluationResult)
            evaluation = await structured_llm.ainvoke(eval_prompt)
        except Exception:
            fallback_prompt = [
                SystemMessage(
                    content=(
                        "You are a strict Quality Evaluator. Respond ONLY with valid JSON matching:\n"
                        '{"passed": true|false, "score": 1..10, "feedback": "..."}'
                    )
                ),
                eval_prompt[1],
            ]
            raw = extract_text((await llm.ainvoke(fallback_prompt)).content).strip()
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0].strip()
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0].strip()
            evaluation = EvaluationResult.model_validate(json.loads(raw))

        return {
            "passed": evaluation.passed,
            "score": evaluation.score,
            "feedback": evaluation.feedback,
        }

    def route_after_eval(state: EvalOptState) -> str:
        if state["passed"] or state["iteration"] >= state["max_iterations"]:
            return END
        return "generator"

    builder = StateGraph(EvalOptState)
    builder.add_node("generator", generator_node)
    builder.add_node("evaluator", evaluator_node)

    builder.add_edge(START, "generator")
    builder.add_edge("generator", "evaluator")
    builder.add_conditional_edges("evaluator", route_after_eval, ["generator", END])

    return builder.compile()


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_evaluator_optimizer(
    input_text: str,
    target_format: str = "Executive Brief",
    max_iterations: int = 3,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 05 (Evaluator-Optimizer) using a cyclic LangGraph StateGraph
    and streams each generation & evaluation cycle as Server-Sent Events (SSE).
    """
    yield AgentEvent(
        step="start",
        node="Evaluator-Optimizer Input",
        content=(
            f"Starting iterative refinement loop (max **{max_iterations}** iterations, "
            f"format: **{target_format}**)."
        ),
        data={"max_iterations": max_iterations, "target_format": target_format},
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)
    graph = _build_eval_opt_graph(llm)

    initial_state: EvalOptState = {
        "input_text": input_text,
        "target_format": target_format,
        "iteration": 0,
        "max_iterations": max_iterations,
        "draft": "",
        "feedback": "",
        "score": 0,
        "passed": False,
    }

    last_draft = ""
    last_score = 0
    last_iteration = 0
    did_pass = False

    try:
        async for update in graph.astream(initial_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                if node_name == "generator":
                    last_iteration = node_output.get("iteration", last_iteration)
                    last_draft = node_output.get("draft", "")
                    yield AgentEvent(
                        step="step_complete",
                        node=f"Generator (Draft #{last_iteration})",
                        content=last_draft,
                        data={"iteration": last_iteration, "draft": last_draft},
                    ).to_sse()

                elif node_name == "evaluator":
                    did_pass = bool(node_output.get("passed", False))
                    last_score = int(node_output.get("score", 0))
                    feedback = node_output.get("feedback", "")

                    if did_pass:
                        yield AgentEvent(
                            step="gate_passed",
                            node=f"Evaluator (Iteration #{last_iteration})",
                            content=(
                                f"✅ **Passed Quality Bar! (Score: {last_score}/10)**\n\n"
                                f"**Feedback:** {feedback}"
                            ),
                            data={"passed": True, "score": last_score, "feedback": feedback},
                        ).to_sse()
                    else:
                        will_retry = last_iteration < max_iterations
                        suffix = (
                            "Looping back to Generator for refinement..."
                            if will_retry
                            else f"Reached max iterations ({max_iterations}); returning best draft."
                        )
                        yield AgentEvent(
                            step="gate_failed",
                            node=f"Evaluator (Iteration #{last_iteration})",
                            content=(
                                f"🔁 **Revision Requested (Score: {last_score}/10)**\n\n"
                                f"**Feedback:** {feedback}\n\n_{suffix}_"
                            ),
                            data={"passed": False, "score": last_score, "feedback": feedback},
                            status="running" if will_retry else "gated",
                        ).to_sse()

        yield AgentEvent(
            step="completed",
            node="Final Approved Output" if did_pass else "Best Draft (Max Iterations)",
            content=last_draft,
            data={
                "passed": did_pass,
                "score": last_score,
                "iterations": last_iteration,
                "final_output": last_draft,
            },
            status="completed",
        ).to_sse()

    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Evaluator-Optimizer Graph",
            content=f"Execution failed: {str(e)}",
            status="failed",
        ).to_sse()
