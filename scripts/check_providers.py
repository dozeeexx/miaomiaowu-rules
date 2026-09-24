#!/usr/bin/env python3
"""Full-GET health check for every unique remote rule Provider."""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path
import argparse
import sys
import urllib.error
import urllib.parse
import urllib.request

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILES = (
    ROOT / "templates" / "miaomiaowu" / "dozee_fake_ip__v3.yaml",
    ROOT / "templates" / "miaomiaowu" / "dozee_fake_ip__v4.yaml",
)
MRS_MAGIC = b"\x28\xb5\x2f\xfd"
USER_AGENT = "dozee-miaomiaowu-provider-health/1.0"
PLACEHOLDER = ("Dozee_Custom_Proxy",
               "https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list")
CLASSICAL_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD", "DOMAIN-REGEX",
                   "DOMAIN-WILDCARD", "IP-CIDR", "IP-CIDR6", "IP-SUFFIX", "IP-ASN",
                   "GEOIP", "GEOSITE", "PROCESS-NAME", "PROCESS-PATH"}


def load_configs(paths: tuple[Path, ...] = TEMPLATE_FILES) -> list[dict]:
    configs = []
    for path in paths:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path.name} is not a YAML mapping")
        configs.append(data)
    return configs


def iter_unique_providers(configs: list[dict]):
    names_by_url: dict[str, list[str]] = defaultdict(list)
    provider_by_url: dict[str, dict] = {}
    for config in configs:
        providers = config.get("rule-providers", {})
        if not isinstance(providers, dict):
            raise ValueError("rule-providers must be a mapping")
        for name, provider in providers.items():
            if not isinstance(provider, dict) or not provider.get("url"):
                raise ValueError(f"Provider {name} has no remote URL")
            url = provider["url"]
            if name not in names_by_url[url]:
                names_by_url[url].append(name)
            provider_by_url.setdefault(url, provider)
            previous = provider_by_url[url]
            for field, default in (("format", "yaml"), ("behavior", "classical")):
                if previous.get(field, default) != provider.get(field, default):
                    raise ValueError(f"Provider {name}: conflicting {field} for shared URL")
    if not provider_by_url:
        raise ValueError("no remote Providers found")
    for url in sorted(provider_by_url):
        yield " / ".join(names_by_url[url]), provider_by_url[url]


def payload_state(provider: dict, payload: bytes) -> str:
    """Classify active content separately from an intentional text placeholder."""
    fmt = provider.get("format", "yaml")
    if fmt == "mrs":
        return "active"
    if fmt == "yaml":
        return "active"
    active_lines = [
        line.strip()
        for line in payload.decode("utf-8", "replace").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    return "active" if active_lines else "placeholder"


def validate_payload(name: str, provider: dict, payload: bytes) -> list[str]:
    errors: list[str] = []
    if not payload:
        return [f"{name}: empty payload"]

    fmt = provider.get("format", "yaml")
    if fmt == "mrs":
        if len(payload) <= 4 or payload[:4] != MRS_MAGIC:
            errors.append(f"{name}: invalid MRS magic")
    elif fmt == "yaml":
        try:
            data = yaml.safe_load(payload.decode("utf-8"))
        except Exception as exc:  # noqa: BLE001 - report remote payload failure
            errors.append(f"{name}: invalid YAML ({exc.__class__.__name__})")
        else:
            if not isinstance(data, dict) or not isinstance(data.get("payload"), list):
                errors.append(f"{name}: YAML payload list is missing")
            elif not data["payload"]:
                errors.append(f"{name}: YAML has a non-empty payload requirement")
            elif any(not isinstance(row, str) or not row.strip() for row in data["payload"]):
                errors.append(f"{name}: YAML payload entries must be non-empty strings")
    elif fmt == "text":
        try:
            text = payload.decode("utf-8")
        except UnicodeDecodeError:
            return [f"{name}: invalid UTF-8 text"]
        lines = [row.strip() for row in text.splitlines()
                 if row.strip() and not row.lstrip().startswith(("#", "//"))]
        if not lines:
            if (name, provider.get("url")) != PLACEHOLDER or not text.strip():
                errors.append(f"{name}: unexpectedly empty active rule set")
        else:
            for row in lines:
                parts = row.split(",")
                if len(parts) < 2 or parts[0] not in CLASSICAL_TYPES or not parts[1].strip():
                    errors.append(f"{name}: invalid classical text rule")
                    break
    else:
        errors.append(f"{name}: unsupported Provider format {fmt!r}")
    return errors


def fetch(url: str) -> tuple[int, bytes]:
    parsed = urllib.parse.urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Provider URL must be HTTPS without embedded credentials")
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=45) as response:
        return int(response.status), response.read()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        configs = load_configs()
        providers = list(iter_unique_providers(configs))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: cannot load templates: {exc}", file=sys.stderr)
        return 1

    failures = 0
    print(f"Checking {len(providers)} unique remote Providers")
    for name, provider in providers:
        url = provider["url"]
        try:
            status, payload = fetch(url)
            errors = [] if status == 200 else [f"{name}: HTTP {status}"]
            errors.extend(validate_payload(name, provider, payload))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            errors = [f"{name}: fetch failed ({exc.__class__.__name__})"]
            payload = b""
        if errors:
            failures += len(errors)
            for error in errors:
                print(f"ERROR: {error}", file=sys.stderr)
        else:
            fmt = provider.get("format", "yaml")
            state = payload_state(provider, payload)
            print(f"OK: {name} [{fmt}, {state}, {len(payload)} bytes]")

    if failures:
        print(f"ERROR: {failures} Provider checks failed", file=sys.stderr)
        return 1
    print(f"OK: {len(providers)} unique Providers passed transport/format checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
