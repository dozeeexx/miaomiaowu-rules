#!/usr/bin/env python3
from pathlib import Path
import re
import sys
from typing import NoReturn

try:
    import yaml
except ImportError:
    print('Missing dependency: PyYAML. Install with: python3 -m pip install pyyaml', file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILES = (
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v3.yaml',
    ROOT / 'templates' / 'miaomiaowu' / 'dozee_fake_ip__v4.yaml',
)
V3_TEMPLATE = TEMPLATE_FILES[0]
V4_TEMPLATE = TEMPLATE_FILES[1]

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

V4_APP_RULE_PROVIDERS = {
    'Dozee_Android_Crypto_Apps': {
        'file': ROOT / 'rules' / 'android' / 'Crypto_Apps.yaml',
        'group': '💰 加密货币',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/android/Crypto_Apps.yaml',
    },
    'Dozee_Android_CN_Apps_Core': {
        'file': ROOT / 'rules' / 'android' / 'China_Apps_Core.yaml',
        'group': '🔒 国内服务',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/android/China_Apps_Core.yaml',
    },
}

V4_APP_RULESET_RULES = tuple(
    f"RULE-SET,{provider_name},{provider['group']}"
    for provider_name, provider in V4_APP_RULE_PROVIDERS.items()
)

ALLOWED_PREFIXES = {
    'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD', 'DOMAIN-REGEX',
    'IP-CIDR', 'IP-CIDR6', 'IP-ASN', 'GEOIP', 'GEOSITE',
    'DST-PORT', 'SRC-PORT', 'PROCESS-NAME', 'PROCESS-PATH', 'NETWORK',
}

CRYPTO_CUSTOM_ALLOWED_PREFIXES = {'DOMAIN', 'DOMAIN-SUFFIX', 'DOMAIN-KEYWORD', 'DOMAIN-WILDCARD'}

CRYPTO_CUSTOM_FORBIDDEN_SUBSTRINGS = (
    'polymarket', 'predict.fun', 'predict.fail', 'kalshi', 'predictit.org',
    'manifold.markets', 'metaculus.com', 'limitless.exchange', 'opinion.trade',
    'discord.', 'twitter.', 'x.com', 'facebook.', 'instagram.', 'github.com',
    'google.', 'youtube.',
)

APP_PACKAGE_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z][A-Za-z0-9_]*)+$')


def fail(msg: str) -> NoReturn:
    print(f'ERROR: {msg}', file=sys.stderr)
    sys.exit(1)


def load_yaml(path: Path):
    try:
        return yaml.safe_load(path.read_text(encoding='utf-8'))
    except Exception as exc:  # noqa: BLE001 - validation script should print concise failures
        fail(f'{path} is not valid YAML: {exc}')


def validate_rule_file(rule_file: Path, *, crypto_custom: bool = False) -> None:
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
        if crypto_custom and parts[0] not in CRYPTO_CUSTOM_ALLOWED_PREFIXES:
            fail(f'{rule_file}:{lineno} crypto custom list should stay domain-only, got {parts[0]!r}: {line}')
        if crypto_custom and any(token in line.lower() for token in CRYPTO_CUSTOM_FORBIDDEN_SUBSTRINGS):
            fail(f'{rule_file}:{lineno} should not capture prediction/social/dev/google domain in crypto custom list: {line}')
        active_lines.append(line)
    duplicates = sorted({line for line in active_lines if active_lines.count(line) > 1})
    if duplicates:
        fail(f'{rule_file} contains duplicate active rules: {duplicates[:5]}')


def validate_app_package_rule_file(rule_file: Path) -> set[str]:
    if not rule_file.exists():
        fail(f'missing {rule_file}')
    data = load_yaml(rule_file)
    if not isinstance(data, dict):
        fail(f'{rule_file} should be a YAML mapping with a payload list')
    payload = data.get('payload')
    if not isinstance(payload, list):
        fail(f'{rule_file} should be a YAML mapping with a payload list')
    packages: list[str] = []
    for idx, raw_rule in enumerate(payload, 1):
        if not isinstance(raw_rule, str):
            fail(f'{rule_file}:payload[{idx}] should be a string')
        rule = raw_rule.strip()
        parts = [part.strip() for part in rule.split(',')]
        if len(parts) != 2 or parts[0] != 'PROCESS-NAME':
            fail(f'{rule_file}:payload[{idx}] must be PROCESS-NAME,<android.package>, got: {rule}')
        package = parts[1]
        if not APP_PACKAGE_RE.match(package):
            fail(f'{rule_file}:payload[{idx}] invalid Android package name: {package}')
        packages.append(package)
    duplicates = sorted({package for package in packages if packages.count(package) > 1})
    if duplicates:
        fail(f'{rule_file} contains duplicate packages: {duplicates[:5]}')
    return set(packages)


