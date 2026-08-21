"""Tests for the seed kit's least-privilege App token helper.

The invariant under test is structural, not stylistic: there must be no
way to obtain a token carrying more than the caller named, and elevated
permissions must be impossible to request silently.
"""

import importlib.util
import io
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

_path = pathlib.Path(__file__).resolve().parent.parent / "seed" / "scripts" / "gh_token.py"
_spec = importlib.util.spec_from_file_location("gh_token", _path)
gh_token = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gh_token)


def _mint(*args, **kwargs):
    """Call mint() with the network stubbed; return (token, captured_body)."""
    captured = {}

    def fake_api(path, bearer, method="GET", payload=None):
        if path.startswith("/app/installations?"):
            return [{"id": 42, "account": {"login": "warblersafety"}}]
        captured["path"] = path
        captured["payload"] = payload
        return {"token": "ghs_stub", "expires_at": "2026-08-21T00:00:00Z"}

    with mock.patch.object(gh_token, "api", fake_api), \
         mock.patch.object(gh_token, "app_jwt", lambda *a, **k: "jwt-stub"):
        result = gh_token.mint(*args, app_id="1", key_path="/dev/null", **kwargs)
    return result, captured


class ScopingTests(unittest.TestCase):
    def test_token_requests_exactly_what_was_named(self):
        (token, _), captured = _mint(
            "warblersafety", ["scratch"], {"contents": "write"})
        self.assertEqual(token, "ghs_stub")
        self.assertEqual(captured["payload"]["repositories"], ["scratch"])
        self.assertEqual(captured["payload"]["permissions"], {"contents": "write"})

    def test_nothing_extra_is_added_to_the_request(self):
        _, captured = _mint("warblersafety", ["scratch"],
                            {"contents": "write", "issues": "write"})
        self.assertEqual(set(captured["payload"]), {"repositories", "permissions"})
        for elevated in gh_token.ELEVATED:
            self.assertNotIn(elevated, captured["payload"]["permissions"])

    def test_empty_repositories_is_refused(self):
        with self.assertRaises(gh_token.TokenError) as caught:
            _mint("warblersafety", [], {"contents": "write"})
        self.assertIn("no repositories", str(caught.exception).lower())

    def test_empty_permissions_is_refused(self):
        with self.assertRaises(gh_token.TokenError) as caught:
            _mint("warblersafety", ["scratch"], {})
        self.assertIn("no permissions", str(caught.exception).lower())

    def test_no_public_entry_point_mints_unscoped(self):
        """mint() is the only way in, and both scoping args are required."""
        import inspect
        signature = inspect.signature(gh_token.mint)
        for required in ("repositories", "permissions"):
            self.assertIs(signature.parameters[required].default,
                          inspect.Parameter.empty,
                          f"{required} must have no default -- a default is an "
                          f"unscoped path by another name")


