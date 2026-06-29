# miaomiaowu-rules

这个仓库现在只维护 **一份长期主用的妙妙屋 V3 模板** 和 **一份自定义规则列表**，方便以后长期只做：

- 增删节点
- 增删自定义规则
- 在必要时小范围调整业务分组

## 当前保留内容

```text
templates/miaomiaowu/dozee_fake_ip__v3.yaml
rules/Custom_Proxy.list
scripts/validate.py
.github/workflows/validate.yml
README.md
```

## 当前主模板

- `templates/miaomiaowu/dozee_fake_ip__v3.yaml`

特点：

- 仅保留一份主用 `fake-ip` V3 模板
- 不按国家/地区分组
- 保留 `🌠 中转节点` / `🌄 落地节点`
- 通过 `__PROXY_NODES__` / `__PROXY_PROVIDERS__` 动态注入节点
- 自定义规则通过 `Dozee_Custom_Proxy` 接到 `🧩 自定义`

## 当前自定义规则

- `rules/Custom_Proxy.list`

这里适合长期维护：

- 你自己指定的网站/域名/规则
- 想强制走某个业务分组的目标
- 以后新增的自定义站点策略

## Raw 地址

### V3 模板

```text
https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/templates/miaomiaowu/dozee_fake_ip__v3.yaml
```

### 自定义规则

```text
https://raw.githubusercontent.com/dozeeexx/miaomiaowu-rules/main/rules/Custom_Proxy.list
```

## 维护原则

- **节点增删**：尽量不改模板，通过模板里的动态节点注入处理。
- **自定义网站/规则**：优先改 `rules/Custom_Proxy.list`。
- **新增业务分组**：同步修改模板里的 `proxy-groups`、`rules`、`rule-providers`。
- **规则顺序**：自定义规则放在私有/国内直连规则之后、广义海外规则之前，避免被提前吞掉。
- **仓库保持精简**：不再维护额外旧配置、额外模板变体、界面分组源文件等无关内容。

## 不再保留的内容

当前仓库已经主动移除，不再维护：

- `templates/miaomiaowu/dozee_redirhost__v3.yaml`
- `configs/proxy-groups.json`
- 其他历史遗留模板变体或界面分组源文件

## 校验

本仓库的校验入口：

```bash
python3 scripts/validate.py
```

当前校验会确认：

- `rules/Custom_Proxy.list` 格式合法
- 主模板 `dozee_fake_ip__v3.yaml` 存在
- 模板里包含 `🧩 自定义` 分组
- 模板里包含 `Dozee_Custom_Proxy` rule-provider
- `RULE-SET,Dozee_Custom_Proxy,🧩 自定义` 规则存在且顺序正确

GitHub Actions 也会在 `push` / `pull request` 时自动执行校验。
