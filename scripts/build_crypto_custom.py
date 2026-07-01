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
import json
import re
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUTFILE = ROOT / "rules" / "Dozee_Crypto_Custom.list"

META_REFERENCE_LIST = "https://raw.githubusercontent.com/MetaCubeX/meta-rules-dat/meta/geo/geosite/category-cryptocurrency.list"
BLACKMATRIX_CRYPTO = "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Crypto/Crypto.list"
V2FLY_BASE = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/"

SUPPLEMENT_CLASSICAL_SOURCES = {
    "blackmatrix7/Cryptocurrency": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Cryptocurrency/Cryptocurrency.list",
    "blackmatrix7/Binance": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/Binance/Binance.list",
    "blackmatrix7/OKX": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Clash/OKX/OKX.list",
    "enriquephl/Web3": "https://raw.githubusercontent.com/enriquephl/QuantumultX_config/main/ClashRuleSet/Clash/Web3.list",
}

SUPPLEMENT_LURIXO_GEOSITE_SOURCES = {
    "lurixo/geosite-cryptocurrency": "https://raw.githubusercontent.com/lurixo/sing-box-rules/dev/geosite/geosite-cryptocurrency.json",
    "lurixo/geosite-binance": "https://raw.githubusercontent.com/lurixo/sing-box-rules/dev/geosite/geosite-binance.json",
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

# Keep prediction-market primary domains out of the crypto supplement. The
# existing Prediction_Market.list intentionally stays before broad crypto rules.
EXCLUDE_SUBSTRINGS = {
    "polymarket",
    "predict.fun",
    "predict.fail",
    "kalshi",
    "predictit.org",
    "manifold.markets",
    "metaculus.com",
    "limitless.exchange",
    "opinion.trade",
    # Existing broad business categories should keep owning these.
    "discord.",
    "twitter.",
    "x.com",
    "facebook.",
    "instagram.",
    "github.com",
    "google.",
    "youtube.",
    # Tracking/CDN/fraud/infra-only domains from mobile exchange lists. These
    # are useful observations but too broad for a shared crypto strategy group.
    "appsflyer",
    "appsflayer.com",
    "appsflyersdk.com",
    "forter.com",
    "siftscience.com",
    "braze.eu",
    "cloudfront.net",
    "elb.amazonaws.com",
    "amazontrust.com",
    "myqcloud.com",
}

# Generic infrastructure suffixes are often used by crypto apps but are not
# crypto-specific. Do not route a whole generic service to 💰 加密货币.
EXCLUDE_SUFFIXES = {
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


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


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


def parse_lurixo_geosite_url(url: str) -> list[str]:
    """Convert sing-box geosite JSON rules into Mihomo classical candidates.

    package_name/process-like rules are deliberately ignored: they are useful in
    sing-box Android, but not portable to the shared Miaomiaowu V3 template.
    """
    obj = json.loads(fetch(url))
    out: list[str] = []
    for block in obj.get("rules", []):
        if not isinstance(block, dict):
            continue
        for value in block.get("domain", []) or []:
            if rule := normalize_rule("DOMAIN", value):
                out.append(rule)
        for value in block.get("domain_suffix", []) or []:
            if rule := normalize_rule("DOMAIN-SUFFIX", value):
                out.append(rule)
        for value in block.get("domain_keyword", []) or []:
            if rule := normalize_rule("DOMAIN-KEYWORD", value):
                out.append(rule)
    return out


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
    lower = rule.lower()
    if any(token in lower for token in EXCLUDE_SUBSTRINGS):
        return True
    _rule_type, value = split_rule(rule)
    return suffix_is_excluded(value)


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
    for name, url in SUPPLEMENT_LURIXO_GEOSITE_SOURCES.items():
        candidates_by_source[name] = parse_lurixo_geosite_url(url)
    candidates_by_source["dozee/manual"] = [
        rule for raw in MANUAL_RULES if (rule := normalize_classical(raw))
    ]

    candidates = [rule for rules in candidates_by_source.values() for rule in rules]

    selected: list[str] = []
    selected_seen: set[str] = set()
    for rule in candidates:
        if (
            rule in selected_seen
            or is_covered_by_baseline(rule, baseline, baseline_domain_suffixes)
            or not is_publishable(rule)
        ):
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


def render(rules: list[str], stats: dict[str, int]) -> str:
    lines = [
        "# 加密货币 / Web3 个人完善规则：命中后走「💰 加密货币」策略组。",
        "#",
        "# 生成方式：python3 scripts/build_crypto_custom.py",
        "# 自动同步：GitHub Actions 每天 10:17 北京时间运行 .github/workflows/sync-crypto-rules.yml。",
        "# 设计：主规则用 MetaCubeX category-cryptocurrency.mrs；第三方补充用 blackmatrix7 Crypto.list；",
        "# 本文件合并 v2fly / blackmatrix7 / lurixo / enrique Web3 / 人工增强后，只发布筛选后的补漏规则。",
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
    lines.extend(rules)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail if the committed output differs")
    args = parser.parse_args()

    rules, stats = build_rules()
    content = render(rules, stats)
    if args.check:
        current = OUTFILE.read_text(encoding="utf-8") if OUTFILE.exists() else ""
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