def validate_rules() -> None:
    for provider_name, provider in LOCAL_RULE_PROVIDERS.items():
        validate_rule_file(
            provider['file'],
            crypto_custom=(provider_name == 'Dozee_Crypto_Custom'),
        )

    seen_packages: dict[str, str] = {}
    for provider_name, provider in V4_APP_RULE_PROVIDERS.items():
        packages = validate_app_package_rule_file(provider['file'])
        for package in packages:
            previous = seen_packages.get(package)
            if previous:
                fail(f'Android package {package} appears in both {previous} and {provider_name}')
            seen_packages[package] = provider_name


def validate_expected_provider(template_file: Path, providers: dict, provider_name: str, expected: dict) -> None:
    if provider_name not in providers:
        fail(f'{template_file} missing rule-provider {provider_name}')
    provider = providers[provider_name]
    expected_behavior = expected.get('behavior', 'classical')
    expected_format = expected.get('format', 'text')
    if provider.get('behavior') != expected_behavior:
        fail(f'{template_file} provider {provider_name} behavior should be {expected_behavior}')
    if provider.get('format') != expected_format:
        fail(f'{template_file} provider {provider_name} format should be {expected_format}')
    if provider.get('url') != expected['url']:
        fail(f'{template_file} provider {provider_name} url mismatch: {provider.get("url")}')


