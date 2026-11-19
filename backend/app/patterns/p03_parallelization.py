"""
Pattern 03: Parallelization (Fan-Out / Fan-In Concurrency)
Flow: in -> [LLM 1 || LLM 2 || LLM 3] (asyncio) -> Merge / Synthesizer -> out
Framework: Native Python Asyncio + Unified LLM Factory
"""

import asyncio
import time
from typing import AsyncGenerator, Dict, List, Optional, Tuple
from langchain_core.messages import SystemMessage, HumanMessage

from backend.app.core.llm_factory import extract_text, get_chat_model
from backend.app.core.events import AgentEvent

PARALLEL_WORKERS: List[Tuple[str, str]] = [
    (
        "Worker 1: Product & Market Analyst",
        "You are a sharp Product & Market Strategist. Evaluate the proposal strictly from a "
        "customer value, market differentiation, and adoption perspective. "
        "Provide 3-4 concise bullet points covering strengths and market risks."
    ),
    (
        "Worker 2: Systems & Engineering Architect",
        "You are a Principal Systems Architect. Evaluate the proposal strictly from a "
        "technical feasibility, scalability, latency, and maintainability perspective. "
        "Provide 3-4 concise bullet points covering architecture considerations."
    ),
    (
        "Worker 3: Security & Risk Auditor",
        "You are a Security, Privacy, and FinOps Auditor. Evaluate the proposal strictly for "
        "security vulnerabilities, compliance/PII risks, and cost/operational failure modes. "
        "Provide 3-4 concise bullet points covering mitigations."
    ),
]


async def _run_worker(
    llm,
    worker_name: str,
    system_prompt: str,
    input_text: str,
) -> Dict[str, object]:
    """Run a single parallel analyst branch and measure its elapsed time."""
    t0 = time.perf_counter()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Proposal / Scenario to Analyze:\n{input_text}"),
    ]
    response = await llm.ainvoke(messages)
    elapsed = time.perf_counter() - t0
    return {
        "worker_name": worker_name,
        "content": extract_text(response.content),
        "elapsed_s": round(elapsed, 2),
    }


async def run_parallelization(
    input_text: str,
    target_format: str = "Executive Brief",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.3,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 03 (Parallelization) step by step:
    1. Fans out the input concurrently to 3 independent specialist LLM calls via asyncio.
    2. Streams each worker's result as soon as it completes (showing wall-clock savings).
    3. Merges all parallel outputs into a unified synthesis using a final LLM call.
    """
    yield AgentEvent(
        step="start",
        node="Parallel Dispatcher",
        content=(
            f"Dispatching input ({len(input_text)} chars) to **{len(PARALLEL_WORKERS)} parallel LLM workers** "
            f"simultaneously via `asyncio`..."
        ),
        data={"worker_count": len(PARALLEL_WORKERS), "target_format": target_format},
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)

    # 1. Fan-Out: Launch all 3 workers concurrently
    batch_start = time.perf_counter()
    tasks = [
        asyncio.create_task(_run_worker(llm, name, prompt, input_text))
        for name, prompt in PARALLEL_WORKERS
    ]

    yield AgentEvent(
        step="thought",
        node="Fan-Out Batch",
        content=(
            "Running concurrently:\n"
            + "\n".join(f"- `{name}`" for name, _ in PARALLEL_WORKERS)
        ),
    ).to_sse()

    worker_results: List[Dict[str, object]] = []

    for completed_task in asyncio.as_completed(tasks):
        try:
            res = await completed_task
            worker_results.append(res)
            yield AgentEvent(
                step="step_complete",
                node=str(res["worker_name"]),
                content=f"⏱️ *Completed in {res['elapsed_s']}s*\n\n{res['content']}",
                data={"elapsed_s": res["elapsed_s"]},
            ).to_sse()
        except Exception as e:
            # Cancel remaining tasks on failure
            for t in tasks:
                if not t.done():
                    t.cancel()
            yield AgentEvent(
                step="error",
                node="Fan-Out Batch",
                content=f"Parallel worker failed: {str(e)}",
                status="failed",
            ).to_sse()
            return

    total_wall_s = round(time.perf_counter() - batch_start, 2)
    sum_sequential_s = round(sum(float(r["elapsed_s"]) for r in worker_results), 2)

    yield AgentEvent(
        step="thought",
        node="Merge / Synthesizer",
        content=(
            f"All {len(worker_results)} branches finished! "
            f"Wall-clock time: **{total_wall_s}s** (vs. ~**{sum_sequential_s}s** if run sequentially).\n"
            f"Merging perspectives into **{target_format}**..."
        ),
        data={
            "wall_clock_s": total_wall_s,
            "sequential_estimate_s": sum_sequential_s,
        },
    ).to_sse()

    # 2. Fan-In: Merge all parallel outputs
    combined_analyses = "\n\n".join(
        f"### {r['worker_name']}\n{r['content']}" for r in worker_results
    )

    merge_messages = [
        SystemMessage(
            content=(
                f"You are an Executive Synthesizer. Combine the independent parallel specialist analyses "
                f"below into a cohesive, conflict-resolved **{target_format}**. "
                f"Highlight consensus points, key trade-offs, and a clear final recommendation."
            )
        ),
        HumanMessage(
            content=f"Original Proposal:\n{input_text}\n\nParallel Specialist Analyses:\n{combined_analyses}"
        ),
    ]

    try:
        merged = await llm.ainvoke(merge_messages)
        final_output = extract_text(merged.content)
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Merge / Synthesizer",
            content=f"Merge step failed: {str(e)}",
            status="failed",
        ).to_sse()
        return

    yield AgentEvent(
        step="completed",
        node="Output (Merged)",
        content=final_output,
        data={
            "wall_clock_s": total_wall_s,
            "sequential_estimate_s": sum_sequential_s,
            "final_output": final_output,
        },
        status="completed",
    ).to_sse()
