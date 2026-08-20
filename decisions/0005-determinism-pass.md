# 0005 — Determinism pass for the weak-model era

**Status:** accepted (Steve, 2026-08-19) · **Amends:** the seed kit and
delivery mechanics; extends 0001's loud-failure principle

## Context

Steve commissioned an analysis: where does correct behavior still rest on
model instruction-following that a weaker model will fumble? Findings:
the process repo's CI was advisory (a red check did not block merging);
the rulebook's 75-line budget was enforced by counting (violated twice in
one day, both caught by hand); the workload `dev` merge — the riskiest
unattended moment — was governed by four distributed prose rules; and
nothing made a unit's acceptance criteria structurally required. Also
corrected: rulesets/branch protection are free on public repos only, so
Issue #4's machine-account gates reach sofa-claude but not private
workload repos — there, the deterministic stack is Vercel wiring plus a
paved-path merge tool.

## Decision

Three levers, applied where outcomes are verifiable and never to judgment:

- **Gates.** Steve enabled a `main` ruleset on sofa-claude: PRs required,
  status checks (`why-this-change`, `secrets`, `tests`) must pass;
  approvals deliberately 0 until the machine account exists (an author
  cannot approve their own PR). A `line-budget` CI job now fails any PR
  that pushes CLAUDE.md past 74 lines.
- **Paved paths.** Workload `dev` merges happen only via
  `scripts/merge_dev.py` (seed kit, tested at source): it refuses unless
  CI is green, a `## Reviewer pass` comment exists, the base is `dev`,
  the head is `claude/*`, and the PR isn't draft — one instruction
  replacing four rules, `gh`-native underneath. Unit issues are filed via
  a GitHub issue form that makes acceptance criteria required at
  creation.
- **Boundary.** Stakes tiers, triage, review content, promotion timing
  stay judgment — mechanizing judgment is the legacy theater trap.

## Consequences

A weak model can no longer merge red, oversize the rulebook, file an
AC-less unit, or merge a workload PR that skipped review — those failures
became impossible rather than prohibited. Prose shrinks as gates land.
After this PR merges, Steve adds `line-budget` to the ruleset's required
checks (30 seconds). Issues #5 and #7 remain the next mechanizations,
scheduled with the Grant 1 rails.
