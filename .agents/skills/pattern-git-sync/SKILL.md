---
name: pattern-git-sync
description: >-
  Commits and pushes repository changes to origin/master after a pattern implementation's
  Live SSE Smoke Test passes and TEST_REPORT.md and README.md are updated.
---

# Pattern Git Sync Skill

Safely stage, commit, and push verified pattern implementations and QA reports to `origin/master`.

## Preconditions (Must All Be True)

1. `verify_patterns.py` passed (`backend.ok: true` and `frontend_build.ok: true`).
2. The Live SSE Smoke Test for the new/modified pattern returned `HTTP 200` and reached `completed`.
3. `TEST_REPORT.md` and `README.md` have been updated with the observed results.

## Workflow

1. **Check working tree status**:
   ```bash
   git status
   ```
   Verify that `.env` or other secret/temporary files are NOT untracked or staged.

2. **Stage, commit, and push** (requires `BypassSandbox: true` if `.git` is read-only in sandbox or network is needed for push):
   ```bash
   git add -A && git commit -m "feat: implement Pattern XX (<Pattern Name>) and update QA report" && git push origin master
   ```
   *(Prefer explicit file paths over `git add -A` if unrelated scratch files exist in the working tree.)*

3. **Verify clean state**:
   Confirm `git status` reports `nothing to commit, working tree clean` and `Your branch is up to date with 'origin/master'`.
