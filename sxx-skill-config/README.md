# sxx-skill-config：技能配置与治理元技能

## 目的

当你积累了很多技能（自己写的、网上下载的），很容易陷入混乱：
- 每个技能各自管理配置（API 密钥、路径、Cookie），写法不一致
- 输入/输出目录散落在各处，迁移困难
- 第三方技能可能包含危险行为（删文件、外传数据、偷 Cookie 等）
- 没有一个统一入口去查看/编辑配置

`sxx-skill-config` 的目标是建立一套统一规则，让技能库变成“可管理的系统”。

## 核心约定（最重要）

父目录固定为 `skills/`，每个技能都拥有**自己的**配置文件，与其他技能完全解耦：
- 技能目录：`skills/<skill-name>/...`
- 真实配置：`skills/<skill-name>/config.json`（不建议提交到 Git）
- 示例配置：`skills/<skill-name>/config.example.json`（可提交/可分发）

配置读取规则（建议写进每个技能的脚本/文档里）：
1) 只读取本技能目录的 `config.json`
2) `config.example.json`永远不会被自动读取（只用于示例/分发说明）

## config.json 的 __ui 元数据（给网页面板用）

JSON 不支持注释。为了让网页端能用“中文显示名 + 合适控件（目录选择/开关/下拉/密码框…）”来渲染配置项，本项目约定把这部分信息写在同一个文件的 `__ui` 字段里。

约定：
- 顶层字段（例如 `output_dir` / `settings` / `secrets`）给技能运行用
- `__ui` 给网页面板用；技能脚本应忽略
- `__ui.fields` 的 key 用“字段路径”（点号路径），例如 `settings.xxx`、`secrets.xxx`

最小示例：
```json
{
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {
    "enable_feature": false
  },
  "secrets": {
    "api_key": ""
  },
  "__ui": {
    "fields": {
      "output_dir": { "label": "输出目录", "type": "directory", "required": true },
      "settings.enable_feature": { "label": "启用功能", "type": "boolean" },
      "secrets.api_key": { "label": "API Key", "type": "secret" }
    },
    "order": ["output_dir", "settings.enable_feature", "secrets.api_key"]
  }
}
```

常见 `type`：
- `directory`：目录选择（带“选择…”按钮）
- `boolean`：开关
- `string` / `number` / `textarea`
- `select`：下拉（需要 `options`）
- `secret`：敏感信息（不回显；留空=保持不变；可点“清空”）

改造原则（非常重要）：
- 改造技能时不要改变该技能的核心逻辑/流程/默认行为；只在必要位置把硬编码的“设置点”外置到配置。
- 配置项按技能定制：根据该技能真实需要来定义字段；不要教条地给所有技能强加 `input_dir` 等字段。
- 改造完成必须可用：改造后要同时生成 `config.example.json`（示例）与 `config.json`（本地可直接用的默认值；`secrets` 留空或占位）。

常用命名（按需使用，非强制）：
```json
{
  "output_dir": "...",
  "settings": {},
  "secrets": {}
}
```

## 输出路径约定（推荐）

配置文件只负责提供“该技能需要的可变参数”，不会自动决定输出目录结构，也不会自动改写 Markdown 文档里的路径。

为了让脚本型技能与文档型技能都“低复杂度 + 高可靠”，推荐统一约定：
- 输出根目录：读取 `output_dir`（如果本技能使用）
- 目标目录：`<输出根目录>/<任务标识或时间戳>/`
- 文档中出现的输出路径：只写相对 `目标目录` 的相对路径（避免写死绝对路径）

## 文档（面向 AI 的工作指南）

本技能强调“文档驱动”，让 AI 按清单办事并输出结果：
- 新建技能（创建独立配置）：见 `references/create-skill.md`
- 第三方技能安全审计（生成报告）：见 `references/audit-third-party-skill.md`
- 改造/接入统一配置（含验证清单）：见 `references/refactor-skill.md`

## 可选工具脚本（辅助，不替代文档）

- `scripts/server/server.py`：本地网页面板（交互式表单），用于遍历并管理每个技能目录下的 `config.json`

运行：
```bash
python3 skills/sxx-skill-config/scripts/server/server.py
```

打开：
- http://localhost:8781
