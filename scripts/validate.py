#!/usr/bin/env python3
from pathlib import Path
import re
import sys

try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML. Install with: python3 -m pip install pyyaml', file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = ROOT / 'rules' / 'Custom_Proxy.list'
TEMPLATE_FILES = [
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v3.yaml',
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_redirhost__v3.yaml',
]
PROVIDER_NAME = 'Dozee_Custom_Proxy'
GROUP_NAME = '🧩 自定义'
EXPECTED_RULE = f'RULE-SET,{PROVIDER_NAME},{GROUP_NAME}'
EXPECTED_URL = 'https://testingcf.jsdelivr.net/gh/dozeeexx/miaomiaowu-rules@main/rules/Custom_Proxy.list'

ALLOWED_PREFIXES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'DOMAIN-REGEX',
    'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP', 'GEOSITE',
    'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'NETWORK',
}


def fail(msg: str) -> None:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def validate_rules() -> None:
    if not RULE_FILE.exists():
        fail(f'missing {RULE_FILE}')
    for lineno, raw in enumerate(RULE_FILE.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            fail(f'{RULE_FILE}:{lineno} invalid rule, expected TYPE,value: {line}')
        if parts[0] not in ALLOWED_PREFIXES:
            fail(f'{RULE_FILE}:{lineno} unsupported rule type {parts[0]!r}: {line}')
        if parts[0] in {'IP-CIDR', 'IP-CIDR6'} and len(parts) == 2:
            print(f'WARN: {RULE_FILE}:{lineno} IP rule can add ,no-resolve: {line}')


def validate_template(path: Path) -> None:
    if not path.exists():
        fail(f'missing {path}')
    data = yaml.safe_load(path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        fail(f'{path} is not a YAML mapping')

    groups = data.get('proxy-groups') or []
    group_names = {g.get('name') for g in groups if isinstance(g, dict)}
    if GROUP_NAME not in group_names:
        fail(f'{path} missing proxy group {GROUP_NAME}')

    rules = data.get('rules') or []
    if EXPECTED_RULE not in rules:
        fail(f'{path} missing rule {EXPECTED_RULE}')

    providers = data.get('rule-providers') or {}
    if PROVIDER_NAME not in providers:
        fail(f'{path} missing rule-provider {PROVIDER_NAME}')
    provider = providers[PROVIDER_NAME]
    if provider.get('behavior') != 'classical':
        fail(f'{path} provider {PROVIDER_NAME} behavior should be classical')
    if provider.get('format') != 'text':
        fail(f'{path} provider {PROVIDER_NAME} format should be text')
    if provider.get('url') != EXPECTED_URL:
        fail(f'{path} provider {PROVIDER_NAME} url mismatch: {provider.get("url")}')

    private_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('GEOIP,private,')), -1)
    custom_index = rules.index(EXPECTED_RULE)
    match_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('MATCH,')), len(rules))
    if private_index >= 0 and custom_index <= private_index:
        fail(f'{path} custom rule should stay after private/LAN direct rules')
    if custom_index >= match_index:
        fail(f'{path} custom rule must be before MATCH')


def main() -> None:
    validate_rules()
    for path in TEMPLATE_FILES:
        validate_template(path)
    print('OK: rules and templates validated')


if __name__ == '__main__':
    main()
