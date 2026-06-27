#!/usr/bin/env python3
from pathlib import Path
import json
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
CUSTOM_CATEGORY_NAME = 'dozee-custom'
FAKE_IP_TEMPLATE_NAME = 'dozee_fake_ip__v3.yaml'
EXPECTED_RULE = f'RULE-SET,{PROVIDER_NAME},{GROUP_NAME}'
EXPECTED_RULE_URL = 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list'
EXPECTED_FAKE_IP_DNS = {
    'prefer-h3': True,
    'enhanced-mode': 'fake-ip',
    'default-nameserver': ['223.5.5.5', '119.29.29.29'],
    'nameserver': ['https://doh.pub/dns-query', 'https://dns.alidns.com/dns-query'],
    'fallback': ['https://1.1.1.1/dns-query', 'https://dns.google/dns-query'],
    'nameserver-policy-key': 'geosite:cn,private,apple,steam,onedrive,category-games@cn',
    'nameserver-policy': ['https://doh.pub/dns-query', 'https://dns.alidns.com/dns-query'],
    'fallback-filter-geoip': True,
    'fallback-filter-geoip-code': 'CN',
    'proxy-server-nameserver': ['https://doh.pub/dns-query', 'https://dns.alidns.com/dns-query'],
    'fake-ip-filter': ['+.lan', '+.local', '+.example.com', 'localhost.ptlogin2.qq.com'],
}
REQUIRED_RULES = [
    'DOMAIN-SUFFIX,polymarket.com',
    'DOMAIN,polymarket-upload.s3.us-east-2.amazonaws.com',
    'DOMAIN-SUFFIX,polymarket.sh',
    'DOMAIN-SUFFIX,polymarket.us',
    'DOMAIN-SUFFIX,polymarketexchange.com',
    'DOMAIN-SUFFIX,polymarketclearing.com',
    'DOMAIN,pmx-dev01.us.auth0.com',
    'DOMAIN,pmx-preprod.us.auth0.com',
    'DOMAIN,pmx-prod.us.auth0.com',
    'DOMAIN-SUFFIX,magic.link',
    'DOMAIN-SUFFIX,intercom.io',
    'DOMAIN-SUFFIX,intercomcdn.com',
    'DOMAIN-SUFFIX,intercomusercontent.com',
    'DOMAIN-SUFFIX,intercomassets.com',
    'DOMAIN-SUFFIX,intercom-messenger.com',
    'DOMAIN-SUFFIX,intercom-attachments.com',
    'DOMAIN-SUFFIX,predict.fun',
]

ALLOWED_PREFIXES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'DOMAIN-REGEX',
    'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP', 'GEOSITE',
    'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'NETWORK',
}


