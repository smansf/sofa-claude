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
        if path == "/app/installations":
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
    def test_elevated_permission_requires_a_reason(self):
        for name in gh_token.ELEVATED:
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


class NoStandingExecutionTests(unittest.TestCase):
    def test_helper_starts_no_daemon_or_timer(self):
        """Grant 1 is dormant: nothing here may begin work on its own."""
        source = _path.read_text()
        for forbidden in ("threading", "sched", "daemon", "launchd",
                          "crontab", "LaunchAgent", "while True"):
            self.assertNotIn(forbidden, source)

    def test_no_deletion_call_site(self):
        source = _path.read_text()
        self.assertNotIn('"DELETE"', source)
        self.assertNotIn("'DELETE'", source)


if __name__ == "__main__":
    unittest.main()
