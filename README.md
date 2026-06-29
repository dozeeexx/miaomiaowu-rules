# miaomiaowu-rules

这个仓库现在只保留两类长期维护内容：

1. **一份主用的妙妙屋 V3 模板**
2. **一些自定义规则**

当前主模板：

- `templates/miaomiaowu/dozee_fake_ip__v3.yaml`

当前自定义规则：

- `rules/Custom_Proxy.list`

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
- **仓库保持精简**：不再维护额外的旧配置、额外模板变体、界面分组源文件等无关内容。

## 校验

仓库内置校验脚本：

```bash
python3 scripts/validate.py
```

GitHub Actions 也会在 push / pull request 时自动校验。
