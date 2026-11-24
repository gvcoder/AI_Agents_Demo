"""
Pattern 08: Reflection (Draft -> Self-Critic -> Revise -> Verified Output)
Flow: in -> Draft -> Self-Critic (Structured Rubric) -> Revise -> Verified Output
Framework: Pydantic AI
"""

from typing import AsyncGenerator, List, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from backend.app.core.events import AgentEvent
from backend.app.patterns.p02_routing import get_pydantic_ai_model


# -------------------------------------------------------------------------
# Structured Self-Critique Schema
# -------------------------------------------------------------------------
class ReflectionCritique(BaseModel):
    clarity_score: int = Field(description="Clarity & structure score from 1 to 10.", ge=1, le=10)
    logic_score: int = Field(description="Logical soundness & factual accuracy score from 1 to 10.", ge=1, le=10)
    tone_score: int = Field(description="Appropriateness of tone & completeness score from 1 to 10.", ge=1, le=10)
    flaws_found: List[str] = Field(
        description="Concrete weaknesses, ambiguities, missing edge cases, or tone issues in the draft."
    )
    improvement_plan: str = Field(
        description="Actionable instructions for revising the draft to fix the identified flaws."
    )
    needs_revision: bool = Field(
        description="True if any flaw should be fixed before delivering the final answer."
    )


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_reflection(
    input_text: str,
    target_format: str = "Executive Brief",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 08 (Reflection) step by step using Pydantic AI:
    1. Generates an initial zero-shot draft.
    2. Performs an explicit structured self-critique pass against clarity, logic, and tone.
    3. Revises the draft to resolve every identified flaw before returning the final output.
    """
    yield AgentEvent(
        step="start",
        node="Reflection Input",
        content=(
            f"Received task ({len(input_text)} chars). Target format: **{target_format}**.\n"
            "Starting **Draft ➔ Self-Critic ➔ Revise** reflection cycle..."
        ),
        data={"target_format": target_format},
    ).to_sse()

    model_spec = get_pydantic_ai_model(provider)
    if model_name and ":" in model_name:
        model_spec = model_name

    # 1. Pass 1: Initial Draft
    yield AgentEvent(
        step="thought",
        node="Pass 1: Initial Drafter",
        content=f"Generating initial zero-shot draft in **{target_format}** format...",
    ).to_sse()

    drafter_agent = Agent(
        model=model_spec,
        system_prompt=(
            f"You are a helpful assistant. Produce an initial draft responding to the user's request "
            f"in **{target_format}** format."
        ),
    )

    try:
        draft_run = await drafter_agent.run(input_text)
        initial_draft = str(draft_run.output)
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Pass 1: Initial Drafter",
            content=f"Draft generation failed: {str(e)}",
            status="failed",
        ).to_sse()
        return

    yield AgentEvent(
        step="step_complete",
        node="Pass 1: Initial Draft",
        content=initial_draft,
        data={"draft": initial_draft},
    ).to_sse()

    # 2. Pass 2: Structured Self-Critique
    yield AgentEvent(
        step="thought",
        node="Pass 2: Self-Critic",
        content="Reviewing initial draft for logical gaps, missing edge cases, clarity, and tone...",
    ).to_sse()

    critic_agent = Agent(
        model=model_spec,
        output_type=ReflectionCritique,
        system_prompt=(
            "You are a rigorous Self-Critic reviewing your own initial draft. "
            "Be candid and specific: identify any vague claims, missing caveats, structural clutter, "
            "or tone mismatches, score Clarity/Logic/Tone from 1-10, and produce a concrete improvement plan."
        ),
    )

    try:
        critique_run = await critic_agent.run(
            f"Original Request:\n{input_text}\n\n"
            f"Target Format: {target_format}\n\n"
            f"Initial Draft:\n{initial_draft}"
        )
        critique: ReflectionCritique = critique_run.output
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Pass 2: Self-Critic",
            content=f"Self-critique failed: {str(e)}",
            status="failed",
        ).to_sse()
        return

    flaws_md = "\n".join(f"- {f}" for f in critique.flaws_found) or "- None"
    yield AgentEvent(
        step="critique",
        node="Pass 2: Self-Critic (Rubric)",
        content=(
            f"🔍 **Self-Critique Scores** — Clarity: `{critique.clarity_score}/10` | "
            f"Logic: `{critique.logic_score}/10` | Tone: `{critique.tone_score}/10`\n\n"
            f"**Flaws / Gaps Identified:**\n{flaws_md}\n\n"
            f"**Improvement Plan:** {critique.improvement_plan}\n"
            f"**Revision Needed:** `{critique.needs_revision}`"
        ),
        data=critique.model_dump(),
    ).to_sse()

    # 3. Pass 3: Self-Revision
    if not critique.needs_revision:
        yield AgentEvent(
            step="completed",
            node="Verified Output (No Revision Needed)",
            content=initial_draft,
            data={"revised": False, "final_output": initial_draft},
            status="completed",
        ).to_sse()
        return

    yield AgentEvent(
        step="thought",
        node="Pass 3: Reviser",
        content="Applying self-critique improvement plan to produce the verified final output...",
    ).to_sse()

    reviser_agent = Agent(
        model=model_spec,
        system_prompt=(
            f"You are a Master Editor. Rewrite and elevate the initial draft in **{target_format}** "
            "format so that EVERY flaw identified in the self-critique is resolved cleanly."
        ),
    )

    try:
        revise_run = await reviser_agent.run(
            f"Original Request:\n{input_text}\n\n"
            f"Initial Draft:\n{initial_draft}\n\n"
            f"Self-Critique Flaws:\n{flaws_md}\n\n"
            f"Improvement Plan:\n{critique.improvement_plan}\n\n"
            "Produce the final, verified response:"
        )
        final_output = str(revise_run.output)
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Pass 3: Reviser",
            content=f"Revision failed: {str(e)}",
            status="failed",
        ).to_sse()
        return

    yield AgentEvent(
        step="completed",
        node="Verified Output (Revised)",
        content=final_output,
        data={"revised": True, "final_output": final_output},
        status="completed",
    ).to_sse()
