# FuTseYi-Site-Source

个人网站源码与构建仓库。网站使用原生 HTML、CSS 和 JavaScript，并通过 Python 生成静态页面。所有内容修改、构建与发布流程均在本仓库维护。

## 项目结构

```text
FuTseYi-Site-Source/
├── .github/workflows/       # 自动测试、贡献同步与跨仓库发布
├── assets/                  # 样式、脚本、字体与图片
├── posts/                   # Markdown 文章与配套资源
├── scripts/                 # 静态构建、内容处理与校验
├── tests/                   # 单元测试与浏览器回归测试
├── contributions.json       # 经过校验的版本化贡献数据
├── index.html               # 首页
├── preview.py               # 本地预览与统一构建入口
└── requirements.txt         # Python 构建依赖
```

## 技术栈

- **HTML / CSS / JavaScript** — 原生页面、样式与交互，不使用前端框架
- **Python** — Markdown 处理、静态构建与页面校验
- **Pagefind** — 静态站内搜索
- **GitHub GraphQL API** — 获取公开贡献记录，并写入版本化数据文件
- **GitHub Actions** — 自动验证、构建与跨仓库部署

## 本地开发

运行前请确保安装 Python 3.10 或更高版本。

```bash
python preview.py              # 启动本地预览
python preview.py --build-only # 构建并校验静态网站
```

运行单元测试：

```bash
python -m unittest discover -s tests -t . -p "test_*.py"
```

Windows 可使用 `py -3` 替代 `python`。预览命令会按需在本地环境安装依赖。详细说明参见 [PREVIEW.md](PREVIEW.md)。

## 自动部署

本项目通过 GitHub Actions 自动构建并发布。符合发布条件的变更进入 `main` 后，工作流会执行测试、离线构建及校验，再将完整的 `_site/` 静态产物推送至 [futseyi.github.io](https://github.com/FuTseYi/futseyi.github.io) 的 `main` 分支。

### 部署流程

```mermaid
sequenceDiagram
    autonumber
    actor Developer as 开发者
    participant Source as 源码仓库
    participant CI as PR 验证工作流
    participant Deploy as 发布工作流
    participant App as GitHub App
    participant Output as 静态发布仓库
    participant Pages as GitHub Pages
    participant Vercel as Vercel

    Developer->>Source: 提交 Pull Request
    Source->>CI: 触发 pull_request 验证
    activate CI
    Note over CI: 单元测试、静态构建及 Chromium / WebKit 测试
    CI-->>Developer: 返回验证结果（不发布）
    deactivate CI

    Developer->>Source: 合并变更至 main
    Note over Source,Deploy: 仅在满足发布工作流的路径条件时触发
    Source->>Deploy: push 触发 deploy.yml
    activate Deploy
    Note over Deploy: 测试、离线构建并校验唯一 _site/
    Deploy->>App: 申请限定发布仓库的短期 Token
    App-->>Deploy: 返回 Contents 写入令牌
    Deploy->>Output: 将 _site/ 推送至 main
    deactivate Deploy

    par GitHub Pages
        Output->>Pages: main 更新触发静态站点发布
    and Vercel
        Output->>Vercel: main 更新触发生产部署
    end

    Note over Pages,Vercel: 两个平台使用同一份已生成的静态产物
```

### 贡献数据同步

贡献数据与网站构建相互独立。定时任务、手动触发或刷新逻辑更新时，`refresh-contributions.yml` 通过 GitHub GraphQL 获取记录，并校验、过滤和合并历史数据。

```mermaid
sequenceDiagram
    autonumber
    participant Trigger as 定时 / 手动 / 代码更新
    participant Refresh as 贡献刷新工作流
    participant GraphQL as GitHub GraphQL
    participant Source as 源码仓库 main
    participant Deploy as 发布工作流

    Trigger->>Refresh: 触发贡献更新
    Refresh->>GraphQL: 查询公开贡献历史
    GraphQL-->>Refresh: 返回贡献数据
    Note over Refresh: 排除单纯 Fork 和指定仓库，保留真实贡献
    Refresh->>Refresh: 校验并合并 contributions.json

    alt 数据发生变化
        Refresh->>Source: 使用 GITHUB_TOKEN 提交数据文件
        Refresh->>Deploy: workflow_dispatch 触发 deploy.yml
        Note over Deploy: 按上方发布流程构建并部署
    else 数据未变化
        Note over Refresh: 不提交，也不额外触发发布
    end
```

### 运行机制说明

- **唯一构建**：网站只在源码仓库生成 `_site/`，发布仓库及托管平台不重复构建。
- **自动验证**：Pull Request 运行测试和浏览器检查，不触发正式发布。
- **短期授权**：跨仓库推送使用 GitHub App 临时令牌，不依赖长期个人访问令牌。
- **离线构建**：构建使用已提交的 `contributions.json`，不在构建阶段实时请求 GitHub API。
- **自动同步**：贡献数据更新时，以仓库自带的 `GITHUB_TOKEN` 提交并显式触发同一发布工作流。
- **版本追溯**：每次发布生成 `build-info.json`，记录源码提交与 Actions 运行信息。

发布仓库中的文件由本仓库自动生成，不应直接修改；其说明文档由 [PUBLISHED_README.md](PUBLISHED_README.md) 维护。
