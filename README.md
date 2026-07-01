# miaomiaowu-rules

只长期维护这些：

- `templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- `rules/Custom_Proxy.list`
- `rules/Prediction_Market.list`
- `rules/Dozee_Crypto_Custom.list`

## 看这一页就够了

- **加减节点**：改节点来源，不改模板
- **改自定义规则**：改 `rules/Custom_Proxy.list`
- **改预测市场规则**：改 `rules/Prediction_Market.list`
- **改加密货币补强规则**：改 `rules/Dozee_Crypto_Custom.list`，或运行 `python3 scripts/build_crypto_custom.py` 重建
- **加业务分组**：同时改 `proxy-groups / rules / rule-providers`
- **加中转节点**：节点名带 `中转|relay|entry`
- **加落地节点**：节点名带 `落地|exit|egress`

## 模板原则

- 主模板是 `fake-ip`
- 不按国家 / 地区分组
- 预留 `🌠 中转节点` / `🌄 落地节点`
- 自定义规则走 `Dozee_Custom_Proxy -> 🧩 自定义`
- 预测市场走 `Dozee_Prediction_Market -> 📈 预测市场`
- 加密货币走 `crypto-main / crypto-blackmatrix / Dozee_Crypto_Custom -> 💰 加密货币`
- 预测市场规则排在泛加密货币规则前面，避免 Polymarket 被泛 crypto 抢走

## 加密货币规则源

- 主规则：MetaCubeX `category-cryptocurrency.mrs`
- 第三方补充：blackmatrix7 `Crypto.list`
- 个人补强：`Dozee_Crypto_Custom.list`，由 v2fly + blackmatrix7 + 人工增强筛选去重生成

## Raw 地址

- 模板：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- 自定义规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list`
- 预测市场规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Prediction_Market.list`
- 加密货币补强规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Dozee_Crypto_Custom.list`

## 不再维护

- `templates/miaomiaowu/dozee_redirhost__v3.yaml`
- `configs/proxy-groups.json`

## 校验

```bash
python3 scripts/build_crypto_custom.py --check
python3 scripts/validate.py
```