class ElevationTests(unittest.TestCase):
    def test_read_level_needs_no_reason(self):
        """`actions=read` is what an ordinary CI check needs."""
        self.assertEqual(gh_token.elevated_permissions({"actions": "read"}), [])
        self.assertEqual(gh_token.elevated_permissions({"administration": "read"}), [])
        (token, _), _ = _mint("warblersafety", ["scratch"],
                              {"actions": "read", "checks": "read"})
        self.assertEqual(token, "ghs_stub")

    def test_read_level_is_still_recorded(self):
        """Narrowing the audit trail would narrow the detection control."""
        self.assertEqual(gh_token.recorded_permissions({"actions": "read"}),
                         ["actions"])
        self.assertEqual(gh_token.recorded_permissions({"contents": "write"}), [])

    def test_unknown_level_counts_as_a_write(self):
        """Deny-by-default: only the exact string `read` is not elevation."""
        for level in ("write", "admin", True, "WRITE", "true", "", None, "rw"):
            with self.subTest(level=level):
                self.assertEqual(
                    gh_token.elevated_permissions({"administration": level}),
                    ["administration"])

    def test_read_is_matched_case_and_space_insensitively(self):
        for level in ("read", "READ", " read "):
            with self.subTest(level=level):
                self.assertEqual(
                    gh_token.elevated_permissions({"actions": level}), [])

    def test_elevated_permission_requires_a_reason(self):
        repo_level = [p for p in gh_token.ELEVATED if p not in gh_token.ORG_LEVEL]
        self.assertTrue(repo_level, "the repo-level elevated set must not be empty")
        for name in repo_level:
            with self.subTest(permission=name):
                with self.assertRaises(gh_token.TokenError) as caught:
                    _mint("warblersafety", ["scratch"], {name: "write"})
                self.assertIn("reason", str(caught.exception).lower())

    def test_blank_reason_does_not_count(self):
        with self.assertRaises(gh_token.TokenError):
            _mint("warblersafety", ["scratch"], {"administration": "write"},
                  reason="   ")

    def test_elevated_with_reason_is_announced_on_stderr(self):
        stderr = io.StringIO()
        with mock.patch.object(sys, "stderr", stderr):
            (token, _), captured = _mint(
                "warblersafety", ["scratch"], {"administration": "write"},
                reason="bootstrap: apply protect-main ruleset")
        self.assertEqual(token, "ghs_stub")
        self.assertIn("elevated", stderr.getvalue())
        self.assertIn("apply protect-main ruleset", stderr.getvalue())
        self.assertNotIn(token, stderr.getvalue(),
                         "the announcement must never carry the credential")


class TransportTests(unittest.TestCase):
    """Network failures must surface as TokenError, never as a traceback."""

    def test_unreachable_github_becomes_a_token_error(self):
        import urllib.error
        with mock.patch.object(gh_token.urllib.request, "urlopen",
                               side_effect=urllib.error.URLError("offline")):
            with self.assertRaises(gh_token.TokenError) as caught:
                gh_token.api("/app", "jwt-stub")
        self.assertIn("Cannot reach GitHub", str(caught.exception))

    def test_unparseable_response_becomes_a_token_error(self):
        class FakeResponse:
            def read(self): return b"<html>not json</html>"
            def __enter__(self): return self
            def __exit__(self, *a): return False
        with mock.patch.object(gh_token.urllib.request, "urlopen",
                               return_value=FakeResponse()):
            with self.assertRaises(gh_token.TokenError) as caught:
                gh_token.api("/app", "jwt-stub")
        self.assertIn("Unparseable response", str(caught.exception))


class ConfigurationTests(unittest.TestCase):
    def test_missing_key_fails_with_an_actionable_message(self):
        with self.assertRaises(gh_token.TokenError) as caught:
            gh_token.app_jwt("1", "/nonexistent/path/app.pem")
        message = str(caught.exception)
        self.assertIn("SOFA_APP_KEY", message)
        self.assertIn("Steve's ceremony", message)

    def test_missing_app_id_fails_cleanly(self):
        with mock.patch.dict(os.environ, {}, clear=True), \
             self.assertRaises(gh_token.TokenError) as caught:
            gh_token.mint("warblersafety", ["scratch"], {"contents": "write"})
        self.assertIn("SOFA_APP_ID", str(caught.exception))

    def test_unknown_account_names_the_fix(self):
        with mock.patch.object(gh_token, "api",
                               lambda *a, **k: [{"id": 1, "account": {"login": "other"}}]):
            with self.assertRaises(gh_token.TokenError) as caught:
                gh_token.installation_id("warblersafety", "jwt-stub")
        self.assertIn("no installation", str(caught.exception).lower())

    def test_id_is_never_hardcoded(self):
        source = _path.read_text()
        self.assertNotIn("4665307", source,
                         "the App ID is configuration, not source")


