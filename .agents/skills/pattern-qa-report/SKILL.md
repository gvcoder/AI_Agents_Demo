---
name: pattern-qa-report
description: >-
  Automated QA verification and test-report generator for the AI Agent Design Patterns
  Playground. Use after implementing or modifying any design pattern (01-20), router,
  or frontend integration to run automated checks and create/update TEST_REPORT.md.
---

# Pattern QA & Test Report Skill

Run automated verification checks across the FastAPI backend and React frontend, then create or update `TEST_REPORT.md` at the repository root.

## Workflow

1. **Run the verification script**:
   ```bash
   .venv/bin/python .agents/skills/pattern-qa-report/scripts/verify_patterns.py
   ```
   This outputs a JSON summary with:
   - `backend.ok` and `backend.routes` (verifies `backend.app.main:app` imports cleanly and lists all registered `/api/pXX-.../run` endpoints).
   - `frontend_build.ok` (runs `npm run build` inside `frontend/`).
   - `env.providers` (checks whether `GEMINI_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` are configured in `.env`).

2. **Check frontend pattern registry**:
   Verify that each newly implemented pattern in `frontend/src/data/patternsData.js` has a matching `endpoint` field pointing to its backend `/api/pXX-.../run` route and a `sampleInput` (if applicable).

3. **Optional live SSE smoke test** (only if a provider key is configured or Ollama is running):
   Start or hit the FastAPI backend (`POST /api/pXX-.../run`) and confirm SSE events stream cleanly (`start` -> `completed`). If no API keys are configured, record live LLM execution as `SKIPPED (no API key configured in .env)` — never fabricate live results.

4. **Create or update `TEST_REPORT.md`** at the repository root:
   - Update the summary timestamp, total implemented patterns count, and overall status.
   - Maintain a table of all implemented patterns (`01`..`20`) with:
     - Pattern `#` & Name
     - Framework
     - Backend Route (`PASS` / `FAIL`)
     - Frontend `patternsData.js` & Build (`PASS` / `FAIL`)
     - Live SSE Smoke Test (`PASS` / `SKIPPED` / `FAIL`)
   - Append a concise **Latest Run Notes** section detailing what was verified and any warnings or blockers.
