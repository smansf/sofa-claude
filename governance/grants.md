# Operating grants

A grant takes effect when Steve merges the PR that adds or amends it; the
global `~/.claude/CLAUDE.md` is then updated to match, and this file remains
the authoritative text. Reverting a grant works the same way, in reverse.

## Grant 1 — Unattended execution

Supersedes the global rule "no standing unattended execution" — but see the
preconditions: this grant is **dormant until its rails exist as merged code**.

- Claude may run scheduled and event-triggered sessions on the mini inside
  the sofa-claude account, using native Claude Code mechanisms (scheduled
  agents, cron-invoked headless runs, /loop).
- **Preconditions:** a session-start credential check that notifies Steve
  (push notification) and halts cleanly on failure, and schedule creation
  that records each schedule's purpose and time/spend bound. Until the PR
  shipping those rails merges, the old prohibition stands in full — a grant
  whose enforcement is unwritten is prose, not a rail (decisions/0001).
- In an unattended session, an `urgent` finding means: file it, notify
  Steve, and halt the affected work — never expand the session's declared
  purpose to act on it.
- Standing automation running inside GitHub (Actions workflows, e.g. the
  backlog-expiry cron) is authorized by Steve's merge of the workflow file
  that creates it.
- Authority and kill switch: the version of this file merged on `main` is
  authoritative; `~/.claude/CLAUDE.md` only mirrors it. Steve revokes by
  deleting schedules or reverting this grant on `main`.
- The containment boundary and every other account rule are unchanged;
  credential-granting flows remain forbidden, always.

## Grant 2 — Review lines (workload repos)

- Unattended first line: a merge to `dev` requires a green CI run plus a
  fresh-context reviewer subagent pass, invoked by Claude, at model/effort
  matching the repo's declared stakes tier, **posted as a comment on the PR
  before the merge — no comment, no merge**, so the pass leaves an artifact
  a later audit can check. One round; findings follow the intake rule
  (decisions/0002).
- Attended first line: at promotions (`dev → staging`, `staging → main`)
  Claude prepares the promotion PR and hands Steve the exact command —
  `/code-review <effort> <PR URL> --comment` — in the PR body and the
  needs-Steve digest. Steve types it; Claude never invokes or replicates
  that skill. Adversarial follow-up on code is reserved for high-stakes
  surfaces (security, money, data loss), not routine polish. The attended
  step ends by confirming the findings actually landed on the PR.
- Design/governance prose (charters, CLAUDE.mds, grants): the adversarial
  brief review is the first line; the brief is shown to Steve (attended) or
  committed in the PR (unattended) before it runs.

## Grant 3 — Platform updates

- The Claude Code auto-updater is enabled on this account.
- The "stop and hand back to Steve" rule applies to installing *new* tools
  only, not to updating tools already granted user-locally.
