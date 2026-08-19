# 0003 — Seed review round: lanes confirmed, draft lifecycle, dormant grants

**Status:** accepted (Steve, 2026-08-19) · **Amends:** 0002 (review lines),
Grant 1

## Context

The founding PR ran both review lines against the identical diff as a
deliberate experiment. Built-in `/code-review` (medium): 8 findings, all
mechanical or platform facts — the seed kit not shipping the expiry
workflow, GitHub auto-disabling public-repo crons after 60 quiet days,
doubled CI triggers, a false-green test gate, a dangling cross-file
reference, the grant not covering the repo's own cron, rule duplication,
and the what-bled gate being blind to body edits. Adversarial brief: 8
findings, all governance holes — the paper production gate under
unattended operation, prose-only grant rails, an invisible `keep` backlog,
missing workload session discipline, an unattested reviewer pass, and the
`urgent`/declared-purpose conflict. Overlap: two findings. Also learned:
the first `/code-review` run (high) died without posting anything —
delivery must be confirmed, never assumed.

## Decision

- The review lanes stand as 0002 assigned them, and **both lanes run only
  on seam artifacts** — changes that are simultaneously rulebook and
  enforcement machinery, which in practice means PRs to this repo.
  Workload code PRs get one lane.
- **PR lifecycle:** a PR opens at first push as draft and stays draft
  through review and fix rounds; "ready" is reserved for the state where
  merging is the only remaining step.
- **Grants with unbuilt machinery are written dormant:** preconditions
  named in the grant, grant inert until the rails merge as code. A promised
  but unwritten enforcement is prose, not a rail — 0001's loud-failure
  principle applied to governance itself.
- Attended reviews end by confirming the findings actually landed on the
  PR.

## Consequences

Twelve of the fourteen distinct findings were fixed in the founding PR's
single fix round; two became `keep` issues (machine-account ruleset
enforcement of the human-only merge gates; the workload pr-visibility
port). The digest now ends with the open `keep` count — a bare number —
so silent filing stays visible in aggregate without narration.
