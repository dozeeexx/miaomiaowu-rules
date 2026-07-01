# miaomiaowu-rules

妙妙屋 V3 模板 + 自制规则集仓库。默认模板尽量稳定；新增需求优先做成独立业务分组和独立规则集。

## 看这一页就够了

- **加减节点**：改节点来源，不改模板。
- **改自定义规则**：改 `rules/Custom_Proxy.list`。
- **改预测市场规则**：改 `rules/Prediction_Market.list`。
- **改加密货币/Web3 规则**：改 `scripts/build_crypto_custom.py` 的筛选/人工增强逻辑，然后运行生成器；不要手写覆盖生成结果。
- **加业务分组**：同时改 `proxy-groups / rules / rule-providers`，并更新 `scripts/validate.py`。
- **加中转节点**：节点名带 `中转|relay|entry`。
- **加落地节点**：节点名带 `落地|exit|egress`。

## 长期维护文件

- `templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- `rules/Custom_Proxy.list`
- `rules/Prediction_Market.list`
- `rules/Dozee_Crypto_Custom.list`
- `scripts/build_crypto_custom.py`
- `scripts/validate.py`
- `.github/workflows/validate.yml`
- `.github/workflows/sync-crypto-rules.yml`

## 模板原则

- 主模板是 `fake-ip`。
- 不按国家 / 地区分组。
- 预留 `🌠 中转节点` / `🌄 落地节点`。
- 自定义规则走 `Dozee_Custom_Proxy -> 🧩 自定义`。
- 预测市场走 `Dozee_Prediction_Market -> 📈 预测市场`。
- 加密货币/Web3 走 `crypto-main / crypto-blackmatrix / Dozee_Crypto_Custom -> 💰 加密货币`。
- 预测市场规则排在泛加密货币规则前面，避免 Polymarket 被泛 crypto 抢走。
- 节点仍由妙妙屋动态注入，不在模板里硬编码节点名。

## 加密货币/Web3 规则流水线

最终客户端只引用我们自己的 V3 模板和自制补强规则；第三方源只当原料，不直接全量信任。

### 上游来源

- 主规则：MetaCubeX `category-cryptocurrency.mrs`，在模板中作为 `crypto-main` 直接引用。
- 第三方补充：blackmatrix7 `Crypto.list`，在模板中作为 `crypto-blackmatrix` 直接引用。
- 自制补强原料：
  - v2fly `domain-list-community/category-cryptocurrency`
  - blackmatrix7 `Cryptocurrency / Binance / OKX`
  - lurixo `sing-box-rules` 的 `geosite-cryptocurrency / geosite-binance`
  - enriquephl `Web3.list`
  - `scripts/build_crypto_custom.py` 内的人工增强域名

### 筛选策略

`rules/Dozee_Crypto_Custom.list` 由 `scripts/build_crypto_custom.py` 生成：

- 对第三方源去重，并排除已被 MetaCubeX 主规则和 blackmatrix7 `Crypto.list` 覆盖的域名。
- 默认只发布 `DOMAIN / DOMAIN-SUFFIX / DOMAIN-WILDCARD`。
- 仅保留少量加密货币专属 `DOMAIN-KEYWORD`，主要用于 Binance/交易所 App 生成域名。
- 不发布 IP 段、sing-box `package_name`、进程规则、regex 规则。
- 排除预测市场主域名、Google/X/Discord/GitHub 等已有大类。
- 排除通用 CDN、追踪、风控、云厂商域名，避免误伤。

### 每日同步

`.github/workflows/sync-crypto-rules.yml` 每天 **10:17 北京时间** 自动运行：

1. 拉取上游源。
2. 重建 `rules/Dozee_Crypto_Custom.list`。
3. 执行生成结果检查和 V3 模板校验。
4. 如果上游变化导致输出有差异，自动提交到 `main`。

也可以在 GitHub Actions 页面手动运行 `Sync crypto/Web3 rules`。

## Raw 地址

- 模板：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- 自定义规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list`
- 预测市场规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Prediction_Market.list`
- 加密货币/Web3 补强规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Dozee_Crypto_Custom.list`

## 本地校验

```bash
python3 scripts/build_crypto_custom.py
python3 scripts/build_crypto_custom.py --check
python3 scripts/validate.py
```

GitHub `Validate rules and templates` 会在 push / PR / 手动触发时执行：

```bash
python scripts/build_crypto_custom.py --check
python scripts/validate.py
```

## 不再维护

- `templates/miaomiaowu/dozee_redirhost__v3.yaml`
- `configs/proxy-groups.json`

## 隐私提醒

公开仓库里的域名会被别人看到。不要提交订阅链接、节点凭据、API token、cookie、钱包地址、家庭/NAS 私有域名等敏感信息。
