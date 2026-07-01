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

LOCAL_RULE_PROVIDERS = {
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
    'Dozee_Crypto_Custom': {
        'file': ROOT / 'rules' / 'Dozee_Crypto_Custom.list',
        'group': '💰 加密货币',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Dozee_Crypto_Custom.list',
    },
}

REMOTE_RULE_PROVIDERS = {
    'crypto-main': {
        'group': '💰 加密货币',
        'behavior': 'domain',
        'format': 'mrs',
        'url': 'https://gh-proxy.com/https://github.com/MetaCubeX/meta-rules-dat/raw/refs/heads/meta/geo/geosite/category-cryptocurrency.mrs',
    },
    'crypto-blackmatrix': {
        'group': '💰 加密货币',
        'behavior': 'classical',
        'format': 'text',
        'url': 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Crypto/Crypto.list',
    },
}

ALLOWED_PREFIXES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'DOMAIN-REGEX',
    'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP', 'GEOSITE',
    'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'NETWORK',
}

CRYPTO_CUSTOM_FORBIDDEN_SUBSTRINGS = (
    'polymarket', 'predict.fun', 'predict.fail', 'kalshi', 'predictit.org',
    'manifold.markets', 'metaculus.com', 'limitless.exchange', 'opinion.trade',
    'discord.', 'twitter.', 'x.com', 'facebook.', 'instagram.', 'github.com',
    'google.', 'youtube.',
)


def fail(msg: str) -> None:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def validate_rule_file(rule_file: Path, *, forbid_crypto_crossovers: bool = False) -> None:
    if not rule_file.exists():
        fail(f'missing {rule_file}')
    active_lines = []
    for lineno, raw in enumerate(rule_file.read_text(encoding='utf-8').splitlines(), 1):
        line = raw.strip()
        if not line or line.startswith('#'):
            continue
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 2:
            fail(f'{rule_file}:{lineno} invalid rule, expected TYPE,value: {line}')
        if parts[0] not in ALLOWED_PREFIXES:
            fail(f'{rule_file}:{lineno} unsupported rule type {parts[0]!r}: {line}')
        if forbid_crypto_crossovers and any(token in line.lower() for token in CRYPTO_CUSTOM_FORBIDDEN_SUBSTRINGS):
            fail(f'{rule_file}:{lineno} should not capture prediction/social/dev/google domain in crypto custom list: {line}')
        active_lines.append(line)
    duplicates = sorted({line for line in active_lines if active_lines.count(line) > 1})
    if duplicates:
        fail(f'{rule_file} contains duplicate active rules: {duplicates[:5]}')


def validate_rules() -> None:
    for provider_name, provider in LOCAL_RULE_PROVIDERS.items():
        validate_rule_file(
            provider['file'],
            forbid_crypto_crossovers=(provider_name == 'Dozee_Crypto_Custom'),
        )


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

    for play_domain in ('+.xn--ngstr-lra8j.com', 'services.googleapis.cn', '+.services.googleapis.cn', 'clientservices.googleapis.com', 'connectivitycheck.gstatic.com', 'beacons.gvt2.com', 'beacons.gcp.gvt2.com'):
        if play_domain not in nameserver_policy:
            fail(f'{TEMPLATE_FILE} missing DNS policy for Google Play domain {play_domain}')

    for play_rule in (
        'DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT',
        'DOMAIN-SUFFIX,services.googleapis.cn,DIRECT',
        'DOMAIN,clientservices.googleapis.com,DIRECT',
        'DOMAIN,connectivitycheck.gstatic.com,DIRECT',
        'DOMAIN,beacons.gvt2.com,DIRECT',
        'DOMAIN,beacons.gcp.gvt2.com,DIRECT',
    ):
        if play_rule not in rules:
            fail(f'{TEMPLATE_FILE} missing Google Play direct rule {play_rule}')

    expected_providers = {**LOCAL_RULE_PROVIDERS, **REMOTE_RULE_PROVIDERS}
    for provider_name, expected in expected_providers.items():
        group_name = expected['group']
        expected_rule = f'RULE-SET,{provider_name},{group_name}'
        if group_name not in group_names:
            fail(f'{TEMPLATE_FILE} missing proxy group {group_name}')
        if expected_rule not in rules:
            fail(f'{TEMPLATE_FILE} missing rule {expected_rule}')
        if provider_name not in providers:
            fail(f'{TEMPLATE_FILE} missing rule-provider {provider_name}')
        provider = providers[provider_name]
        expected_behavior = expected.get('behavior', 'classical')
        expected_format = expected.get('format', 'text')
        if provider.get('behavior') != expected_behavior:
            fail(f'{TEMPLATE_FILE} provider {provider_name} behavior should be {expected_behavior}')
        if provider.get('format') != expected_format:
            fail(f'{TEMPLATE_FILE} provider {provider_name} format should be {expected_format}')
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

    for rule in rules:
        if not isinstance(rule, str) or not rule.startswith('RULE-SET,'):
            continue
        parts = rule.split(',')
        if len(parts) < 3:
            fail(f'{TEMPLATE_FILE} malformed RULE-SET rule: {rule}')
        provider_name, group_name = parts[1], parts[2]
        if provider_name not in providers:
            fail(f'{TEMPLATE_FILE} rule references missing provider {provider_name}: {rule}')
        if group_name not in group_names and group_name not in {'DIRECT', 'REJECT'}:
            fail(f'{TEMPLATE_FILE} rule references missing group {group_name}: {rule}')

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

    for provider_name, expected in expected_providers.items():
        expected_rule = f"RULE-SET,{provider_name},{expected['group']}"
        rule_index = rules.index(expected_rule)
        if private_index >= 0 and rule_index <= private_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule should stay after private/LAN direct rules')
        if rule_index >= broad_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule must be before broad geolocation-!cn')
        if rule_index >= match_index:
            fail(f'{TEMPLATE_FILE} {provider_name} rule must be before MATCH')

    prediction_rule = 'RULE-SET,Dozee_Prediction_Market,📈 预测市场'
    crypto_order = [
        'RULE-SET,crypto-main,💰 加密货币',
        'RULE-SET,crypto-blackmatrix,💰 加密货币',
        'RULE-SET,Dozee_Crypto_Custom,💰 加密货币',
    ]
    if prediction_rule not in rules:
        fail(f'{TEMPLATE_FILE} missing prediction-market rule')
    prediction_index = rules.index(prediction_rule)
    crypto_indexes = [rules.index(rule) for rule in crypto_order]
    if any(index <= prediction_index for index in crypto_indexes):
        fail(f'{TEMPLATE_FILE} prediction-market rule must stay before broad crypto rules')
    if crypto_indexes != sorted(crypto_indexes):
        fail(f'{TEMPLATE_FILE} crypto rules should be ordered main -> third-party extra -> Dozee custom')


def main() -> None:
    validate_rules()
    validate_template()
    print('OK: custom rules and main V3 template validated')


if __name__ == '__main__':
    main()
