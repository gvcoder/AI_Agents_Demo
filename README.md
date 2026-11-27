# 🤖 AI Agent Design Patterns Playground

An interactive, educational testbed implementing the **Top 20 AI Agent Design Patterns** with a modern **React + Vite** frontend and a **FastAPI** backend in Python.

Each pattern is implemented using the most idiomatic, modern AI agent framework (LangGraph, Pydantic AI, Smolagents, LlamaIndex, OpenAI Agents SDK, CrewAI, AutoGen, or native Python concurrency), complete with real-time Server-Sent Events (SSE) streaming, interactive trace visualizations, and architectural documentation.

---

## 🧭 Taxonomy & Implementation Tracker

The 20 patterns are organized into 4 categories:

### 1. Workflows (Deterministic & Semi-Deterministic Pipelines)
- [x] **01. Prompt Chaining** (`LangGraph`) — Breaks a task into fixed steps; a verification gate catches errors before downstream steps.
- [x] **02. Routing** (`Pydantic AI`) — Classifies incoming queries to route to specialist prompts or fine-tuned models.
- [x] **03. Parallelization** (`Native Asyncio`) — Runs independent subtasks simultaneously and synthesizes results.
- [x] **04. Orchestrator-Workers** (`LangGraph`) — Central orchestrator dynamically plans and delegates worker subtasks on the fly.
- [x] **05. Evaluator-Optimizer** (`LangGraph`) — Generator-evaluator feedback loop refining output until criteria are met.

### 2. Reasoning (Cognitive Search & Self-Correction)
- [x] **06. ReAct** (`Smolagents`) — Interleaves Thought, Action (Tool calling), and Observation cycles.
- [x] **07. Plan-and-Execute** (`LangGraph`) — Decouples macro planning from execution with dynamic replanning on failure.
- [x] **08. Reflection** (`Pydantic AI / Native`) — Explicit self-critique pass evaluating tone, logic, and precision.
- [x] **09. Tree of Thoughts (ToT)** (`Search Algorithms - BFS/MCTS`) — Explores reasoning trees, evaluating states and pruning poor paths.
- [x] **10. Self-Consistency** (`Native Asyncio`) — Samples multiple reasoning trajectories in parallel and applies majority voting.

### 3. Capabilities (Tools, Retrieval, Memory & Safety)
- [x] **11. Tool Use** (`Pydantic AI`) — Type-safe structured function calling with schema validation.
- [ ] **12. Agentic RAG** (`LlamaIndex`) — Autonomous multi-turn retrieval with dynamic query rewriting and chunk grading.
- [ ] **13. Memory** (`LlamaIndex / LangGraph`) — Dual-tier memory (short-term buffer + long-term vector/key-value store).
- [ ] **14. Human-in-the-Loop** (`LangGraph`) — Graph breakpoints pausing high-stakes actions for operator review/approval.
- [ ] **15. Guardrails** (`NeMo / Pydantic AI`) — Input/output perimeter safety against prompt injections and PII leakage.

### 4. Multi-Agent (Collaborative & Hierarchical Topologies)
- [ ] **16. Supervisor** (`LangGraph`) — Central coordinator routing work to specialist agents and synthesizing results.
- [ ] **17. Hierarchical Teams** (`CrewAI`) — Multi-tiered organization with managers overseeing sub-agent squads.
- [ ] **18. Hand-off** (`OpenAI Agents SDK / Swarm`) — Decentralized peer hand-off passing session control to specialist agents.
- [ ] **19. Agent-as-Tool** (`Smolagents / LangGraph`) — Encapsulates an autonomous sub-agent inside an ordinary tool function.
- [ ] **20. Debate** (`AutoGen`) — Multiple agents argue opposing viewpoints before an impartial judge rules.

---

## 🛠️ Tech Stack & Framework Matrix

| Component | Technology |
|---|---|
| **Package Manager** | `uv` (Fast Python package and virtual environment manager) |
| **Backend Runtime** | Python 3.10+, FastAPI, Uvicorn, SSE Starlette |
| **Frontend** | React 18, Vite, Tailwind CSS, Lucide Icons |
| **Supported LLMs** | Google Gemini (`gemini-2.5-flash`), OpenAI (`gpt-4o-mini`), Claude (`claude-3-5-sonnet`), Local Ollama (`llama3.2`) |