def validate_template(template_file: Path) -> None:
    if not template_file.exists():
        fail(f'missing {template_file}')
    data = load_yaml(template_file)
    if not isinstance(data, dict):
        fail(f'{template_file} is not a YAML mapping')

    groups = data.get('proxy-groups') or []
    group_names = {g.get('name') for g in groups if isinstance(g, dict)}
    rules = data.get('rules') or []
    providers = data.get('rule-providers') or {}
    dns = data.get('dns') or {}
    nameserver_policy = dns.get('nameserver-policy') or {}

    for play_domain in ('+.xn--ngstr-lra8j.com', 'services.googleapis.cn', '+.services.googleapis.cn', 'clientservices.googleapis.com', 'connectivitycheck.gstatic.com', 'beacons.gvt2.com', 'beacons.gcp.gvt2.com'):
        if play_domain not in nameserver_policy:
            fail(f'{template_file} missing DNS policy for Google Play domain {play_domain}')

    for play_rule in (
        'DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT',
        'DOMAIN-SUFFIX,services.googleapis.cn,DIRECT',
        'DOMAIN,clientservices.googleapis.com,DIRECT',
        'DOMAIN,connectivitycheck.gstatic.com,DIRECT',
        'DOMAIN,beacons.gvt2.com,DIRECT',
        'DOMAIN,beacons.gcp.gvt2.com,DIRECT',
    ):
        if play_rule not in rules:
            fail(f'{template_file} missing Google Play direct rule {play_rule}')

    expected_providers = {**LOCAL_RULE_PROVIDERS, **REMOTE_RULE_PROVIDERS}
    for provider_name, expected in expected_providers.items():
        group_name = expected['group']
        expected_rule = f'RULE-SET,{provider_name},{group_name}'
        if group_name not in group_names:
            fail(f'{template_file} missing proxy group {group_name}')
        if expected_rule not in rules:
            fail(f'{template_file} missing rule {expected_rule}')
        validate_expected_provider(template_file, providers, provider_name, expected)

    if template_file.name.endswith('__v4.yaml'):
        if list(rules[:len(V4_APP_RULESET_RULES)]) != list(V4_APP_RULESET_RULES):
            fail(f'{template_file} V4 app rule-set order must be crypto -> CN core')
        for provider_name, expected in V4_APP_RULE_PROVIDERS.items():
            if expected['group'] not in group_names:
                fail(f'{template_file} missing V4 app target group {expected["group"]}')
            expected_rule = f"RULE-SET,{provider_name},{expected['group']}"
            if expected_rule not in rules:
                fail(f'{template_file} missing V4 app rule-set {expected_rule}')
            validate_expected_provider(
                template_file,
                providers,
                provider_name,
                {**expected, 'behavior': 'classical', 'format': 'yaml'},
            )
        inline_process_rules = [rule for rule in rules if isinstance(rule, str) and rule.startswith('PROCESS-NAME,')]
        if inline_process_rules:
            fail(f'{template_file} should keep app packages in V4 rule-providers, not inline rules: {inline_process_rules[:3]}')
    else:
        unexpected = set(providers) & set(V4_APP_RULE_PROVIDERS)
        if unexpected:
            fail(f'{template_file} is the stable V3 template and must not include V4 app providers: {sorted(unexpected)}')

    for name, rp in providers.items():
        if not isinstance(rp, dict):
            fail(f'{template_file} rule-provider {name} should be a mapping')
        url = rp.get('url', '')
        path = rp.get('path', '')
        if (isinstance(url, str) and url.endswith('.mrs')) or (isinstance(path, str) and path.endswith('.mrs')):
            if rp.get('format') != 'mrs':
                fail(f'{template_file} rule-provider {name} uses .mrs but format is not mrs')

    for rule in rules:
        if not isinstance(rule, str) or not rule.startswith('RULE-SET,'):
            continue
        parts = rule.split(',')
        if len(parts) < 3:
            fail(f'{template_file} malformed RULE-SET rule: {rule}')
        provider_name, group_name = parts[1], parts[2]
        if provider_name not in providers:
            fail(f'{template_file} rule references missing provider {provider_name}: {rule}')
        if group_name not in group_names and group_name not in {'DIRECT', 'REJECT'}:
            fail(f'{template_file} rule references missing group {group_name}: {rule}')

    private_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and 'private' in r), -1)
    match_index = next((i for i, r in enumerate(rules) if isinstance(r, str) and r.startswith('MATCH,')), len(rules))
    broad_index = next((i for i, r in enumerate(rules) if r == 'RULE-SET,geolocation-!cn,🌐 非中国'), match_index)
    google_quic_reject = 'AND,((RULE-SET,google),(NETWORK,UDP),(DST-PORT,443)),REJECT'
    google_rule = 'RULE-SET,google,🔍 谷歌服务'
    if google_quic_reject not in rules:
        fail(f'{template_file} missing Google QUIC reject rule')
    if google_rule not in rules:
        fail(f'{template_file} missing Google service rule')
    if rules.index(google_quic_reject) >= rules.index(google_rule):
        fail(f'{template_file} Google QUIC reject rule must stay before Google service rule')

    for provider_name, expected in expected_providers.items():
        expected_rule = f"RULE-SET,{provider_name},{expected['group']}"
        rule_index = rules.index(expected_rule)
        if private_index >= 0 and rule_index <= private_index:
            fail(f'{template_file} {provider_name} rule should stay after private/LAN direct rules')
        if rule_index >= broad_index:
            fail(f'{template_file} {provider_name} rule must be before broad geolocation-!cn')
        if rule_index >= match_index:
            fail(f'{template_file} {provider_name} rule must be before MATCH')

    prediction_rule = 'RULE-SET,Dozee_Prediction_Market,📈 预测市场'
    crypto_order = [
        'RULE-SET,crypto-main,💰 加密货币',
        'RULE-SET,crypto-blackmatrix,💰 加密货币',
        'RULE-SET,Dozee_Crypto_Custom,💰 加密货币',
    ]
    if prediction_rule not in rules:
        fail(f'{template_file} missing prediction-market rule')
    prediction_index = rules.index(prediction_rule)
    crypto_indexes = [rules.index(rule) for rule in crypto_order]
    if any(index <= prediction_index for index in crypto_indexes):
        fail(f'{template_file} prediction-market rule must stay before broad crypto rules')
    if crypto_indexes != sorted(crypto_indexes):
        fail(f'{template_file} crypto rules should be ordered main -> third-party extra -> Dozee custom')


def validate_v4_is_v3_plus_app_layer() -> None:
    v3 = load_yaml(V3_TEMPLATE)
    v4 = load_yaml(V4_TEMPLATE)
    for key in ('mode', 'dns', 'proxies', 'proxy-groups'):
        if v4.get(key) != v3.get(key):
            fail(f'V4 should keep V3 {key} unchanged')
    if v4.get('rules', [])[len(V4_APP_RULESET_RULES):] != v3.get('rules', []):
        fail('V4 should be V3 rules plus only the top Android app rule-set layer')
    v3_providers = v3.get('rule-providers') or {}
    v4_providers = v4.get('rule-providers') or {}
    for provider_name, provider in v3_providers.items():
        if v4_providers.get(provider_name) != provider:
            fail(f'V4 should keep V3 provider {provider_name} unchanged')
    extra_providers = set(v4_providers) - set(v3_providers)
    expected_extra = set(V4_APP_RULE_PROVIDERS)
    if extra_providers != expected_extra:
        fail(f'V4 provider extras should be exactly {sorted(expected_extra)}, got {sorted(extra_providers)}')


def main() -> None:
    validate_rules()
    for template_file in TEMPLATE_FILES:
        validate_template(template_file)
    validate_v4_is_v3_plus_app_layer()
    print('OK: custom rules and V3/V4 templates validated')


if __name__ == '__main__':
    main()
