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
3. Overwrite the **body** of Issue #1 with: current state, in-flight PRs,
   the next session's starting point. Append nothing; the body is the whole
   handoff.
4. Refresh the **body** of Issue #2 (needs-Steve digest): list only items
   genuinely blocked on Steve — pending merges/promotions, open grant
   decisions, halted runs — each with its paste-ready command where one
   applies (e.g. `/code-review high <PR URL> --comment`). An empty list is
   a valid and good state.
5. Give Steve a plain-English recap (what shipped, what's blocked, what's
   next) and a ready-to-paste prompt for the next session.
