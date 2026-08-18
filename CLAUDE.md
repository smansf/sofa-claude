# sofa-claude

Claude-native development process for Steve's projects. Four roles: a seed kit
workload repos copy at bootstrap, the governance record, a small closed set of
skills, and the "needs Steve" digest. Work happens in workload repos, never
here. Account rules inherit from `~/.claude/CLAUDE.md`.

Origin: rebuilt 2026-08 from `smansf/sofa-claude-legacy`, which spiraled into
process-about-process. Diagnosis and full design rationale:
[decisions/0001](decisions/0001-rebuild-from-legacy.md).

## What this repo is not

Not an orchestration engine, dashboard, metrics platform, runtime dependency,
or a home for workload code. Workloads copy from `seed/` once and owe nothing
back; good patterns are harvested back here occasionally, never pushed out.

## Delivery

- Branch `claude/*`, PR to `main`, Steve merges — always. Open the PR at the
  first push, draft if unready; a pushed branch with no PR is a defect.
- Every PR body fills **What bled**: the concrete incident in real work that
  motivated the change. CI rejects an unfilled section. No bleed, no merge.
- Healthy steady state: near-zero PRs here while workload repos grow. This
  queue is the spiral detector — if it fills, the factory is manufacturing
  factory parts again.

## Backlog

- Intake kill step for mid-unit discoveries: fix now if inside the frozen
  acceptance criteria; file only if severity:P1/P2 or it invalidates the
  current unit's premise; otherwise drop it, silently. Filing is the
  exception, not the default, and discoveries are never narrated in PRs.
- `severity:P3` issues auto-close after 14 days untouched (scheduled
  workflow). P1/P2 and `standing` are exempt. A P3 dying unworked is the
  system working, not a loss.
- Acceptance criteria are frozen on the issue before work starts. Done means
  merged. A work stream states its end condition when it opens, and ends.

## Proportionality

Review depth scales with product stakes, never diff contents. In a throwaway
repo everything is trivial tier, no exceptions. One review round per unit; a
second round only for P1/P2 findings — everything else follows the intake
kill step.

## Skills

The set is closed: `onboard`, `wrap-up`, `bootstrap`. Adding one takes a
bleed, like any rule. `/onboard` first in every session (reads Issue #1's
body only); `/wrap-up` before ending a substantive session (refreshes
Issues #1 and #2).

## Rulebook budget

This file stays under 75 lines. Adding a rule means removing or merging one.
Decision records (`decisions/`) are one page each, individually supersedable.
Grants (`governance/`) take effect only by Steve merging the PR that adds or
amends them.

## Never

Merge to `main` — that is Steve's act, every time, in this repo.
