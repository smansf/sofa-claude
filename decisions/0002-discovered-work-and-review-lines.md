# 0002 — Discovered work, labels, and review lines

**Status:** accepted (Steve, 2026-08-19) · **Amends:** 0001's intake kill
step and the severity:P1–P5 label scheme (removed)

## Context

0001 shipped an intake rule that silently *dropped* sub-P2 discoveries.
Steve challenged it: dropping destroys the mineable record and masks the
root cause — the legacy corrosion came from the **obligation and narration**
attached to filed issues, and from disproportionate finding generation, not
from recording itself. Legacy data also showed five priority ranks
collapsing to about two in practice (zero P1s ever filed; P4/P5 behaviorally
identical), while the grading itself generated meta-work. "Priority" labeled
a feeling, not a decision.

## Decision

**Two-level triage.** First, at discovery: fix in flight only what blocks
the current unit or is a trivial defect in code already being touched,
hard-capped at trivial size — wants its own design ⇒ file it. Everything
else real is filed at any severity, silently (never narrated in PRs,
recaps, or the digest). Noise floor: an observation with no statable harm
scenario is opinion, not work, and is not filed.

Second, on the issue, one question — *what happens if nobody acts*:
`urgent` (invalidates the active unit's premise or is active harm;
interrupts now), `keep` (must eventually be fixed; never expires), or
**unlabeled** — the default, which auto-closes after 14 days untouched.
Closed, not deleted: the trail stays searchable at zero attention cost.
Complexity and size are judged at pickup as the unit's tier, never at
filing — a stale size guess is worse than none.

**Review lines.** Code, unattended (workload `dev` merges): fresh-context
reviewer subagent, one round — the only line available, since
`/code-review` is human-invocation-only. Code, attended (promotions;
sofa-claude PRs): Steve's typed `/code-review` is the first line, and the
process hands him the exact `--comment` command in the PR body and digest.
Adversarial review of *code* is reserved for high-stakes surfaces
(security, money, data loss). Design/governance *prose*: the adversarial
brief review is the first line — no native tool competes — and the brief is
always visible (in chat or committed in the PR) before it runs.

## Consequences

Filing becomes nearly free — no severity deliberation, two crisp promotion
tests only. The backlog self-cleans without destroying the record. Human
review friction is two typed commands at promotion boundaries, accepted on
trial. The repo's labels are now `urgent`, `keep`, `standing`, and the
machinery-applied `expiring`.
