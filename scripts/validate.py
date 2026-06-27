#!/usr/bin/env python3
from pathlib import Path
import json
import re
import sys

try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML. Install with: python3 -m pip install pyyaml', file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = ROOT / 'rules' / 'Custom_Proxy.list'
PROXY_GROUPS_FILE = ROOT / 'configs' / 'proxy-groups.json'
TEMPLATE_FILES = [
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v3.yaml',
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_redirhost__v3.yaml',
]
PROVIDER_NAME = 'Dozee_Custom_Proxy'
GROUP_NAME = '🧩 自定义'
EXPECTED_RULE = f'RULE-SET,{PROVIDER_NAME},{GROUP_NAME}'
EXPECTED_URL = 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list'

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


def validate_proxy_groups() -> None:
    if not PROXY_GROUPS_FILE.exists():
        fail(f'missing {PROXY_GROUPS_FILE}')

    data = None
    try:
        data = json.loads(PROXY_GROUPS_FILE.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        fail(f'{PROXY_GROUPS_FILE} is not valid JSON: {exc}')

    if not isinstance(data, list):
        fail(f'{PROXY_GROUPS_FILE} root is not a JSON list')
    assert isinstance(data, list)

    group_names = set()
    custom_group: dict | None = None
    for idx, item in enumerate(data, 1):
        if not isinstance(item, dict):
            fail(f'{PROXY_GROUPS_FILE}:{idx} group entry is not an object')
        name = item.get('name')
        if not isinstance(name, str) or not name.strip():
            fail(f'{PROXY_GROUPS_FILE}:{idx} missing group name')
        group_names.add(name)

        site_rules = item.get('site_rules') or []
        ip_rules = item.get('ip_rules') or []
        if not site_rules and not ip_rules:
            fail(f'{PROXY_GROUPS_FILE}:{name} must define site_rules or ip_rules')

        if name == 'dozee-custom':
            custom_group = item

    if custom_group is None:
        fail(f'{PROXY_GROUPS_FILE} missing custom group dozee-custom')
    assert custom_group is not None

    if custom_group.get('group_label') != GROUP_NAME:
        fail(f'{PROXY_GROUPS_FILE} custom group_label should be {GROUP_NAME}')
    if custom_group.get('presets') != ['custom']:
        fail(f'{PROXY_GROUPS_FILE} custom group presets should be ["custom"]')

    site_rules = custom_group.get('site_rules') or []
    if len(site_rules) != 1:
        fail(f'{PROXY_GROUPS_FILE} custom group must have exactly one site rule provider')

    provider = site_rules[0]
    if provider.get('key') != PROVIDER_NAME:
        fail(f'{PROXY_GROUPS_FILE} custom provider key should be {PROVIDER_NAME}')
    if provider.get('behavior') != 'classical':
        fail(f'{PROXY_GROUPS_FILE} provider {PROVIDER_NAME} behavior should be classical')
    if provider.get('format') != 'text':
        fail(f'{PROXY_GROUPS_FILE} provider {PROVIDER_NAME} format should be text')
    if provider.get('url') != EXPECTED_URL:
        fail(f'{PROXY_GROUPS_FILE} provider {PROVIDER_NAME} url mismatch: {provider.get("url")}')


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
    validate_proxy_groups()
    for path in TEMPLATE_FILES:
        validate_template(path)
    print('OK: rules, proxy groups, and templates validated')


if __name__ == '__main__':
    main()
