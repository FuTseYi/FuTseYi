---
title: GitHub README 透明图片出现灰底的解决方法
date: 2026-11-02
tags: GitHub, Web Development, Troubleshooting
---

# 1 问题现象

最近在维护个人网站和 GitHub Profile README 时，我把 Active In 区域的组织 Logo 改成了本地托管的透明图片。网页中显示正常，VS Code 的 Markdown 预览也没有异常，但 GitHub 仓库和个人主页上的 README，却给图片加上了一层浅灰色背景。

最初看起来像是透明通道丢失，或者 GitHub 的图片代理缓存了旧资源。不过，图片下载到本地后仍然透明，网页中的同一张图片也正常显示，问题便不太像出在文件本身。

# 2 定位到 README 的图片属性

README 由脚本从网站内容自动生成。检查生成的 HTML，发现每张 Logo 都同时指定了宽度和高度：

```html
<img src="logo.svg" alt="" width="32" height="32" align="middle">
```

在 [GitHub Community 的相关讨论](https://github.com/orgs/community/discussions/192847) 中，也有人报告了相同的表现：README 的 `<img>` 同时设置 `width` 和 `height` 时，GitHub 渲染页面会出现额外的灰色背景，并提出移除其中一个尺寸属性作为规避方式。

这并不意味着 HTML 不应该同时声明图片宽高。在一般网页中，明确宽高有助于预留布局空间；这里遇到的是 GitHub Markdown 渲染环境下的具体表现。

# 3 最小修复

我只修改了 README 生成脚本，保留宽度，移除高度：

```diff
- <img src="logo.svg" alt="" width="32" height="32" align="middle">
+ <img src="logo.svg" alt="" width="32" align="middle">
```

图片高度因此由自身的宽高比决定，不需要修改 SVG、PNG、图片 URL 或网站的 CSS。更重要的是，修复写在同步脚本中，后续自动生成网站仓库 README 和个人 Profile README 时都会沿用同一规则。

# 4 验证与总结

重新同步两个 README 后，GitHub 页面上的灰色背景都消失了。网站原有的 Logo 布局没有变化，图片也仍然由同一套资源提供。

这次问题的关键不在于图片是否透明，而在于**同一段 HTML 在普通网页、编辑器预览和 GitHub README 中可能有不同的渲染结果**。遇到类似现象时，除了检查图片本身，也值得检查最终生成的标签和属性。

参考：[GitHub Community — GitHub adds grey background color to img in markdown](https://github.com/orgs/community/discussions/192847)。
