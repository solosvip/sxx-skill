---
name: sxx-skill-config
description: "技能配置与治理元技能。用统一的网页管理每个 skill 的配置。用于统一每个技能目录下 config.json 的配置标准；指导/辅助把旧技能改造成可接入统一配置的结构。"
---

# sxx-skill-config：技能配置与治理系统

这个技能相当于你的技能库“操作系统”：建立统一配置标准与安全治理流程，让技能能在同一套体系下稳定运行。

## 用法

### 1) 创建新技能（文档驱动）

创建流程：见 `references/create-skill.md`。

### 2) 第三方技能安全审计（文档驱动）

审计方法与报告模板：见 `references/audit-third-party-skill.md`。

### 3) 改造旧技能（文档驱动）

改造流程与验证清单：见 `references/refactor-skill.md`。

### 4) 管理配置（网页面板）

启动本地网页面板，用于遍历所有技能，并把每个技能的 `config.json` 渲染成交互式表单（用户不需要直接编辑 JSON 文本）。

**用户说"打开技能设置""打开配置网页"等时，必须执行下面这段幂等启动命令：**
- 先检测 8781 端口是否已有服务在跑；已在跑就直接打开浏览器，未跑才启动，避免"端口被占用→静默失败"。

```bash
if ! lsof -ti tcp:8781 >/dev/null 2>&1; then
  python3 ~/.claude/skills/sxx-skill-config/scripts/server/server.py >/dev/null 2>&1 &
  sleep 2
fi
open http://localhost:8781
```

## 配置体系（核心约定）

### 目录结构

```
skills/
  <skill-name>/
    SKILL.md                  # 技能说明
    config.json               # 本技能真实配置（不建议提交）
    config.example.json       # 本技能示例配置（可提交，用于独立分享说明）
    scripts/
      main.ts
```

### 配置文件（每技能独立）

每个技能只读取自己目录下的 `config.json`，与其他技能完全解耦。

其中：
- `config.json`：给技能运行用（脚本读取它）
- `__ui`：给网页面板用（渲染显示名/控件类型/说明）；技能脚本应忽略它

### 改造原则（必须遵守）

当你用本技能去“改造/接入”任意第三方或旧技能时，必须遵守：
- 不改变该技能的核心逻辑与流程：不要改它原本的工作步骤、产物结构、默认行为；只在“必要的位置”动手（把硬编码的路径/开关/凭据外置到配置，并让文档/脚本改为读取这些配置）。
- 配置项按技能定制：根据该技能真实存在的“设置点”来设计 `config.json`；不要为了统一而强行添加无用字段（例如不需要统一输入目录就不要加 `input_dir`）。
- 改造完成必须可用：改造后必须生成 `config.json`（本地可直接使用的默认值）与 `config.example.json`（可分发的示例）；`secrets` 默认留空或占位；不要提交/不要随技能分发真实的 `config.json`。

#### 常用命名（按需使用）

配置字段不要求统一模板，但推荐优先复用这些“通用名字”（仅当技能确实需要时才使用）：
- `output_dir`：输出根目录（写文件/图片/产物用）
- `input_dir`：输入根目录（只有当技能需要统一从某个目录取输入时才用；若输入来自用户传入路径，则通常不需要）
- `settings`：非敏感设置（开关/参数/路径等）
- `secrets`：敏感信息（API 密钥 / 令牌 / Cookie）

示例 1（只需要输出目录）：
```json
{
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {},
  "secrets": {}
}
```

示例 2（需要统一输入/输出目录）：
```json
{
  "input_dir": "~/Documents/BaoyuSkills/Input",
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {},
  "secrets": {}
}
```

### 配置读取方式（脚本示例）

不强制使用任何“通用配置加载器”。每个技能的脚本自行读取本技能目录下的 `config.json` 即可。

如果你的入口脚本位于 `scripts/` 目录（例如 `scripts/main.ts`），推荐这样读取：
```typescript
import { readFileSync } from 'fs';

// scripts/main.ts -> ../config.json
const configUrl = new URL('../config.json', import.meta.url);
const config = JSON.parse(readFileSync(configUrl, 'utf-8'));

// 根据本技能定义的字段读取（不要假设一定存在 input_dir）
console.log(config.output_dir);
```