class OrgLevelTests(unittest.TestCase):
    """Org-level permissions are installation-wide; the repo list is no bound."""

    def test_org_level_permission_is_refused_by_mint(self):
        for name in gh_token.ORG_LEVEL:
            with self.subTest(permission=name):
                with self.assertRaises(gh_token.TokenError) as caught:
                    _mint("warblersafety", ["scratch"], {name: "write"},
                          reason="a reason is not enough for org-level")
                self.assertIn("installation-wide", str(caught.exception))

    def test_cli_cannot_request_org_level(self):
        with mock.patch.object(sys, "stderr", io.StringIO()):
            code = gh_token.main(["--account", "warblersafety", "--repos", "scratch",
                                  "--perm", "organization_administration=write",
                                  "--reason", "trying it on", "--", "true"])
        self.assertEqual(code, 2)

    def _create(self, **over):
        seen = {}

        def fake_mint(account, repositories, permissions, **kwargs):
            seen["repositories"] = repositories
            seen["permissions"] = permissions
            seen["allow"] = kwargs.get("_allow_org_level")
            return "ghs_secret", "2026-08-21T00:00:00Z"

        kwargs = dict(reason="bootstrap", scope_repo="scratch")
        kwargs.update(over)
        with mock.patch.object(gh_token, "mint", fake_mint), \
             mock.patch.object(gh_token, "api", lambda *a, **k: {"full_name": "o/r"}):
            result = gh_token.create_repo("warblersafety", "wilson", **kwargs)
        return result, seen

    def test_create_repo_scopes_to_an_existing_repo_not_the_new_one(self):
        """The repo being created does not exist yet; GitHub 422s on it."""
        _, seen = self._create()
        self.assertEqual(seen["repositories"], ["scratch"])
        self.assertNotIn("wilson", seen["repositories"])

    def test_create_repo_does_not_return_the_token(self):
        result, seen = self._create()
        self.assertEqual(result, {"full_name": "o/r"})
        self.assertNotIn("ghs_secret", json.dumps(result))
        self.assertTrue(seen["allow"])
        self.assertEqual(set(seen["permissions"]),
                         {"organization_administration", "administration"})

    def test_create_repo_requires_a_reason(self):
        with self.assertRaises(gh_token.TokenError):
            self._create(reason="")

    def test_create_repo_refuses_to_scope_to_the_repo_being_created(self):
        with self.assertRaises(gh_token.TokenError) as caught:
            self._create(scope_repo="wilson")
        self.assertIn("does not exist yet", str(caught.exception))

    def test_create_repo_refuses_an_empty_scope(self):
        with self.assertRaises(gh_token.TokenError):
            self._create(scope_repo="")


