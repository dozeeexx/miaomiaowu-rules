#!/usr/bin/env python3
"""Build the curated Dozee crypto/Web3 supplement rule list.

Design:
- Third-party main provider remains MetaCubeX category-cryptocurrency.mrs.
- Third-party extra provider remains blackmatrix7 Crypto.list.
- This generated file only keeps high-value supplement rules not already covered by
  those two selected providers, after filtering broad/non-crypto/prediction-market
  domains.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
import argparse
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
    # Tracking-only domain from one third-party Binance list; not needed here.
    "appsflayer.com",
}

ALLOWED_TYPES = {
    "DOMAIN",
    "DOMAIN-SUFFIX",
    "DOMAIN-KEYWORD",
    "DOMAIN-WILDCARD",
    "IP-CIDR",
    "IP-CIDR6",
    "PROCESS-NAME",
    "PROCESS-PATH",
}


def fetch(url: str) -> str:
    with urllib.request.urlopen(url, timeout=30) as response:
        return response.read().decode("utf-8", "replace")


def normalize_classical(raw: str) -> str | None:
    line = raw.strip()
    if not line or line.startswith("#"):
        return None
    if line.startswith("- "):
        line = line[2:].strip()
    if line == "payload:" or line.startswith("payload:"):
        return None
    parts = [part.strip() for part in line.split(",")]
    if len(parts) < 2:
        return None
    rule_type = parts[0].upper()
    if rule_type not in ALLOWED_TYPES:
        return None
    value = parts[1].lower().rstrip(".")
    if not value:
        return None
    suffix = ",no-resolve" if any(part.lower() == "no-resolve" for part in parts[2:]) else ""
    return f"{rule_type},{value}{suffix}"


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


def should_exclude(rule: str) -> bool:
    lower = rule.lower()
    return any(token in lower for token in EXCLUDE_SUBSTRINGS)


def build_rules() -> tuple[list[str], dict[str, int]]:
    primary_seen = set(parse_meta_reference(META_REFERENCE_LIST))
    blackmatrix_seen = set(parse_classical_url(BLACKMATRIX_CRYPTO))
    baseline = primary_seen | blackmatrix_seen

    candidates: list[str] = []
    candidates.extend(parse_v2fly_file("category-cryptocurrency"))
    for url in SUPPLEMENT_CLASSICAL_SOURCES.values():
        candidates.extend(parse_classical_url(url))
    for raw in MANUAL_RULES:
        if rule := normalize_classical(raw):
            candidates.append(rule)

    selected: list[str] = []
    selected_seen: set[str] = set()
    for rule in candidates:
        if rule in baseline or rule in selected_seen or should_exclude(rule):
            continue
        selected_seen.add(rule)
        selected.append(rule)

    # Deterministic and reviewable output.
    selected.sort(key=lambda r: (r.split(",", 1)[0], r.split(",", 1)[1]))
    stats = {
        "metacubex_reference_rules": len(primary_seen),
        "blackmatrix_crypto_rules": len(blackmatrix_seen),
        "supplement_candidates": len(candidates),
        "custom_selected_rules": len(selected),
    }
    return selected, stats


def render(rules: list[str], stats: dict[str, int]) -> str:
    lines = [
        "# 加密货币 / Web3 个人完善规则：命中后走「💰 加密货币」策略组。",
        "#",
        "# 生成方式：python3 scripts/build_crypto_custom.py",
        "# 设计：主规则用 MetaCubeX category-cryptocurrency.mrs；第三方补充用 blackmatrix7 Crypto.list；",
        "# 本文件只保留两者之外的高价值补漏，来源包含 v2fly/blackmatrix7/人工增强，已筛选去重。",
        "# 不收预测市场主域名，也不收 Google/X/Discord/GitHub 等已有大类。",
        "#",
        f"# MetaCubeX reference rules: {stats['metacubex_reference_rules']}",
        f"# blackmatrix7 Crypto rules: {stats['blackmatrix_crypto_rules']}",
        f"# supplement candidates before filter: {stats['supplement_candidates']}",
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
