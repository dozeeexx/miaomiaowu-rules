#!/usr/bin/env python3
from pathlib import Path
import sys

try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML. Install with: python3 -m pip install pyyaml', file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILE = ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v3.yaml'
RULE_PROVIDERS = {
    'Dozee_Custom_Proxy': {
        'file': ROOT / 'rules' / 'Custom_Proxy.list',
        'group': '🧩 自定义',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list',
    },
    'Dozee_Prediction_Market': {
        'file': ROOT / 'rules' / 'Prediction_Market.list',
        'group': '📈 预测市场',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Prediction_Market.list',
    },
}

ALLOWED_PREFIXES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'DOMAIN-REGEX',
    'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP', 'GEOSITE',
    'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'NETWORK',
}


def fail(msg: str) -> None:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def validate_rule_file(rule_file: Path) -> None:
    if not rule_file.exists():
        fail(f'missing {rule_file}')
    for lineno, raw in enumerate(rule_file.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            fail(f'{rule_file}:{lineno} invalid rule, expected TYPE,value: {line}')
        if parts[0] not in ALLOWED_PREFIXES:
            fail(f'{rule_file}:{lineno} unsupported rule type {parts[0]!r}: {line}')


def validate_rules() -> None:
    for provider in RULE_PROVIDERS.values():
        validate_rule_file(provider['file'])


def validate_template() -> None:
    if not TEMPLATE_FILE.exists():
        fail(f'missing {TEMPLATE_FILE}')
    data = yaml.safe_load(TEMPLATE_FILE.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        fail(f'{TEMPLATE_FILE} is not a YAML mapping')

    groups = data.get('proxy-groups') or []
    group_names = {g.get('name') for g in groups if isinstance(g, dict)}
    rules = data.get('rules') or []
    providers = data.get('rule-providers') or {}
    dns = data.get('dns') or {}
    nameserver_policy = dns.get('nameserver-policy') or {}

    for play_domain in ('+.xn--ngstr-lra8j.com', 'services.googleapis.cn', 'clientservices.googleapis.com'):
        if play_domain not in nameserver_policy:
            fail(f'{TEMPLATE_FILE} missing DNS policy for Google Play domain {play_domain}')

    for play_rule in (
        'DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT',
        'DOMAIN,services.googleapis.cn,DIRECT',
        'DOMAIN,clientservices.googleapis.com,DIRECT',
    ):
        if play_rule not in rules:
            fail(f'{TEMPLATE_FILE} missing Google Play direct rule {play_rule}')

    for provider_name, expected in RULE_PROVIDERS.items():
        group_name = expected['group']
        expected_rule = f'RULE-SET,{provider_name},{group_name}'
        if group_name not in group_names:
            fail(f'{TEMPLATE_FILE} missing proxy group {group_name}')
        if expected_rule not in rules:
            fail(f'{TEMPLATE_FILE} missing rule {expected_rule}')
        if provider_name not in providers:
            fail(f'{TEMPLATE_FILE} missing rule-provider {provider_name}')
        provider = providers[provider_name]
        if provider.get('behavior') != 'classical':
            fail(f'{TEMPLATE_FILE} provider {provider_name} behavior should be classical')
        if provider.get('format') != 'text':
            fail(f'{TEMPLATE_FILE} provider {provider_name} format should be text')
        if provider.get('url') != expected['url']:
            fail(f'{TEMPLATE_FILE} provider {provider_name} url mismatch: {provider.get("url")}')

    for name, rp in providers.items():
        if not isinstance(rp, dict):
            fail(f'{TEMPLATE_FILE} rule-provider {name} should be a mapping')
        url = rp.get('url', '')
        path = rp.get('path', '')
        if (isinstance(url, str) and url.endswith('.mrs')) or (isinstance(path, str) and path.endswith('.mrs')):
            if rp.get('format') != 'mrs':
                fail(f'{TEMPLATE_FILE} rule-provider {name} uses .mrs but format is not mrs')

    private_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and 'private' in r), -1)
    match_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('MATCH,')), len(rules))
    broad_index = next((i for i, r in enumerate(rules) if r == 'RULE-SET,geolocation-!cn,🌐 非中国'), match_index)
    google_quic_reject = 'AND,((RULE-SET,google),(NETWORK,UDP),(DST-PORT,443)),REJECT'
    google_rule = 'RULE-SET,google,🔍 谷歌服务'
    if google_quic_reject not in rules:
        fail(f'{TEMPLATE_FILE} missing Google QUIC reject rule')
    if google_rule not in rules:
        fail(f'{TEMPLATE_FILE} missing Google service rule')
    if rules.index(google_quic_reject) >= rules.index(google_rule):
        fail(f'{TEMPLATE_FILE} Google QUIC reject rule must stay before Google service rule')
    for provider_name, expected in RULE_PROVIDERS.items():
        expected_rule = f"RULE-SET,{provider_name},{expected['group']}"
        rule_index = rules.index(expected_rule)
        if private_index >= 0 and rule_index <= private_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule should stay after private/LAN direct rules')
        if rule_index >= broad_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule must be before broad geolocation-!cn')
        if rule_index >= match_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule must be before MATCH')


def main() -> None:
    validate_rules()
    validate_template()
    print('OK: custom rules and main V3 template validated')


if __name__ == '__main__':
    main()
