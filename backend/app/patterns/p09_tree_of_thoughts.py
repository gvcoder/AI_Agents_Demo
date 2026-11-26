"""
Pattern 09: Tree of Thoughts (ToT) — Algorithmic Beam / BFS Search
Flow: Root -> Branch (N thoughts) -> Score -> Prune (Top-K Beam) -> Expand -> Best Path -> out
Framework: Native Python Asyncio + Unified LLM Factory
"""

import asyncio
import json
from dataclasses import dataclass, field
from typing import Any, AsyncGenerator, Dict, List, Optional
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from backend.app.core.events import AgentEvent
from backend.app.core.llm_factory import extract_text, get_chat_model


# -------------------------------------------------------------------------
# Structured Schemas for Branching & Scoring
# -------------------------------------------------------------------------
class CandidateBranches(BaseModel):
    thoughts: List[str] = Field(
        description="Distinct, non-overlapping candidate reasoning steps or strategies.",
        min_length=2,
        max_length=4,
    )


class ThoughtScore(BaseModel):
    score: float = Field(description="Heuristic promise score from 1.0 to 10.0.", ge=1.0, le=10.0)
    rationale: str = Field(description="Concise 1-sentence justification for the score.")


@dataclass
class ThoughtNode:
    node_id: str
    depth: int
    thought: str
    path: List[str] = field(default_factory=list)
    score: float = 0.0
    rationale: str = ""


# -------------------------------------------------------------------------
# Helper Coroutines
# -------------------------------------------------------------------------
async def _generate_branches(
    llm,
    input_text: str,
    parent_path: List[str],
    num_branches: int,
) -> List[str]:
    path_ctx = (
        "\n".join(f"Step {i + 1}: {t}" for i, t in enumerate(parent_path))
        if parent_path
        else "None (Root)"
    )
    prompt = [
        SystemMessage(
            content=(
                f"You are a Tree-of-Thoughts Reasoner. Generate exactly {num_branches} genuinely "
                "distinct, concrete next reasoning steps or strategic approaches for the problem. "
                "Each thought should explore a different angle or hypothesis."
            )
        ),
        HumanMessage(
            content=(
                f"Problem:\n{input_text}\n\n"
                f"Current Reasoning Path:\n{path_ctx}\n\n"
                f"Propose {num_branches} distinct next thoughts:"
            )
        ),
    ]

    try:
        structured = llm.with_structured_output(CandidateBranches)
        res = await structured.ainvoke(prompt)
        return res.thoughts[:num_branches]
    except Exception:
        fallback_prompt = [
            SystemMessage(
                content=(
                    f"Generate {num_branches} distinct candidate next thoughts. "
                    'Respond ONLY with valid JSON: {"thoughts": ["...", "..."]}'
                )
            ),
            prompt[1],
        ]
        raw = extract_text((await llm.ainvoke(fallback_prompt)).content).strip()
        if "```json" in raw:
            raw = raw.split("```json")[1].split("```")[0].strip()
        elif "```" in raw:
            raw = raw.split("```")[1].split("```")[0].strip()
        parsed = CandidateBranches.model_validate(json.loads(raw))
        return parsed.thoughts[:num_branches]


