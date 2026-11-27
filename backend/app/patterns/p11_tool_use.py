"""
Pattern 11: Tool Use (Type-Safe Structured Function Calling)
Flow: LLM -> Structured Tool Request (JSON) -> Tool Runner -> Result -> LLM -> out
Framework: Pydantic AI
"""

import json
from typing import Any, AsyncGenerator, Dict, Literal, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent
from pydantic_ai.messages import ToolCallPart, ToolReturnPart

from backend.app.core.events import AgentEvent
from backend.app.patterns.p02_routing import get_pydantic_ai_model


# -------------------------------------------------------------------------
# Deterministic Domain Data & Type-Safe Tools
# -------------------------------------------------------------------------
_CLOUD_SPEND_DB: Dict[str, Dict[str, Any]] = {
    "compute": {"monthly_usd": 14200.0, "budget_usd": 15000.0, "unit": "vCPU-hours", "usage": 185000},
    "database": {"monthly_usd": 6850.0, "budget_usd": 6000.0, "unit": "IOPS-GB", "usage": 42000},
    "storage": {"monthly_usd": 2150.0, "budget_usd": 3000.0, "unit": "TB-months", "usage": 94},
    "ai_inference": {"monthly_usd": 9400.0, "budget_usd": 8000.0, "unit": "1M tokens", "usage": 3120},
}

_FX_TO_USD: Dict[str, float] = {
    "USD": 1.0,
    "EUR": 1.08,
    "GBP": 1.27,
    "INR": 0.012,
}


class CloudSpendArgs(BaseModel):
    service: Literal["compute", "database", "storage", "ai_inference"] = Field(
        description="Cloud service category to inspect."
    )
    month: str = Field(description="Billing month label, e.g. '2026-11'.")


def _build_tool_agent(model_spec: str) -> Agent:
    agent = Agent(
        model=model_spec,
        system_prompt=(
            "You are a FinOps Cloud Cost Analyst. Always use the provided tools to fetch "
            "live spend data, convert currencies, and compute annual run-rate forecasts. "
            "Never guess numbers — rely strictly on tool outputs."
        ),
    )

    @agent.tool_plain
    def get_cloud_spend(
        service: Literal["compute", "database", "storage", "ai_inference"],
        month: str = "2026-11",
    ) -> Dict[str, Any]:
        """Fetch monthly cloud spend, budget cap, and utilization for a given service."""
        record = _CLOUD_SPEND_DB[service]
        variance = round(record["monthly_usd"] - record["budget_usd"], 2)
        return {
            "service": service,
            "month": month,
            "monthly_usd": record["monthly_usd"],
            "budget_usd": record["budget_usd"],
            "over_budget": variance > 0,
            "variance_usd": variance,
            "usage": f"{record['usage']} {record['unit']}",
        }

    @agent.tool_plain
    def convert_currency(
        amount: float,
        from_currency: Literal["USD", "EUR", "GBP", "INR"],
        to_currency: Literal["USD", "EUR", "GBP", "INR"],
    ) -> Dict[str, Any]:
        """Convert a monetary amount between USD, EUR, GBP, and INR."""
        usd_value = amount * _FX_TO_USD[from_currency]
        converted = round(usd_value / _FX_TO_USD[to_currency], 2)
        return {
            "original": f"{amount:.2f} {from_currency}",
            "converted": f"{converted:.2f} {to_currency}",
            "value": converted,
            "currency": to_currency,
        }

    @agent.tool_plain
    def forecast_annual_run_rate(
        monthly_spend_usd: float,
        monthly_growth_pct: float = 0.0,
    ) -> Dict[str, Any]:
        """Project 12-month cumulative cloud spend in USD given a monthly growth percentage."""
        total = 0.0
        current = monthly_spend_usd
        rate = 1.0 + (monthly_growth_pct / 100.0)
        for _ in range(12):
            total += current
            current *= rate
        return {
            "starting_monthly_usd": round(monthly_spend_usd, 2),
            "monthly_growth_pct": monthly_growth_pct,
            "projected_12m_total_usd": round(total, 2),
            "month_12_run_rate_usd": round(current / rate, 2),
        }

    return agent


# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_tool_use(
    input_text: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.1,
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 11 (Tool Use) using Pydantic AI's type-safe tool schemas
    and streams structured tool calls and tool return payloads via SSE.
    """
    yield AgentEvent(
        step="start",
        node="Tool Use Agent",
        content=(
            "Initialized Pydantic AI Agent with 3 schema-validated tools: "
            "`get_cloud_spend`, `convert_currency`, `forecast_annual_run_rate`."
        ),
    ).to_sse()

    model_spec = get_pydantic_ai_model(provider)
    if model_name and ":" in model_name:
        model_spec = model_name

    agent = _build_tool_agent(model_spec)

    try:
        seen_calls = set()
        seen_returns = set()

        async with agent.iter(input_text) as agent_run:
            async for node in agent_run:
                # Inspect newly generated messages on each graph node
                for msg in agent_run.all_messages():
                    for part in getattr(msg, "parts", []):
                        if isinstance(part, ToolCallPart):
                            call_key = part.tool_call_id or f"{part.tool_name}:{part.args}"
                            if call_key not in seen_calls:
                                seen_calls.add(call_key)
                                yield AgentEvent(
                                    step="tool_call",
                                    node=f"Tool Call ➔ {part.tool_name}",
                                    content=f"```json\n{part.args_as_json_str()}\n```",
                                    data={"tool_name": part.tool_name, "args": part.args_as_dict()},
                                ).to_sse()

                        elif isinstance(part, ToolReturnPart):
                            ret_key = part.tool_call_id or f"{part.tool_name}:{part.content}"
                            if ret_key not in seen_returns:
                                seen_returns.add(ret_key)
                                content_str = (
                                    json.dumps(part.content, indent=2)
                                    if isinstance(part.content, (dict, list))
                                    else str(part.content)
                                )
                                yield AgentEvent(
                                    step="observation",
                                    node=f"Tool Result ⬅ {part.tool_name}",
                                    content=f"```json\n{content_str}\n```",
                                    data={"tool_name": part.tool_name, "result": part.content},
                                ).to_sse()

            final_output = str(agent_run.result.output) if agent_run.result else ""

        yield AgentEvent(
            step="completed",
            node="Final Answer",
            content=final_output,
            data={"final_output": final_output},
            status="completed",
        ).to_sse()

    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Tool Use Agent",
            content=f"Tool execution failed: {str(e)}",
            status="failed",
        ).to_sse()
