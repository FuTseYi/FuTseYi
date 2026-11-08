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

### 部署与贡献更新

每次向源码仓库 `main` 推送变更（包括 Blog），都会先运行贡献刷新。每月 1 日、15 日的定时任务与手动触发也会执行同一流程。仅 `contributions.json` 的自动提交不再次触发刷新，避免循环。

```mermaid
sequenceDiagram
    autonumber
    actor Author as 开发者
    participant Source as Source / main
    participant Refresh as 贡献刷新 Action
    participant API as GitHub GraphQL
    participant Build as 网站发布 Action
    participant App as GitHub App
    participant Output as Published / main
    participant Pages as GitHub Pages
    participant Vercel as Vercel

    Author->>Source: 提交源码或 Blog
    Note over Refresh: 也支持定时和手动运行
    Source->>Refresh: push 触发（排除纯贡献数据提交）
    Refresh->>API: 查询公开贡献
    API-->>Refresh: 返回记录
    alt 贡献记录有变化
        Refresh->>App: 申请 Source 短期写入令牌
        Refresh->>Source: App Bot 提交 contributions.json
        Note over Source,Refresh: 数据提交不再次触发贡献刷新
    else 数据未变化或 API 暂不可用
        Note over Refresh: 保留上一次校验通过的快照
    end
    Refresh->>Build: workflow_run（刷新流程完成后）
    Note over Build: 单元测试、离线构建并验证 _site/
    Build->>App: 申请 Published 短期写入令牌
    App-->>Build: GitHub App Token
    opt 静态文件有实质变化
        Build->>Output: App Bot 推送 _site/ 到 main
        par Pages
            Output->>Pages: 直接发布静态文件
        and Vercel
            Output->>Vercel: 部署同一份产物
        end
    end
```

Pull Request 只运行独立的验证工作流，不发布到生产环境。发布工作流也可单独手动运行。


### 运行机制说明

- **唯一构建**：网站只在源码仓库生成 `_site/`，发布仓库及托管平台不重复构建。
- **自动验证**：Pull Request 运行测试和浏览器检查，不触发正式发布。
- **短期授权**：跨仓库推送使用 GitHub App 临时令牌，不依赖长期个人访问令牌。
- **离线构建**：构建使用已提交的 `contributions.json`，不在构建阶段实时请求 GitHub API。
- **自动同步**：每次 Source 推送均先检查贡献数据；有变化时由 GitHub App Bot 提交，刷新工作流完成后才进行离线构建，避免额外 Dispatch 和重复发布。
- **版本追溯**：每次发布生成 `build-info.json`，记录源码提交与 Actions 运行信息。

发布仓库中的文件由本仓库自动生成，不应直接修改；其说明文档由 [PUBLISHED_README.md](PUBLISHED_README.md) 维护。
