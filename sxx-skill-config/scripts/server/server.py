#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse


# 目录约定：skills/<skill-name>/config.json（每个技能独立配置）
# 当前文件：skills/sxx-skill-config/scripts/server/server.py
# SKILLS_DIR：从 server/ 目录向上 3 级 -> skills/
SERVER_DIR = Path(__file__).resolve().parent
SKILLS_DIR = (SERVER_DIR.parent.parent.parent).resolve()
PUBLIC_DIR = (SERVER_DIR / "public").resolve()
PORT = 8781

# CSRF / DNS-rebinding 防护：只接受来自本机回环地址的请求。
# - Host 校验：挡 DNS-rebinding（恶意域名解析到 127.0.0.1 后偷读密钥），其 Host 头仍是恶意域名。
# - Origin 校验（仅写接口）：挡跨站请求伪造（别的网页偷偷 POST 改写 config.json）。
ALLOWED_HOSTS = {f"localhost:{PORT}", f"127.0.0.1:{PORT}"}
ALLOWED_ORIGINS = {f"http://localhost:{PORT}", f"http://127.0.0.1:{PORT}"}


def to_tilde_path(p: str) -> str:
    """
    把绝对路径尽量转换成带 ~ 的形式（更适合写进 config.json 给人看）。
    例如：/Users/<用户名>/Documents -> ~/Documents
    """
    s = (p or "").strip()
    if not s:
        return s
    # 去掉末尾分隔符（mac 的 choose folder 会返回 / 结尾）
    s = s.rstrip("/\\")

    try:
        home = str(Path.home().resolve())
    except Exception:
        return s

    if s == home:
        return "~"
    if s.startswith(home + os.sep):
        return "~" + s[len(home) :]
    return s


def choose_directory_system_dialog(title: str = "", initial: str = "") -> dict:
    """
    弹出系统级目录选择器（本地环境使用）。
    - 成功：{ cancelled: false, path: "<可写入 config.json 的路径>", abs_path: "<绝对路径>" }
    - 取消：{ cancelled: true }
    """
    if sys.platform != "darwin":
        raise ValueError("当前仅支持 macOS 的系统级目录选择器（osascript）。")

    prompt = (title or "").strip() or "请选择目录"

    # initial 允许传入 ~，这里做展开；无效/不存在则忽略
    default_dir = None
    if initial:
        try:
            expanded = os.path.expanduser(initial)
            candidate = Path(expanded).resolve()
            if candidate.exists() and candidate.is_dir():
                default_dir = str(candidate)
        except Exception:
            default_dir = None

    def esc_as(s: str) -> str:
        # AppleScript 字符串字面量的最小转义（避免引号/反斜杠破坏脚本）
        return (s or "").replace("\\", "\\\\").replace('"', '\\"')

    script = f'POSIX path of (choose folder with prompt "{esc_as(prompt)}"'
    if default_dir:
        script += f' default location POSIX file "{esc_as(default_dir)}"'
    script += ")"

    try:
        # choose folder 会阻塞直到用户选择/取消；给一个宽松超时，避免服务永久卡死
        out = subprocess.run(
            ["osascript", "-e", script],
            text=True,
            capture_output=True,
            timeout=300,
        )
    except subprocess.TimeoutExpired:
        return {"cancelled": True}

    if out.returncode != 0:
        # 用户点取消时通常也会返回非 0；这里统一按“取消”处理
        return {"cancelled": True}

    abs_path = (out.stdout or "").strip()
    if not abs_path:
        return {"cancelled": True}

    abs_path = abs_path.rstrip("/\\")
    return {
        "cancelled": False,
        "path": abs_path,
        "abs_path": abs_path,
    }


