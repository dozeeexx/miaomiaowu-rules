#!/usr/bin/env python3
from __future__ import annotations

import copy
import importlib.util
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
V3 = ROOT / "templates" / "miaomiaowu" / "dozee_fake_ip__v3.yaml"
V4 = ROOT / "templates" / "miaomiaowu" / "dozee_fake_ip__v4.yaml"
TEMPLATES = (V3, V4)

GOOGLE_GROUP = "🔍 谷歌服务"
FOREIGN_DOH = [
    "https://dns.cloudflare.com/dns-query",
    "https://dns.google/dns-query",
]
DOMESTIC_DOH = [
    "https://120.53.53.53/dns-query",
    "https://223.5.5.5/dns-query",
]
GOOGLE_PLAY_PROVIDER = {
    "type": "http",
    "behavior": "domain",
    "url": "https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/geo/geosite/google-play.mrs",
    "path": "./ruleset/google-play.mrs",
    "interval": 86400,
    "format": "mrs",
}
GOOGLE_PLAY_PROXY_RULES = (
    f"DOMAIN-SUFFIX,services.googleapis.cn,{GOOGLE_GROUP}",
    f"DOMAIN-SUFFIX,googleapis.cn,{GOOGLE_GROUP}",
    f"DOMAIN,clientservices.googleapis.com,{GOOGLE_GROUP}",
    f"RULE-SET,google-play,{GOOGLE_GROUP}",
)
GOOGLE_PLAY_DIRECT_EXCEPTIONS = (
    "DOMAIN,connectivitycheck.gstatic.com,DIRECT",
    "DOMAIN,beacons.gvt2.com,DIRECT",
    "DOMAIN,beacons.gcp.gvt2.com,DIRECT",
)
GOOGLE_PLAY_FOREIGN_DNS_KEYS = (
    "rule-set:google-play",
    "+.services.googleapis.cn",
    "+.googleapis.cn",
    "clientservices.googleapis.com",
)
OLD_GOOGLE_PLAY_DNS_KEYS = (
    "+.xn--ngstr-lra8j.com",
    "services.googleapis.cn",
)
OLD_GOOGLE_PLAY_ROUTES = (
    "DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT",
    f"DOMAIN-SUFFIX,xn--ngstr-lra8j.com,{GOOGLE_GROUP}",
    "DOMAIN-SUFFIX,services.googleapis.cn,DIRECT",
    "DOMAIN,clientservices.googleapis.com,DIRECT",
)
DOMESTIC_RULES = (
    "RULE-SET,geolocation-cn,🔒 国内服务",
    "RULE-SET,cn,🔒 国内服务",
    "RULE-SET,cn-ip,🔒 国内服务,no-resolve",
)
GOOGLE_QUIC_REJECT = "AND,((RULE-SET,google),(NETWORK,UDP),(DST-PORT,443)),REJECT"
APP_PROVIDER = "Dozee_Android_Crypto_Apps"
APP_RULE = "RULE-SET,Dozee_Android_Crypto_Apps,💰 加密货币"
PRIVATE_RULE = "RULE-SET,private-ip,🏠 私有网络,no-resolve"


