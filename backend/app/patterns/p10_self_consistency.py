"""
Pattern 10: Self-Consistency (Parallel Sampling + Majority Vote)
Flow: in -> [Sample 1 || Sample 2 || ... || Sample N] (temp > 0) -> Majority Vote -> Consensus
Framework: Native Python Asyncio + Unified LLM Factory
"""

import asyncio
import json
import re
import time
from collections import Counter
from typing import Any, AsyncGenerator, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.app.core.events import AgentEvent
from backend.app.core.llm_factory import extract_text, get_chat_model


# -------------------------------------------------------------------------
# Structured Sample Schema
# -------------------------------------------------------------------------
class ReasoningSample(BaseModel):
    reasoning: str = Field(description="Step-by-step chain-of-thought reasoning for this sample.")
    final_answer: str = Field(
        description="Concise canonical final answer (e.g., a number, short phrase, or option label) for voting."
    )


def _normalize_answer(ans: str) -> str:
    """Normalize an answer string for robust majority voting."""
    cleaned = ans.strip().lower()
    cleaned = re.sub(r"[\s]+", " ", cleaned)
    cleaned = cleaned.strip(".,!?;:\"'`")
    return cleaned


async def _run_sample(
    llm,
    sample_idx: int,
    input_text: str,
) -> Dict[str, Any]:
    t0 = time.perf_counter()
    prompt = [
        SystemMessage(
            content=(
                "You are an analytical problem solver. Think step by step carefully, "
                "show your reasoning, and then provide a concise canonical `final_answer` "
                "(e.g., just the number with unit or short definitive value)."
            )
        ),
        HumanMessage(content=input_text),
    ]

    sample: Optional[ReasoningSample] = None
    try:
        structured = llm.with_structured_output(ReasoningSample)
        sample = await structured.ainvoke(prompt)
    except Exception:
        fallback_prompt = [
            SystemMessage(
                content=(
                    "Think step by step and respond ONLY with valid JSON matching:\n"
                    '{"reasoning": "...", "final_answer": "..."}'
                )
            ),
            prompt[1],
        ]
        raw = extract_text((await llm.ainvoke(fallback_prompt)).content).strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        try:
            sample = ReasoningSample.model_validate(json.loads(raw))
        except Exception:
            sample = ReasoningSample(
                reasoning=raw,
                final_answer=raw.splitlines()[-1].strip() if raw else "unknown",
            )

    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "sample_idx": sample_idx,
        "reasoning": sample.reasoning,
        "final_answer": sample.final_answer,
        "normalized": _normalize_answer(sample.final_answer),
        "elapsed_s": elapsed,
    }


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_self_consistency(
    input_text: str,
    num_samples: int = 5,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.7,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 10 (Self-Consistency):
    1. Samples `num_samples` independent reasoning trajectories concurrently (temp > 0).
    2. Streams each sample's reasoning and candidate answer as it completes.
    3. Tallies votes across all samples and selects the majority consensus answer.
    """
    effective_temp = temperature if temperature > 0.0 else 0.7
    yield AgentEvent(
        step="start",
        node="Self-Consistency Sampler",
        content=(
            f"Launching **{num_samples} independent reasoning samples** in parallel "
            f"(temperature: `{effective_temp}`) for majority voting..."
        ),
        data={"num_samples": num_samples, "temperature": effective_temp},
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=effective_temp)

    tasks = [
        asyncio.create_task(_run_sample(llm, idx, input_text))
        for idx in range(1, num_samples + 1)
    ]

    samples: List[Dict[str, Any]] = []
    for completed_task in asyncio.as_completed(tasks):
        try:
            res = await completed_task
            samples.append(res)
            yield AgentEvent(
                step="step_complete",
                node=f"Sample #{res['sample_idx']}",
                content=(
                    f"⏱️ *{res['elapsed_s']}s* | **Candidate Answer:** `{res['final_answer']}`\n\n"
                    f"{res['reasoning']}"
                ),
                data=res,
            ).to_sse()
        except Exception as e:
            for t in tasks:
                if not t.done():
                    t.cancel()
            yield AgentEvent(
                step="error",
                node="Self-Consistency Sampler",
                content=f"Sampling failed: {str(e)}",
                status="failed",
            ).to_sse()
            return

    # Tally Majority Vote
    counts = Counter(s["normalized"] for s in samples)
    winning_norm, winning_votes = counts.most_common(1)[0]

    # Map normalized key back to the cleanest display string
    display_map: Dict[str, str] = {}
    winning_reasoning = ""
    for s in sorted(samples, key=lambda x: x["sample_idx"]):
        display_map.setdefault(s["normalized"], s["final_answer"])
        if s["normalized"] == winning_norm and not winning_reasoning:
            winning_reasoning = s["reasoning"]

    winning_display = display_map[winning_norm]
    confidence_pct = round((winning_votes / len(samples)) * 100, 1)

    tally_lines = "\n".join(
        f"- **`{display_map[norm]}`**: {cnt}/{len(samples)} votes"
        + (" ✅ **(Consensus)**" if norm == winning_norm else "")
        for norm, cnt in counts.most_common()
    )

    yield AgentEvent(
        step="vote_tally",
        node="Majority Vote Aggregator",
        content=(
            f"🗳️ **Vote Breakdown ({winning_votes}/{len(samples)} = {confidence_pct}% agreement):**\n\n"
            f"{tally_lines}"
        ),
        data={
            "winner": winning_display,
            "votes": winning_votes,
            "total": len(samples),
            "confidence_pct": confidence_pct,
        },
    ).to_sse()

    yield AgentEvent(
        step="completed",
        node="Consensus Answer",
        content=(
            f"### Consensus Answer: `{winning_display}` ({winning_votes}/{len(samples)} votes)\n\n"
            f"**Representative Reasoning:**\n{winning_reasoning}"
        ),
        data={
            "consensus": winning_display,
            "votes": winning_votes,
            "total": len(samples),
        },
        status="completed",
    ).to_sse()
