#!/usr/bin/env python3
"""Build the curated Dozee crypto/Web3 supplement rule list.

Design:
- The V3 template keeps MetaCubeX category-cryptocurrency.mrs as the broad
  Mihomo-native main provider.
- The template keeps blackmatrix7 Crypto.list as the broad text extra provider.
- This generated file merges several third-party upstreams, but only publishes
  screened supplement rules that are not already covered by the two broad
  providers.
- The generator intentionally avoids IP CIDR, app package/process rules, and
  most broad DOMAIN-KEYWORD entries so the shared template stays conservative.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import argparse
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTFILE = ROOT / "rules" / "Dozee_Crypto_Custom.list"

# Synchronization guardrails stop an upstream outage or parser regression from
# replacing a healthy generated list with an empty or dramatically smaller one.
# The previous committed header is used as the comparison baseline, so these
# checks do not require a second mutable state file.
SOURCE_MIN_RULES = {
    "metacubex_reference_rules": 1,
    "blackmatrix7_crypto_rules": 1,
    "source_v2fly_category_cryptocurrency": 1,
    "source_blackmatrix7_cryptocurrency": 1,
    "source_blackmatrix7_binance": 1,
    "source_blackmatrix7_okx": 1,
    "source_enriquephl_web3": 1,
    "source_dozee_manual": 1,
}
MIN_SELECTED_RULES = 20
MAX_DROP_PERCENT = 30

META_REFERENCE_LIST = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-cryptocurrency.list"
BLACKMATRIX_CRYPTO = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Crypto/Crypto.list"
V2FLY_BASE = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/"

SUPPLEMENT_CLASSICAL_SOURCES = {
    "blackmatrix7/Cryptocurrency": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Cryptocurrency/Cryptocurrency.list",
    "blackmatrix7/Binance": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Binance/Binance.list",
    "blackmatrix7/OKX": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OKX/OKX.list",
    "enriquephl/Web3": "https://raw.githubusercontent.com/enriquephl/QuantumultX_config/main/ClashRuleSet/Clash/Web3.list",
}

# Manual additions focus on exchange app/API domains, wallets, on-chain infra,
# scanners, DEX/NFT/data services. Avoid generic social/CDN/dev domains.
MANUAL_RULES = """
DOMAIN-SUFFIX,binanceapi.com
DOMAIN-SUFFIX,binancefuture.com
DOMAIN-SUFFIX,bnbstatic.com
DOMAIN-SUFFIX,okx-dns.com
DOMAIN-SUFFIX,okx-dns1.com
DOMAIN-SUFFIX,okx-dns2.com
DOMAIN-SUFFIX,gate.com
DOMAIN-SUFFIX,gate.io
DOMAIN-SUFFIX,gate.ac
DOMAIN-SUFFIX,gateio.ws
DOMAIN-SUFFIX,gateio.im
DOMAIN-SUFFIX,byapps.net
DOMAIN-SUFFIX,byapis.com
DOMAIN-SUFFIX,bitgetapi.com
DOMAIN-SUFFIX,bitgetapp.com
DOMAIN-SUFFIX,bitgetapps.com
DOMAIN-SUFFIX,bitgetstatic.com
DOMAIN-SUFFIX,bitgetimg.com
DOMAIN-SUFFIX,mexc.com
DOMAIN-SUFFIX,mexc.co
DOMAIN-SUFFIX,mexc.fm
DOMAIN-SUFFIX,mexcimg.com
DOMAIN-SUFFIX,kucoin.plus
DOMAIN-SUFFIX,coinbase.com
DOMAIN-SUFFIX,coinbaseapi.com
DOMAIN-SUFFIX,kraken.com
DOMAIN-SUFFIX,krakenfx.com
DOMAIN-SUFFIX,metamask.io
DOMAIN-SUFFIX,metamask.app.link
DOMAIN-SUFFIX,walletconnect.com
DOMAIN-SUFFIX,walletconnect.org
DOMAIN-SUFFIX,rabby.io
DOMAIN-SUFFIX,phantom.app
DOMAIN-SUFFIX,backpack.app
DOMAIN-SUFFIX,zerion.io
DOMAIN-SUFFIX,rainbow.me
DOMAIN-SUFFIX,keplr.app
DOMAIN-SUFFIX,ledger.com
DOMAIN-SUFFIX,trezor.io
DOMAIN-SUFFIX,alchemy.com
DOMAIN-SUFFIX,alchemyapi.io
DOMAIN-SUFFIX,infura.io
DOMAIN-SUFFIX,quicknode.com
DOMAIN-SUFFIX,ankr.com
DOMAIN-SUFFIX,drpc.org
DOMAIN-SUFFIX,publicnode.com
DOMAIN-SUFFIX,thirdweb.com
DOMAIN-SUFFIX,etherscan.io
DOMAIN-SUFFIX,bscscan.com
DOMAIN-SUFFIX,polygonscan.com
DOMAIN-SUFFIX,arbiscan.io
DOMAIN-SUFFIX,basescan.org
DOMAIN-SUFFIX,solscan.io
DOMAIN-SUFFIX,coingecko.com
DOMAIN-SUFFIX,coinmarketcap.com
DOMAIN-SUFFIX,tradingview.com
DOMAIN-SUFFIX,dextools.io
DOMAIN-SUFFIX,dexscreener.com
DOMAIN-SUFFIX,defillama.com
DOMAIN-SUFFIX,uniswap.org
DOMAIN-SUFFIX,1inch.io
DOMAIN-SUFFIX,opensea.io
DOMAIN-SUFFIX,blur.io
DOMAIN-SUFFIX,magiceden.io
DOMAIN-SUFFIX,base.org
DOMAIN-SUFFIX,chainlist.org
DOMAIN-SUFFIX,chain.link
DOMAIN-SUFFIX,thegraph.com
DOMAIN-SUFFIX,graphprotocol.com
DOMAIN-SUFFIX,ipfs.io
DOMAIN-SUFFIX,ipfs.tech
DOMAIN-SUFFIX,pinata.cloud
DOMAIN-SUFFIX,arweave.net
DOMAIN-SUFFIX,abs.xyz
DOMAIN-SUFFIX,airdrop.sns.id
DOMAIN-SUFFIX,alphafi.xyz
DOMAIN-SUFFIX,ao-testnet.xyz
DOMAIN-SUFFIX,ar-io.net
DOMAIN-SUFFIX,ardrive.io
DOMAIN-SUFFIX,cetus.zone
DOMAIN-SUFFIX,circle.com
DOMAIN-SUFFIX,galxe.com
DOMAIN-SUFFIX,llama.fi
DOMAIN-SUFFIX,moonpay.com
DOMAIN-SUFFIX,moonpaycloud.com
DOMAIN-SUFFIX,moonshot.money
DOMAIN-SUFFIX,mystenlabs.com
DOMAIN-SUFFIX,naviprotocol.io
DOMAIN-SUFFIX,nexus.xyz
DOMAIN-SUFFIX,save.finance
DOMAIN-SUFFIX,slush.app
DOMAIN-SUFFIX,sm.xyz
DOMAIN-SUFFIX,sns.id
DOMAIN-SUFFIX,sui.io
DOMAIN-SUFFIX,sui.rpcpool.com
DOMAIN-SUFFIX,suiet.app
DOMAIN-SUFFIX,suilend.fi
DOMAIN-SUFFIX,suins.io
DOMAIN-SUFFIX,suiscan.xyz
DOMAIN-SUFFIX,suivision.xyz
DOMAIN-SUFFIX,volo.fi
DOMAIN-SUFFIX,volosui.com
DOMAIN-SUFFIX,wallet.okex.org
DOMAIN-SUFFIX,walrus.xyz
DOMAIN-SUFFIX,yzilabs.io
""".strip().splitlines()

# Prediction-market and tracking brand tokens intentionally match dynamic names.
# Full domains MUST use suffix boundaries, never arbitrary substring matching.
EXCLUDE_SUBSTRINGS = {"polymarket", "kalshi", "appsflyer"}
EXCLUDE_BRAND_LABELS = {
    "discord", "twitter", "facebook", "instagram", "google", "youtube",
}

# Existing business categories and generic infrastructure retain ownership.
EXCLUDE_SUFFIXES = {
    "predict.fun",
    "predict.fail",
    "predictit.org",
    "manifold.markets",
    "metaculus.com",
    "limitless.exchange",
    "opinion.trade",
    "x.com",
    "github.com",
    "myqcloud.com",
    "ably.io",
    "amazonaws.com",
    "amazontrust.com",
    "appsflyer.com",
    "appsflyersdk.com",
    "appsflayer.com",  # typo observed in one third-party Binance list
    "braze.eu",
    "cloudfront.net",
    "commonservice.io",
    "forter.com",
    "siftscience.com",
}

# DOMAIN-KEYWORD is intentionally limited to a small set of mobile-app / CDN
# brand tokens that often appear as generated hostnames. Generic words such as
# bitcoin/ethereum/crypto/ripple are excluded, and most normal services should
# be represented by DOMAIN-SUFFIX instead.
KEYWORD_ALLOWLIST = {
    "bitget",
    "bnappzh",
    "bnbchain",
    "bnbstatic",
    "bnbzh",
    "bntrace",
    "bscdn",
    "bscscan",
    "bsctrace",
    "coinmarketcap",
    "dcellar",
    "gopax",
    "greenfieldscan",
    "opbnbscan",
    "saasexch",
    "tokocrypto",
    "trustwallet",
    "wazirx",
}

# A few exchange core domains are intentionally kept in the custom supplement
# even when a broad upstream provider also covers them. This gives the existing
# Dozee_Crypto_Custom provider a small safety net for app traffic observed to
# fall through to MATCH/🐟 漏网之鱼 when broad providers are stale or unavailable.
FORCE_PUBLISH_RULES = {
    "DOMAIN-SUFFIX,gate.io",
    "DOMAIN-SUFFIX,gate.ac",
}

ALLOWED_INPUT_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-WILDCARD",
    "IP-CIDR",
    "IP-CIDR6",
    "PROCESS-NAME",
    "PROCESS-PATH",
}
DOMAIN_OUTPUT_TYPES = {"DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-WILDCARD"}


FETCH_USER_AGENT = "dozee-miaomiaowu-rules-builder/1.0"


@lru_cache(maxsize=1)
def github_token() -> str | None:
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        return token
    try:
        result = subprocess.run(
            ["gh", "auth", "token"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return None
    token = result.stdout.strip()
    return token or None


def fetch_raw_github_via_api(url: str) -> str | None:
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "raw.githubusercontent.com":
        return None
    parts = parsed.path.lstrip("/").split("/", 3)
    if len(parts) != 4:
        return None
    owner, repo, ref, file_path = parts
    api_path = urllib.parse.quote(file_path)
    api_ref = urllib.parse.quote(ref)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{api_path}?ref={api_ref}"
    headers = {
        "User-Agent": FETCH_USER_AGENT,
        "Accept": "application/vnd.github.raw",
    }
    if token := github_token():
        headers["Authorization"] = f"Bearer {token}"
    request = urllib.request.Request(api_url, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": FETCH_USER_AGENT},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code != 429:
            raise
        if content := fetch_raw_github_via_api(url):
            return content
        # raw.githubusercontent.com occasionally rate-limits urllib while curl
        # succeeds from the same host. Fall back to curl so scheduled syncs do
        # not fail on transient raw GitHub 429 responses.
        result = subprocess.run(
            ["curl", "-fsSL", "-A", FETCH_USER_AGENT, url],
            check=True,
            capture_output=True,
            text=True,
            timeout=45,
        )
        return result.stdout


def normalize_rule(rule_type: str, value: str, *, no_resolve: bool = False) -> str | None:
    rule_type = rule_type.upper().strip()
    value = value.lower().strip().rstrip(".")
    if rule_type not in ALLOWED_INPUT_TYPES or not value:
        return None
    suffix = ",no-resolve" if no_resolve and rule_type in {"IP-CIDR", "IP-CIDR6"} else ""
    return f"{rule_type},{value}{suffix}"


def split_rule(rule: str) -> tuple[str, str]:
    parts = rule.split(",")
    return parts[0].upper(), parts[1].lower().rstrip(".")


def normalize_classical(raw: str) -> str | None:
    line = raw.strip()
    if not line or line.startswith("#") or line.startswith("//"):
        return None
    if line.startswith("- "):
        line = line[2:].strip()
    if line == "payload:" or line.startswith("payload:"):
        return None
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
        return None
    return normalize_rule(
        parts[0],
        parts[1],
        no_resolve=any(part.lower() == "no-resolve" for part in parts[2:]),
    )


def parse_classical_url(url: str) -> list[str]:
    return [rule for line in fetch(url).splitlines() if (rule := normalize_classical(line))]


def parse_meta_reference(url: str) -> list[str]:
    out: list[str] = []
    for raw in fetch(url).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#", 1)[0].strip().split()[0].lower().rstrip(".")
        if not line:
            continue
        if line.startswith("+."):
            out.append("DOMAIN-SUFFIX," + line[2:])
        elif line.startswith("full:"):
            out.append("DOMAIN," + line[5:])
        elif line.startswith("domain:"):
            out.append("DOMAIN-SUFFIX," + line[7:])
        elif line.startswith("keyword:"):
            out.append("DOMAIN-KEYWORD," + line[8:])
        elif re.match(r"^[a-z0-9*_.-]+\.[a-z0-9_.-]+$", line):
            # Meta text sibling emits some exact/FQDN entries without a +. prefix.
            out.append("DOMAIN," + line)
    return out


@lru_cache(maxsize=None)
def parse_v2fly_file(name: str) -> tuple[str, ...]:
    out: list[str] = []
    for raw in fetch(V2FLY_BASE + name).splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        core = line.split()[0].strip()
        if core.startswith("include:"):
            out.extend(parse_v2fly_file(core.split(":", 1)[1]))
        elif core.startswith("full:"):
            out.append("DOMAIN," + core[5:].lower().rstrip("."))
        elif core.startswith("domain:"):
            out.append("DOMAIN-SUFFIX," + core[7:].lower().rstrip("."))
        elif core.startswith("keyword:"):
            out.append("DOMAIN-KEYWORD," + core[8:].lower())
        elif core.startswith("regexp:"):
            # Regex rules are intentionally skipped: expensive and risky in shared templates.
            continue
        elif re.match(r"^[A-Za-z0-9_.-]+\.[A-Za-z0-9_.-]+$", core):
            out.append("DOMAIN-SUFFIX," + core.lower().rstrip("."))
    return tuple(out)


def suffix_is_excluded(value: str) -> bool:
    return any(value == suffix or value.endswith("." + suffix) for suffix in EXCLUDE_SUFFIXES)


def should_exclude(rule: str) -> bool:
    _rule_type, value = split_rule(rule)
    return (
        any(token in value for token in EXCLUDE_SUBSTRINGS)
        or bool(set(value.split(".")) & EXCLUDE_BRAND_LABELS)
        or suffix_is_excluded(value)
    )


def baseline_suffixes(baseline: set[str]) -> set[str]:
    return {split_rule(rule)[1] for rule in baseline if split_rule(rule)[0] == "DOMAIN-SUFFIX"}


def is_covered_by_baseline(rule: str, baseline: set[str], suffixes: set[str]) -> bool:
    if rule in baseline:
        return True
    rule_type, value = split_rule(rule)
    if rule_type in {"DOMAIN", "DOMAIN-SUFFIX"}:
        return any(value == suffix or value.endswith("." + suffix) for suffix in suffixes)
    return False


def is_publishable(rule: str) -> bool:
    rule_type, value = split_rule(rule)
    if should_exclude(rule):
        return False
    if rule_type in DOMAIN_OUTPUT_TYPES:
        return True
    if rule_type == "DOMAIN-KEYWORD":
        return value in KEYWORD_ALLOWLIST
    return False


def build_rules() -> tuple[list[str], dict[str, int]]:
    primary_seen = set(parse_meta_reference(META_REFERENCE_LIST))
    blackmatrix_seen = set(parse_classical_url(BLACKMATRIX_CRYPTO))
    baseline = primary_seen | blackmatrix_seen
    baseline_domain_suffixes = baseline_suffixes(baseline)

    candidates_by_source: dict[str, list[str]] = {}
    candidates_by_source["v2fly/category-cryptocurrency"] = list(parse_v2fly_file("category-cryptocurrency"))
    for name, url in SUPPLEMENT_CLASSICAL_SOURCES.items():
        candidates_by_source[name] = parse_classical_url(url)
    candidates_by_source["dozee/manual"] = [
        rule for raw in MANUAL_RULES if (rule := normalize_classical(raw))
    ]

    candidates = [rule for rules in candidates_by_source.values() for rule in rules]

    selected: list[str] = []
    selected_seen: set[str] = set()
    for rule in candidates:
        if rule in selected_seen or not is_publishable(rule):
            continue
        if rule not in FORCE_PUBLISH_RULES and is_covered_by_baseline(rule, baseline, baseline_domain_suffixes):
            continue
        selected_seen.add(rule)
        selected.append(rule)

    selected_suffix_values = {split_rule(rule)[1] for rule in selected if split_rule(rule)[0] == "DOMAIN-SUFFIX"}
    selected = [
        rule
        for rule in selected
        if not (
            split_rule(rule)[0] == "DOMAIN"
            and any(
                split_rule(rule)[1] == suffix or split_rule(rule)[1].endswith("." + suffix)
                for suffix in selected_suffix_values
            )
        )
    ]

    # Deterministic and reviewable output.
    selected.sort(key=lambda r: (r.split(",", 1)[0], r.split(",", 1)[1]))
    stats = {
        "metacubex_reference_rules": len(primary_seen),
        "blackmatrix7_crypto_rules": len(blackmatrix_seen),
        "supplement_sources": len(candidates_by_source),
        "supplement_candidates_before_filter": len(candidates),
        "custom_selected_rules": len(selected),
    }
    for name, rules in candidates_by_source.items():
        key = "source_" + re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
        stats[key] = len(rules)
    return selected, stats


def parse_rendered_stats(content: str) -> dict[str, int]:
    """Read numeric generator stats embedded in the committed output header."""
    stats: dict[str, int] = {}
    legacy_names = {
        "MetaCubeX reference rules": "metacubex_reference_rules",
        "blackmatrix7 Crypto rules": "blackmatrix7_crypto_rules",
        "selected custom supplement rules": "custom_selected_rules",
    }
    for raw in content.splitlines():
        match = re.match(r"^# ([A-Za-z0-9_ ]+): (\d+)$", raw.strip())
        if match:
            stats[legacy_names.get(match.group(1), match.group(1))] = int(match.group(2))
    return stats


def guardrail_errors(stats: dict[str, int], previous_stats: dict[str, int] | None) -> list[str]:
    """Return blocking errors for empty sources or suspicious shrinkage."""
    errors: list[str] = []
    for key, minimum in SOURCE_MIN_RULES.items():
        current = stats.get(key, 0)
        if current < minimum:
            errors.append(f"{key} has {current} rules; minimum is {minimum}")

    selected = stats.get("custom_selected_rules", 0)
    if selected < MIN_SELECTED_RULES:
        errors.append(
            f"custom_selected_rules has {selected} rules; minimum is {MIN_SELECTED_RULES}"
        )

    if previous_stats:
        comparable_keys = set(SOURCE_MIN_RULES) | {"custom_selected_rules"}
        for key in sorted(comparable_keys):
            previous = previous_stats.get(key)
            current = stats.get(key, 0)
            if previous and current * 100 < previous * (100 - MAX_DROP_PERCENT):
                errors.append(
                    f"{key} dropped from {previous} to {current} (>{MAX_DROP_PERCENT}% decrease)"
                )
    return errors


def render(rules: list[str], stats: dict[str, int]) -> str:
    lines = [
        "# 加密货币 / Web3 个人完善规则：命中后走「💰 加密货币」策略组。",
        "#",
        "# 生成方式：python3 scripts/build_crypto_custom.py",
        "# 自动同步：GitHub Actions 计划每天北京时间 04:30 触发（平台可能延迟），运行 .github/workflows/sync-crypto-rules.yml。",
        "# 设计：主规则用 MetaCubeX category-cryptocurrency.mrs；第三方补充用 blackmatrix7 Crypto.list；",
        "# 本文件合并 v2fly / blackmatrix7 / enrique Web3 / 人工增强后，只发布筛选后的补漏规则。",
        "# 策略：不发布 IP、package/process 规则；只保留域名规则和少量加密货币专属 DOMAIN-KEYWORD。",
        "# 不收预测市场主域名，也不收 Google/X/Discord/GitHub/通用 CDN/追踪风控等已有或高误伤大类。",
        "#",
        f"# MetaCubeX reference rules: {stats['metacubex_reference_rules']}",
        f"# blackmatrix7 Crypto rules: {stats['blackmatrix7_crypto_rules']}",
        f"# supplement sources: {stats['supplement_sources']}",
        f"# supplement candidates before filter: {stats['supplement_candidates_before_filter']}",
        f"# selected custom supplement rules: {stats['custom_selected_rules']}",
        "",
    ]
    lines.extend(f"# {key}: {value}" for key, value in sorted(stats.items()))
    lines.append("")
    lines.extend(rules)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed output differs")
    args = parser.parse_args()

    rules, stats = build_rules()
    content = render(rules, stats)
    current = OUTFILE.read_text(encoding="utf-8") if OUTFILE.exists() else ""
    previous_stats = parse_rendered_stats(current) if current else None
    errors = guardrail_errors(stats, previous_stats)
    old_rules = {rule for raw in current.splitlines() if (rule := normalize_classical(raw))}
    if old_rules:
        removed = len(old_rules - set(rules))
        if removed * 100 > len(old_rules) * MAX_DROP_PERCENT:
            errors.append(f"output removed {removed}/{len(old_rules)} rules (>{MAX_DROP_PERCENT}%)")
        if len(rules) > len(old_rules) * 2:
            errors.append("output grew by more than 100%; review upstream changes")
    if errors:
        for error in errors:
            print(f"ERROR: sync guardrail: {error}", file=sys.stderr)
        return 1
    if args.check:
        if current != content:
            print(f"ERROR: {OUTFILE} is out of date; run scripts/build_crypto_custom.py", file=sys.stderr)
            return 1
        print(f"OK: {OUTFILE} is up to date ({stats['custom_selected_rules']} rules)")
        return 0

    OUTFILE.write_text(content, encoding="utf-8")
    print(f"wrote {OUTFILE} ({stats['custom_selected_rules']} rules)")
    print(stats)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
