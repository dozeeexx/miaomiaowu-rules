# miaomiaowu-rules

给 `iluobei/miaomiaowu` 用的个人自定义规则仓库。

目标很简单：**妙妙屋继续使用自带规则，只额外加一份我自己维护的规则；命中这些规则的网站会进入代理客户端里的「🧩 自定义」策略组，可以单独选择节点/自动选择/中转/落地/直连。**

## 日常维护

只改这个文件：

```text
rules/Custom_Proxy.list
```

每行一条 Mihomo/Clash classical 规则，例如：

```text
DOMAIN-SUFFIX,example.com
DOMAIN,api.example.com
DOMAIN-KEYWORD,example
IP-CIDR,1.2.3.4/32,no-resolve
```

提交到 GitHub 后，模板里的 rule-provider 会按 `interval: 3600` 自动刷新；想立刻生效可以在代理面板里手动更新 rule-provider 或重新拉取配置。

Raw 地址：

```text
https://testingcf.jsdelivr.net/gh/dozeeexx/miaomiaowu-rules@main/rules/Custom_Proxy.list
```

## 妙妙屋怎么用

本仓库已经准备了两份基于妙妙屋自带模板改好的模板：

```text
templates/miaomiaowu/dozee_fake_ip__v3.yaml
templates/miaomiaowu/dozee_redirhost__v3.yaml
```

使用方式：

1. 在妙妙屋部署目录里找到挂载的 `rule_templates/` 目录。
2. 把上面其中一个模板放进去，例如 `dozee_fake_ip__v3.yaml`。
3. 在妙妙屋生成订阅时选择这个模板。
4. 客户端里会出现策略组：`🧩 自定义`。
5. 以后新增网站时，只维护 `rules/Custom_Proxy.list`。

如果是 Docker Compose 部署，通常类似：

```yaml
volumes:
  - ./rule_templates:/app/rule_templates
```

把模板文件放到宿主机的 `./rule_templates/` 即可。

## 这个模板改了什么

相对妙妙屋原始模板，只做三处最小改动：

1. `proxy-groups` 增加：`🧩 自定义`
2. `rules` 增加：`RULE-SET,Dozee_Custom_Proxy,🧩 自定义`
3. `rule-providers` 增加：`Dozee_Custom_Proxy`，指向 `rules/Custom_Proxy.list`

规则顺序上，`Dozee_Custom_Proxy` 放在 private/LAN 直连之后、其他通用规则之前，所以你的自定义规则优先级比较高。

## 隐私提醒

如果这个仓库是 public，`rules/Custom_Proxy.list` 里的域名会公开。不要提交：

- 机场订阅 URL
- 节点/代理账号密码
- API token / cookie
- 过于私人的家庭、NAS、内网域名

## 校验

本仓库带了一个轻量校验脚本：

```bash
python3 scripts/validate.py
```

它会检查：规则格式、模板 YAML、`RULE-SET` / `rule-provider` / `🧩 自定义` 分组是否一致。