def get_fs_roots() -> list[dict]:
    home = Path.home().resolve()
    workspace = SKILLS_DIR.parent.resolve()
    roots = [
        {"id": "documents", "label": "文稿（Documents）", "path": (home / "Documents").resolve(), "display": "~/Documents"},
        {"id": "desktop", "label": "桌面（Desktop）", "path": (home / "Desktop").resolve(), "display": "~/Desktop"},
        {"id": "downloads", "label": "下载（Downloads）", "path": (home / "Downloads").resolve(), "display": "~/Downloads"},
        {"id": "home", "label": "用户目录（Home）", "path": home, "display": "~"},
        {"id": "workspace", "label": "当前项目（Workspace）", "path": workspace, "display": str(workspace)},
    ]
    # 过滤不存在的目录（例如某些系统没有 Desktop）
    out = []
    for r in roots:
        try:
            if r["path"].exists() and r["path"].is_dir():
                out.append(r)
        except Exception:
            continue
    return out


def resolve_under_root(root_path: Path, rel: str) -> Path:
    # rel 只能是相对路径，不允许 ..，不允许绝对路径
    rel = (rel or "").replace("\\", "/").strip()
    if rel.startswith("/"):
        raise ValueError("path 只能是相对路径")
    parts = [p for p in rel.split("/") if p]
    if any(p == ".." for p in parts):
        raise ValueError("path 不允许包含 ..")

    base = root_path.resolve()
    target = (base / Path(*parts)).resolve()
    if str(target) != str(base) and not str(target).startswith(str(base) + os.sep):
        raise ValueError("越界访问被拒绝")
    return target


def read_frontmatter(skill_md_path: Path) -> dict:
    """
    只解析 SKILL.md 开头的 YAML frontmatter（--- ... ---），提取一层 key: value。
    不依赖第三方 YAML 库，够用即可（name/description 等）。
    """
    try:
        text = skill_md_path.read_text(encoding="utf-8")
    except Exception:
        return {}

    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}

    end = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end = i
            break
    if end is None:
        return {}

    data: dict[str, str] = {}
    for line in lines[1:end]:
        s = line.strip()
        if not s or s.startswith("#") or ":" not in s:
            continue
        k, v = s.split(":", 1)
        k = k.strip()
        v = v.strip()
        if not k:
            continue
        # 去掉最外层引号（常见场景：description: "..."）
        if (len(v) >= 2) and ((v[0] == v[-1] == '"') or (v[0] == v[-1] == "'")):
            v = v[1:-1]
        data[k] = v
    return data


def summarize_config(config: dict) -> dict:
    settings = config.get("settings") if isinstance(config.get("settings"), dict) else {}
    secrets = config.get("secrets") if isinstance(config.get("secrets"), dict) else {}

    other_keys = [k for k in config.keys() if k not in ("settings", "secrets", "__ui")]
    other_keys.sort()

    settings_keys = sorted(settings.keys())
    secrets_keys = sorted(secrets.keys())

    return {
        "input_dir": config.get("input_dir"),
        "output_dir": config.get("output_dir"),
        "other_keys": other_keys,
        "settings_keys": settings_keys,
        "secrets_keys": secrets_keys,
    }


def is_skill_dir(p: Path) -> bool:
    return p.is_dir() and (p / "SKILL.md").exists()


def list_skills() -> list[str]:
    names: list[str] = []
    for entry in SKILLS_DIR.iterdir():
        if not entry.is_dir():
            continue
        name = entry.name.strip()
        if not name or name.startswith("."):
            continue
        if is_skill_dir(entry):
            names.append(name)
    names.sort()
    return names


def assert_skill_name(skill: str) -> None:
    if not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", skill or ""):
        raise ValueError(f"非法技能名：{skill}")
    d = SKILLS_DIR / skill
    if not is_skill_dir(d):
        raise ValueError(f"未找到技能目录：{d}")


def read_json(p: Path):
    raw = p.read_text(encoding="utf-8")
    return json.loads(raw)