### __ui 元数据（给网页面板用）

JSON 本身不支持注释，所以“显示名/说明/控件类型/可选项”等信息，统一放在 `__ui` 里。

约定：
- 真实配置字段仍然在 JSON 顶层（例如 `output_dir` / `settings` / `secrets`）
- `__ui` 放在文件末尾（本项目写回时也会自动把 `__ui` 放到最后）
- `__ui.fields` 的 key 使用“字段路径”（支持点号路径），例如：
  - `output_dir`
  - `settings.write_back_to_source_article`
  - `secrets.openai_api_key`

最小示例：
```json
{
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {
    "enable_feature": false
  },
  "secrets": {
    "openai_api_key": ""
  },
  "__ui": {
    "fields": {
      "output_dir": {
        "label": "输出目录",
        "type": "directory",
        "required": true,
        "description": "本技能所有产物写入该目录下"
      },
      "settings.enable_feature": {
        "label": "启用功能",
        "type": "boolean",
        "description": "开关类配置"
      },
      "secrets.openai_api_key": {
        "label": "OpenAI API Key",
        "type": "secret",
        "description": "敏感信息：网页不回显，留空=保持不变"
      }
    },
    "order": [
      "output_dir",
      "settings.enable_feature",
      "secrets.openai_api_key"
    ]
  }
}
```

支持的 `type`（按需使用）：
- `string`：单行文本
- `number`：数字
- `boolean`：开关
- `directory`：目录路径（带“选择…”按钮）
- `select`：下拉（配合 `options`）
- `textarea`：多行文本
- `secret`：敏感信息（密码框；不回显）

`select` 示例（可选）：
```json
{
  "label": "模型",
  "type": "select",
  "options": [
    { "label": "gpt-4o", "value": "gpt-4o" },
    { "label": "gpt-4.1", "value": "gpt-4.1" }
  ]
}
```

### secrets 在网页中的行为（约定）

- 网页不会回显 secrets 的真实值（只显示“已设置/未设置”）。
- secrets 输入框：留空表示“保持不变”。
- 如需清空某个 secret：点击该项旁的“清空”按钮。
- 实现说明：为支持“留空=保持不变”，密钥真实值会经由本机 localhost（回环地址）读入网页内存用于回传，但**不会在界面上显示**。这是本机工具的常见做法；若需要“密钥永不离开磁盘”的更强保证，需另做服务端脱敏改造。

### 目录选择器的安全边界（约定）

目录选择器只允许在少数“根目录”下浏览子目录（例如：文稿/桌面/下载/用户目录/当前项目），并禁止 `..` 与绝对路径越界访问。

### 输出路径与文档型技能（重要）

配置文件只负责提供“该技能需要的可变参数”，不会自动决定输出目录结构，也不会自动改写 Markdown 文档里的路径。

输出路径由“执行者”控制：
- 脚本型技能：由 `scripts/*.ts` 决定；如果本技能有 `output_dir`，应基于 `config.output_dir` 拼接输出路径。
- 文档型技能（主要靠 `SKILL.md` 驱动 AI 落盘）：由文档约定决定，建议在 `SKILL.md` 开头明确“输出根目录”，后续只写相对路径。

推荐约定（降低复杂度、提高可靠性）：
- 输出根目录：读取 `output_dir`（如果本技能使用）
- 输入目录：读取 `input_dir`（如果本技能使用）
- 目标目录：`<输出根目录>/<任务标识或时间戳>/`
- 文档中出现的所有输出路径：相对 `目标目录`（不要写机器相关的绝对路径）

说明：
- 文档/脚本只引用配置中的变量名（例如 `output_dir` / `settings.xxx` / `secrets.xxx`），具体值由本技能目录下的 `config.json` 决定。

### 独立分享（可选）

本方案天然支持独立分享：配置文件就在技能目录下。

建议只分发 `config.example.json`（示例），由使用者自行复制为 `config.json` 并填写；不要分发真实的 `config.json`。

## 脚本目录（辅助工具）

| 脚本 | 作用 |
|--------|---------|
| `scripts/server/server.py` | 本地网页面板（遍历技能并用交互式表单管理各技能的 config.json） |
