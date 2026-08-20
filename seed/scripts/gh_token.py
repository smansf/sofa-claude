#!/usr/bin/env python3
"""Mint a short-lived, least-privilege GitHub App installation token.

Every GitHub credential this process uses comes from here. There is no
unscoped path: callers name the repositories and the permissions, and get
a token that carries those and nothing else. The App's ceiling stays high;
the working credential sits far below it (governance/grants.md, Grant 4).

Elevated permissions -- `administration` (which GitHub bundles repository
deletion into) and `organization_administration` -- additionally require a
stated reason, which is echoed to stderr. Elevation is meant to be rare,
deliberate, and visible in a transcript, not ambient.

Prefer `--exec`, which sets GH_TOKEN for one child process only, so the
token never reaches stdout, a log, or a shell variable that outlives the
command. `--print` exists for callers that genuinely cannot use `--exec`.

Configuration (no value is ever hardcoded):
    SOFA_APP_ID    the App's numeric ID
    SOFA_APP_KEY   path to its PEM private key (default ~/.config/sofa-claude/app.pem)

Usage:
    gh_token.py --account ORG --repos a,b --perm contents=write -- gh pr list
    gh_token.py --account ORG --repos a --perm administration=write \
                --reason "bootstrap: apply protect-main ruleset" -- ...
"""

import argparse
import base64
import json
import os
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

API = "https://api.github.com"
DEFAULT_KEY = "~/.config/sofa-claude/app.pem"
# GitHub bundles repository deletion into `administration`; it cannot be
# split off. Requesting either of these must therefore be deliberate.
ELEVATED = ("administration", "organization_administration")


class TokenError(RuntimeError):
    """Raised with an actionable message; never carries a credential."""


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b"=")


def app_jwt(app_id, key_path, now=None):
    """Sign a ~9-minute JWT with the App's private key, via openssl."""
    path = pathlib.Path(os.path.expanduser(key_path))
    if not path.exists():
        raise TokenError(
            f"App private key not found at {path}. Set SOFA_APP_KEY, or place "
            f"the key there with mode 600. Generating or moving keys is "
            f"Steve's ceremony -- do not create one to get past this.")
    if not os.access(path, os.R_OK):
        raise TokenError(f"App private key at {path} exists but is unreadable.")
    now = int(time.time() if now is None else now)
    header = _b64(json.dumps({"alg": "RS256", "typ": "JWT"}).encode())
    payload = _b64(json.dumps(
        {"iat": now - 60, "exp": now + 540, "iss": str(app_id)}).encode())
    signing_input = header + b"." + payload
    try:
        proc = subprocess.run(["openssl", "dgst", "-sha256", "-sign", str(path)],
                              input=signing_input, capture_output=True)
    except FileNotFoundError:
        raise TokenError("openssl not found on PATH; cannot sign the App JWT.")
    if proc.returncode != 0:
        raise TokenError(
            f"Signing the App JWT with {path} failed -- is it a valid RSA "
            f"private key? openssl: {proc.stderr.decode().strip()[:200]}")
    return (signing_input + b"." + _b64(proc.stdout)).decode()


def api(path, bearer, method="GET", payload=None):
    request = urllib.request.Request(
        API + path, method=method,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"Authorization": "Bearer " + bearer,
                 "Accept": "application/vnd.github+json",
                 "X-GitHub-Api-Version": "2022-11-28",
                 "User-Agent": "sofa-claude"})
    try:
        with urllib.request.urlopen(request) as response:
            return json.load(response)
    except urllib.error.HTTPError as err:
        detail = ""
        try:
            detail = json.loads(err.read()).get("message", "")
        except Exception:
            pass
        raise TokenError(f"GitHub {err.code} on {method} {path}: {detail}")


def installation_id(account, jwt):
    """The App's installation on `account` (an org or user login)."""
    for inst in api("/app/installations", jwt):
        if ((inst.get("account") or {}).get("login") or "").lower() == account.lower():
            return inst["id"]
    raise TokenError(
        f"The App has no installation on {account!r}. Install it there first "
        f"-- installing an App is Steve's step, not Claude's.")


def mint(account, repositories, permissions, reason=None,
         app_id=None, key_path=None):
    """Return a short-lived token carrying exactly `permissions` on `repositories`.

    `repositories` and `permissions` are required and must be non-empty:
    there is deliberately no way to ask this function for everything the
    installation can do.
    """
    if not repositories:
        raise TokenError(
            "Refusing to mint: no repositories named. Least privilege is the "
            "only path -- name the repositories this task actually touches.")
    if not permissions:
        raise TokenError(
            "Refusing to mint: no permissions named. Least privilege is the "
            "only path -- name the permissions this task actually needs.")
    elevated = sorted(p for p in permissions if p in ELEVATED)
    if elevated and not (reason or "").strip():
        raise TokenError(
            f"Refusing to mint {', '.join(elevated)} without a stated reason. "
            f"These carry repository deletion, which GitHub does not let us "
            f"split off. Pass --reason naming the single call this is for.")
    app_id = app_id or os.environ.get("SOFA_APP_ID")
    if not app_id:
        raise TokenError("SOFA_APP_ID is not set; it is the App's numeric ID.")
    key_path = key_path or os.environ.get("SOFA_APP_KEY") or DEFAULT_KEY
    if elevated:
        print(f"[gh_token] elevated ({', '.join(elevated)}) on "
              f"{account}/{{{','.join(repositories)}}}: {reason.strip()}",
              file=sys.stderr)
    jwt = app_jwt(app_id, key_path)
    result = api(f"/app/installations/{installation_id(account, jwt)}/access_tokens",
                 jwt, "POST",
                 {"repositories": list(repositories), "permissions": dict(permissions)})
    return result["token"], result.get("expires_at")


def _permission(arg):
    if "=" not in arg:
        raise argparse.ArgumentTypeError(
            f"--perm expects name=level, e.g. contents=write (got {arg!r})")
    name, _, level = arg.partition("=")
    return name.strip(), level.strip()


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Mint a scoped, short-lived GitHub App token.")
    parser.add_argument("--account", required=True,
                        help="org or user login the App is installed on")
    parser.add_argument("--repos", required=True,
                        help="comma-separated repository names (not full names)")
    parser.add_argument("--perm", required=True, action="append", type=_permission,
                        metavar="NAME=LEVEL", help="repeatable; e.g. contents=write")
    parser.add_argument("--reason", help="required for elevated permissions")
    parser.add_argument("--print", dest="print_token", action="store_true",
                        help="print the token to stdout (prefer -- CMD instead)")
    parser.add_argument("command", nargs=argparse.REMAINDER,
                        help="-- CMD ARGS: run CMD with GH_TOKEN set, token never printed")
    args = parser.parse_args(argv)

    command = [a for a in args.command if a != "--"]
    if not command and not args.print_token:
        parser.error("give a command after -- , or pass --print if you truly "
                     "need the token itself")
    try:
        token, expires = mint(args.account,
                              [r.strip() for r in args.repos.split(",") if r.strip()],
                              dict(args.perm), args.reason)
    except TokenError as err:
        print(f"CREDENTIAL FAILURE -- nothing was minted.\n{err}", file=sys.stderr)
        return 2
    if command:
        env = dict(os.environ, GH_TOKEN=token, GITHUB_TOKEN=token)
        return subprocess.run(command, env=env).returncode
    print(f"[gh_token] expires {expires}", file=sys.stderr)
    print(token)
    return 0


if __name__ == "__main__":
    sys.exit(main())