def normalize_config_for_write(config: dict) -> dict:
    """
    写回 config.json 时做两个事情：
    1) 保持“技能运行配置”在前、“__ui 元数据”在最后（更易读）
    2) 确保 settings/secrets 至少是对象（避免网页/脚本读到非预期类型）
    """
    out: dict = {}

    # 常见字段优先
    if "output_dir" in config:
        out["output_dir"] = config.get("output_dir")
    if "input_dir" in config:
        out["input_dir"] = config.get("input_dir")

    settings = config.get("settings")
    out["settings"] = settings if isinstance(settings, dict) else {}

    secrets = config.get("secrets")
    out["secrets"] = secrets if isinstance(secrets, dict) else {}

    # 其他字段（保持原顺序）
    for k, v in config.items():
        if k in ("output_dir", "input_dir", "settings", "secrets", "__ui"):
            continue
        out[k] = v

    # __ui 永远放最后（给网页用；技能脚本应忽略）
    if "__ui" in config:
        out["__ui"] = config.get("__ui")

    return out


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, data, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_text(self, text: str, status: int = 200, content_type: str = "text/plain; charset=utf-8"):
        body = text.encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, p: Path, content_type: str):
        if not p.exists() or not p.is_file():
            self._send_text("未找到", status=404)
            return
        body = p.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _host_ok(self) -> bool:
        return (self.headers.get("Host") or "").strip() in ALLOWED_HOSTS

    def _origin_ok(self) -> bool:
        # 无 Origin（同源表单 / curl 等）放行；有 Origin 必须是本机回环来源
        origin = (self.headers.get("Origin") or "").strip()
        return (not origin) or (origin in ALLOWED_ORIGINS)

    def do_GET(self):
        if not self._host_ok():
            self._send_text("非法 Host（仅允许本机访问）", status=403)
            return

        u = urlparse(self.path)

        # 1) 页面
        if u.path == "/":
            self._send_file(PUBLIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        # 1.5) 文件系统：根目录列表（用于“选择目录”）
        if u.path == "/api/fs/roots":
            roots = []
            for r in get_fs_roots():
                roots.append({"id": r["id"], "label": r["label"], "display": r["display"]})
            self._send_json({"roots": roots})
            return

        # 1.6) 文件系统：列出某个目录下的子目录（用于“选择目录”）
        if u.path == "/api/fs/list":
            qs = parse_qs(u.query or "")
            root_id = (qs.get("root") or [""])[0]
            rel = (qs.get("path") or [""])[0]

            roots = {r["id"]: r for r in get_fs_roots()}
            if root_id not in roots:
                self._send_json({"error": "非法 root"}, status=400)
                return

            try:
                root = roots[root_id]
                target = resolve_under_root(root["path"], rel)
                if not target.exists() or not target.is_dir():
                    raise ValueError("目录不存在")

                dirs = []
                for entry in sorted(target.iterdir(), key=lambda p: p.name.lower()):
                    try:
                        if not entry.is_dir():
                            continue
                        name = entry.name
                        if name.startswith("."):
                            continue
                        child_rel = str(entry.relative_to(root["path"]).as_posix())
                        dirs.append({"name": name, "path": child_rel})
                    except Exception:
                        continue

                # 当前目录的展示路径（绝对路径，写入 config.json 后无需 expanduser）
                display = str(target)

                self._send_json({"root": root_id, "cwd": rel, "display": display, "dirs": dirs})
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 1.7) 系统级目录选择器（本地环境）
        if u.path == "/api/os/choose-directory":
            qs = parse_qs(u.query or "")
            title = (qs.get("title") or [""])[0]
            initial = (qs.get("initial") or [""])[0]
            try:
                result = choose_directory_system_dialog(title=title, initial=initial)
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
            return

        # 2) 接口：列出技能
        if u.path == "/api/skills":
            skills = []
            for name in list_skills():
                d = SKILLS_DIR / name
                skill_md_path = d / "SKILL.md"
                fm = read_frontmatter(skill_md_path)

                config_path = d / "config.json"
                example_path = d / "config.example.json"
                has_config = config_path.exists()
                has_example = example_path.exists()

                item = {
                    # 目录名（也就是技能 id）
                    "name": name,
                    # SKILL.md frontmatter（用于展示给用户看）
                    "yaml_name": fm.get("name", ""),
                    "description": fm.get("description", ""),
                    # 文件状态
                    "skill_md_path": str(skill_md_path),
                    "config_path": str(config_path),
                    "example_path": str(example_path),
                    "has_config": has_config,
                    "has_example": has_example,
                    "config_summary": None,
                    "config_error": "",
                }

                # 只在存在 config.json 时读取并汇总“可设置项”（不展示 secrets 的值）
                if has_config:
                    try:
                        cfg = read_json(config_path)
                        if isinstance(cfg, dict):
                            item["config_summary"] = summarize_config(cfg)
                        else:
                            item["config_error"] = "config.json 不是 JSON 对象"
                    except Exception as e:
                        item["config_error"] = f"config.json 解析失败：{e}"

                skills.append(item)
            self._send_json({"skills": skills})
            return

        # 3) 接口：读取某个技能配置
        if u.path == "/api/config":
            qs = parse_qs(u.query or "")
            skill = (qs.get("skill") or [""])[0]
            try:
                assert_skill_name(skill)
                d = SKILLS_DIR / skill
                config_path = d / "config.json"
                example_path = d / "config.example.json"

                source = "none"
                exists = False
                note = ""
                base_config = None

                if config_path.exists():
                    source = "config.json"
                    exists = True
                    base_config = read_json(config_path)
                elif example_path.exists():
                    source = "config.example.json"
                    exists = False
                    base_config = read_json(example_path)
                    note = "当前技能没有 config.json，正在使用 config.example.json 作为初始值；点击保存将写入 config.json。"
                else:
                    base_config = {
                        "settings": {},
                        "secrets": {},
                        "__ui": {"fields": {}, "order": []},
                    }
                    note = "暂无配置文件（config.json/config.example.json 都不存在）。"

                if not isinstance(base_config, dict):
                    raise ValueError("配置文件必须是 JSON 对象")

                self._send_json(
                    {
                        "skill": skill,
                        "exists": exists,
                        "source": source,
                        "config_path": str(config_path),
                        "example_path": str(example_path),
                        "config": base_config,
                        "note": note,
                    }
                )
                return
            except Exception as e:
                self._send_json({"error": str(e)}, status=400)
                return

        self._send_text("未找到", status=404)

    def do_POST(self):
        if not self._host_ok() or not self._origin_ok():
            self._send_text("非法来源（仅允许本机访问）", status=403)
            return

        u = urlparse(self.path)
        if u.path != "/api/config":
            self._send_text("未找到", status=404)
            return

        qs = parse_qs(u.query or "")
        skill = (qs.get("skill") or [""])[0]
        try:
            assert_skill_name(skill)
            length = int(self.headers.get("Content-Length") or "0")
            raw = self.rfile.read(length).decode("utf-8")
            new_config = json.loads(raw) if raw else None

            if not isinstance(new_config, dict):
                raise ValueError("配置必须是 JSON 对象")

            d = SKILLS_DIR / skill
            config_path = d / "config.json"
            normalized = normalize_config_for_write(new_config)
            config_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            self._send_json({"success": True, "path": str(config_path)})
        except Exception as e:
            self._send_json({"error": str(e)}, status=400)


def main():
    print(f"配置面板已启动：http://localhost:{PORT}")
    print(f"技能目录：{SKILLS_DIR}")
    # 使用线程版 HTTPServer：避免“系统选择器阻塞”导致整个页面请求卡住
    httpd = ThreadingHTTPServer(("127.0.0.1", PORT), Handler)
    httpd.serve_forever()


if __name__ == "__main__":
    # 允许从任意工作目录启动
    os.chdir(str(PUBLIC_DIR.parent))
    main()
