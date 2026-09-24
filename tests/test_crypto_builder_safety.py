"""Offline regressions for curated-source filtering and sync safety."""
from __future__ import annotations

import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

GOOD_STATS = {
    "metacubex_reference_rules": 235, "blackmatrix7_crypto_rules": 204,
    "supplement_sources": 6, "supplement_candidates_before_filter": 710,
    "custom_selected_rules": 85,
    "source_v2fly_category_cryptocurrency": 235,
    "source_blackmatrix7_cryptocurrency": 43,
    "source_blackmatrix7_binance": 12, "source_blackmatrix7_okx": 3,
    "source_enriquephl_web3": 312, "source_dozee_manual": 105,
}

from scripts import build_crypto_custom as builder
from scripts import validate as validator


class DomainFilterTests(unittest.TestCase):
    def test_unrelated_domain_fragments_are_not_excluded(self):
        for domain in ("bitmex.com", "notx.com", "x.com.example", "notgithub.com",
                       "notgoogle.com", "notdiscord.com", "notforter.com",
                       "notpredict.fun", "myqcloud.com.example"):
            with self.subTest(domain=domain):
                self.assertTrue(builder.is_publishable("DOMAIN-SUFFIX," + domain))

    def test_real_roots_and_subdomains_remain_excluded(self):
        for domain in ("x.com", "api.x.com", "github.com", "api.github.com",
                       "google.cn", "accounts.google.com", "discord.com",
                       "predict.fun", "api.predict.fun", "cdn.cloudfront.net",
                       "api.forter.com", "api.myqcloud.com"):
            with self.subTest(domain=domain):
                self.assertFalse(builder.is_publishable("DOMAIN-SUFFIX," + domain))

    def test_intentional_brand_tokens_and_keyword_allowlist_stay_scoped(self):
        for rule in ("DOMAIN-SUFFIX,polymarket-api.example", "DOMAIN-SUFFIX,kalshi-cdn.example",
                     "DOMAIN-SUFFIX,appsflyer-mobile.example", "DOMAIN-KEYWORD,crypto"):
            with self.subTest(rule=rule):
                self.assertFalse(builder.is_publishable(rule))
        self.assertTrue(builder.is_publishable("DOMAIN-KEYWORD,bitget"))
        self.assertFalse(builder.is_publishable("PROCESS-NAME,com.example.wallet"))