class AuditTests(unittest.TestCase):
    def test_elevation_is_written_to_a_durable_record(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "nested" / "elevations.log"
            gh_token.record_elevation("warblersafety", ["scratch"],
                                      {"administration": "write"},
                                      "bootstrap: apply protect-main",
                                      audit_path=str(log))
            entry = json.loads(log.read_text().strip())
        self.assertEqual(entry["repositories"], ["scratch"])
        self.assertEqual(entry["reason"], "bootstrap: apply protect-main")
        self.assertEqual(entry["event"], "requested")
        self.assertIn("at", entry)

    def test_record_never_contains_a_token(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "elevations.log"
            gh_token.record_elevation("o", ["r"], {"administration": "write"},
                                      "why", audit_path=str(log))
            self.assertNotIn("ghs_", log.read_text())
            self.assertNotIn("token", log.read_text())

    def test_unwritable_audit_log_fails_closed(self):
        """No record, no elevation -- the mint must not proceed."""
        with tempfile.TemporaryDirectory() as tmp:
            blocker = pathlib.Path(tmp) / "blocked"
            blocker.write_text("not a directory")
            with self.assertRaises(gh_token.TokenError) as caught:
                gh_token.record_elevation("o", ["r"], {"administration": "write"},
                                          "why", audit_path=str(blocker / "log"))
        self.assertIn("could not be recorded", str(caught.exception))


class NoCredentialLeakTests(unittest.TestCase):
    def test_there_is_no_way_to_print_a_token(self):
        """stdout lands in a transcript on disk; the tool must not offer it."""
        source = _path.read_text()
        self.assertNotIn("--print", source)
        with mock.patch.object(sys, "stderr", io.StringIO()), \
             self.assertRaises(SystemExit):
            gh_token.main(["--account", "o", "--repos", "r",
                           "--perm", "contents=write"])

    def test_command_runs_with_token_in_env_not_argv(self):
        captured = {}

        def fake_run(command, env=None):
            captured["command"] = command
            captured["env"] = env
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(gh_token, "mint",
                               lambda *a, **k: ("ghs_secret", "later")), \
             mock.patch.object(gh_token.subprocess, "run", fake_run):
            gh_token.main(["--account", "o", "--repos", "r",
                           "--perm", "contents=write", "--", "gh", "pr", "list"])
        self.assertEqual(captured["command"], ["gh", "pr", "list"])
        self.assertEqual(captured["env"]["GH_TOKEN"], "ghs_secret")
        self.assertNotIn("ghs_secret", " ".join(captured["command"]))


class ArgumentTests(unittest.TestCase):
    def test_only_the_leading_separator_is_stripped(self):
        """`--` inside the child command is the child's, not argparse's."""
        captured = {}

        def fake_run(command, env=None):
            captured["command"] = command
            return subprocess.CompletedProcess(command, 0)

        with mock.patch.object(gh_token, "mint",
                               lambda *a, **k: ("ghs_secret", "later")), \
             mock.patch.object(gh_token.subprocess, "run", fake_run):
            gh_token.main(["--account", "o", "--repos", "r", "--perm",
                           "contents=write", "--",
                           "git", "diff", "main", "--", "seed/"])
        self.assertEqual(captured["command"],
                         ["git", "diff", "main", "--", "seed/"])


class ElevationRecordPairingTests(unittest.TestCase):
    def test_a_failed_mint_leaves_only_a_request(self):
        """A `requested` with no `granted` means access was never obtained."""
        with tempfile.TemporaryDirectory() as tmp:
            log = pathlib.Path(tmp) / "elevations.log"
            with mock.patch.dict(os.environ, {"SOFA_AUDIT_LOG": str(log),
                                              "SOFA_APP_ID": "1"}), \
                 mock.patch.object(sys, "stderr", io.StringIO()), \
                 mock.patch.object(gh_token, "app_jwt",
                                   mock.Mock(side_effect=gh_token.TokenError("no key"))):
                with self.assertRaises(gh_token.TokenError):
                    gh_token.mint("o", ["r"], {"administration": "write"},
                                  reason="wiring")
            events = [json.loads(line)["event"]
                      for line in log.read_text().splitlines()]
        self.assertEqual(events, ["requested"])


class NoStandingExecutionTests(unittest.TestCase):
    def test_helper_imports_nothing_that_can_schedule_work(self):
        """Grant 1 is dormant: nothing here may begin work on its own.

        Tests the module's imports rather than its source text -- a loop
        that pages an API is not a timer, and a spelling check cannot tell
        the difference.
        """
        imported = {name.split(".")[0]
                    for name in dir(gh_token)
                    if isinstance(getattr(gh_token, name, None), type(os))}
        for scheduler in ("threading", "sched", "asyncio", "signal",
                          "multiprocessing"):
            self.assertNotIn(scheduler, imported)

    def test_subprocess_is_only_used_to_sign_and_to_run_the_child(self):
        """The only processes started are openssl and the caller's command."""
        import inspect
        calls = [line.strip() for line in inspect.getsource(gh_token).splitlines()
                 if "subprocess.run(" in line]
        self.assertEqual(len(calls), 2, calls)


if __name__ == "__main__":
    unittest.main()
