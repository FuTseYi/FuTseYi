# futseyi.github.io

> [!WARNING]
> 本仓库是自动生成的静态网站发布仓库。请勿直接修改文件：后续自动发布可能覆盖手动更改。

网站源码、博客、构建脚本与发布配置统一维护在 [FuTseYi-Site](https://github.com/FuTseYi/FuTseYi-Site)。

Source 中的 GitHub Actions 生成唯一的 `_site/` 静态产物，并在文件发生变化时通过 **FuTseYi Site Automation** GitHub App Bot 推送到本仓库 `main`。GitHub Pages 与 Vercel 使用同一份产物，不在此重复构建。

`README.md` 由 Source 的 `PUBLISHED_README.md` 生成；`build-info.json` 记录所对应的源码提交和构建运行，供追溯与回滚。
