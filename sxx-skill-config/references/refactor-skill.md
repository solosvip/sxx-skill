# 改造旧技能以接入统一配置（AI 指南）

## 目标

把一个旧技能（自己写的/第三方下载的）改造成符合 `skills/`体系的结构：
- 每个技能拥有独立的 `config.json`，与其他技能完全解耦
- 代码不硬编码路径/密钥，统一从配置读取
- 生成 `skills/<skill>/config.example.json`（示例），便于独立分享时让别人知道怎么填
- 给出可验证的改造结果（能跑、能解释、风险可控）

## 改造原则（必须遵守）

- 不改变该技能的核心逻辑与流程：不要改它原本的工作步骤、产物结构、默认行为；只在“必要的位置”动手（把硬编码的设置点外置到配置，并让文档/脚本改为读取这些配置）。
- 配置项按技能定制：根据该技能真实存在的“设置点”来设计 `config.json`；不要为了统一而强行添加无用字段（例如不需要统一输入目录就不要加 `input_dir`）。
- 改造完成必须可用：改造后必须生成 `config.json`（本地可直接用的默认值）与 `config.example.json`（可分发示例）；`secrets` 默认留空或占位；不要提交/不要随技能分发真实的 `config.json`。

## 改造前：先做安全审计

如果是第三方技能，必须先按安全审计指南走一遍并输出报告：
- `references/audit-third-party-skill.md`

## 改造流程（按步骤执行）

### 1) 识别“配置点”

在代码中找出所有“应该外置”的东西，并列清单：
- 路径：输入/输出目录、浏览器路径、profile 目录、临时目录
- 账号与凭据：API 密钥、Cookie、令牌、用户名密码
- 运行参数：模型名、超时、并发、开关
- 固定 URL：接口地址、Webhook、上传地址

把每一个配置点分类到：
- `output_dir`：输出根目录（只有当技能需要统一输出目录时才用）
- `input_dir`：输入根目录（只有当技能需要统一输入目录时才用；如果输入来自用户传入路径，通常不需要）
- `settings`：非敏感配置（可公开结构，值通常由用户填写）
- `secrets`：敏感信息（密钥/令牌/Cookie）

### 2) 补齐本技能的配置文件

确保目标技能包含：
- `config.example.json`（示例配置，可提交/可分发）
- `config.json`（真实配置，不建议提交）
如果缺少这些文件，就在技能根目录新建它们（示例见本指南第 5 步）。注意：改造完成时 `config.json` 必须已经存在且可直接使用（至少能跑到主流程，缺少 secrets 时能给清晰报错）。

同时建议补齐 `__ui` 元数据：让网页面板能把这些配置项渲染成交互式表单（显示中文名、合适控件、说明等）。

### 3) 修改代码：用配置替代硬编码

在入口脚本（例如 `scripts/main.ts`）加入“读取本技能目录下的 config.json”：
```ts
import { readFileSync } from 'fs';

// scripts/main.ts -> ../config.json
const configUrl = new URL('../config.json', import.meta.url);
const config = JSON.parse(readFileSync(configUrl, 'utf-8'));
```

然后逐个替换：
- `"/Users/.../Downloads"` → `config.settings.xxx`（或本技能定义的其它路径字段）
- `"sk-..."` / Cookie 字符串 → `config.secrets.xxx`
- `"https://api..."` → `config.settings.base_url`（如果用户需要可改）

要求：
- 不要在日志里打印 secrets
- 不要为了“接入配置”而改变原有产物结构/输出规则；如果本技能使用 `output_dir`，则输出应写入 `config.output_dir`（或其子目录）

### 3.5) 改造文档里的输出路径（常见遗漏点）

很多技能把“输出目录结构”写在 Markdown（例如 `SKILL.md`）里：配置文件不会自动改写文档，因此需要用“文档约定”把输出路径讲清楚。

改造要点：
- 把文档中机器相关的绝对路径删除/替换（例如 `/Users/...`、`C:\\...`）
- 在 `SKILL.md` 开头新增“路径约定”，让 AI 落盘时统一从配置读取输出根目录
- 文档后续只写相对路径，统一相对“目标目录”

推荐模板（可直接粘贴到 `SKILL.md`开头）：

```md
## 路径约定
- 输出根目录：读取 `output_dir`（如果本技能使用）
- 输入目录：读取 `input_dir`（如果本技能使用）
- 目标目录：<输出根目录>/<任务标识或时间戳>/
- 本文档出现的所有输出路径都相对「目标目录」
```

### 4) 补齐本技能的真实配置（config.json）

在技能根目录准备 `config.json`，并确保至少包含“本技能真正需要的字段”（不要照抄模板）。常见情况下会包含：
- `output_dir`（如果本技能写产物且需要统一输出目录）
- `settings`（没有也可以是 `{}`）
- `secrets`（没有也可以是 `{}`，或用占位符提示用户填写）

注意：`config.json` 不建议提交到 Git。

### 5) 生成本技能示例配置（用于独立分享）

在技能根目录生成 `config.example.json`，只写示例值与字段说明，例如：
```json
{
  "output_dir": "~/Documents/BaoyuSkills/Output/my-skill",
  "settings": {
    "example_setting": "这里填写可公开的示例配置"
  },
  "secrets": {
    "example_api_key": "在此填入密钥（不要提交到 Git）"
  }
}
```

注意：
- `config.example.json` 不会被自动读取
- 独立运行时由使用者复制为 `config.json` 并填写

## __ui 元数据（让网页面板可交互配置）

JSON 不支持注释。为了让网页面板显示“中文显示名/说明/控件类型”，约定把这些信息写在同一个文件的 `__ui` 字段里：

- `__ui.fields` 的 key 使用“字段路径”（点号路径），例如：
  - `output_dir`
  - `settings.xxx`
  - `secrets.xxx`
- `__ui.order` 用于控制网页上的展示顺序（可选）

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

说明：
- `__ui` 只给网页用；技能脚本应忽略它。
- `secret` 类型在网页中不回显；留空表示“保持不变”；可点“清空”清掉已有值。

## 验证清单（改造后必须完成）

### 本地验证

- 在本技能目录 `config.json` 写入所需字段
- 运行技能主流程，确认：
  - 能正确读取本技能定义的配置字段（不要假设一定存在 `input_dir`）
  - 输出写入预期目录
  - 不会打印/写出 secrets

### 独立分享验证（可选）

目标：只分发 `config.example.json` 时，接收者能清楚地复制为 `config.json` 并填写后运行。

做法：
- 复制 `config.example.json` → `config.json`
- 填写最小可运行配置
- 运行技能，确认能走通主流程

### 安全回归

- 确认没有新增危险行为（删文件、执行未知命令、外传数据）
- 如果技能需要网络/浏览器自动化，在 `SKILL.md` 明确说明：
  - 会访问哪些网站/接口
  - 会读取哪些本机数据
  - 风险与建议的隔离方式
