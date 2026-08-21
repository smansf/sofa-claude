---
name: wrap-up
description: End-of-session handoff — drain in-flight work, reconcile issue state, refresh the standing handoff and needs-Steve issues, and give a plain recap.
---

# wrap-up

1. Drain or explicitly hand off any in-flight background work; nothing
   should be silently mid-air when the session ends.
2. Reconcile GitHub state: every pushed `claude/*` branch has a PR; issues
   touched this session reflect reality; anything discovered but not filed
   was *deliberately* dropped per the intake kill step (do not file a
   parting wave of findings — that is the legacy failure mode).
3. Overwrite the **body** of the handoff issue named in **this repo's**
   CLAUDE.md — in sofa-claude that is Issue #1, in a workload repo it is
   whatever bootstrap filled in. **Confirm it carries `standing` before
   writing**, and stop if it does not: overwriting a body is destructive
   and there is no comment log to recover from, so writing to a guessed
   number would silently destroy someone's unrelated issue. Content:
   current state, in-flight PRs, the next session's starting point.
   Append nothing; the body is the whole handoff.
4. Refresh the **body** of the needs-Steve digest issue (Issue #2 in
   sofa-claude), under the same `standing`-label guard: list only items
   genuinely blocked on Steve — pending merges/promotions, open grant
   decisions, halted runs — each with its paste-ready command where one
   applies (e.g. `/code-review high <PR URL> --comment`). An empty list is
   a valid and good state. End the digest with one line — the current count
   of open `keep`-labeled issues across repos — a number, not a list, so
   silent filing stays visible in aggregate.
5. Give Steve a plain-English recap (what shipped, what's blocked, what's
   next) and a ready-to-paste prompt for the next session.
