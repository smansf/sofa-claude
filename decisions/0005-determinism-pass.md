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
- **Paved paths — honestly classified after this PR's own doc-review.**
  Workload `dev` merges go via `scripts/merge_dev.py` (seed kit, tested
  at source): it refuses unless every *named required check* succeeded
  (absent is not green; skipped is not green for required checks), a
  fresh-context reviewer comment *starting* with the marker exists (and
  no refusal text can double as the credential), the base is `dev`, the
  head is `claude/*`, and the PR isn't draft. Transport failures are loud
  and explicitly forbid the by-hand workaround. This is a **paved path,
  not a wall**: on free private repos nothing stops a raw `gh pr merge`,
  so the rule "merging any other way is a defect" remains
  instruction-backed — named here so nobody mistakes it for enforced.
  Unit issues: the web form requires acceptance criteria and blank issues
  are disabled, but `gh`-filed issues bypass forms — the form is a
  web-path guardrail; the gh path remains instruction-backed.
- **Boundary.** Stakes tiers, triage, review content, promotion timing
  stay judgment — mechanizing judgment is the legacy theater trap.

## Consequences

On sofa-claude, merging red or oversizing the rulebook became impossible
(ruleset + `line-budget`, which caps characters as well as lines so
rule-joining can't dodge it). On workload repos, the riskiest moments
became one-instruction paved paths with loud refusals — materially
harder to get wrong, but still instruction-backed at the edges named
above. Residual bypasses are recorded, not denied: raw `gh pr merge`,
`gh`-filed AC-less units, a self-posted reviewer marker, and the stale
reviewer credential (Issue #10, `keep`). After this PR merges, Steve
adds `line-budget` to the ruleset's required checks (30 seconds).
Issues #5, #7, and #10 are the next mechanizations, scheduled with the
Grant 1 rails.
