---
title: 使用 Biome 进行代码检查
date: 2025-06-07
tags: biome, Blog
---

> Biome 检测到多个 `.astro` 和 `.svelte` 文件的格式问题，主要是 **代码缩进和换行不一致**。Biome 会尝试自动修复这些问题，但你需要手动确认或调整配置。

# 1 **解决方案**

## 1.1 **自动修复格式问题**

运行以下命令，让 Biome 自动修复所有格式问题：

```bash
biome format ./src --write
```

这会直接修改文件，使其符合 Biome 的默认规则。

------

## 1.2 **手动检查差异**

如果自动修复后仍有问题，可以对比 Biome 的期望格式和当前文件的差异：

```bash
biome check ./src
```

Biome 会显示哪些行需要调整，例如：

```bash
× Formatter would have printed the following content:
  1 │ - import·{·Icon·}·from·"astro-icon/components";
  2 │ + import·{·Icon·}·from·"astro-icon/components";
```

`-` 表示当前代码，`+` 表示 Biome 期望的格式。

## 1.3 **调整 Biome 配置（可选）**

如果默认规则不符合你的需求，可以在 `biome.json` 中修改配置：

```json
{
  "formatter": {
    "indentStyle": "space",  // 或 "tab"
    "indentWidth": 2,       // 缩进宽度
    "lineWidth": 80         // 每行最大字符数
  },
  "linter": {
    "rules": {
      "recommended": true,
      "correctness": {
        "noUnusedVariables": "off"  // 关闭未使用变量的检查
      }
    }
  }
}
```

然后重新运行检查：

```bash
biome check ./src
```

## 1.4 **忽略特定文件或规则**

如果某些文件不需要格式化，可以在 `biome.json` 中添加 `ignore`：

```json
{
  "files": {
    "ignore": [
      "src/components/LightDarkSwitch.svelte",
      "src/utils/url-utils.ts"
    ]
  }
}
```

## 1.5 **使用 `npx` 临时运行**

如果不想全局安装，可以用 `npx` 直接运行：

```bash
npx @biomejs/biome format --write ./src
```
