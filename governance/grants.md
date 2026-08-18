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

## Grant 2 — Automated pre-merge code review (workload repos)

- A merge to a workload repo's `dev` requires a green CI run plus a
  fresh-context reviewer subagent pass, invoked by Claude, at model/effort
  matching the repo's declared stakes tier.
- Steve's typed `/code-review` remains reserved for his own use (typically
  at promotions); Claude still never invokes or replicates that skill.

## Grant 3 — Platform updates

- The Claude Code auto-updater is enabled on this account.
- The "stop and hand back to Steve" rule applies to installing *new* tools
  only, not to updating tools already granted user-locally.