def fail(msg: str) -> None:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def validate_proxy_groups() -> None:
    if not PROXY_GROUPS_FILE.exists():
        fail(f'missing {PROXY_GROUPS_FILE}')

    data = json.loads(PROXY_GROUPS_FILE.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        fail(f'{PROXY_GROUPS_FILE} is not a JSON array')

    custom = next(
        (item for item in data if isinstance(item, dict) and item.get('name') == CUSTOM_CATEGORY_NAME),
        None,
    )
    if custom is None:
        fail(f'{PROXY_GROUPS_FILE} missing category {CUSTOM_CATEGORY_NAME}')

    if custom.get('label') != '自定义':
        fail(f'{PROXY_GROUPS_FILE} custom label mismatch: {custom.get("label")}')
    if custom.get('emoji') != '🧩':
        fail(f'{PROXY_GROUPS_FILE} custom emoji mismatch: {custom.get("emoji")}')
    if custom.get('group_label') != GROUP_NAME:
        fail(f'{PROXY_GROUPS_FILE} custom group_label mismatch: {custom.get("group_label")}')
    if custom.get('presets') != ['custom']:
        fail(f'{PROXY_GROUPS_FILE} custom presets should be ["custom"]')

    site_rules = custom.get('site_rules') or []
    if len(site_rules) != 1:
        fail(f'{PROXY_GROUPS_FILE} custom category should have exactly one site_rule')

    provider = site_rules[0]
    if provider.get('key') != PROVIDER_NAME:
        fail(f'{PROXY_GROUPS_FILE} custom provider key mismatch: {provider.get("key")}')
    if provider.get('behavior') != 'classical':
        fail(f'{PROXY_GROUPS_FILE} custom provider behavior should be classical')
    if provider.get('format') != 'text':
        fail(f'{PROXY_GROUPS_FILE} custom provider format should be text')
    if provider.get('url') != EXPECTED_RULE_URL:
        fail(f'{PROXY_GROUPS_FILE} custom provider url mismatch: {provider.get("url")}')


def validate_rules() -> None:
    if not RULE_FILE.exists():
        fail(f'missing {RULE_FILE}')

    seen_rules: list[str] = []
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
        seen_rules.append(line)

    missing = [rule for rule in REQUIRED_RULES if rule not in seen_rules]
    if missing:
        fail(f'{RULE_FILE} missing required prediction-market rules: {missing}')


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
    if provider.get('url') != EXPECTED_RULE_URL:
        fail(f'{path} provider {PROVIDER_NAME} url mismatch: {provider.get("url")}')

    if path.name == FAKE_IP_TEMPLATE_NAME:
        dns = data.get('dns') or {}
        if dns.get('enable') is not True:
            fail(f'{path} fake-ip dns should be enabled')
        for key, expected in [
            ('prefer-h3', EXPECTED_FAKE_IP_DNS['prefer-h3']),
            ('enhanced-mode', EXPECTED_FAKE_IP_DNS['enhanced-mode']),
            ('default-nameserver', EXPECTED_FAKE_IP_DNS['default-nameserver']),
            ('nameserver', EXPECTED_FAKE_IP_DNS['nameserver']),
            ('fallback', EXPECTED_FAKE_IP_DNS['fallback']),
            ('proxy-server-nameserver', EXPECTED_FAKE_IP_DNS['proxy-server-nameserver']),
            ('fake-ip-filter', EXPECTED_FAKE_IP_DNS['fake-ip-filter']),
        ]:
            if dns.get(key) != expected:
                fail(f'{path} fake-ip dns {key} mismatch: {dns.get(key)}')
        policy = dns.get('nameserver-policy') or {}
        policy_key = EXPECTED_FAKE_IP_DNS['nameserver-policy-key']
        if policy.get(policy_key) != EXPECTED_FAKE_IP_DNS['nameserver-policy']:
            fail(f'{path} fake-ip dns nameserver-policy mismatch: {policy.get(policy_key)}')
        fallback_filter = dns.get('fallback-filter') or {}
        if fallback_filter.get('geoip') is not EXPECTED_FAKE_IP_DNS['fallback-filter-geoip']:
            fail(f'{path} fake-ip dns fallback-filter geoip mismatch: {fallback_filter.get("geoip")}')
        if fallback_filter.get('geoip-code') != EXPECTED_FAKE_IP_DNS['fallback-filter-geoip-code']:
            fail(f'{path} fake-ip dns fallback-filter geoip-code mismatch: {fallback_filter.get("geoip-code")}')

    private_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('GEOIP,private,')), -1)
    custom_index = rules.index(EXPECTED_RULE)
    match_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('MATCH,')), len(rules))
    if private_index >= 0 and custom_index <= private_index:
        fail(f'{path} custom rule should stay after private/LAN direct rules')
    if custom_index >= match_index:
        fail(f'{path} custom rule must be before MATCH')


def main() -> None:
    validate_proxy_groups()
    validate_rules()
    for path in TEMPLATE_FILES:
        validate_template(path)
    print('OK: rules, proxy groups, and templates validated')


if __name__ == '__main__':
    main()
