# sxx-skill

苏醒醒的开源 Skill 分享仓库。把打磨好、可独立运行的 Claude / Codex 技能一个一个分享出来。

## 这是什么

每个技能是一个独立目录，自带说明与示例配置，可以单独取用、独立运行，不依赖本仓库的其他技能。

## 怎么用一个技能

1. 把对应技能目录复制到你自己的 skills 目录下。
2. 如果该技能带 `config.example.json`，复制成 `config.json` 并填入你自己的路径 / 密钥。
3. 按该技能目录里的 `SKILL.md` 使用。

## 关于配置与密钥

- 本仓库只收录 `config.example.json`（示例，不含真实密钥）。
- 真实的 `config.json`（可能含 API Key / Cookie）已被 `.gitignore` 屏蔽，不会进入仓库。
- 取用技能后，请在你本地自行填写 `config.json`。

## License

[MIT](LICENSE)