async def _score_node(llm, input_text: str, node: ThoughtNode) -> ThoughtNode:
    path_str = "\n".join(f"Step {i + 1}: {t}" for i, t in enumerate(node.path))
    prompt = [
        SystemMessage(
            content=(
                "You are a strict Tree-of-Thoughts State Evaluator. Rate how promising this "
                "reasoning path is for solving the problem completely, accurately, and efficiently "
                "on a scale from 1.0 to 10.0."
            )
        ),
        HumanMessage(
            content=(
                f"Problem:\n{input_text}\n\n"
                f"Candidate Path ({node.node_id}):\n{path_str}"
            )
        ),
    ]

    try:
        structured = llm.with_structured_output(ThoughtScore)
        res = await structured.ainvoke(prompt)
        node.score = round(float(res.score), 2)
        node.rationale = res.rationale
    except Exception:
        node.score = 5.0
        node.rationale = "Fallback heuristic score."
    return node


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_tree_of_thoughts(
    input_text: str,
    target_format: str = "Executive Brief",
    branching_factor: int = 3,
    max_depth: int = 2,
    beam_width: int = 2,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.5,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 09 (Tree of Thoughts) using BFS / Beam Search:
    1. Branches into `branching_factor` candidate thoughts at each depth.
    2. Scores all candidate paths in parallel.
    3. Prunes low-scoring branches, keeping top `beam_width` nodes.
    4. Selects the ★ Best Path and synthesizes the final solution.
    """
    yield AgentEvent(
        step="start",
        node="ToT Search Config",
        content=(
            f"Starting **Tree of Thoughts (Beam/BFS Search)** — "
            f"Branching: `{branching_factor}`, Depth: `{max_depth}`, Beam Width: `{beam_width}`."
        ),
        data={
            "branching_factor": branching_factor,
            "max_depth": max_depth,
            "beam_width": beam_width,
        },
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)

    frontier: List[ThoughtNode] = [
        ThoughtNode(node_id="Root", depth=0, thought="Root", path=[])
    ]

    try:
        for depth in range(1, max_depth + 1):
            yield AgentEvent(
                step="thought",
                node=f"Depth {depth} — Branching",
                content=f"Expanding {len(frontier)} frontier node(s) into `{branching_factor}` candidate branches each...",
            ).to_sse()

            # Expand all frontier nodes in parallel
            branch_lists = await asyncio.gather(
                *[
                    _generate_branches(llm, input_text, parent.path, branching_factor)
                    for parent in frontier
                ]
            )

            candidates: List[ThoughtNode] = []
            for p_idx, (parent, thoughts) in enumerate(zip(frontier, branch_lists), start=1):
                for b_idx, thought in enumerate(thoughts, start=1):
                    nid = f"D{depth}-B{p_idx}.{b_idx}"
                    candidates.append(
                        ThoughtNode(
                            node_id=nid,
                            depth=depth,
                            thought=thought,
                            path=parent.path + [thought],
                        )
                    )

            # Score all candidates in parallel
            scored_nodes = await asyncio.gather(
                *[_score_node(llm, input_text, node) for node in candidates]
            )
            scored_nodes.sort(key=lambda n: n.score, reverse=True)

            kept = scored_nodes[:beam_width]
            pruned = scored_nodes[beam_width:]

            kept_md = "\n".join(
                f"- ✅ **`{n.node_id}` (Score {n.score}/10):** {n.thought} — _{n.rationale}_"
                for n in kept
            )
            pruned_md = "\n".join(
                f"- ❌ **`{n.node_id}` (Score {n.score}/10 — Pruned):** {n.thought}"
                for n in pruned
            ) or "- None"

            yield AgentEvent(
                step="step_complete",
                node=f"Depth {depth} — Score & Prune",
                content=f"**Surviving Beam (Top {len(kept)}):**\n{kept_md}\n\n**Pruned Branches:**\n{pruned_md}",
                data={
                    "depth": depth,
                    "kept": [{"id": n.node_id, "score": n.score} for n in kept],
                    "pruned": [{"id": n.node_id, "score": n.score} for n in pruned],
                },
            ).to_sse()

            frontier = kept

        best_node = frontier[0]
        best_path_md = "\n".join(
            f"{i + 1}. {step}" for i, step in enumerate(best_node.path)
        )

        yield AgentEvent(
            step="thought",
            node="★ Best Path Selected",
            content=(
                f"Winning path **`{best_node.node_id}`** (Score `{best_node.score}/10`):\n\n"
                f"{best_path_md}\n\nSynthesizing final solution in **{target_format}** format..."
            ),
            data={"best_node_id": best_node.node_id, "score": best_node.score},
        ).to_sse()

        synth_messages = [
            SystemMessage(
                content=(
                    f"You are an Expert Problem Solver. Using the winning Tree-of-Thoughts reasoning path, "
                    f"deliver a complete, crystal-clear final solution in **{target_format}** format."
                )
            ),
            HumanMessage(
                content=(
                    f"Problem:\n{input_text}\n\n"
                    f"Winning Reasoning Path ({best_node.node_id}, Score {best_node.score}/10):\n"
                    f"{best_path_md}"
                )
            ),
        ]
        final_res = await llm.ainvoke(synth_messages)
        final_output = extract_text(final_res.content)

        yield AgentEvent(
            step="completed",
            node="Output (Optimal Path)",
            content=final_output,
            data={
                "best_node_id": best_node.node_id,
                "score": best_node.score,
                "final_output": final_output,
            },
            status="completed",
        ).to_sse()

    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Tree of Thoughts Search",
            content=f"Search failed: {str(e)}",
            status="failed",
        ).to_sse()
