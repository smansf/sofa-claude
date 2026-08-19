---
name: onboard
description: Start-of-session orientation — one cheap read of the standing handoff issue, a staleness check, then scope confirmation with Steve before any deep work.
---

# onboard

1. Read the **body only** of Issue #1 (`gh issue view 1 --json body`). Never
   read its comments — they are an append-only log, not live state.
2. Sanity-check the body against `git log --oneline -10` on `main` and the
   open-PR list. If the handoff predates visible activity, say so — treat
   the repo and GitHub as truth, the handoff as a pointer.
3. State your understanding of current scope in two or three sentences and
   confirm it with Steve (or, in an unattended run, against the schedule's
   declared purpose). Only then read anything else or act.
4. Freshness check on the operator toolbox: if `~/.claude/skills/` differs
   from sofa-claude `main`'s `.claude/skills/` (compare via `gh`), refresh
   the copies from merged `main` — never from a branch — before relying on
   any skill.

Do not deep-read decision records, grants, or history reflexively — pull
them in only when the confirmed scope needs them.
