# miaomiaowu-rules

这个仓库现在只做两件长期维护的事：

1. 维护一份 **妙妙屋 V3 主模板**
2. 维护一份 **自定义规则列表**

目标很简单：

- 日常主要只改节点
- 需要时再改自定义规则
- 模板长期保持稳定，不再堆历史变体

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

这是现在唯一的长期主用模板，特点是：

- `fake-ip` 模式
- 顶层结构固定为：`mode / dns / proxies / proxy-groups / rules / rule-providers`
- 不按国家 / 地区分组
- 通过 `__PROXY_NODES__` / `__PROXY_PROVIDERS__` 动态注入节点
- 自定义规则通过 `Dozee_Custom_Proxy` 接到 `🧩 自定义`
- 预留了 `🌠 中转节点` 和 `🌄 落地节点`

### 关于中转 / 落地

这两个组是 **提前预留** 的，不是强制要求当前日用节点一定要有。

- `🌠 中转节点`
  - 通过节点名里的关键词自动识别
  - 关键词示例：`中转|relay|entry`
- `🌄 落地节点`
  - 通过节点名里的关键词自动识别
  - 关键词示例：`落地|exit|egress`

如果当前日用节点 **本来就不是** 这种命名体系，那么最终生成的订阅里不出现这两个组，**是正常的**。

未来如果你真的要加中转 / 落地节点，直接把节点命名成类似下面这样即可：

- `中转-新加坡-01`
- `relay-jp-01`
- `entry-hk-01`
- `落地-美国-01`
- `exit-sg-01`
- `egress-jp-01`

这样它们会自动进入对应分组，不用额外改模板结构。

## 当前自定义规则

- `rules/Custom_Proxy.list`

这里适合长期维护：

- 你自己指定的网站 / 域名 / 规则
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

## 日常维护方式

### 1. 增删节点

尽量不要改模板本体。

直接更新节点来源，让模板里的动态注入接住新增 / 删除的节点即可。

### 2. 增删自定义规则

优先改：

```text
rules/Custom_Proxy.list
```

### 3. 新增业务分组

如果以后要加新的业务组，再同步改这三处：

- `proxy-groups`
- `rules`
- `rule-providers`

### 4. 规则顺序

自定义规则要放在私有 / 国内直连规则之后、广义海外规则之前，避免被提前吞掉。

### 5. 不再走国家 / 地区分组路线

这个仓库后续不再维护一堆国家 / 地区分组，只保留业务分组 + 预留的中转 / 落地坑位。

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
