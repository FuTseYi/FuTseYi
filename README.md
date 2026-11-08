# FuTseYi-Site-Source

个人网站的唯一源码与构建仓库。基于原生 HTML、CSS、JavaScript 和 Python 生成静态网站；构建后的文件统一发布到 [FuTseYi.github.io](https://github.com/FuTseYi/FuTseYi.github.io)，供 GitHub Pages 和 Vercel 使用。

## 项目结构

```text
FuTseYi-Site-Source/
├── .github/workflows/  # 验证、贡献刷新、发布与 Profile 同步
├── assets/             # 样式、脚本、字体与图片
├── posts/              # Markdown 文章及其资源
├── scripts/            # 内容生成、索引、同步与校验
├── tests/              # 单元与浏览器回归测试
├── BLOG_INDEX.json     # 由文章元数据生成的编辑检索索引
├── contributions.json  # Git 跟踪的公开贡献数据快照
├── index.html          # 可直接维护的首页
├── preview.py          # 本地预览及唯一构建入口
└── requirements.txt    # Python 构建依赖
```

## 技术栈

- **HTML / CSS / JavaScript**：无前端构建框架的静态页面与交互
- **Python / Markdown**：文章生成、首页同步及构建验证
- **Pagefind**：构建时生成静态搜索索引
- **GitHub GraphQL**：查询公开贡献记录
- **GitHub Actions + GitHub App**：测试、刷新数据、同步 Profile 和跨仓库发布

## 本地开发

要求 Python 3.10 或更新版本。

```sh
python preview.py
python preview.py --build-only
python -m unittest discover -s tests -t . -p "test_*.py"
```

Windows 可使用 `py -3` 替代 `python`。预览、浏览器检查和环境设置见 [PREVIEW.md](PREVIEW.md)。

## 构建与发布

**Source**（本仓库）是唯一维护入口；**Published**（`FuTseYi/FuTseYi.github.io`）仅保存由 Source 产生的静态成品。GitHub Pages 与 Vercel 使用 Published 的同一份文件，不重复生成网站。发布仓库的 `README.md` 由 [PUBLISHED_README.md](PUBLISHED_README.md) 复制生成。

```mermaid
sequenceDiagram
    autonumber
    actor Maintainer as Maintainer
    participant Source as Source main
    participant Refresh as Refresh Action
    participant API as GitHub GraphQL
    participant App as GitHub App
    participant Deploy as Publish Action
    participant Published as Published main
    participant Hosts as GitHub Pages / Vercel

    opt 每月定时或手动刷新贡献
        Maintainer->>Refresh: schedule / workflow_dispatch
        Refresh->>App: 申请 Source 写入 Token
        App-->>Refresh: Installation token
        Refresh->>API: 使用内置 GITHUB_TOKEN 查询
        API-->>Refresh: 公开贡献数据
        opt 贡献快照实际变化
            Refresh->>Source: App Bot 提交 contributions.json
        end
    end
    opt 日常代码或内容更新
        Maintainer->>Source: Push / merge
    end
    Source->>Deploy: main push
    Note over Deploy: 测试并离线生成唯一 _site/
    Deploy->>App: 申请 Published 写入 Token
    App-->>Deploy: Installation token
    opt 静态文件实际变化
        Deploy->>Published: App Bot 提交静态产物
        Published->>Hosts: 使用同一份文件部署
    end
```

贡献刷新独立运行：每月 **1 日、15 日 UTC 01:17** 定时执行，也可手动触发；只有数据变化时，才由 GitHub App Bot 提交 `contributions.json`。Source `main` 上的任何 Push（包括 Bot 的贡献快照提交）都会触发网站发布，发布工作流也支持手动运行。构建只读取已提交的贡献快照，不调用 GraphQL；静态产物未变化时不会产生 Published 提交。Profile README 由独立的 [sync-readme.yml](.github/workflows/sync-readme.yml) 根据首页和文章相关变更同步到 `FuTseYi/FuTseYi`。

## 文档

- [AGENTS.md](AGENTS.md)：仓库工程原则与修改、验证边界
- [PREVIEW.md](PREVIEW.md)：开发、构建、测试和自动发布操作
- [BLOG_GUIDELINES.md](BLOG_GUIDELINES.md)：博客编辑、研究与索引规范
- [LICENSING.md](LICENSING.md)：代码、内容及第三方素材的许可说明
- [PUBLISHED_README.md](PUBLISHED_README.md)：Published 仓库 README 的唯一来源

**Every line of code should justify its existence. Define once. Reuse everywhere.**
