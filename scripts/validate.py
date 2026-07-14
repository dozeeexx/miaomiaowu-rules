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

METACUBEX_CDN_PREFIX = 'https://testingcf.jsdelivr.net/gh/MetaCubeX/meta-rules-dat@meta/'

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
        'url': f'{METACUBEX_CDN_PREFIX}geo/geosite/category-cryptocurrency.mrs',
    },
    'crypto-blackmatrix': {
        'group': '💰 加密货币',
        'behavior': 'classical',
        'format': 'text',
        'url': 'https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Crypto/Crypto.list',
    },
}

CORE_RULE_PROVIDER_GROUPS = {
    'category-ai-!cn': '💬 AI 服务',
    'youtube': '📹 油管视频',
    'google': '🔍 谷歌服务',
    'telegram': '📲 电报消息',
    'geolocation-cn': '🔒 国内服务',
    'cn': '🔒 国内服务',
    'github': '🐱 Github',
    'gitlab': '🐱 Github',
    'facebook': '🌐 社交媒体',
    'instagram': '🌐 社交媒体',
    'twitter': '🌐 社交媒体',
    'tiktok': '🌐 社交媒体',
    'linkedin': '🌐 社交媒体',
    'netflix': '🎬 流媒体',
    'hulu': '🎬 流媒体',
    'disney': '🎬 流媒体',
    'hbo': '🎬 流媒体',
    'amazon': '🎬 流媒体',
    'bahamut': '🎬 流媒体',
    'geolocation-!cn': '🌐 非中国',
    'google-ip': '🔍 谷歌服务',
    'private-ip': '🏠 私有网络',
    'cn-ip': '🔒 国内服务',
    'telegram-ip': '📲 电报消息',
}

CORE_IP_RULE_PROVIDERS = {'google-ip', 'private-ip', 'cn-ip', 'telegram-ip'}
CORE_RULE_PROVIDER_DETAILS = {
    name: {
        'group': group,
        'behavior': 'ipcidr' if name in CORE_IP_RULE_PROVIDERS else 'domain',
        'format': 'mrs',
        'url': (
            f'{METACUBEX_CDN_PREFIX}geo/geoip/{name.removesuffix("-ip")}.mrs'
            if name in CORE_IP_RULE_PROVIDERS
            else f'{METACUBEX_CDN_PREFIX}geo/geosite/{name}.mrs'
        ),
        'path': f'./ruleset/{name}.mrs',
    }
    for name, group in CORE_RULE_PROVIDER_GROUPS.items()
}

BASE_RULE_PROVIDER_GROUPS = {
    **CORE_RULE_PROVIDER_GROUPS,
    **{name: provider['group'] for name, provider in LOCAL_RULE_PROVIDERS.items()},
    **{name: provider['group'] for name, provider in REMOTE_RULE_PROVIDERS.items()},
}

V4_APP_RULE_PROVIDERS = {
    'Dozee_Android_Crypto_Apps': {
        'file': ROOT / 'rules' / 'android' / 'Crypto_Apps.yaml',
        'group': '💰 加密货币',
        'url': 'https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/android/Crypto_Apps.yaml',
    },
}

RETIRED_V4_APP_RULE_PROVIDERS = {
    'Dozee_Android_Prediction_Apps': ROOT / 'rules' / 'android' / 'Prediction_Market_Apps.yaml',
    'Dozee_Android_CN_Apps_Core': ROOT / 'rules' / 'android' / 'China_Apps_Core.yaml',
}

SINKHOLE_REJECT_RULES = (
    'IP-CIDR,0.0.0.0/32,REJECT,no-resolve',
    'IP-CIDR6,::/128,REJECT,no-resolve',
)
PRIVATE_RULE = 'RULE-SET,private-ip,🏠 私有网络,no-resolve'
BASE_RULE_PREFIX = (*SINKHOLE_REJECT_RULES, PRIVATE_RULE)
V4_APP_RULESET_RULES = tuple(
    f"RULE-SET,{provider_name},{provider['group']}"
    for provider_name, provider in V4_APP_RULE_PROVIDERS.items()
)
V4_RULE_PREFIX = (*BASE_RULE_PREFIX, *V4_APP_RULESET_RULES)

