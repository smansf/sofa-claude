# Operating grants

A grant takes effect when Steve merges the PR that adds or amends it; the
global `~/.claude/CLAUDE.md` is then updated to match, and this file remains
the authoritative text. Reverting a grant works the same way, in reverse.

## Grant 1 — Unattended execution

Supersedes the global rule "no standing unattended execution."

- Claude may run scheduled and event-triggered sessions on the mini inside
  the sofa-claude account, using native Claude Code mechanisms (scheduled
  agents, cron-invoked headless runs, /loop).
- Rails: every unattended run begins with a credential validity check — on
  failure it notifies Steve (push notification) and halts cleanly rather
  than dying silently. Schedules declare a purpose and a time/spend bound at
  creation. The containment boundary and every other account rule are
  unchanged; credential-granting flows remain forbidden, always.
- Kill switch: Steve deletes the schedule, or reverts this grant. If this
  grant's text is absent from `~/.claude/CLAUDE.md`, the old prohibition
  stands.

## Grant 2 — Review lines (workload repos)

- Unattended first line: a merge to `dev` requires a green CI run plus a
  fresh-context reviewer subagent pass, invoked by Claude, at model/effort
  matching the repo's declared stakes tier. One round; findings follow the
  intake rule (decisions/0002).
- Attended first line: at promotions (`dev → staging`, `staging → main`)
  Claude prepares the promotion PR and hands Steve the exact command —
  `/code-review <effort> <PR URL> --comment` — in the PR body and the
  needs-Steve digest. Steve types it; Claude never invokes or replicates
  that skill. Adversarial follow-up on code is reserved for high-stakes
  surfaces (security, money, data loss), not routine polish.
- Design/governance prose (charters, CLAUDE.mds, grants): the adversarial
  brief review is the first line; the brief is shown to Steve (attended) or
  committed in the PR (unattended) before it runs.

## Grant 3 — Platform updates

- The Claude Code auto-updater is enabled on this account.
- The "stop and hand back to Steve" rule applies to installing *new* tools
  only, not to updating tools already granted user-locally.
