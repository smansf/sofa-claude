---
name: wrap-up
description: End-of-session handoff — drain in-flight work, reconcile issue state, refresh the standing handoff and needs-Steve issues, and give a plain recap.
---

# wrap-up

Every `gh` call in this skill runs under a short-lived App token minted
by the repo's credential helper — in a workload repo
`python3 scripts/gh_token.py --account <owner> --repos <name>
--perm <name=level> -- gh ...`; in sofa-claude itself the helper lives
at `seed/scripts/gh_token.py` — never ambient session auth. Grant 4's
regime has no ambient fallback.

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
4. Refresh the **body** of the needs-Steve digest issue — **always
   sofa-claude's own** (Issue #2 in smansf/sofa-claude), whatever repo
   the session ran in: the digest aggregates across repos, and workload
   repos carry none of their own. From a workload repo this is the one
   write that leaves the repo's scope — mint for it explicitly:
   `python3 scripts/gh_token.py --account smansf --repos sofa-claude
   --perm issues=write --reason "needs-Steve digest" -- gh issue edit 2
   --repo smansf/sofa-claude --body-file ...`. If that mint fails, the
   App's smansf installation does not cover sofa-claude — put the digest
   content in the recap for Steve instead of writing nothing silently.
   Same `standing`-label guard: list only
   items genuinely blocked on Steve — pending merges/promotions, open grant
   decisions, halted runs — each with its paste-ready command where one
   applies (e.g. `/code-review high <PR URL> --comment`). An empty list is
   a valid and good state. End the digest with one line — the current count
   of open `keep`-labeled issues across repos — a number, not a list, so
   silent filing stays visible in aggregate.
5. Give Steve a plain-English recap (what shipped, what's blocked, what's
   next) and a ready-to-paste prompt for the next session.