GOOGLE_PLAY_DIRECT_RULES = (
    'DOMAIN-SUFFIX,xn--ngstr-lra8j.com,DIRECT',
    'DOMAIN-SUFFIX,services.googleapis.cn,DIRECT',
    'DOMAIN,clientservices.googleapis.com,DIRECT',
    'DOMAIN,connectivitycheck.gstatic.com,DIRECT',
    'DOMAIN,beacons.gvt2.com,DIRECT',
    'DOMAIN,beacons.gcp.gvt2.com,DIRECT',
)
DOMESTIC_RULES = (
    'RULE-SET,geolocation-cn,🔒 国内服务',
    'RULE-SET,cn,🔒 国内服务',
    'RULE-SET,cn-ip,🔒 国内服务,no-resolve',
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

    for provider_name, retired_file in RETIRED_V4_APP_RULE_PROVIDERS.items():
        if retired_file.exists():
            fail(f'retired V4 app provider file should be removed: {provider_name} -> {retired_file}')


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
    if 'path' in expected and provider.get('path') != expected['path']:
        fail(f'{template_file} provider {provider_name} path mismatch: {provider.get("path")}')


def validate_template(template_file: Path) -> None:
    if not template_file.exists():
        fail(f'missing {template_file}')
    data = load_yaml(template_file)
    if not isinstance(data, dict):
        fail(f'{template_file} is not a YAML mapping')

    groups = data.get('proxy-groups') or []
    if not isinstance(groups, list):
        fail(f'{template_file} proxy-groups should be a list')
    group_name_list: list[str] = []
    for index, group in enumerate(groups, 1):
        if not isinstance(group, dict) or not isinstance(group.get('name'), str):
            fail(f'{template_file} proxy-groups[{index}] should be a named mapping')
        group_name_list.append(group['name'])
    group_names = set(group_name_list)
    rules = data.get('rules') or []
    if not isinstance(rules, list) or any(not isinstance(rule, str) for rule in rules):
        fail(f'{template_file} rules should be a list of strings')
    providers = data.get('rule-providers') or {}
    if not isinstance(providers, dict):
        fail(f'{template_file} rule-providers should be a mapping')
    dns = data.get('dns') or {}
    if not isinstance(dns, dict):
        fail(f'{template_file} dns should be a mapping')
    nameserver_policy = dns.get('nameserver-policy') or {}
    if not isinstance(nameserver_policy, dict):
        fail(f'{template_file} dns.nameserver-policy should be a mapping')

    if data.get('proxies', 'missing') is not None:
        fail(f'{template_file} should keep proxies: null for dynamic node injection')
    duplicate_groups = sorted({name for name in group_name_list if group_name_list.count(name) > 1})
    if duplicate_groups:
        fail(f'{template_file} contains duplicate proxy-group names: {duplicate_groups}')
    allowed_group_members = group_names | {
        'DIRECT', 'REJECT', '__PROXY_NODES__', '__PROXY_PROVIDERS__',
    }
    for group in groups:
        members = group.get('proxies') or []
        if not isinstance(members, list) or any(not isinstance(member, str) for member in members):
            fail(f'{template_file} proxy-group {group["name"]} proxies should be a list of strings')
        unknown_members = sorted(set(members) - allowed_group_members)
        if unknown_members:
            fail(f'{template_file} proxy-group {group["name"]} hardcodes unknown members: {unknown_members[:5]}')
        if len(members) != len(set(members)):
            fail(f'{template_file} proxy-group {group["name"]} contains duplicate members')
        dialer_group = group.get('dialer-proxy-group')
        if dialer_group is not None and dialer_group not in group_names:
            fail(f'{template_file} proxy-group {group["name"]} references missing dialer group {dialer_group}')
    duplicate_rules = sorted({rule for rule in rules if rules.count(rule) > 1})
    if duplicate_rules:
        fail(f'{template_file} contains duplicate rules: {duplicate_rules[:5]}')
    if not rules or rules[-1] != 'MATCH,🐟 漏网之鱼':
        fail(f'{template_file} must end with exactly MATCH,🐟 漏网之鱼')

    for play_domain in ('+.xn--ngstr-lra8j.com', 'services.googleapis.cn', '+.services.googleapis.cn', 'clientservices.googleapis.com', 'connectivitycheck.gstatic.com', 'beacons.gvt2.com', 'beacons.gcp.gvt2.com'):
        if play_domain not in nameserver_policy:
            fail(f'{template_file} missing DNS policy for Google Play domain {play_domain}')

    for play_rule in GOOGLE_PLAY_DIRECT_RULES:
        if play_rule not in rules:
            fail(f'{template_file} missing Google Play direct rule {play_rule}')

    expected_provider_groups = dict(BASE_RULE_PROVIDER_GROUPS)
    if template_file == V4_TEMPLATE:
        expected_provider_groups.update(
            {name: provider['group'] for name, provider in V4_APP_RULE_PROVIDERS.items()}
        )
    if set(providers) != set(expected_provider_groups):
        missing = sorted(set(expected_provider_groups) - set(providers))
        unexpected = sorted(set(providers) - set(expected_provider_groups))
        fail(f'{template_file} rule-provider set mismatch; missing={missing[:5]}, unexpected={unexpected[:5]}')
    for provider_name, group_name in expected_provider_groups.items():
        if group_name not in group_names:
            fail(f'{template_file} missing proxy group {group_name}')
        expected_rule = f'RULE-SET,{provider_name},{group_name}'
        expected_rule_with_no_resolve = f'{expected_rule},no-resolve'
        if expected_rule not in rules and expected_rule_with_no_resolve not in rules:
            fail(f'{template_file} missing rule {expected_rule}')

    expected_provider_details = {
        **CORE_RULE_PROVIDER_DETAILS,
        **LOCAL_RULE_PROVIDERS,
        **REMOTE_RULE_PROVIDERS,
    }
    for provider_name, expected in expected_provider_details.items():
        validate_expected_provider(template_file, providers, provider_name, expected)

    expected_rule_prefix = V4_RULE_PREFIX if template_file == V4_TEMPLATE else BASE_RULE_PREFIX
    if tuple(rules[:len(expected_rule_prefix)]) != expected_rule_prefix:
        fail(f'{template_file} must reject IPv4/IPv6 sinkholes before private/LAN rules')

    if template_file == V4_TEMPLATE:
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
        unexpected = set(providers) & (set(V4_APP_RULE_PROVIDERS) | set(RETIRED_V4_APP_RULE_PROVIDERS))
        if unexpected:
            fail(f'{template_file} is the stable V3 template and must not include V4 app providers: {sorted(unexpected)}')

    retired = set(providers) & set(RETIRED_V4_APP_RULE_PROVIDERS)
    if retired:
        fail(f'{template_file} contains retired V4 app providers: {sorted(retired)}')

    provider_paths: list[str] = []
    for name, rp in providers.items():
        if not isinstance(rp, dict):
            fail(f'{template_file} rule-provider {name} should be a mapping')
        if rp.get('type') != 'http':
            fail(f'{template_file} rule-provider {name} type should be http')
        url = rp.get('url', '')
        path = rp.get('path', '')
        if not isinstance(url, str) or not url.startswith('https://'):
            fail(f'{template_file} rule-provider {name} should use an HTTPS URL')
        if not isinstance(path, str) or not path.startswith('./'):
            fail(f'{template_file} rule-provider {name} should use a relative cache path')
        provider_paths.append(path)
        if rp.get('behavior') not in {'domain', 'ipcidr', 'classical'}:
            fail(f'{template_file} rule-provider {name} has invalid behavior')
        if rp.get('format') not in {'mrs', 'text', 'yaml'}:
            fail(f'{template_file} rule-provider {name} has invalid format')
        if not isinstance(rp.get('interval'), int) or rp['interval'] <= 0:
            fail(f'{template_file} rule-provider {name} interval should be a positive integer')
        if url.endswith('.mrs') or path.endswith('.mrs'):
            if rp.get('format') != 'mrs':
                fail(f'{template_file} rule-provider {name} uses .mrs but format is not mrs')
    duplicate_paths = sorted({path for path in provider_paths if provider_paths.count(path) > 1})
    if duplicate_paths:
        fail(f'{template_file} rule-providers share cache paths: {duplicate_paths[:5]}')

    referenced_providers: set[str] = set()
    for rule in rules:
        parts = rule.split(',')
        target = parts[-2] if parts[-1] == 'no-resolve' else parts[-1]
        if target not in group_names and target not in {'DIRECT', 'REJECT', 'REJECT-DROP', 'PASS'}:
            fail(f'{template_file} rule references missing target group {target}: {rule}')
        nested_provider_refs = re.findall(r'(?:^|\()RULE-SET,([^,)]+)', rule)
        referenced_providers.update(nested_provider_refs)
        for provider_name in nested_provider_refs:
            if provider_name not in providers:
                fail(f'{template_file} rule references missing provider {provider_name}: {rule}')
        if not rule.startswith('RULE-SET,'):
            continue
        if len(parts) < 3:
            fail(f'{template_file} malformed RULE-SET rule: {rule}')
        group_name = parts[2]
        if group_name not in group_names and group_name not in {'DIRECT', 'REJECT'}:
            fail(f'{template_file} rule references missing group {group_name}: {rule}')

    unused_providers = sorted(set(providers) - referenced_providers)
    if unused_providers:
        fail(f'{template_file} contains unused rule-providers: {unused_providers[:5]}')

    private_index = rules.index(PRIVATE_RULE)
    match_index = rules.index('MATCH,🐟 漏网之鱼')
    broad_index = next((i for i, r in enumerate(rules) if r == 'RULE-SET,geolocation-!cn,🌐 非中国'), match_index)
    domestic_index = min(rules.index(rule) for rule in DOMESTIC_RULES)
    if any(rules.index(rule) >= domestic_index for rule in GOOGLE_PLAY_DIRECT_RULES):
        fail(f'{template_file} explicit Google Play direct rules must stay before broad domestic rules')
    google_quic_reject = 'AND,((RULE-SET,google),(NETWORK,UDP),(DST-PORT,443)),REJECT'
    google_rule = 'RULE-SET,google,🔍 谷歌服务'
    if google_quic_reject not in rules:
        fail(f'{template_file} missing Google QUIC reject rule')
    if google_rule not in rules:
        fail(f'{template_file} missing Google service rule')
    if rules.index(google_quic_reject) >= rules.index(google_rule):
        fail(f'{template_file} Google QUIC reject rule must stay before Google service rule')

    for provider_name, expected in {**LOCAL_RULE_PROVIDERS, **REMOTE_RULE_PROVIDERS}.items():
        expected_rule = f"RULE-SET,{provider_name},{expected['group']}"
        rule_index = rules.index(expected_rule)
        if private_index >= 0 and rule_index <= private_index:
            fail(f'{template_file} {provider_name} rule should stay after private/LAN direct rules')
        if rule_index >= domestic_index:
            fail(f'{template_file} explicit business rule {provider_name} must stay before broad domestic rules')
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
    v3_rules = v3.get('rules', [])
    private_index = v3_rules.index(PRIVATE_RULE)
    expected_v4_rules = [
        *v3_rules[:private_index + 1],
        *V4_APP_RULESET_RULES,
        *v3_rules[private_index + 1:],
    ]
    if v4.get('rules', []) != expected_v4_rules:
        fail('V4 should add only the Crypto Android app rule-set after private/LAN rules')
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