def load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class GooglePlayTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.configs = {path.name: load(path) for path in TEMPLATES}

    def test_validator_uses_complete_google_play_model(self) -> None:
        spec = importlib.util.spec_from_file_location("validator", ROOT / "scripts" / "validate.py")
        if spec is None or spec.loader is None:
            self.fail("cannot import scripts/validate.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.GOOGLE_PLAY_PROXY_RULES, GOOGLE_PLAY_PROXY_RULES)
        self.assertEqual(module.GOOGLE_PLAY_DIRECT_EXCEPTIONS, GOOGLE_PLAY_DIRECT_EXCEPTIONS)
        self.assertEqual(module.GOOGLE_PLAY_FOREIGN_DNS_KEYS, GOOGLE_PLAY_FOREIGN_DNS_KEYS)
        self.assertFalse(hasattr(module, "GOOGLE_PLAY_DIRECT_RULES"))

    def test_google_play_provider_is_complete_and_identical(self) -> None:
        providers = []
        for name, config in self.configs.items():
            with self.subTest(template=name):
                self.assertIn("google-play", config["rule-providers"])
                self.assertEqual(config["rule-providers"]["google-play"], GOOGLE_PLAY_PROVIDER)
                providers.append(config["rule-providers"]["google-play"])
        self.assertEqual(providers[0], providers[1])

    def test_control_and_download_routes_use_google_without_single_host_patch(self) -> None:
        for name, config in self.configs.items():
            rules = config["rules"]
            with self.subTest(template=name):
                for rule in GOOGLE_PLAY_PROXY_RULES:
                    self.assertIn(rule, rules)
                for rule in OLD_GOOGLE_PLAY_ROUTES:
                    self.assertNotIn(rule, rules)
                explicit_rotating_hosts = [
                    rule for rule in rules
                    if "xn--ngstr-lra8j.com" in rule or "rr1." in rule or "rr2." in rule or "rr3." in rule
                ]
                self.assertEqual(explicit_rotating_hosts, [])

    def test_google_play_dns_uses_foreign_rule_set_policy(self) -> None:
        for name, config in self.configs.items():
            policy = config["dns"]["nameserver-policy"]
            with self.subTest(template=name):
                self.assertTrue(config["dns"]["respect-rules"])
                for key in GOOGLE_PLAY_FOREIGN_DNS_KEYS:
                    self.assertEqual(policy.get(key), FOREIGN_DOH)
                for key in OLD_GOOGLE_PLAY_DNS_KEYS:
                    self.assertNotIn(key, policy)

    def test_direct_connectivity_exceptions_and_domestic_dns_stay_unchanged(self) -> None:
        dns_keys = (
            "connectivitycheck.gstatic.com",
            "beacons.gvt2.com",
            "beacons.gcp.gvt2.com",
        )
        for name, config in self.configs.items():
            with self.subTest(template=name):
                for rule in GOOGLE_PLAY_DIRECT_EXCEPTIONS:
                    self.assertIn(rule, config["rules"])
                for key in dns_keys:
                    self.assertEqual(config["dns"]["nameserver-policy"].get(key), DOMESTIC_DOH)

    def test_google_play_precedes_cn_and_google_quic_precedes_play_proxy(self) -> None:
        for name, config in self.configs.items():
            rules = config["rules"]
            domestic_index = min(rules.index(rule) for rule in DOMESTIC_RULES)
            play_indexes = [rules.index(rule) for rule in GOOGLE_PLAY_PROXY_RULES]
            with self.subTest(template=name):
                self.assertLess(rules.index(GOOGLE_QUIC_REJECT), min(play_indexes))
                self.assertTrue(all(index < domestic_index for index in play_indexes))

    def test_v4_is_v3_plus_only_crypto_app_layer(self) -> None:
        v3 = self.configs[V3.name]
        v4 = self.configs[V4.name]
        for key in ("mode", "dns", "proxies", "proxy-groups"):
            self.assertEqual(v4[key], v3[key])
        private_index = v3["rules"].index(PRIVATE_RULE)
        expected_rules = copy.deepcopy(v3["rules"])
        expected_rules.insert(private_index + 1, APP_RULE)
        self.assertEqual(v4["rules"], expected_rules)
        self.assertEqual(set(v4["rule-providers"]) - set(v3["rule-providers"]), {APP_PROVIDER})
        for provider, data in v3["rule-providers"].items():
            self.assertEqual(v4["rule-providers"].get(provider), data)


class GooglePlayValidatorMutationTests(unittest.TestCase):
    def make_sandbox(self) -> Path:
        temp_root = Path(tempfile.mkdtemp(prefix="mmw-google-play-validator-")) / "repo"
        shutil.copytree(
            ROOT,
            temp_root,
            ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
        )
        self.addCleanup(shutil.rmtree, temp_root.parent, True)
        return temp_root

    def mutate_both(self, root: Path, mutate) -> None:
        for filename in (V3.name, V4.name):
            path = root / "templates" / "miaomiaowu" / filename
            data = load(path)
            mutate(data)
            path.write_text(
                yaml.safe_dump(data, allow_unicode=True, sort_keys=False),
                encoding="utf-8",
            )

    def assert_validator_rejects(self, root: Path, expected: str) -> None:
        result = subprocess.run(
            [sys.executable, "scripts/validate.py"],
            cwd=root,
            text=True,
            capture_output=True,
            check=False,
        )
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, output)
        self.assertIn(expected, output)

    def test_validator_rejects_services_googleapis_cn_direct(self) -> None:
        root = self.make_sandbox()

        def mutate(config: dict) -> None:
            rules = config["rules"]
            index = rules.index(GOOGLE_PLAY_PROXY_RULES[0])
            rules[index] = "DOMAIN-SUFFIX,services.googleapis.cn,DIRECT"

        self.mutate_both(root, mutate)
        self.assert_validator_rejects(root, "Google Play control domains must use 🔍 谷歌服务")

    def test_validator_rejects_domestic_google_play_dns(self) -> None:
        root = self.make_sandbox()

        def mutate(config: dict) -> None:
            config["dns"]["nameserver-policy"]["+.services.googleapis.cn"] = DOMESTIC_DOH

        self.mutate_both(root, mutate)
        self.assert_validator_rejects(root, "Google Play DNS policy must use foreign DoH")

    def test_validator_rejects_missing_google_play_provider(self) -> None:
        root = self.make_sandbox()

        def mutate(config: dict) -> None:
            del config["rule-providers"]["google-play"]

        self.mutate_both(root, mutate)
        self.assert_validator_rejects(root, "missing rule-provider google-play")

    def test_validator_rejects_google_play_after_cn(self) -> None:
        root = self.make_sandbox()

        def mutate(config: dict) -> None:
            rules = config["rules"]
            play_rule = GOOGLE_PLAY_PROXY_RULES[-1]
            rules.remove(play_rule)
            rules.insert(rules.index(DOMESTIC_RULES[-1]) + 1, play_rule)

        self.mutate_both(root, mutate)
        self.assert_validator_rejects(root, "Google Play proxy rules must stay before broad domestic rules")


if __name__ == "__main__":
    unittest.main()
