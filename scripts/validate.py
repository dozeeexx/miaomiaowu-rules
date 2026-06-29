#!/usr/bin/env python3
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML. Install with: python3 -m pip install pyyaml', file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = ROOT / 'rules' / 'Custom_Proxy.list'
TEMPLATE_FILE = ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v3.yaml'
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


def validate_template() -> None:
    if not TEMPLATE_FILE.exists():
        fail(f'missing {TEMPLATE_FILE}')
    data = yaml.safe_load(TEMPLATE_FILE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        fail(f'{TEMPLATE_FILE} is not a YAML mapping')

    groups = data.get('proxy-groups') or []
    group_names = {g.get('name') for g in groups if isinstance(g, dict)}
    if GROUP_NAME not in group_names:
        fail(f'{TEMPLATE_FILE} missing proxy group {GROUP_NAME}')

    rules = data.get('rules') or []
    if EXPECTED_RULE not in rules:
        fail(f'{TEMPLATE_FILE} missing rule {EXPECTED_RULE}')

    providers = data.get('rule-providers') or {}
    if PROVIDER_NAME not in providers:
        fail(f'{TEMPLATE_FILE} missing rule-provider {PROVIDER_NAME}')
    provider = providers[PROVIDER_NAME]
    if provider.get('behavior') != 'classical':
        fail(f'{TEMPLATE_FILE} provider {PROVIDER_NAME} behavior should be classical')
    if provider.get('format') != 'text':
        fail(f'{TEMPLATE_FILE} provider {PROVIDER_NAME} format should be text')
    if provider.get('url') != EXPECTED_URL:
        fail(f'{TEMPLATE_FILE} provider {PROVIDER_NAME} url mismatch: {provider.get("url")}')

    for name, rp in providers.items():
        if not isinstance(rp, dict):
            fail(f'{TEMPLATE_FILE} rule-provider {name} should be a mapping')
        url = rp.get('url', '')
        path = rp.get('path', '')
        if (isinstance(url, str) and url.endswith('.mrs')) or (isinstance(path, str) and path.endswith('.mrs')):
            if rp.get('format') != 'mrs':
                fail(f'{TEMPLATE_FILE} rule-provider {name} uses .mrs but format is not mrs')

    private_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and 'private' in r), -1)
    custom_index = rules.index(EXPECTED_RULE)
    match_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('MATCH,')), len(rules))
    if private_index >= 0 and custom_index <= private_index:
        fail(f'{TEMPLATE_FILE} custom rule should stay after private/LAN direct rules')
    if custom_index >= match_index:
        fail(f'{TEMPLATE_FILE} custom rule must be before MATCH')


def main() -> None:
    validate_rules()
    validate_template()
    print('OK: custom rules and main V3 template validated')


if __name__ == '__main__':
    main()
