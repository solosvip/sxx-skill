# 创建新技能（AI 指南）

## 目标

- 在 `skills/` 体系内创建新技能，并为该技能创建独立的 `config.json`。
- 技能代码不硬编码路径/账号/密钥，不私自读取不必要的本机数据。
- 技能天然支持独立运行与分享：配置文件就在技能目录下（建议只分发 `config.example.json`）。

## 目录与文件约定

```
skills/
  <skill-name>/
    SKILL.md                    # 技能入口说明（给 AI 用）
    config.json                 # 本技能真实配置（不建议提交）
    config.example.json         # 本技能示例配置（可提交）
    scripts/
      main.ts
    references/                 # 可选：较长的流程/模板/参考资料
```

## 配置读取规则（必须遵守）

1) 每个技能只读取自己目录下的 `config.json`，与其他技能完全解耦。  
2) 不强制使用任何“通用配置加载器”。脚本直接读取本技能目录下的 `config.json` 即可。  
3) `config.example.json`只用于示例/分发说明，默认不会被技能自动读取（除非你显式写代码去读它）。

## 新技能最小骨架（必须包含）

- `skills/<skill-name>/SKILL.md`
- `skills/<skill-name>/scripts/main.ts`
- `skills/<skill-name>/config.example.json`（示例配置）
- `skills/<skill-name>/config.json`（真实配置，不建议提交；可以先由示例复制一份）

## 创建流程（按步骤执行）

1) 确定技能名（`skill-name`）
- 使用小写字母/数字/短横线，避免空格与中文文件夹名。

2) 生成目录结构
- 创建 `scripts/`、`references/`（可选）。

3) 准备配置文件
- 写 `config.example.json`：只放示例值与字段结构，让人一看就知道怎么填（不要放真实密钥）。
- 写 `config.json`：真实配置文件（可以先从 `config.example.json` 复制一份再填写）。
- 为了让网页面板能把配置渲染成交互式表单，建议同时写入 `__ui` 元数据（见下文“__ui 元数据”）。

4) 编写 `scripts/main.ts`
- 第一件事：读取 `../config.json`
- 所有可变参数都从这里读取（只读本技能需要的字段；不要教条地假设一定存在 `input_dir`）：
  - 输出根目录（如果本技能需要统一输出目录）：`config.output_dir`
  - 非敏感配置：`config.settings.*`
  - 密钥/令牌：`config.secrets.*`
- 不要：
  - 在代码里写死 API 密钥 / Cookie / 个人目录
  - 随意读取桌面/文档/浏览器数据（除非技能明确需要，并且写清楚）

推荐读取方式（入口脚本位于 `scripts/` 时，例如 `scripts/main.ts`）：
```ts
import { readFileSync } from 'fs';

// scripts/main.ts -> ../config.json
const configUrl = new URL('../config.json', import.meta.url);
const config = JSON.parse(readFileSync(configUrl, 'utf-8'));
```

5) 编写 `SKILL.md`（给 AI 看的）
- frontmatter 必须包含：
  - `name: <skill-name>`
  - `description: ...`（用中文写清“何时使用这个技能”，尽量列出触发词/场景）
- 正文至少说明：
  - 这个技能做什么
  - 如何运行（在 Codex 中的命令形式）
  - 需要哪些配置字段（哪些在 settings，哪些在 secrets）
  - 输出目录/产物说明（写到哪里、生成哪些文件）

## 输出路径约定（强烈建议）

很多技能的“输出目录结构”写在 Markdown 文档里：配置文件不会自动改写文档，因此必须靠“文档约定”把输出路径讲清楚。

为了低复杂度 + 高可靠，建议在每个技能的 `SKILL.md` 开头固定写一段“路径约定”，并在文档后续只使用相对路径：

```md
## 路径约定
- 输出根目录：读取 `output_dir`（如果本技能使用）
- 输入目录：读取 `input_dir`（如果本技能使用）
- 目标目录：<输出根目录>/<任务标识或时间戳>/
- 本文档出现的所有输出路径都相对「目标目录」（不要写机器相关的绝对路径）
```

脚本型技能也遵守同一套约定：所有写文件/生成图片/导出产物，都应基于 `config.output_dir`（或其子目录）拼出最终路径。

6) 准备 `config.example.json`（本技能示例）
- 只放示例值与字段结构，让人一看就知道怎么填。
- 不要放真实密钥。
- 不要为了统一而强行塞字段：只写本技能真正需要的设置点；敏感信息统一放进 `secrets`（示例用占位符）。

## __ui 元数据（让网页面板可交互配置）

JSON 不支持注释。为了让网页面板显示“中文显示名/说明/控件类型”，约定把这些信息写在同一个文件的 `__ui` 字段里：

- `__ui.fields` 的 key 使用“字段路径”（点号路径），例如：
  - `output_dir`
  - `settings.model`
  - `secrets.openai_api_key`
- `__ui.order` 用于控制网页上的展示顺序（可选）

示例：
```json
{
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {
    "model": "gpt-4o"
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
      "settings.model": {
        "label": "模型",
        "type": "select",
        "options": [
          { "label": "gpt-4o", "value": "gpt-4o" },
          { "label": "gpt-4.1", "value": "gpt-4.1" }
        ]
      },
      "secrets.openai_api_key": {
        "label": "OpenAI API Key",
        "type": "secret",
        "description": "敏感信息：网页不回显，留空=保持不变"
      }
    },
    "order": ["output_dir", "settings.model", "secrets.openai_api_key"]
  }
}
```

说明：
- `__ui` 只给网页用；技能脚本应忽略它。
- `secret` 类型在网页中不回显；留空表示“保持不变”；可点“清空”清掉已有值。

## 自检清单（创建完成后）

- `scripts/main.ts` 没有硬编码密钥/路径
- 默认读配置即可运行到主流程（缺配置能给出清晰报错）
- 输出写入 `config.output_dir` 或其子目录，不写到未知位置
- `config.example.json` 可读、可理解、无敏感信息
