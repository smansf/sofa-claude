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

## Grant 4 — App credentials

Supersedes the fine-grained PAT as the process's GitHub credential. Takes
effect on merge; `~/.claude/CLAUDE.md`'s credential rule is then updated to
match, and this file remains authoritative.

- The GitHub surface is a GitHub App (`sofa-claude-ops`), not a personal
  access token. Its private key lives outside any repository, mode 600,
  and is never read, printed, copied, or transmitted — presence checks
  only. Registering the App, generating its key, and installing it on an
  account remain Steve's ceremonies, forbidden to Claude like every other
  credential-granting flow.
- **Least privilege is the only mint path.** Every token names the
  repositories it touches and the permissions it needs, and carries
  nothing else. `seed/scripts/gh_token.py` is the single sanctioned way to
  obtain one; it refuses to mint without both. There is no unscoped path,
  by construction rather than by convention.
- **Elevation is deliberate, bounded, and announced.** `administration`
  and `organization_administration` are requested only by bootstrap's two
  call sites — repo creation, and setting a default branch or applying a
  ruleset — never by ongoing work. Requesting either requires a stated
  reason, echoed to stderr so a transcript shows every elevation.
- **No standing token.** Tokens are minted per operation, expire within
  the hour, and are passed to a single child process. None is written to
  disk, exported into a shell, or left in `GH_TOKEN` between commands.
- **Deletion has no call site.** GitHub bundles repository deletion into
  `administration` and does not let us split it off, so an admin-bearing
  token can delete the repositories in its scope. That reach is bounded by
  scoping: wiring tokens name the single repo being wired, and creation
  tokens — which cannot be scoped to nothing, as an empty list silently
  means all — name the throwaway scratch repo. A real workload repo is
  never inside an admin-bearing token's scope once its bootstrap ends.
- **The widening is recorded, not glossed.** Steve granted the App
  organization-level Administration on `warblersafety` (2026-08-20),
  moving its ceiling from per-repo to org-wide: within that org the App
  can in principle delete repositories and change membership. Nothing in
  the process invokes either, and scoped minting is the compensating
  control that keeps the working credential far below that ceiling. The
  ceiling is real and this grant names it rather than relying on it going
  unnoticed.
- Grant 1 is unchanged and still dormant: nothing here creates a daemon,
  timer, or self-refreshing process. Token minting happens on demand
  inside active work. Tokens minted inside GitHub Actions come from
  `actions/create-github-app-token` and repo secrets, authorized by
  Steve's merge of the workflow file, per Grant 1.
- Revoking works in reverse: Steve uninstalls the App or reverts this
  grant on `main`.
