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

**Dormant until its rails exist as merged code.** Supersedes the
fine-grained PAT as the process's GitHub credential once active; until
then the PAT rules stand and this grant is inert.

- **Preconditions:** `seed/scripts/gh_token.py` is actually the credential
  path — `merge_dev.py`, the seed workflows, and the `bootstrap` skill
  obtain tokens through it and no ambient `GH_TOKEN` remains (sofa-claude
  Issues #22, #23). Until those PRs merge, a declared credential no code
  calls is prose, not a rail (decisions/0003), and merging this grant
  alone would raise the App's ceiling before the control that answers it
  is load-bearing.

- The GitHub surface is a GitHub App (`sofa-claude-ops`), not a personal
  access token. Its private key lives outside any repository, mode 600,
  and is never read, printed, copied, or transmitted — presence checks
  only. Registering the App, generating its key, and installing it on an
  account remain Steve's ceremonies, forbidden to Claude like every other
  credential-granting flow.

- **Least privilege is the sanctioned mint path.** Every token names the
  repositories it touches and the permissions it needs, and carries
  nothing else. `seed/scripts/gh_token.py` refuses to mint without both.
  This is a paved path, not a wall: the capability is the private key, and
  anything holding the key can sign a JWT and request everything the
  installation allows. The helper constrains the process's own conduct —
  it is not a boundary an actor outside the process is held by, and this
  grant does not pretend otherwise (decisions/0001).

- **What scoping does and does not bound.** A token's `repositories` list
  bounds **repository-level** permissions only. **Organization-level**
  permissions — `organization_administration`, `members`,
  `organization_secrets` — are installation-wide and ignore that list
  entirely, as verified against the API on 2026-08-20: a token scoped to
  one throwaway repo performed an org-level repository creation. Any mint
  including an org-level permission is org-wide for its lifetime. No
  scoping arrangement changes this.

- **Elevation is confined by interface, not by scope.** Because org-level
  permission cannot be bounded, it is not offered as a permission a caller
  may request. `gh_token.py` exposes exactly one operation that uses it —
  repository creation — which mints, acts, and discards internally; the
  command line refuses org-level permissions outright. There is no way,
  within the process, to obtain a reusable org-admin token. This is
  containment of the interface, not of the credential.

- **Every elevation is recorded durably.** Requesting an elevated
  permission requires a stated reason and appends an audit record —
  timestamp, account, repositories, permissions, reason, never the token —
  to the elevation log. A stderr line is not a record: under Grant 1 no
  one is watching the terminal, and an announcement no one can read later
  is not a control.

- **No standing token.** Tokens are minted per operation, expire within
  the hour, and are passed to a single child process. None is written to
  disk, exported into a shell, or left in `GH_TOKEN` between commands.
  The helper offers no way to print a token to stdout, because in this
  environment stdout is captured into a session transcript on disk and
  into model context, where it outlives the command that needed it.

- **The elevated permission carries more than deletion.** Repository
  `administration` is what applies a ruleset — and therefore what can
  remove one. The human-only merge gate on `staging` and `main` is
  platform config sitting inside the same permission bootstrap needs to
  create it, so a wiring token can strip the gate, after which an ordinary
  `contents` token merges to `main` without breaching any rule stated
  here. Bootstrap therefore verifies protection by behaviour — attempting
  a write and requiring the refusal — never by trusting a success code
  (Issue #23). GitHub bundles repository deletion into the same
  permission and does not let us split it off.

- **The widening is recorded, not glossed.** Steve granted the App
  organization-level Administration on `warblersafety` (2026-08-20),
  moving its ceiling from per-repo to org-wide: within that org the App
  can in principle delete repositories, change settings, and change
  membership. Repository deletion was already reachable before that grant,
  since rulesets require repository `administration`; what the org-level
  grant adds is repository creation, org settings, and membership. Steve
  accepted this knowingly on 2026-08-20 after the scoping claim above was
  corrected. The controls are confinement to one interface, a durable
  audit record, and behavioural verification of protection — discipline
  and detection, not containment. Naming that plainly is the point of
  this bullet.

- Grant 1 is unchanged and still dormant: nothing here creates a daemon,
  timer, or self-refreshing process. Token minting happens on demand
  inside active work. Tokens minted inside GitHub Actions come from
  `actions/create-github-app-token` and repo secrets, authorized by
  Steve's merge of the workflow file, per Grant 1.

- Revoking works in reverse: Steve uninstalls the App, removes a
  permission from it, or reverts this grant on `main`.
