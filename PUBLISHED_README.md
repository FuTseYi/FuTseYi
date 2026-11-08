# futseyi.github.io

> [!WARNING]
> **本仓库是自动生成的静态网站托管仓库，请勿直接修改代码。**
>
> 所有网页文件均由源码仓库通过 GitHub Actions 自动构建并发布。此处的手动修改会在下一次自动发布时被覆盖。

## 源码

网站的源码、内容与构建流程统一维护在 **[FuTseYi-Site-Source 源码仓库](https://github.com/FuTseYi/FuTseYi-Site-Source)**（访问需具备仓库权限）。

## 运作机制

本仓库仅保存已构建完成的静态网站文件。源码仓库在验证通过后，将生成的 `_site/` 内容自动推送至本仓库的 `main` 分支，由 **GitHub Pages** 和 **Vercel** 使用同一份静态产物进行托管发布。

构建与部署均由源码仓库统一管理，本仓库不重复构建。每次发布附带 `build-info.json`，用于追溯对应的源码提交和 GitHub Actions 运行记录。
