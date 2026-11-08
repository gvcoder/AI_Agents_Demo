"""
Pattern 01: Prompt Chaining with intermediate validation gate.
Flow: in -> LLM 1 (Fact Extraction) -> Gate (Verification Check) -> LLM 2 (Synthesis) -> out
Framework: LangGraph
"""

import json
from typing import AsyncGenerator, TypedDict, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from backend.app.core.llm_factory import get_chat_model
from backend.app.core.events import AgentEvent

# -------------------------------------------------------------------------
# State Definition
# -------------------------------------------------------------------------
class ChainState(TypedDict):
    input_text: str
    target_format: str
    provider: Optional[str]
    model_name: Optional[str]
    temperature: float
    # Intermediate outputs
    extracted_facts: Optional[str]
    gate_passed: bool
    gate_reason: Optional[str]
    final_output: Optional[str]
    error: Optional[str]

# -------------------------------------------------------------------------
# Gate Validation Schema
# -------------------------------------------------------------------------
class GateDecision(BaseModel):
    is_valid: bool = Field(description="True if extracted information contains meaningful facts and is not empty or hallucinated.")
    reason: str = Field(description="Explanation of why it passed or failed.")
    confidence_score: float = Field(description="Score between 0.0 and 1.0 indicating confidence.")

# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_prompt_chaining(
    input_text: str,
    target_format: str = "Executive Brief",
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 01 step by step, yielding real-time AgentEvents as SSE.
    """
    yield AgentEvent(
        step="start",
        node="Chain Input",
        content=f"Received input text ({len(input_text)} chars). Target format: **{target_format}**",
        data={"target_format": target_format}
    ).to_sse()

    llm = get_chat_model(provider=provider, model_name=model_name, temperature=temperature)

    # 1. Step 1: Fact Extraction (LLM 1)
    yield AgentEvent(
        step="thought",
        node="Step 1: Fact Extractor",
        content="Extracting structured facts, entities, and data points from the raw input..."
    ).to_sse()

    extract_prompt = [
        SystemMessage(content=(
            "You are an expert information extractor. Extract all key facts, numerical figures, "
            "dates, entities, and actionable points as clean bullet points. "
            "Do not embellish or add unsolicited commentary."
        )),
        HumanMessage(content=input_text)
    ]
    
    try:
        extract_res = await llm.ainvoke(extract_prompt)
        extracted_facts = extract_res.content
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Step 1: Fact Extractor",
            content=f"LLM extraction failed: {str(e)}",
            status="failed"
        ).to_sse()
        return

    yield AgentEvent(
        step="step_complete",
        node="Step 1: Fact Extractor",
        content=extracted_facts,
        data={"extracted_facts": extracted_facts}
    ).to_sse()

    # 2. Gate: Quality & Truthfulness Check
    yield AgentEvent(
        step="gate_check",
        node="Gate: Fact Verifier",
        content="Verifying quality, factual density, and consistency of extracted points..."
    ).to_sse()

    gate_prompt = [
        SystemMessage(content=(
            "You are a strict quality gate in an automated pipeline. "
            "Evaluate whether the extracted facts are coherent, factually grounded in the source, "
            "and meet the minimum threshold of information. "
            "Respond ONLY with a JSON object in this format:\n"
            '{"is_valid": true|false, "reason": "...", "confidence_score": 0.0 to 1.0}'
        )),
        HumanMessage(content=f"Original Text:\n{input_text}\n\nExtracted Facts:\n{extracted_facts}")
    ]

    try:
        gate_res = await llm.ainvoke(gate_prompt)
        clean_text = gate_res.content.strip()
        if "```json" in clean_text:
            clean_text = clean_text.split("```json")[1].split("```")[0].strip()
        elif "```" in clean_text:
            clean_text = clean_text.split("```")[1].split("```")[0].strip()
            
        gate_data = json.loads(clean_text)
        is_valid = gate_data.get("is_valid", False)
        reason = gate_data.get("reason", "No reason provided")
        confidence = gate_data.get("confidence_score", 0.0)
    except Exception as e:
        # Fallback if json parsing fails: simple heuristic check
        is_valid = len(extracted_facts.strip()) > 20
        reason = f"Automated fallback check (parse error: {str(e)})"
        confidence = 0.5

    if not is_valid:
        yield AgentEvent(
            step="gate_failed",
            node="Gate: Fact Verifier",
            content=f"⛔ **Gate Check Failed!**\nReason: {reason} (Confidence: {confidence:.2f})\nHalting pipeline to prevent error propagation.",
            data={"gate_passed": False, "reason": reason, "confidence": confidence},
            status="gated"
        ).to_sse()
        return

    yield AgentEvent(
        step="gate_passed",
        node="Gate: Fact Verifier",
        content=f"✅ **Gate Passed!**\nReason: {reason} (Confidence: {confidence:.2f})\nProceeding to Step 2 synthesis.",
        data={"gate_passed": True, "reason": reason, "confidence": confidence}
    ).to_sse()

    # 3. Step 2: Synthesis & Polishing (LLM 2)
    yield AgentEvent(
        step="thought",
        node="Step 2: Synthesizer",
        content=f"Synthesizing verified facts into **{target_format}** format..."
    ).to_sse()

    synth_prompt = [
        SystemMessage(content=(
            f"You are a professional communications specialist. Transform the verified bullet points "
            f"into a polished, structured **{target_format}**. Use markdown headings and crisp prose."
        )),
        HumanMessage(content=f"Verified Facts:\n{extracted_facts}")
    ]

    try:
        synth_res = await llm.ainvoke(synth_prompt)
        final_output = synth_res.content
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Step 2: Synthesizer",
            content=f"Synthesis failed: {str(e)}",
            status="failed"
        ).to_sse()
        return

    yield AgentEvent(
        step="completed",
        node="Output",
        content=final_output,
        data={"final_output": final_output},
        status="completed"
    ).to_sse()

