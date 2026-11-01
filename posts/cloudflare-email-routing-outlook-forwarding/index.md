---
title: Cloudflare Email Routing：自有域名邮件转发实践
date: 2026-10-14
tags: Cloudflare, Email Routing, Outlook, 域名邮箱, 实践记录
---

# 1 前言

一直想给自己的域名配一套邮箱地址：对外使用简洁的自定义地址，收到的邮件仍然由熟悉的 Outlook 统一管理。

但仔细想想，我现阶段并不需要用域名**发送**邮件，也不需要为它单独开一个邮箱客户端、购买存储空间或维护邮件服务器。真正需要的只有一件事：

**别人给自有域名发信，邮件可以自动转发到现有的 Outlook 收件箱。**

最后选择了 [Cloudflare Email Routing](https://developers.cloudflare.com/email-service/)。整个过程不需要部署服务器，也没有额外购买企业邮箱。配置完成后，我用其他邮箱实际测试过收信，转发链路正常。

这篇文章把步骤和几个容易忽略的细节记录下来，以后换域名或调整转发规则时也能直接参考。

> 文中邮箱与域名统一使用 `example.com` 等示例值；实际操作时替换为自己的域名和已验证的收件邮箱即可。

# 2 先理解：这是邮件转发，不是独立邮箱

这套方案的邮件路径很简单：

```text
发件人
   ↓
me@example.com / contact@example.com
   ↓
Cloudflare Email Routing（接收、匹配规则并转发）
   ↓
已验证的 Outlook 收件箱
```

Cloudflare 在这里承担的是**邮件入口和转发规则**，真正存储邮件、分类、搜索与管理的仍然是 Outlook。

这意味着：

- 我可以对外使用多个自有域名邮箱地址，但不必分别登录多个邮箱。
- 更换日常收件邮箱时，只需要修改 Cloudflare 的转发目标，不必通知所有联系人修改地址。
- Email Routing 本身不提供传统邮箱的收件箱、IMAP/POP3 或独立邮件存储。
- **通过 Outlook 直接回复时，默认显示的仍是 Outlook 发件地址。** 如果未来想以自有域名发信，需要另外配置合适的发信服务；这与本文的免费收信转发是两回事。

对目前只需要收信的我来说，这样反而更轻量。

# 3 准备条件

我只准备了三样东西：

1. **一个自己的域名**：域名已经添加到 Cloudflare，并且 DNS 托管状态为 `Active`。
2. **Cloudflare 账号**：能够管理这个域名的 DNS 和 Email Routing。
3. **一个长期使用的 Outlook 邮箱**：作为最终的邮件接收地址。

需要提前确认的一点是：**同一个域名的 MX 记录决定入站邮件交给谁处理。**

如果域名已经接入 Microsoft 365、Google Workspace 等邮箱服务，不要直接覆盖正在使用的 MX 记录。否则原本的收信系统可能受到影响。这次我的域名没有需要保留的其他收信服务，所以可以直接启用 Cloudflare 的邮件路由。

# 4 Cloudflare Email Routing 配置过程

## 4.1 启用邮件路由

进入 [Cloudflare Dashboard](https://dash.cloudflare.com/)：

```text
Cloudflare Dashboard
→ Email / 电子邮件服务
→ Email Routing / 邮件路由
→ 选择自己的域名
→ 启用
```

不同版本的控制台可能在菜单命名上略有差异，核心是找到对应域名的 **Email Routing** 页面。

启用后，我先检查域名状态是否为 `Enabled` / `Ready`，再查看 DNS 是否已经同步。**仅显示“邮件路由已启用”，还不代表某个自定义邮箱地址已经可以收信**，后面必须继续创建转发规则。

## 4.2 检查 DNS：MX、SPF、DKIM

Cloudflare 会提示配置邮件路由所需的 DNS 记录。我的配置中，启用后相关记录已经自动同步，没有必要逐条手动复制。

其中最重要的是：

| 记录类型 | 用途 | 配置建议 |
| --- | --- | --- |
| `MX` | 把入站邮件交给 Cloudflare 的邮件服务器 | 使用 Cloudflare 自动创建的记录和优先级 |
| `TXT (SPF)` | 声明邮件转发相关的授权策略 | 不要在同一域名下留下互相冲突的多条 SPF 记录 |
| `TXT (DKIM)` | 用于邮件认证相关配置 | 按 Cloudflare 控制台的实际提示配置 |

在 DNS 页面能看到 Cloudflare 对应的 MX 服务器记录，是检查是否接管收信入口的直观方式。**MX 优先级以控制台生成的值为准**，不要照搬其他人的数字。

如果域名已经有 SPF 记录，也应当合并所需机制，而不是额外再创建一条独立的 `v=spf1` 记录。

## 4.3 添加并验证 Outlook 目标邮箱

这一步非常关键，也是我实际配置过程中碰到的一个限制。

进入：

```text
Email Routing
→ Destination Addresses / 目标地址
→ Add destination address / 添加目标地址
```

填写自己真正使用的 Outlook 邮箱地址，提交后，Cloudflare 会向该邮箱发送验证邮件。

回到 Outlook 收件箱，找到标题类似下面的邮件：

```text
[Action required] Verify your Email Routing address
```

点击邮件中的 **Verify email address**，再回 Cloudflare 检查状态是否已经变成 `Verified`。

**要先验证目标地址，再创建转发规则。** 未验证时直接创建规则，可能会收到 `Destination address is not verified` 这样的错误提示。

## 4.4 创建四个自定义邮箱地址

目标地址验证完成后，进入域名的 **Routing Rules / 路由规则** 页面，点击 **Create routing rule / 创建路由规则**。

在我的中文控制台里，创建规则时主要填写三项：

| 字段 | 我的选择 |
| --- | --- |
| 电子邮件匹配模式 | 只输入 `@` 前面的地址前缀，例如 `me` |
| 域名 | 选择正在配置的自有域名 |
| 操作 | **发送到电子邮件**，然后选择已验证的 Outlook 目标地址 |

这里不需要选择 `发送到 Worker`。只有简单转发需求时，用控制台内置规则就足够了。

为了兼顾个人身份、正式联系和研究交流，我最终采用四个地址。下表全部以示例域名演示：

| 示例地址 | 用途 |
| --- | --- |
| `me@example.com` | 个人数字身份与名片 |
| `contact@example.com` | 正式联系、简历与求职 |
| `hello@example.com` | 个人网站、日常交流 |
| `research@example.com` | 学术与科研合作 |

这四条规则的操作都相同：**转发至同一个已验证的 Outlook 收件箱**。创建完成后，确认每条规则的状态均为 `Active` / `已启用`。

我没有继续增加更多用途相近的别名。对个人使用来说，能覆盖真实场景、又不会增加额外管理负担，比追求地址数量更重要。

## 4.5 保持 Catch-all 关闭

`Catch-all` 是通配符收件规则，可以处理那些没有被明确创建的地址，例如有人发信到 `random@example.com`。

这个功能听上去很方便，但也可能扩大垃圾邮件的入口。

我更倾向于**只启用明确创建的四条规则，Catch-all 保持关闭**。这样每一个对外地址都有清晰用途，也方便以后按需调整。

# 5 实际验证：确保邮件真的能收到

规则显示为 `Active` 后，我没有直接把它当成配置完成，而是从其他邮箱向自定义地址发送测试信，再到 Outlook 检查收件结果。

我的检查顺序是：

1. 先向其中一个自定义地址发送邮件，确认 Outlook 正常收到。
2. 再向另一个自定义地址发送邮件，排除只有单条规则有效的情况。
3. 核对发件人、主题和正文，确认内容没有明显异常。
4. 如果收件箱未显示，就检查垃圾邮件文件夹，以及 Cloudflare 的邮件活动日志。

实际收信测试成功后，这套方案才算真正可用。它不需要 Outlook 做任何特殊的收件服务器配置，仍然按原来的方式使用 Outlook 即可。

# 6 几个值得记住的细节

## 6.1 目标邮箱没验证，规则可能无法创建

这是最容易漏掉的一步。Cloudflare 发出的验证邮件需要在**最终收件邮箱**里点击确认，仅仅添加目标地址还不够。

## 6.2 路由开启不等于地址已创建

DNS 正常、Email Routing 显示已启用，只说明域名层面的邮件入口已经准备好。只有添加匹配特定地址的转发规则，邮件才能按预期转发到目标邮箱。

## 6.3 邮件认证与转发不是百分之百无损

Cloudflare 会对来信进行身份认证和反滥用检查。少数发送方的 SPF、DKIM、DMARC 配置不规范时，邮件可能被拒收；部分邮件也可能被 Outlook 归类为垃圾邮件。

因此，准备将域名邮箱用于申请通知、账户验证或其他重要事务前，最好用不同发件方实际测试，并保留一个可用的备用联系方式。

## 6.4 这套方案只解决“收”，不解决“发”

例如别人发邮件给 `contact@example.com`，我能在 Outlook 收到；但直接点击回复，默认发件地址依然是原来的 Outlook 邮箱。

如果以后需要以 `contact@example.com` 的身份发送或回复邮件，就要另外研究域名发信的 SMTP 或邮件服务配置。本文并没有配置这部分，也不建议仅为了收信需求而增加不必要的复杂度。

## 6.5 不在公开教程里放真实邮箱和控制台截图

邮箱地址、账户标识及 DNS 之外的后台信息，没必要为了写教程完整公开。使用 `example.com` 这样的示例域名，既能把步骤讲明白，也更利于读者直接迁移到自己的配置中。

# 7 总结

这次折腾下来，我觉得 Cloudflare Email Routing 非常适合已经拥有域名、同时又习惯使用 Outlook 或其他成熟邮箱服务的人。

整个思路其实只有四步：

```text
域名接入 Cloudflare
→ 启用 Email Routing 并确认 DNS
→ 验证 Outlook 目标邮箱
→ 创建自定义地址转发规则并测试收信
```

我最终保留了四个用途清晰的域名邮箱地址，所有来信统一由一个 Outlook 收件箱管理，Catch-all 关闭，也没有为了“看起来更专业”去购买暂时用不到的企业邮箱。

**用自己的域名作为稳定的对外入口，用成熟的邮箱服务负责日常收件。** 对现阶段的我来说，这已经是简洁、可维护且足够实用的方案。

# 8 参考资料

- [Cloudflare Email Service 文档](https://developers.cloudflare.com/email-service/)
- [Cloudflare：开始配置邮件路由](https://developers.cloudflare.com/email-service/get-started/route-emails/)
- [Cloudflare：邮箱地址与转发规则](https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/)
- [Cloudflare：邮件路由 DNS 配置](https://developers.cloudflare.com/email-service/configuration/domains/)
- [Cloudflare：邮件处理流程](https://developers.cloudflare.com/email-service/concepts/email-lifecycle/)
