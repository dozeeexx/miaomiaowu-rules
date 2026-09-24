"""Offline regressions for the scheduled Provider health checker."""
from __future__ import annotations

import importlib.util
from pathlib import Path
import unittest
import contextlib
import io
from unittest.mock import MagicMock, patch
import urllib.error


class ProviderPayloadTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = Path(__file__).resolve().parents[1] / "scripts/check_providers.py"
        assert path.exists(), "scheduled Provider checker is not implemented"
        spec = importlib.util.spec_from_file_location("check_providers", path)
        assert spec is not None and spec.loader is not None
        global health
        health = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(health)

    def test_unspecified_format_uses_mihomo_yaml_default(self):
        self.assertEqual(health.validate_payload("sample", {}, b"payload: [example.com]"), [])
        self.assertTrue(health.validate_payload("sample", {}, b"DOMAIN,example.com"))

    def test_mrs_requires_the_zstandard_magic(self):
        provider = {"format": "mrs"}
        self.assertEqual(health.validate_payload("google-play", provider, b"\x28\xb5\x2f\xfddata"), [])
        errors = health.validate_payload("google-play", provider, b"not-mrs")
        self.assertTrue(any("MRS magic" in error for error in errors))

    def test_yaml_requires_a_nonempty_payload(self):
        provider = {"format": "yaml"}
        self.assertEqual(
            health.validate_payload("android", provider, b"payload:\n- PROCESS-NAME,com.example.app\n"),
            [],
        )
        errors = health.validate_payload("android", provider, b"payload: []\n")
        self.assertTrue(any("non-empty payload" in error for error in errors))

    def test_comment_only_text_provider_is_reported_as_placeholder_not_failure(self):
        provider = {"format": "text", "behavior": "classical", "url":
                    "https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list"}
        self.assertEqual(health.validate_payload("Dozee_Custom_Proxy", provider, b"# reserved\n"), [])
        self.assertTrue(health.validate_payload("Dozee_Crypto_Custom", provider, b"# vanished\n"))
        self.assertEqual(health.payload_state(provider, b"# reserved\n"), "placeholder")
        self.assertEqual(health.payload_state(provider, b"DOMAIN-SUFFIX,example.com\n"), "active")

    def test_http_200_error_pages_and_malformed_yaml_rows_are_rejected(self):
        for payload in (b"<html>Service unavailable</html>", b"{\"error\": \"not found\"}", b"   "):
            self.assertTrue(health.validate_payload("crypto", {"format": "text"}, payload))
        for payload in (b"payload: [null]", b"payload: [123]", b"payload: ['']"):
            self.assertTrue(health.validate_payload("apps", {"format": "yaml"}, payload))
        self.assertTrue(health.validate_payload("mrs", {"format": "mrs"}, b"\x28\xb5\x2f\xfd"))

    def test_same_url_cannot_hide_conflicting_format_or_behavior(self):
        for field, value in (("format", "yaml"), ("behavior", "ipcidr")):
            first = {"url": "https://example.invalid/list", "format": "mrs", "behavior": "domain"}
            second = dict(first, **{field: value})
            configs = [{"rule-providers": {"one": first}}, {"rule-providers": {"two": second}}]
            with self.subTest(field=field), self.assertRaises(ValueError):
                list(health.iter_unique_providers(configs))

    def test_empty_templates_fail_instead_of_reporting_zero_success(self):
        with self.assertRaises(ValueError):
            list(health.iter_unique_providers([{}]))

    def test_unique_providers_are_deduplicated_by_url(self):
        configs = [
            {"rule-providers": {"one": {"url": "https://example.invalid/rules.mrs", "format": "mrs"}}},
            {"rule-providers": {"two": {"url": "https://example.invalid/rules.mrs", "format": "mrs"}}},
        ]
        unique = list(health.iter_unique_providers(configs))
        self.assertEqual(len(unique), 1)
        self.assertEqual(unique[0][0], "one / two")

    def test_fetch_uses_full_get_and_requires_https(self):
        response = MagicMock()
        response.status = 200
        response.read.return_value = b"entire-body"
        response.geturl.return_value = "https://example.invalid/list"
        response.__enter__.return_value = response
        with patch.object(health.urllib.request, "urlopen", return_value=response) as opener:
            self.assertEqual(health.fetch("https://example.invalid/list"), (200, b"entire-body"))
            request = opener.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertNotIn("Range", request.headers)
            response.read.assert_called_once_with()
            for url in ("http://example.invalid/list", "https://user:password@example.invalid/list"):
                with self.subTest(url_type=url.split(":")[0]), self.assertRaises(ValueError):
                    health.fetch(url)

    def test_main_fails_on_http_206_and_redacts_fetch_exception(self):
        provider = {"url": "https://example.invalid/list?test=canary-value", "format": "mrs"}
        configs = [{"rule-providers": {"sample": provider}}]
        for result in ((206, b"\x28\xb5\x2f\xfddata"), urllib.error.URLError("canary-value")):
            with patch.object(health, "load_configs", return_value=configs), \
                 patch.object(health, "fetch", return_value=result,
                              side_effect=result if isinstance(result, Exception) else None), patch("sys.argv", ["checker"]), \
                 contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()) as err:
                self.assertEqual(health.main(), 1)
                self.assertIn("sample", err.getvalue())
                self.assertNotIn("canary-value", err.getvalue())
