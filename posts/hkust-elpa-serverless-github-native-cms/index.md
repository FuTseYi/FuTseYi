---
title: 把 GitHub 变成内容后台：HKUST-ELPA 的 Serverless 架构实践
date: 2026-10-19
tags: Serverless, Cloudflare Workers, GitHub Actions, Local-First, 开源实践
---

# 1 前言

最近，我把自己整理的 ELPA 口语备考资料做成了一个网站：[HKUST-ELPA](https://hkust-elpa.vercel.app/)。

ELPA 是香港科技大学及香港科技大学（广州）相关的英语能力评估。准备考试时，我发现不少题目回忆和经验分散在聊天记录、文档与往届同学的分享中。资料并不缺少，真正麻烦的是**查找、练习，以及后续持续更新**。

最初我只打算做一个能搜索题目、随机抽题和记笔记的静态网页。但做着做着，出现了更有意思的问题：

**能不能不搭建传统业务数据库和管理后台，也让一个静态题库具备完整的社区投稿、审核和持续发布能力？**

最终，我采用了原生 JavaScript、Cloudflare Workers 与 GitHub 原生协作机制相结合的方案。项目已经发布 [v1.0.0 正式版](https://github.com/FuTseYi/HKUST-ELPA/releases/tag/v1.0.0)。

这篇文章主要记录项目的架构、数据设计和实际工程取舍，也给以后维护类似的轻量内容平台留一份参考。

# 2 技术选型：把复杂度留给真正需要的环节

决定技术方案前，我先把项目数据分成两类：

- **公共内容**：题目、考试经历、相似问法、提示小问、备考经验和来源记录，需要共享、审核与追溯。
- **个人数据**：练习状态、回答笔记和未完成的投稿草稿，需要便捷保存，但没有必要统一上传到服务器。

这两类数据的生命周期不同，没必要放进同一套数据库。

最后确定的技术组合如下：

| 层次 | 技术 | 职责 |
| --- | --- | --- |
| 前端 | HTML / CSS / Vanilla JavaScript | 题库展示、筛选、计时与交互 |
| 站点托管 | Vercel / GitHub Pages | 部署同一套静态文件 |
| 投稿接口 | Cloudflare Workers | 接收和校验投稿、调用 GitHub API |
| 人机验证 | Cloudflare Turnstile | 服务端验证投稿请求 |
| 内容协作 | GitHub Issues / Pull Requests | 投稿队列、审核记录与版本化变更 |
| 自动化 | GitHub Actions | 导入数据、检查差异、创建 PR |
| 本地存储 | localStorage / sessionStorage | 个人学习数据与投稿草稿 |
| 测试 | Node.js Test Runner / Playwright | 逻辑检查与真实浏览器回归 |

整个网站没有前端框架和构建步骤，克隆仓库后启动静态 HTTP 服务就能预览；只有投稿时才需要调用边缘 API。

对这个项目来说，**静态优先不是功能妥协，而是明确区分本地交互与公共内容写入之后的自然选择。**

# 3 系统架构：两条数据链路

## 3.1 个人练习留在浏览器

```text
静态题库 → 浏览器加载
              ↓
       搜索 / 筛选 / 抽题 / 计时
              ↓
         学习状态与笔记
              ↓
           localStorage
              ↓
        JSON 备份与恢复
```

浏览题目、随机抽题、模拟计时和保存笔记都是客户端操作，无需登录，也不需要请求业务服务器。

## 3.2 社区内容通过 GitHub 审核发布

```text
用户填写投稿
      ↓
Cloudflare Turnstile
      ↓
Cloudflare Worker
  ├─ 来源与字段校验
  ├─ 请求大小与限流检查
  └─ Turnstile 服务端验证
      ↓
GitHub Issue
submission:pending
      ↓
仓库所有者审核并标记
submission:approved
      ↓
GitHub Actions + 受信任的导入脚本
      ↓
验证 / 去重 / 关联已有题目
      ↓
自动生成数据 Pull Request
      ↓
人工 Review & Merge
      ↓
静态站点更新
```

这个流程最关键的边界是：**投稿只是提交一条待审核记录，不等于修改正式题库。**

# 4 核心设计：GitHub-Native CMS

这是项目里我认为最值得复用的部分。

## 4.1 Issue 同时承担投稿队列与来源记录

传统内容管理系统一般需要单独维护内容表、审核状态和后台页面。我直接使用 GitHub Issue 作为公开投稿入口。

当 Cloudflare Worker 校验通过后，会创建一条附带 `submission:pending` 标签的 Issue。内容包含两部分：

1. **人类可读的 Markdown 摘要**，方便直接审核题目、考试场次与来源。
2. **结构化的 v2 数据标记**，方便受信任的导入脚本按字段处理。

结构化记录通过 `elpa-submission-v2` 标记封装在 Issue 中；Turnstile Token 不会随投稿记录写入 GitHub。

这种设计不需要自建数据库来保存投稿队列，而且每条投稿天然保留 GitHub Issue 链接，之后可以直接回溯内容来源和审核过程。

## 4.2 审核通过后自动生成 PR，而不是自动发布

审核时，我只需要检查投稿是否准确、是否重复、有没有隐私信息，以及题目分类和表达是否合理。

确认后，由仓库所有者给开放中的 Issue 添加：

```text
submission:approved
```

随后 GitHub Actions 使用仓库内的导入脚本处理投稿：

```text
读取 Issue 事件
→ 校验结构化字段
→ 检查题目和校区、考试类型的关联
→ 识别重复记录及内容补充
→ 更新题库或考试出现记录
→ 执行自动化检查
→ 创建独立 PR
```

最终的 PR 依然由人审核、合并，不会因为一个标签就直接把投稿发布到线上。

这里的 GitHub **不是运行时查询的数据库**，而是承担内容协作、审核和版本管理；正式题库仍由仓库中的结构化文件提供，随静态站点一起发布。

## 4.3 用文件白名单控制自动化边界

自动化导入程序还配有专门的差异检查脚本：`scripts/check-submission-diff.cjs`。

它限制生成的投稿 PR 只能修改预先允许的题库和内容文件，而不能顺带修改前端脚本、工作流或部署配置。

与此同时，Issue 中的用户输入始终按**不可信数据**处理，不作为命令执行；字段会在 Worker 与导入器中重复校验。

自动化负责减少重复劳动，发布控制仍留在维护者手中。

# 5 数据设计：稳定 ID、考试经历与内容补充分离

题库持续更新后，我发现比“如何新增一道题”更难的是：**如何保证后续更新不会破坏旧数据。**

## 5.1 Stable IDs：题目排序不等于题目身份

题目使用稳定 ID 关联学习记录，例如：

```text
D-1   GZ Regular ELPA
F-2   GZ Fast Track
H-*   HK Regular ELPA
T-*   HK Fast Track
```

不同校区和考试类型有对应的数据分区。新导入题目的编号采用与原始 Issue 编号相关的确定性规则；已有题目的 ID 则保持不变。

这样，题库排序、筛选、归档方式即使调整，也不会让用户之前记录的笔记突然关联到另一道题上。

## 5.2 Encounter 与 Supplement：反馈次数要有明确含义

假设一位同学分享了某道已有题目的考试经历，另一位同学只补充了新的追问。

这不应该被当成两次相同的考试出现记录。

因此，投稿模型明确区分：

| 意图 | 处理方式 | 是否增加出现次数 |
| --- | --- | --- |
| `encounter` | 记录一次新的考试经历 | 是 |
| `supplement` | 补充相似问法或提示小问 | 否 |

对已有题目，系统会基于题目 ID、校区、类型和规范化英文内容确认关联；新考试经历附加到原题，内容补充则更新相关信息。

同一条 Issue 的记录也会检查是否已经导入，避免重复处理。

因此，**题目是一个稳定实体，考试经历是可追加的记录，补充问法是另一种数据更新**。这三者不能混为一谈。

## 5.3 Provenance：来源和考试场次不能靠猜

另一个容易被忽略的问题是资料来源。

有的题目保留了学生回忆中的英文表达，有的只是根据中文回忆整理成适合练习的英文问法；资料整理日期也不等于考试发生日期。

项目因此将题目内容、历史场次和来源说明分开管理。对有依据的考试记录保留学期与阶段，对尚未核实的场次不强行补齐。

这一点让社区题库在持续积累内容的同时，仍能保持清晰的来源边界。

# 6 Local-First：无需账号的学习记录

既然个人学习状态没有社区共享需求，就没必要为它专门搭建账号系统。

HKUST-ELPA 允许用户直接在浏览器里：

- 按校区、考试类型、场次、关键词和状态筛选题目；
- 随机抽题，配合准备与陈述计时练习；
- 标记“未练 / 练习中 / 已掌握”；
- 使用 Markdown 记录回答思路；
- 导出笔记、备份和恢复学习记录。

练习状态和笔记使用 `localStorage` 持久化；备份文件采用 JSON 格式，便于用户自行保存和迁移。部分浏览器还支持可选的本地文件夹同步。

需要注意的是，本地记录按浏览器和网站来源隔离：Vercel 与 GitHub Pages 可以部署同一套代码，但两边的 `localStorage` 不会自动同步。因此我保留了显式的备份与恢复入口。

未完成的社区投稿则使用 `sessionStorage` 暂存，在当前标签页刷新后仍可恢复，提交成功后清除。

这套设计的思路是：**共享内容走审核发布链路，个人状态留在用户设备上。**

# 7 Edge Security：给静态网站增加可信写入入口

前端静态化并不意味着所有操作都应该由浏览器直接完成。

投稿时，浏览器只调用 Cloudflare Worker，真正的 GitHub Token 和 Turnstile Secret 保存在 Worker Secrets 中。

当前接口主要实施以下控制：

| 检查 | 具体实现 |
| --- | --- |
| 来源校验 | 仅允许配置的两个生产 Origin |
| 人机验证 | Turnstile 服务端验证 Token、hostname 和 action |
| 数据格式 | 字段约束、内容长度及 JSON 请求体校验 |
| 请求大小 | 24 KiB 上限 |
| 频率限制 | 每 IP、每边缘位置每 60 秒最多 3 次 |
| 服务控制 | 显式的关闭、测试和公开模式 |
| 权限隔离 | Worker 只创建待审核 Issue，不直接写入正式题库 |

Worker 不会仅凭前端显示“验证成功”就信任请求；Cloudflare Turnstile 的校验发生在服务端。

GitHub Actions 导入时又会对结构化数据重新验证。

**浏览器、边缘接口、Issue 和正式题库之间有清楚的信任边界。**

# 8 测试与发布：让小步迭代可重复验证

这个项目后期经历了不少细节调整。我逐渐发现，小型项目同样需要自动化测试，否则一个看似简单的 UI 修改也可能影响数据关联和使用流程。

## 8.1 Node.js 逻辑测试

项目使用 Node.js 内置测试工具覆盖题库数据、投稿校验、Worker 行为和数据导入器。

本地可以直接执行：

```bash
npm run check
npm test
```

## 8.2 Playwright 浏览器回归

浏览器测试使用 Playwright + Chromium，覆盖以下八种宽度：

```text
320 / 375 / 390 / 430
700 / 768 / 1024 / 1280 px
```

测试不仅检查页面是否溢出，也会模拟真实的筛选、抽题、计时、笔记、备份恢复以及投稿交互。

有一次，Fast Track 题目按照反馈热度排序后，页面显示的第一题和复制出去的题号不一致。原因是两处使用了不同的排序来源。

解决时，我没有重编号题库，而是让复制功能直接复用页面的显示排序，再用浏览器回归验证结果。

另一个问题出现在跨校区投稿：从某道题的分享链接进入表单后，如果用户更改校区，原来的题目关联就不再合法。最终在前端切换时清除不兼容的关联，同时由导入器复核对应的校区与题目。

这些都是**单个函数很容易看起来正确，但整条用户操作链路仍可能出错**的例子。

测试运行时会隔离外部验证与真实投稿请求，不会因为回归测试而向公开仓库写入虚构题目。

## 8.3 发布与持续维护

代码通过 GitHub Actions 检查后合并到 `main`，静态站点随部署更新；Cloudflare Worker 独立管理投稿入口。

项目同时部署在 Vercel 和 GitHub Pages，方便保留备用访问入口。

2026 年 10 月，我发布了首个正式版本 [v1.0.0 — Initial Public Release](https://github.com/FuTseYi/HKUST-ELPA/releases/tag/v1.0.0)。

后续日常题库更新仍然通过小步 PR 完成，不需要为了每次内容调整都发布一个新版本。

# 9 总结：让系统复杂度与真实需求匹配

这次开发给我最大的收获，是重新思考“一个完整应用到底需要哪些基础设施”。

HKUST-ELPA 当然也有后端：Cloudflare Worker 承担了必要的写入校验。但它不需要常驻业务服务器，不需要自己搭建账户体系、内容审核后台或业务数据库。

我把不同职责交给了最合适的位置：

```text
Vanilla JavaScript  → 个人练习与页面交互
Cloudflare Workers  → 可信投稿入口
GitHub Issues       → 社区内容收集与来源记录
GitHub Actions      → 受控的数据导入
Pull Requests       → 代码与内容审核
Vercel / Pages      → 静态发布
```

整个流程形成了一个完整的内容生命周期：

**Contribution → Validation → Review → Versioning → Deployment**

对于校园工具、社区知识库、开源资源索引等低频写入、高频阅读的项目，我认为这种架构很值得尝试。

**好的技术选型不是堆叠更多组件，而是让系统只承担真实需要的复杂度。**

HKUST-ELPA 从最初的一份备考笔记，逐渐成为了一次关于 Serverless Architecture、GitHub-Native Collaboration 和 Local-First Design 的工程实践。

我也希望它之后仍然保持最初的状态：轻量、开放、可维护。

# 10 项目与参考资料

- [HKUST-ELPA 在线网站](https://hkust-elpa.vercel.app/)
- [GitHub 开源仓库](https://github.com/FuTseYi/HKUST-ELPA)
- [v1.0.0 初始正式版](https://github.com/FuTseYi/HKUST-ELPA/releases/tag/v1.0.0)
- [Cloudflare Worker 投稿接口](https://github.com/FuTseYi/HKUST-ELPA/blob/v1.0.0/worker/src/index.js)
- [GitHub Actions 投稿审核工作流](https://github.com/FuTseYi/HKUST-ELPA/blob/v1.0.0/.github/workflows/approved-submission.yml)
- [结构化投稿 v2 数据规范](https://github.com/FuTseYi/HKUST-ELPA/blob/v1.0.0/docs/submission-v2-spec.md)
- [Playwright 浏览器回归测试](https://github.com/FuTseYi/HKUST-ELPA/blob/v1.0.0/tests/mobile-browser-smoke.cjs)

---

*Built with Passion. Shared with Everyone.*

*为爱发电 · 开源共建 · 互帮互助*
