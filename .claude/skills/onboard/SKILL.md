---
name: onboard
description: Start-of-session orientation — one cheap read of the standing handoff issue, a staleness check, then scope confirmation with Steve before any deep work.
---

# onboard

1. Resolve the handoff issue from **this repo's** CLAUDE.md, which names
   it ("Standing handoff: Issue N"); in sofa-claude itself that is Issue
   #1. Never assume #1 — in a workload repo it is whatever bootstrap
   filled in, and #1 there is ordinary work. If CLAUDE.md names no handoff
   issue, stop and say so rather than guessing.
2. Read the **body only** of that issue (`gh issue view N --json
   body,labels`). Confirm it carries `standing` before treating it as the
   handoff; an issue without that label is not one. The body is the whole
   handoff — GitHub's edit history preserves prior versions; there is no
   comment log.
3. Sanity-check the body against `git log --oneline -10` on `main` and the
   open-PR list. If the handoff predates visible activity, say so — treat
   the repo and GitHub as truth, the handoff as a pointer.
4. State your understanding of current scope in two or three sentences and
   confirm it with Steve (or, in an unattended run, against the schedule's
   declared purpose). Only then read anything else or act.
5. Freshness check on the operator toolbox: if `~/.claude/skills/` differs
   from sofa-claude `main`'s `.claude/skills/` (compare via `gh`), refresh
   the copies from merged `main` — never from a branch — before relying on
   any skill.
6. Credential presence check: confirm the App key is readable
   (`test -r ~/.config/sofa-claude/app.pem`) and that `SOFA_APP_ID` is
   set. **Presence only — never read, print, or echo a key or token.** If
   either is missing, say so before starting work: every scripted GitHub
   path stops without them, and finding that out mid-unit wastes the unit.

Do not deep-read decision records, grants, or history reflexively — pull
them in only when the confirmed scope needs them.
