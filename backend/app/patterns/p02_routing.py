"""
Pattern 02: Routing (Classifier -> Specialist Dispatch)
Flow: in -> Router (Classification) -> [Technical Specialist | Billing Specialist | General Specialist] -> out
Framework: Pydantic AI
"""

from enum import Enum
from typing import AsyncGenerator, Optional
from pydantic import BaseModel, Field
from pydantic_ai import Agent

from backend.app.core.config import settings
from backend.app.core.events import AgentEvent

# -------------------------------------------------------------------------
# Routing Categories & Classification Schema
# -------------------------------------------------------------------------
class IntentCategory(str, Enum):
    TECHNICAL_SUPPORT = "technical_support"
    BILLING_INQUIRY = "billing_inquiry"
    FEATURE_REQUEST = "feature_request"
    GENERAL = "general"

class ClassificationResult(BaseModel):
    category: IntentCategory = Field(
        description="The primary classification of the user's message."
    )
    confidence: float = Field(
        description="Confidence score between 0.0 and 1.0.",
        ge=0.0,
        le=1.0
    )
    reasoning: str = Field(
        description="Brief justification for why this category was chosen."
    )
    urgency: str = Field(
        description="Urgency level: low | medium | high | critical",
        default="medium"
    )

# -------------------------------------------------------------------------
# Pydantic AI Model Resolver Helper
# -------------------------------------------------------------------------
def get_pydantic_ai_model(provider: Optional[str] = None):
    prov = (provider or settings.DEFAULT_PROVIDER).lower()
    if prov == "gemini":
        # Pydantic AI uses 'google-gla:' or 'google-vertex:'
        return "google-gla:gemini-2.5-flash"
    elif prov == "openai":
        return "openai:gpt-4o-mini"
    elif prov == "anthropic":
        return "anthropic:claude-3-5-sonnet-latest"
    elif prov == "ollama":
        return f"ollama:{settings.OLLAMA_DEFAULT_MODEL}"
    return "google-gla:gemini-2.5-flash"

# -------------------------------------------------------------------------
# Streamable Pattern Execution Generator
# -------------------------------------------------------------------------
async def run_routing(
    user_query: str,
    provider: Optional[str] = None,
    model_name: Optional[str] = None,
    temperature: float = 0.2
) -> AsyncGenerator[str, None]:
    """
    Executes Pattern 02 (Routing) step by step:
    1. Uses a Pydantic AI agent with structured result_type to classify intent.
    2. Emits classification events and routing telemetry.
    3. Dispatches to the corresponding specialist agent prompt.
    """
    yield AgentEvent(
        step="start",
        node="Incoming Query",
        content=f"Received input query: *\"{user_query}\"*",
        data={"query": user_query}
    ).to_sse()

    model_spec = get_pydantic_ai_model(provider)

    # 1. Classification & Routing Gate
    yield AgentEvent(
        step="thought",
        node="Router (Classifier)",
        content="Analyzing query semantics against intent taxonomy (Technical, Billing, Feature, General)..."
    ).to_sse()

    router_agent = Agent(
        model=model_spec,
        output_type=ClassificationResult,
        system_prompt=(
            "You are an intelligent triage router for an enterprise software platform. "
            "Analyze the incoming user request and classify it accurately into one of the designated categories: "
            "1. technical_support (errors, bugs, downtime, stack traces, SDK/API issues)\n"
            "2. billing_inquiry (invoices, subscriptions, credit cards, payment failures, pricing)\n"
            "3. feature_request (new functionality, enhancements, integrations)\n"
            "4. general (greetings, general company inquiries, ambiguous queries)\n"
            "Assign a confidence score (0.0 to 1.0) and explain your reasoning crisply."
        )
    )

    try:
        classification_run = await router_agent.run(user_query)
        result: ClassificationResult = classification_run.output
    except Exception as e:
        yield AgentEvent(
            step="error",
            node="Router (Classifier)",
            content=f"Classification failed: {str(e)}",
            status="failed"
        ).to_sse()
        return

    yield AgentEvent(
        step="route_decided",
        node="Router (Classifier)",
        content=(
            f"🎯 **Route Selected: `{result.category.value.upper()}`**\n\n"
            f"- **Confidence:** `{result.confidence * 100:.1f}%`\n"
            f"- **Urgency:** `{result.urgency.upper()}`\n"
            f"- **Reason:** {result.reasoning}"
        ),
        data=result.model_dump()
    ).to_sse()

    # 2. Dispatch to Specialist Agent
    specialist_prompts = {
        IntentCategory.TECHNICAL_SUPPORT: (
            "Specialist: Technical Support Engineer",
            "You are a Tier 3 Senior Support Engineer. Analyze the user's issue with a diagnostic mindset. "
            "Provide root-cause hypothesis, exact debugging steps, or code remedies where applicable."
        ),
        IntentCategory.BILLING_INQUIRY: (
            "Specialist: Billing & Accounts Concierge",
            "You are an empathetic Enterprise Billing specialist. Explain pricing policies, provide clear breakdown steps, "
            "and guide the user on invoices, refunds, or payment update procedures clearly and politely."
        ),
        IntentCategory.FEATURE_REQUEST: (
            "Specialist: Product Manager",
            "You are a Product Manager. Acknowledge the user's idea, synthesize its business value, "
            "ask any clarifying questions regarding workflow, and explain how it maps to roadmap priorities."
        ),
        IntentCategory.GENERAL: (
            "Specialist: General Representative",
            "You are a helpful and courteous assistant. Provide clear, concise answers to the user's question."
        ),
    }

    specialist_node, specialist_system_prompt = specialist_prompts.get(
        result.category, specialist_prompts[IntentCategory.GENERAL]
    )

    yield AgentEvent(
        step="thought",
        node=specialist_node,
        content=f"Dispatched to **{specialist_node}**. Generating specialized resolution..."
    ).to_sse()

    specialist_agent = Agent(
        model=model_spec,
        system_prompt=specialist_system_prompt
    )

    try:
        specialist_run = await specialist_agent.run(
            f"User Query:\n{user_query}\n\n(Triage Metadata: Urgency={result.urgency}, Category={result.category.value})"
        )
        specialist_response = specialist_run.output
    except Exception as e:
        yield AgentEvent(
            step="error",
            node=specialist_node,
            content=f"Specialist agent execution failed: {str(e)}",
            status="failed"
        ).to_sse()
        return

    yield AgentEvent(
        step="completed",
        node=specialist_node,
        content=specialist_response,
        data={
            "category": result.category.value,
            "response": specialist_response
        },
        status="completed"
    ).to_sse()

