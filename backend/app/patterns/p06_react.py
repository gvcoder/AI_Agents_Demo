"""
Pattern 06: ReAct (Reason + Act + Observe Loop)
Flow: Thought -> Action (Tool Call) -> Observation -> ... -> Final Answer
Framework: Smolagents (ToolCallingAgent + LiteLLMModel)
"""

import ast
import operator
import os
import queue
import threading
from typing import Any, AsyncGenerator, Dict, Optional
import litellm
from smolagents import LiteLLMModel, ToolCallingAgent, tool
from smolagents.memory import ActionStep, FinalAnswerStep

litellm.drop_params = True

from backend.app.core.config import settings
from backend.app.core.events import AgentEvent


# -------------------------------------------------------------------------
# Safe Arithmetic Evaluator (No eval())
# -------------------------------------------------------------------------
_SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
}


def _eval_ast(node: ast.AST) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.left), _eval_ast(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _SAFE_OPS:
        return _SAFE_OPS[type(node.op)](_eval_ast(node.operand))
    raise ValueError(f"Unsupported expression node: {type(node).__name__}")


# -------------------------------------------------------------------------
# Deterministic Domain Tools for ReAct
# -------------------------------------------------------------------------
_PRODUCT_CATALOG: Dict[str, Dict[str, Any]] = {
    "edgegateway x1": {"sku": "HW-EG-X1", "unit_price_usd": 420.0, "stock": 42, "category": "Hardware"},
    "cloudsync pro": {"sku": "SW-CS-PRO", "unit_price_usd": 180.0, "stock": 999, "category": "Annual License"},
    "ai shield enterprise": {"sku": "SW-AIS-ENT", "unit_price_usd": 650.0, "stock": 250, "category": "Annual License"},
}

_SHIPPING_RATES: Dict[str, Dict[str, Any]] = {
    "US": {"lead_time_days": 3, "flat_freight_usd": 45.0, "carrier": "FedEx Priority"},
    "EU": {"lead_time_days": 5, "flat_freight_usd": 120.0, "carrier": "DHL Express"},
    "APAC": {"lead_time_days": 6, "flat_freight_usd": 150.0, "carrier": "DHL Express"},
}


@tool
def lookup_product_catalog(product_name: str) -> str:
    """
    Look up SKU, unit price in USD, and available stock for a product.

    Args:
        product_name: Name of the product to look up (e.g., 'EdgeGateway X1', 'CloudSync Pro').
    """
    key = product_name.strip().lower()
    for catalog_key, info in _PRODUCT_CATALOG.items():
        if key in catalog_key or catalog_key in key:
            return (
                f"Product: {catalog_key.title()} | SKU: {info['sku']} | "
                f"Unit Price: ${info['unit_price_usd']:.2f} | Stock: {info['stock']} | "
                f"Category: {info['category']}"
            )
    return f"Product '{product_name}' not found. Available products: {', '.join(k.title() for k in _PRODUCT_CATALOG)}."


@tool
def get_discount_tier(order_subtotal_usd: float) -> str:
    """
    Determine the volume discount percentage and SLA tier for an order subtotal in USD.

    Args:
        order_subtotal_usd: Pre-discount order subtotal in USD.
    """
    if order_subtotal_usd >= 10000:
        return "Tier: Platinum | Discount: 15% | SLA: 24/7 Dedicated"
    if order_subtotal_usd >= 5000:
        return "Tier: Gold | Discount: 10% | SLA: 4-hour Response"
    if order_subtotal_usd >= 2000:
        return "Tier: Silver | Discount: 5% | SLA: Business Hours"
    return "Tier: Standard | Discount: 0% | SLA: Next Business Day"


@tool
def check_shipping_eta(region: str) -> str:
    """
    Check shipping cost in USD and estimated delivery lead time for a region.

    Args:
        region: Target shipping region code ('US', 'EU', or 'APAC').
    """
    code = region.strip().upper()
    if code in _SHIPPING_RATES:
        info = _SHIPPING_RATES[code]
        return (
            f"Region: {code} | Freight Cost: ${info['flat_freight_usd']:.2f} | "
            f"Lead Time: {info['lead_time_days']} business days | Carrier: {info['carrier']}"
        )
    return f"Unsupported region '{region}'. Supported regions: US, EU, APAC."


@tool
def calculate_expression(expression: str) -> str:
    """
    Safely evaluate an arithmetic expression (supports +, -, *, /, **, %, parentheses).

    Args:
        expression: Arithmetic expression string, e.g. '(15 * 420 + 8 * 180) * 0.90 + 120'.
    """
    try:
        tree = ast.parse(expression.strip(), mode="eval")
        result = _eval_ast(tree.body)
        return f"{result:.2f}"
    except Exception as exc:
        return f"Calculation error: {exc}"


# -------------------------------------------------------------------------
# LiteLLM Model Resolver for Smolagents
# -------------------------------------------------------------------------
def _get_smolagents_model(
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> LiteLLMModel:
    prov = (provider or settings.DEFAULT_PROVIDER).lower()

    if prov == "gemini":
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        target = model_name or "gemini/gemini-3.8-flash"
        return LiteLLMModel(model_id=target, api_key=api_key)

    if prov == "openai":
        api_key = settings.OPENAI_API_KEY or os.getenv("OPENAI_API_KEY")
        target = model_name or "openai/gpt-4o-mini"
        return LiteLLMModel(model_id=target, api_key=api_key, temperature=temperature)

    if prov == "anthropic":
        api_key = settings.ANTHROPIC_API_KEY or os.getenv("ANTHROPIC_API_KEY")
        target = model_name or "anthropic/claude-3-5-sonnet-latest"
        return LiteLLMModel(model_id=target, api_key=api_key, temperature=temperature)

    if prov == "ollama":
        target = model_name or f"ollama_chat/{settings.OLLAMA_DEFAULT_MODEL}"
        return LiteLLMModel(
            model_id=target,
            api_base=settings.OLLAMA_BASE_URL,
            temperature=temperature,
        )

    raise ValueError(f"Unsupported model provider: '{prov}'")


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_react(
    input_text: str,
    max_steps: int = 8,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 06 (ReAct) with Smolagents ToolCallingAgent(stream=True)
    and streams Thought -> Action -> Observation -> Final Answer as SSE.
    """
    yield AgentEvent(
        step="start",
        node="ReAct Agent Input",
        content=(
            f"Starting Smolagents `ToolCallingAgent` (max **{max_steps}** steps).\n"
            f"Available tools: `lookup_product_catalog`, `get_discount_tier`, "
            f"`check_shipping_eta`, `calculate_expression`."
        ),
        data={"max_steps": max_steps},
    ).to_sse()

    try:
        model = _get_smolagents_model(
            provider=provider,
            model_name=model_name,
            temperature=temperature,
        )
        agent = ToolCallingAgent(
            tools=[
                lookup_product_catalog,
                get_discount_tier,
                check_shipping_eta,
                calculate_expression,
            ],
            model=model,
            max_steps=max_steps,
            verbosity_level=0,
        )
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="ReAct Initialization",
            content=f"Failed to initialize Smolagents ReAct agent: {str(e)}",
            status="failed",
        ).to_sse()
        return

    event_queue: queue.Queue = queue.Queue()
    _DONE = object()

    def _worker():
        try:
            for step_obj in agent.run(input_text, stream=True):
                event_queue.put(("step", step_obj))
        except Exception as exc:
            event_queue.put(("error", exc))
        finally:
            event_queue.put(("done", _DONE))

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()

    import asyncio

    final_answer = ""
    while True:
        try:
            kind, payload = await asyncio.to_thread(event_queue.get, True, 0.25)
        except queue.Empty:
            continue

        if kind == "done":
            break
        if kind == "error":
            yield AgentEvent(
                step="error",
                node="ReAct Loop",
                content=f"ReAct execution error: {str(payload)}",
                status="failed",
            ).to_sse()
            return

        step_obj = payload
        if isinstance(step_obj, ActionStep):
            step_num = step_obj.step_number
            thought_text = ""
            if getattr(step_obj, "model_output", None):
                thought_text = str(step_obj.model_output).strip()
            elif getattr(step_obj, "model_output_message", None) and getattr(
                step_obj.model_output_message, "content", None
            ):
                thought_text = str(step_obj.model_output_message.content).strip()

            if thought_text:
                yield AgentEvent(
                    step="thought",
                    node=f"Step {step_num} — Thought",
                    content=thought_text,
                    data={"step_number": step_num},
                ).to_sse()

            if step_obj.tool_calls:
                calls_desc = "\n".join(
                    f"- `{tc.name}({tc.arguments})`" for tc in step_obj.tool_calls
                )
                yield AgentEvent(
                    step="tool_call",
                    node=f"Step {step_num} — Action (Tool Call)",
                    content=calls_desc,
                    data={
                        "step_number": step_num,
                        "tools": [tc.name for tc in step_obj.tool_calls],
                    },
                ).to_sse()

            if step_obj.observations:
                yield AgentEvent(
                    step="observation",
                    node=f"Step {step_num} — Observation",
                    content=str(step_obj.observations),
                    data={"step_number": step_num},
                ).to_sse()

            if step_obj.error:
                yield AgentEvent(
                    step="error",
                    node=f"Step {step_num} — Step Error",
                    content=str(step_obj.error),
                    status="running",
                ).to_sse()

        elif isinstance(step_obj, FinalAnswerStep):
            final_answer = str(step_obj.output)

    yield AgentEvent(
        step="completed",
        node="Final Answer",
        content=final_answer or "Completed without final answer text.",
        data={"final_output": final_answer},
        status="completed",
    ).to_sse()