class ValidatorBoundaryTests(unittest.TestCase):
    def test_validator_accepts_unrelated_domain_fragments(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "crypto.list"
            path.write_text("DOMAIN-SUFFIX,krakenfx.com\nDOMAIN-SUFFIX,bitmex.com\n"
                            "DOMAIN-SUFFIX,notgithub.com\nDOMAIN-SUFFIX,notgoogle.com\n")
            with contextlib.redirect_stderr(io.StringIO()):
                try:
                    validator.validate_rule_file(path, crypto_custom=True)
                except SystemExit:
                    self.fail("validator still mistakes a domain fragment for a suffix")

    def test_validator_keeps_rejecting_real_excluded_domains(self):
        for domain in ("x.com", "api.x.com", "github.com", "api.google.cn", "predict.fun", "kalshi.com"):
            with self.subTest(domain=domain), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "crypto.list"
                path.write_text("DOMAIN-SUFFIX," + domain + "\n")
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    validator.validate_rule_file(path, crypto_custom=True)


class SyncGuardTests(unittest.TestCase):
    def setUp(self):
        self.assertTrue(callable(getattr(builder, "guardrail_errors", None)),
                        "source/output guardrail is not implemented")

    def test_guardrail_accepts_current_source_and_output_baseline(self):
        stats = {
            "metacubex_reference_rules": 235,
            "blackmatrix7_crypto_rules": 204,
            "custom_selected_rules": 85,
            "source_v2fly_category_cryptocurrency": 235,
            "source_blackmatrix7_cryptocurrency": 43,
            "source_blackmatrix7_binance": 12,
            "source_blackmatrix7_okx": 3,
            "source_enriquephl_web3": 312,
            "source_dozee_manual": 105,
        }
        self.assertEqual(builder.guardrail_errors(stats, stats), [])

    def test_guardrail_rejects_empty_source_and_catastrophic_output_drop(self):
        previous = {
            "metacubex_reference_rules": 235,
            "blackmatrix7_crypto_rules": 204,
            "custom_selected_rules": 85,
            "source_v2fly_category_cryptocurrency": 235,
            "source_blackmatrix7_cryptocurrency": 43,
            "source_blackmatrix7_binance": 12,
            "source_blackmatrix7_okx": 3,
            "source_enriquephl_web3": 312,
            "source_dozee_manual": 105,
        }
        current = dict(previous)
        current["source_v2fly_category_cryptocurrency"] = 0
        current["custom_selected_rules"] = 40
        errors = builder.guardrail_errors(current, previous)
        self.assertTrue(any("source_v2fly_category_cryptocurrency" in error for error in errors))
        self.assertTrue(any("custom_selected_rules" in error for error in errors))

    def test_guardrail_allows_first_run_without_previous_rendered_stats(self):
        stats = {
            "metacubex_reference_rules": 235,
            "blackmatrix7_crypto_rules": 204,
            "custom_selected_rules": 85,
            "source_v2fly_category_cryptocurrency": 235,
            "source_blackmatrix7_cryptocurrency": 43,
            "source_blackmatrix7_binance": 12,
            "source_blackmatrix7_okx": 3,
            "source_enriquephl_web3": 312,
            "source_dozee_manual": 105,
        }
        self.assertEqual(builder.guardrail_errors(stats, None), [])

    def test_primary_baselines_cannot_be_empty(self):
        for key in ("metacubex_reference_rules", "blackmatrix7_crypto_rules"):
            with self.subTest(key=key):
                stats = dict(GOOD_STATS, **{key: 0})
                self.assertTrue(any(key in e for e in builder.guardrail_errors(stats, GOOD_STATS)))

    def test_every_source_rejects_more_than_thirty_percent_drop(self):
        for key in GOOD_STATS:
            if key.startswith("source_") or key.endswith("_rules"):
                with self.subTest(key=key):
                    previous = dict(GOOD_STATS, **{key: 100})
                    self.assertEqual(builder.guardrail_errors(dict(previous, **{key: 70}), previous), [])
                    self.assertTrue(builder.guardrail_errors(dict(previous, **{key: 69}), previous))

    def test_all_guardrail_stats_survive_render_round_trip(self):
        parsed = builder.parse_rendered_stats(builder.render([], GOOD_STATS))
        for key in GOOD_STATS:
            self.assertEqual(parsed.get(key), GOOD_STATS[key], key)

    def test_legacy_header_migrates_without_losing_baseline(self):
        parsed = builder.parse_rendered_stats(
            "# MetaCubeX reference rules: 235\n# blackmatrix7 Crypto rules: 204\n"
            "# selected custom supplement rules: 85\n")
        self.assertEqual(parsed.get("custom_selected_rules"), 85)
        self.assertEqual(parsed.get("metacubex_reference_rules"), 235)
        self.assertEqual(parsed.get("blackmatrix7_crypto_rules"), 204)

    def test_cli_blocks_shrinkage_churn_and_growth_before_overwrite(self):
        old_rules = [f"DOMAIN-SUFFIX,asset{i}.example" for i in range(85)]
        cases = (old_rules[:55],
                 [f"DOMAIN-SUFFIX,new{i}.example" for i in range(85)],
                 old_rules + [f"DOMAIN-SUFFIX,new{i}.example" for i in range(86)])
        for new_rules in cases:
            with self.subTest(size=len(new_rules)), tempfile.TemporaryDirectory() as temp:
                path = Path(temp) / "output.list"
                original = builder.render(old_rules, GOOD_STATS)
                path.write_text(original)
                stats = dict(GOOD_STATS, custom_selected_rules=len(new_rules))
                with patch.object(builder, "OUTFILE", path), \
                     patch.object(builder, "build_rules", return_value=(new_rules, stats)), \
                     patch("sys.argv", ["builder"]), contextlib.redirect_stderr(io.StringIO()) as stderr, \
                     contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(builder.main(), 1)
                    self.assertIn("sync guardrail", stderr.getvalue())
                self.assertEqual(path.read_text(), original)

    def test_cli_accepts_small_update_then_check(self):
        old_rules = [f"DOMAIN-SUFFIX,asset{i}.example" for i in range(85)]
        new_rules = old_rules + ["DOMAIN-SUFFIX,added.example"]
        stats = dict(GOOD_STATS, custom_selected_rules=86)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "output.list"
            path.write_text(builder.render(old_rules, GOOD_STATS))
            with patch.object(builder, "OUTFILE", path), \
                 patch.object(builder, "build_rules", return_value=(new_rules, stats)), \
                 contextlib.redirect_stdout(io.StringIO()):
                for args in (["builder"], ["builder", "--check"]):
                    with patch("sys.argv", args):
                        self.assertEqual(builder.main(), 0)
            self.assertEqual(path.read_text(), builder.render(new_rules, stats))
