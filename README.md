# miaomiaowu-rules

只长期维护两样：

- `templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- `rules/Custom_Proxy.list`

## 看这一页就够了

- **加减节点**：改节点来源，不改模板
- **改自定义规则**：改 `rules/Custom_Proxy.list`
- **加业务分组**：同时改 `proxy-groups / rules / rule-providers`
- **加中转节点**：节点名带 `中转|relay|entry`
- **加落地节点**：节点名带 `落地|exit|egress`

## 模板原则

- 主模板是 `fake-ip`
- 不按国家 / 地区分组
- 预留 `🌠 中转节点` / `🌄 落地节点`
- 自定义规则走 `Dozee_Custom_Proxy -> 🧩 自定义`

## Raw 地址

- 模板：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/templates/miaomiaowu/dozee_fake_ip__v3.yaml`
- 规则：`https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list`

## 不再维护

- `templates/miaomiaowu/dozee_redirhost__v3.yaml`
- `configs/proxy-groups.json`

## 校验

```bash
python3 scripts/validate.py
```