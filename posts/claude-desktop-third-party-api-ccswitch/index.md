---
title: Claude Desktop 接入第三方模型 API：基于 ccswitch 的配置与踩坑
date: 2026-04-30
tags: ClaudeDesktop, cc-switch, DeepSeek, 第三方模型API, 踩坑记录
---

# Claude Desktop 接入 ccswitch：第三方模型 API 配置与踩坑记录

最近想让 Claude Desktop 也能像 Claude Code 一样，通过 ccswitch 接入第三方模型 API，方便在桌面端里切换不同 Provider 测试。

我主要参考了 LINUX DO 上 sandleft 佬的这篇教程：

[《如何用功能更强大更美观的 claude 桌面端替代 cli 还能随意切换模型？》](https://linux.do/t/topic/2032344)

原教程已经把核心方案讲清楚了：**Claude Desktop 通过官方 3P Gateway 连接到 ccswitch 本地路由，再由 ccswitch 转发到当前选中的 Provider**。

不过我实际配置时还是遇到了一些坑，比如：

```text
Gateway returned HTTP 400
Gateway returned HTTP 404
requestUrl: http://127.0.0.1:15721/v1/models
```

这篇文章主要是对原教程的逻辑做一次重新梳理，并补充我自己遇到的问题和解决方法。

---

## 一、先搞清楚：Claude Desktop 和 Claude Code 不是同一条链路

这是我最开始最容易混淆的地方。

简单说：

```text
Claude Desktop = 走 ccswitch 本地路由
Claude Code / VS Code Claude 插件 = 走 Claude Code 配置
```

Claude Desktop 的请求链路是：

```text
Claude Desktop
→ http://127.0.0.1:15721
→ ccswitch 本地路由
→ 当前 Provider
→ 第三方模型 API
```

而 VS Code 里的 Claude 插件 / Claude Code 更像是读取 ccswitch 写入或切换后的 Claude Code 配置，比如：

```text
ANTHROPIC_BASE_URL
ANTHROPIC_AUTH_TOKEN
模型名配置
```

所以它的链路更接近：

```text
VS Code Claude 插件 / Claude Code
→ Claude Code 配置
→ 当前 Provider
```

这就解释了一个现象：**ccswitch 本地路由关闭后，VS Code Claude 插件仍然可能正常使用；但 Claude Desktop 要用这套方案，就必须开 ccswitch 本地路由。**

---

## 二、开启 ccswitch 本地路由

在 ccswitch 里进入本地路由相关页面，确认这些状态：

```text
本地路由：运行中
路由总开关：开启
Claude：开启
服务地址：http://127.0.0.1:15721
```

这里最重要的是服务地址。

比如 ccswitch 显示的是：

```text
http://127.0.0.1:15721
```

那 Claude Desktop 里也必须填这个地址。

我一开始填成了另一个端口，例如：

```text
http://127.0.0.1:10809
```

这当然会出问题。

所以第一步先确认：**Claude Desktop 里的 Gateway base URL 必须和 ccswitch 显示的本地路由地址一致。**

---

## 三、配置 Claude Desktop 的 Gateway

在 Claude Desktop 里打开第三方推理配置。

一般路径是：

```text
Help
→ Troubleshooting
→ Enable Developer mode
→ Developer
→ Configure third-party inference
```

Connection 选择：

```text
Gateway
```

然后填写：

```text
Gateway base URL = http://127.0.0.1:15721
Gateway API key = PROXY_MANAGED
Gateway auth scheme = bearer
```

这里注意一点：

**Claude Desktop 里不要填真实的第三方模型 API Key。**

这里填：

```text
PROXY_MANAGED
```

真实 API Key 应该配置在 ccswitch 的 Provider 里。

也就是说：

```text
Claude Desktop 只负责连接 ccswitch；
ccswitch 才负责连接真实的第三方模型 API。
```

---

## 四、最关键的一步：手动补 inferenceModels

只配置 Gateway 还不一定够。

Claude Desktop 会尝试请求：

```text
http://127.0.0.1:15721/v1/models
```

但 ccswitch 本地路由不一定实现了 `/v1/models` 这个接口，于是会出现：

```text
Gateway returned HTTP 404
requestUrl: http://127.0.0.1:15721/v1/models
```

这个 404 很容易误导人。

它的意思不是“整个链路不可用”，而是：

```text
Claude Desktop 想获取模型列表；
但 ccswitch 没有提供 /v1/models；
所以模型列表探测失败。
```

解决方法是：**在 Windows 注册表里手动补上 inferenceModels。**

---

## 五、通过 .reg 添加 inferenceModels

先在 Claude Desktop 表单里填好：

```text
Gateway base URL = http://127.0.0.1:15721
Gateway API key = PROXY_MANAGED
Gateway auth scheme = bearer
```

然后点击右下角：

```text
Export
```

导出 Windows 的 `.reg` 文件。

用记事本打开 `.reg`，找到：

```reg
[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]
```

在下面添加：

```reg
"inferenceModels"="[\"haiku\",\"sonnet\",\"opus\"]"
```

如果只想先测试一个模型，也可以写：

```reg
"inferenceModels"="[\"sonnet\"]"
```

保存后双击导入，或者使用命令：

```powershell
reg import "C:\path\to\your.reg"
```

导入后，完全退出 Claude Desktop，再重新打开。

注意：最好不是只关窗口，而是从托盘里彻底退出后重启。

---

## 六、haiku / sonnet / opus 只是别名

这里也容易误解。

在 `inferenceModels` 里写：

```reg
"inferenceModels"="[\"haiku\",\"sonnet\",\"opus\"]"
```

并不代表你真的在用 Claude Haiku、Claude Sonnet 或 Claude Opus。

在这里，它们更像是 Claude Desktop 识别的模型槽位或别名。

真正请求哪个模型，取决于 ccswitch 里的映射。

比如你可以在 ccswitch 中把这些都映射到同一个模型：

```text
主模型：deepseek-v4-flash
Haiku 默认模型：deepseek-v4-flash
Sonnet 默认模型：deepseek-v4-flash
Opus 默认模型：deepseek-v4-flash
```

也可以根据需要映射到不同模型。

所以不要用“你是什么模型？”这种方式判断真实模型。模型自我介绍很容易受到系统提示、别名和兼容层影响。

更可靠的判断方式是看：

```text
ccswitch 请求记录
ccswitch 日志
第三方模型控制台用量
实际请求里的 model 字段
```

---

## 七、关于模型名后缀，比如 `[1m]`

有些模型名可能会长这样：

```text
deepseek-v4-pro[1m]
```

这类后缀不能一概认为是错的。

很多 Provider 或中转服务会用类似 `[1m]` 的后缀表示特定模型规格，比如 1M 超长上下文版本。如果你的服务商、面板或 ccswitch 配置要求这样写，那就应该保留。

但如果遇到：

```text
HTTP 400
model not found
provider rejected request
```

可以临时切回基础模型名测试，例如：

```text
deepseek-v4-pro
deepseek-v4-flash
```

先确认基础链路没问题，再切回带后缀的版本。

关键是判断这个后缀到底是：

```text
服务商要求的模型规格
```

还是：

```text
界面展示用的标记
```

前者需要保留，后者不应该传给 API。

---

## 八、`thinking: false` 不是必选项

有些教程会建议在 ccswitch 里加：

```json
{
  "thinking": false,
  "includeCoAuthoredBy": false
}
```

我自己测试时，不加也能正常使用。

所以我的建议是：

```text
能用就先不加。
```

如果后续遇到 400、tool_use、thinking、旧会话上下文不兼容之类的问题，再考虑添加。

---

## 九、常见报错怎么理解？

### 1. Gateway returned HTTP 400

400 一般表示请求已经发出去了，但 Provider 拒绝了请求。

常见原因：

```text
模型名错误
Provider 配置错误
API Key 错误
账号额度或模型权限问题
请求格式不兼容
旧会话上下文不兼容
thinking / tool_use 兼容问题
```

可以按这个顺序排查：

```text
1. 检查 ccswitch 当前 Provider 是否选对
2. 检查模型名是否正确
3. 检查真实 API Key 是否填在 ccswitch Provider 里
4. 新开 Claude Desktop 会话测试
5. 必要时尝试 thinking: false
```

### 2. Gateway returned HTTP 404

如果 404 的地址是：

```text
http://127.0.0.1:15721/v1/models
```

那大概率只是 Claude Desktop 在测试模型列表。

这种情况下，重点不是纠结 `/v1/models`，而是补上：

```text
inferenceModels
```

只要实际对话能正常使用，就说明核心链路是通的。

---

## 十、如何确认 Claude Desktop 真的走了 ccswitch？

可以看 ccswitch 的请求记录或日志。

日志一般在：

```text
C:\Users\user\.cc-switch\logs\cc-switch.log
```

也可以查看数据库：

```text
C:\Users\user\.cc-switch\cc-switch.db
```

重点看请求记录里有没有类似字段：

```text
data_source = proxy
provider_id = 当前选中的 Provider
request_model = sonnet / haiku / opus
model = 实际上游模型
status_code = 200
```

如果能看到 `data_source = proxy`，并且 `status_code = 200`，就说明 Claude Desktop 的请求确实经过了 ccswitch 本地路由。

---

## 十一、最终流程总结

如果从头配置，我会按这个顺序来：

### 1. 先在 ccswitch 里配置好 Provider

确保第三方模型 API 在 ccswitch 中可以正常使用。

### 2. 开启 ccswitch 本地路由

确认：

```text
本地路由：运行中
路由总开关：开启
Claude：开启
服务地址：http://127.0.0.1:15721
```

### 3. Claude Desktop 配置 Gateway

填写：

```text
Gateway base URL = http://127.0.0.1:15721
Gateway API key = PROXY_MANAGED
Gateway auth scheme = bearer
```

### 4. 导出 .reg

点击 Claude Desktop 配置页右下角的：

```text
Export
```

### 5. 修改 .reg，补上 inferenceModels

在：

```reg
[HKEY_CURRENT_USER\SOFTWARE\Policies\Claude]
```

下面加：

```reg
"inferenceModels"="[\"haiku\",\"sonnet\",\"opus\"]"
```

或者先只测一个：

```reg
"inferenceModels"="[\"sonnet\"]"
```

### 6. 导入 .reg 并重启 Claude Desktop

```powershell
reg import "C:\path\to\your.reg"
```

然后完全退出并重启 Claude Desktop。

### 7. 新开会话测试

不要只看设置页的 Check again。

如果实际对话可以使用，并且 ccswitch 有请求记录，就说明链路已经跑通。

---

## 十二、最终使用习惯

配置完成后，可以这样理解：

```text
用 Claude Desktop：
需要开启 ccswitch 本地路由。

用 VS Code Claude 插件 / Claude Code：
通常不需要开启 ccswitch 本地路由，
只要 Claude Code 配置已经切换到对应 Provider。
```

如果要切换 Claude Code 使用的 Provider，还是通过 ccswitch 切换配置。

但日常只用 VS Code Claude 插件时，本地路由不一定要开。

---

## 结论

这套方案的核心其实很简单：

```text
Claude Desktop
→ 官方 3P Gateway
→ ccswitch 本地路由
→ 第三方模型 API
```

真正容易踩坑的是几个细节：

```text
1. ccswitch 本地路由必须开启
2. Claude Desktop 的端口要和 ccswitch 一致
3. Gateway API key 建议填 PROXY_MANAGED
4. Windows 下需要手动补 inferenceModels
5. /v1/models 404 不一定影响实际使用
6. haiku / sonnet / opus 只是别名
7. Claude Desktop 和 Claude Code / VS Code 插件不是同一条链路
```

折腾完之后，这套方案还是挺实用的。Claude Desktop 可以通过 ccswitch 接入第三方模型 API，而 Claude Code / VS Code 插件也可以继续使用 ccswitch 写入的配置。

最后再次感谢 LINUX DO 上 sandleft 佬的原教程。本文只是基于原教程的一次个人实践补充，主要记录我在配置过程中遇到的坑和解决思路。
