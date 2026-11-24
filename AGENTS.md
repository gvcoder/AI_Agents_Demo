# Project Agent Guidelines

## Post-Implementation QA, Test Reporting & Git Sync
After implementing or modifying any AI Agent Design Pattern (`01`–`20`), backend router, or frontend pattern integration:
1. Activate and follow the `pattern-qa-report` skill at `.agents/skills/pattern-qa-report/SKILL.md` (or delegate to a dedicated `qa-reporter` subagent with write tools to execute that skill).
2. Always update `TEST_REPORT.md` and `README.md` with accurate, observed verification results.
3. Once the Live SSE Smoke Test succeeds and `TEST_REPORT.md` and `README.md` are updated, activate and follow the `pattern-git-sync` skill at `.agents/skills/pattern-git-sync/SKILL.md` to commit and push the verified changes to `origin/master`.
