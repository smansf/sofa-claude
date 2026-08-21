---
name: onboard
description: Start-of-session orientation — one cheap read of the standing handoff issue, a staleness check, then scope confirmation with Steve before any deep work.
---

# onboard

Every `gh` call in this skill runs under a short-lived App token minted
by the repo's credential helper — in a workload repo
`python3 scripts/gh_token.py --account <owner> --repos <name>
--perm <name=level> -- gh ...`; in sofa-claude itself the helper lives
at `seed/scripts/gh_token.py` — never ambient session auth. Grant 4's
regime has no ambient fallback.

1. Credential presence check, before the first `gh` call: confirm the
   key `gh_token.py` will actually use is readable — the file named by
   `SOFA_APP_KEY` when that is set, else `~/.config/sofa-claude/app.pem`
   (`test -r "${SOFA_APP_KEY:-$HOME/.config/sofa-claude/app.pem}"`) —
   and that `SOFA_APP_ID` is set. **Presence only — never read, print,
   or echo a key or token.** If either is missing, say so before
   starting work: every GitHub path in this session stops without them,
   and finding that out mid-unit wastes the unit. This is an operator
   convenience, not a Grant 1 rail — it neither notifies nor halts, and
   does not count toward that grant's notify-and-halt precondition.
2. Resolve the handoff issue from **this repo's** CLAUDE.md, which names
   it ("Standing handoff: Issue N"); in sofa-claude itself that is Issue
   #1. Never assume #1 — in a workload repo it is whatever bootstrap
   filled in, and #1 there is ordinary work. If CLAUDE.md names no handoff
   issue, stop and say so rather than guessing.
3. Read the **body only** of that issue
   (`... --perm issues=read -- gh issue view N --json body,labels`).
   Confirm it carries `standing` before treating it as the
   handoff; an issue without that label is not one. The body is the whole
   handoff — GitHub's edit history preserves prior versions; there is no
   comment log.
4. Sanity-check the body against `git log --oneline -10` on `main` and the
   open-PR list. If the handoff predates visible activity, say so — treat
   the repo and GitHub as truth, the handoff as a pointer.
5. State your understanding of current scope in two or three sentences and
   confirm it with Steve (or, in an unattended run, against the schedule's
   declared purpose). Only then read anything else or act.
6. Freshness check on the operator toolbox: if `~/.claude/skills/` differs
   from sofa-claude `main`'s `.claude/skills/` (compare via a
   `--account smansf --repos sofa-claude --perm contents=read` mint),
   refresh the copies from merged `main` — **each skill's whole
   directory, not just SKILL.md** (bootstrap ships `wire_repo.py` beside
   its SKILL.md, and the documented invocation runs it from the
   installed path) — never from a branch — before relying on any skill.

Do not deep-read decision records, grants, or history reflexively — pull
them in only when the confirmed scope needs them.
