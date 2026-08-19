# sofa-claude

Claude-native development process for Steve's projects. Four roles: a seed kit
workload repos copy at bootstrap, the governance record, a small closed set of
skills, and the "needs Steve" digest. Work happens in workload repos, never
here. Account rules inherit from `~/.claude/CLAUDE.md`.

Origin: rebuilt 2026-08 from `smansf/sofa-claude-legacy`, which spiraled
into process-about-process. All rationale lives in `decisions/` (start at 0001).

## What this repo is not

Not an orchestration engine, dashboard, metrics platform, runtime dependency,
or a home for workload code. Workloads copy from `seed/` once and owe nothing
back; good patterns are harvested back here occasionally, never pushed out.

## Delivery

- Branch `claude/*`, PR to `main`, Steve merges — always. Open the PR at the
  first push and keep it draft while review and fixes are in progress —
  ready means merging is the only step left. A pushed branch with no PR is
  a defect.
- Every PR body fills **Why this change** with the concrete incident in
  real work that motivated it. CI rejects an unfilled section. No bleed,
  no merge.
- Healthy steady state: near-zero PRs here while workload repos grow. This
  queue is the spiral detector — if it fills, the factory is manufacturing
  factory parts again.

## Discovered work

- First triage, at discovery: fix in flight only what blocks the current
  unit or is a trivial defect in code already being touched — hard-capped
  at trivial size; the moment it wants its own design, file it instead.
  Everything else real is filed, at any severity, **silently** — never
  narrated in PRs, recaps, or the digest. Noise floor: if no one can say
  who gets hurt and how, it is opinion, not work, and is not filed.
- Second triage, on the issue — one question, what happens if nobody acts:
  `urgent` (invalidates the active unit's premise, or active harm —
  interrupts work now), `keep` (must eventually be fixed — never expires),
  or unlabeled (the default — auto-closes after 14 days untouched; closed,
  not deleted, so the record stays searchable). Complexity and size are
  judged at pickup as the unit's tier, never at filing.
- Acceptance criteria are frozen on the issue before work starts. Done means
  merged. A work stream states its end condition when it opens, and ends.

## Review

Depth scales with product stakes, never diff contents. One round per unit;
a second only when an urgent-grade finding survives the fix round — all
else follows the intake rule. Design/governance prose gets the adversarial brief review, its
brief visible in the PR before it runs. Code review is Steve's to type —
the process hands him the exact `/code-review <effort> <PR URL> --comment`
command in the PR body or digest; Claude never invokes or replicates it.

## Skills

The set is closed: `onboard`, `wrap-up`, `bootstrap`, `doc-review` —
adding one takes a bleed. Skills are the operator's toolbox, not repo
content: installed to `~/.claude/skills/` as copies from merged `main`
only (never a branch), and may never require a convention a bootstrapped
repo lacks. `/onboard` first in every session (reads Issue #1's body
only); `/wrap-up` before ending one (refreshes Issues #1 and #2).

## Rulebook budget

This file stays under 75 lines. Adding a rule means removing or merging one.
On conflict, this file is normative: decision records (`decisions/`, one
page each) are dated rationale, never live rules. Grants (`governance/`)
take effect only by Steve merging the PR that adds or amends them.

## Never

Merge to `main` — that is Steve's act, every time, in this repo.