---

## 🚀 Quickstart

### 1. Prerequisites
- Python 3.10+
- Node.js 18+ and `npm`
- `uv` installed (`curl -LsSf https://astral.sh/uv/install.sh | sh`)

### 2. Configure Environment Variables
Copy the template and fill in your preferred model keys:
```bash
cp .env.example .env
```
Supported variables:
- `GEMINI_API_KEY`: For Google Gemini models.
- `OPENAI_API_KEY`: For OpenAI models.
- `ANTHROPIC_API_KEY`: For Claude models.
- `OLLAMA_BASE_URL`: For local models (defaults to `http://localhost:11434`).

### 3. Launch with One Command
```bash
./start.sh
```

- **Frontend UI**: [http://localhost:5173](http://localhost:5173)
- **FastAPI Backend**: [http://localhost:8000](http://localhost:8000)
- **Interactive Swagger Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

---

## 📁 Repository Structure

```
AI_Agents_Demo/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routers/
│   │   │       ├── p01_prompt_chaining.py
│   │   │       └── ...
│   │   ├── core/
│   │   │   ├── config.py         # App settings & API key resolution
│   │   │   ├── events.py         # Standardized SSE AgentEvent model
│   │   │   └── llm_factory.py    # Unified multi-provider ChatModel factory
│   │   ├── patterns/
│   │   │   ├── p01_prompt_chaining.py
│   │   │   └── ...
│   │   └── main.py               # FastAPI entrypoint & middleware
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.jsx       # 20-pattern collapsible navigator
│   │   │   └── PatternWorkspace.jsx # Interactive playground & live SSE trace
│   │   ├── data/
│   │   │   └── patternsData.js   # Pattern metadata, tags, and trade-offs
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
├── DESIGN_PATTERNS_BLUEPRINT.md  # Full theoretical blueprint of all 20 patterns
├── start.sh                      # Single-command dev launcher
└── README.md                     # Project tracker & documentation
```

---

## 📝 Implementation Progress & Changelog

### Version 0.1.0 - Foundation & Pattern 01
- Set up `uv` virtual environment and installed core dependencies.
- Built unified multi-provider LLM factory supporting Gemini, OpenAI, Claude, and local Ollama.
- Created Server-Sent Events (SSE) bus for real-time frontend streaming.
- Built React + Vite + Tailwind frontend with a responsive 20-pattern navigator.
- **Implemented Pattern 01 (Prompt Chaining)** with LangGraph:
  - Step 1: Discrete Fact Extraction.
  - Intermediate Gate: Semantic and factual quality check that halts on hallucination/failure.
  - Step 2: Synthesis into target format (Executive Brief, Action Items, etc.).

### Version 0.2.0 - Pattern 02: Routing
- **Implemented Pattern 02 (Routing)** with Pydantic AI:
  - Structured intent classification (`technical_support`, `billing_inquiry`, `feature_request`, `general`) with confidence and urgency scoring.
  - Dynamic dispatch to specialized system prompts.

### Version 0.3.0 - Pattern 03: Parallelization
- **Implemented Pattern 03 (Parallelization)** with Native Python `asyncio`:
  - Concurrent Fan-Out across 3 specialist perspectives (*Product & Market Analyst*, *Systems & Engineering Architect*, *Security & Risk Auditor*) using `asyncio.create_task` + `asyncio.as_completed`.
  - Real-time wall-clock vs. sequential-estimate timing comparison.
  - Fan-In Merge Synthesizer combining all parallel analyses into the chosen target format.

### Version 0.4.0 - Pattern 04: Orchestrator-Workers
- **Implemented Pattern 04 (Orchestrator-Workers)** with LangGraph (`StateGraph` + `Send` API):
  - **Lead Orchestrator**: Uses structured output (`OrchestratorPlan`) to dynamically decompose an arbitrary request into 2–5 non-overlapping specialist subtasks (`W1`–`W5`) at runtime.
  - **Dynamic Map-Reduce (`Send`)**: Spawns parallel worker nodes dynamically and accumulates results via an `operator.add` state reducer.
  - **Synthesizer**: Merges all worker deliverables into the requested `target_format`, streamed live via `graph.astream(..., stream_mode="updates")`.

### Version 0.5.0 - Pattern 05: Evaluator-Optimizer
- **Implemented Pattern 05 (Evaluator-Optimizer)** with LangGraph (`StateGraph` cyclic loop):
  - **Generator Node**: Produces initial drafts and iteratively revises them based on structured evaluator critique.
  - **Evaluator Node**: Grades each draft (`EvaluationResult`: `passed`, `score` 1–10, `feedback`) against completeness, accuracy, and edge-case criteria.
  - **Bounded Cycle**: Conditional edge loops `evaluator -> generator` until `passed=True` or `max_iterations` is reached, completing **Category 1: Workflows (01–05)**.

### Version 0.6.0 - Pattern 06: ReAct
- **Implemented Pattern 06 (ReAct)** with Smolagents (`ToolCallingAgent` + `LiteLLMModel`):
  - **Domain Tools**: `lookup_product_catalog`, `get_discount_tier`, `check_shipping_eta`, and AST-safe `calculate_expression`.
  - **Streaming Loop**: Streams multi-step `Action` (tool call) and `Observation` events in real time via `agent.run(..., stream=True)` before emitting `Final Answer`.

### Version 0.7.0 - Pattern 07: Plan-and-Execute
- **Implemented Pattern 07 (Plan-and-Execute)** with LangGraph (`StateGraph`):
  - **Macro Planner**: Produces an ordered 3–5 step `Plan` up front.
  - **Step Executor**: Executes one step at a time with accumulated `past_steps` context and structured `StepExecutionResult` (`success`, `output`, `blocker_reason`).
  - **Dynamic Replanner & Synthesizer**: Revises remaining steps if a step hits a blocker, then synthesizes all completed steps into the target format.

### Version 0.8.0 - Pattern 08: Reflection
- **Implemented Pattern 08 (Reflection)** with Pydantic AI (`Draft ➔ Self-Critic ➔ Revise`):
  - **Pass 1 (Initial Drafter)**: Generates an initial zero-shot draft in the target format.
  - **Pass 2 (Self-Critic)**: Uses structured `ReflectionCritique` output (`clarity_score`, `logic_score`, `tone_score`, `flaws_found`, `improvement_plan`, `needs_revision`).
  - **Pass 3 (Reviser)**: Applies the improvement plan to produce the verified final response.

### Version 0.9.0 - Pattern 09: Tree of Thoughts (ToT)
- **Implemented Pattern 09 (Tree of Thoughts)** with Native Python `asyncio` Beam / BFS Search:
  - **Parallel Branching**: Expands each frontier node into `branching_factor` (default `3`) distinct reasoning branches concurrently.
  - **Heuristic Scoring & Pruning**: Evaluates all candidates in parallel (`ThoughtScore` 1–10) and prunes weaker branches, keeping top `beam_width` (default `2`) nodes per depth.
  - **Optimal Path Synthesis**: Selects the `★ Best Path` at `max_depth` and synthesizes the final solution.

### Version 0.10.0 - Pattern 10: Self-Consistency
- **Implemented Pattern 10 (Self-Consistency)** with Native Python `asyncio`:
  - **Parallel Stochastic Sampling**: Runs `num_samples` (default `5`) independent chain-of-thought trajectories concurrently at `temperature > 0` (`ReasoningSample`: `reasoning`, `final_answer`).
  - **Majority Vote Aggregator**: Normalizes candidate answers, tallies votes via `Counter`, and emits the consensus answer with agreement percentage, completing **Category 2: Reasoning (06–10)**.

### Version 0.11.0 - Pattern 11: Tool Use
- **Implemented Pattern 11 (Tool Use)** with Pydantic AI:
  - **Type-Safe Tools**: `get_cloud_spend`, `convert_currency`, and `forecast_annual_run_rate` with `Literal` & Pydantic schema validation.
  - **Live Inspection**: Streams each `ToolCallPart` (JSON arguments) and `ToolReturnPart` (structured JSON result) via `agent.iter()` before emitting `Final Answer`.

