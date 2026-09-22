# -*- coding: utf-8 -*-
"""
世界历史学习 · 时间轴 Web 应用 —— 后端服务
=========================================
纯 Python 标准库实现，无需安装任何第三方依赖。
只负责托管前端静态页面，并提供简单的数据文件读写接口（本地 JSON 持久化）。

用法：
    python server.py
然后浏览器打开  http://127.0.0.1:0100  （即 http://127.0.0.1:100 ）
按 Ctrl+C 停止服务。

可通过环境变量覆盖端口，例如：
    set PORT=8000
    python server.py
"""

import os
import glob
import json
import socket
import time
import threading
import webbrowser
from datetime import datetime
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, unquote, parse_qs

# QQ 机器人安全通道：Token 签发 / 校验 + 机器人私聊分发（独立文件）
from qq_bot import get_token_manager, start_bot as qq_start_bot, restart_bot as qq_restart_bot
from qq_bot import TOKEN_PARAM, PURPOSE_EDIT, PURPOSE_READONLY

# ---------------------------------------------------------------------------
# 配置
# ---------------------------------------------------------------------------
# 默认端口：需求指定"0100"，这里作为十进制整数 100 使用（可读写的编辑端口）
PORT = int(os.environ.get("PORT", "0100"))
# 只读端口：只允许查看 / 导出 / 保存离线网页，禁止任何写入（内容不可更改）
READ_ONLY_PORT = int(os.environ.get("READ_ONLY_PORT", "8424"))
# 默认监听所有网卡（0.0.0.0），以便局域网内其他设备用 “服务器IP:端口” 访问。
# 需要仅本机访问时，可设 HOST=127.0.0.1。
HOST = os.environ.get("HOST", "0.0.0.0")
LOOPBACK = os.environ.get("LOOPBACK", "127.0.0.1")
# 数据文件：后端把数据持久化到这里（项目根目录下 data.json）
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
# 问答页数据文件（文档 + 薄弱点列表），与时间轴数据相互独立，互不覆盖
QA_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_data.json")
# 全局界面配置（配色主题等），所有页面共享同一份，任一页面切换后其余页面保持一致
UI_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_config.json")
# 速查页数据文件（人物/地点薄弱点列表），与时间轴/问答数据相互独立
QUICKREF_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quickref_data.json")
# 备份目录：每次把新数据写入 data.json 前，自动备份旧版到这里（便于手动导入/误改后恢复）
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
# 最多保留的备份份数（超出自动删除最老的）
MAX_BACKUPS = int(os.environ.get("MAX_BACKUPS", "30"))
# 静态资源根目录（前端 html 放在 static/ 下）
WEB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

# 访问凭证有效期（秒）
#  - 编辑端口(100)的 Token 有效期 10 分钟
#  - 只读端口(8424)的 Token 有效期 1 小时
EDIT_TOKEN_TTL = int(os.environ.get("EDIT_TOKEN_TTL", "600"))       # 10 分钟
READONLY_TOKEN_TTL = int(os.environ.get("READONLY_TOKEN_TTL", "3600"))  # 1 小时

# ──────────────────────────────────────────────────────────────────────────────
# 应用版本号 + 全局设置文件（级别: 配色 theme + QQ 机器人凭证 + 版本号，配置外置）
# 机器人凭证现在存于 settings.json（由设置页 settings.html 管理），不再散落在代码里。
# 下面两个只作为「首次生成 settings.json」或环境变量兼容时的默认值；
# settings.json 一旦生成，即为唯一权威来源。
# ──────────────────────────────────────────────────────────────────────────────
APP_VERSION = "v2.10"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
QQ_BOT_DEFAULT_APPID = os.environ.get("QQ_BOT_APPID", "").strip()
QQ_BOT_DEFAULT_SECRET = os.environ.get("QQ_BOT_SECRET", "").strip()

# 可选：手动忽略个别不想列出的 IPv6 地址/子串（逗号分隔）。
# 若某个地址你确认不可用（例如虚拟网卡、非公网可达地址），可用它剔除。
# 例：$env:SKIP_IPV6="2409:8a28:4740:6a24::433"
SKIP_IPV6 = os.environ.get("SKIP_IPV6", "").strip()


def _read_body(handler):
    """读取请求体（字节串）。"""
    length = int(handler.headers.get("Content-Length", 0) or 0)
    if length <= 0:
        return b""
    return handler.rfile.read(length)


def load_data():
    """从 data.json 读取数据；文件不存在或损坏时返回空骨架（多文档格式）。

    数据结构为多文档格式：
        {"version": 2, "docs": [{"id","name","created","title","globalOptions","lanes"}, ...]}
    若读到旧版单文档格式（有 lanes 无 docs），会自动迁移为多文档格式并写回文件。
    """
    empty = {"version": 2, "docs": []}
    if not os.path.exists(DATA_FILE):
        return empty
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and isinstance(obj.get("docs"), list):
            return obj
        # 旧版单文档格式（version 1：直接含 lanes）→ 迁移为多文档格式
        if isinstance(obj, dict) and isinstance(obj.get("lanes"), list):
            from time import time as _now
            import random as _rnd
            doc = {
                "id": "doc" + ("%x" % int(_now() * 1000)) + ("%x" % _rnd.randint(0, 0xFFFFF)),
                "name": obj.get("title") or "时间轴",
                "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "title": obj.get("title") or "世界历史 九年级上册 时间线",
                "globalOptions": obj.get("globalOptions") or {},
                "lanes": obj.get("lanes") or [],
            }
            new = {"version": 2, "docs": [doc]}
            _backup_old(DATA_FILE, new)
            tmp = DATA_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(new, f, ensure_ascii=False, indent=2)
            os.replace(tmp, DATA_FILE)
            return new
    except Exception:
        pass
    return empty


def save_data(obj):
    """把数据写入 data.json（原子写：先写临时文件再替换）。

    写入前会自动把当前 data.json 备份到 backups/ 目录（内容无变化则不重复备份），
    这样无论是手动导入 JSON 覆盖，还是普通编辑，旧数据都可回溯。
    """
    _backup_old(DATA_FILE, obj)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def load_qa_data():
    """从 qa_data.json 读取问答数据（文档 + 薄弱点）；文件不存在或损坏时返回空骨架。"""
    if not os.path.exists(QA_DATA_FILE):
        return {"version": 1, "docs": [], "weakLists": []}
    try:
        with open(QA_DATA_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and "docs" in obj:
            return obj
    except Exception:
        pass
    return {"version": 1, "docs": [], "weakLists": []}


def save_qa_data(obj):
    """把问答数据写入 qa_data.json（原子写），写入前同样自动备份旧版（前缀 qa_）。"""
    _backup_old(QA_DATA_FILE, obj, "qa")
    tmp = QA_DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QA_DATA_FILE)


def load_quickref_data():
    """从 quickref_data.json 读取速查页数据（薄弱点列表）；文件不存在或损坏时返回空骨架。"""
    if not os.path.exists(QUICKREF_DATA_FILE):
        return {"version": 1, "weakLists": []}
    try:
        with open(QUICKREF_DATA_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and "weakLists" in obj:
            return obj
    except Exception:
        pass
    return {"version": 1, "weakLists": []}


def save_quickref_data(obj):
    """把速查页数据写入 quickref_data.json（原子写），写入前自动备份旧版（前缀 quickref_）。"""
    _backup_old(QUICKREF_DATA_FILE, obj, "quickref")
    tmp = QUICKREF_DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QUICKREF_DATA_FILE)


def load_settings():
    """读取全局设置 settings.json（配色 + QQ 机器人凭证 + 版本号）。

    文件不存在或损坏时，按旧 ui_config.json 配色 + 默认凭证生成一份并写回。
    settings.json 生成后即为唯一权威来源。
    """
    empty = _default_settings()
    if not os.path.exists(SETTINGS_FILE):
        save_settings(empty)
        return empty
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict):
            obj.setdefault("version", 2)
            obj.setdefault("appVersion", APP_VERSION)
            qb = obj.get("qqBot")
            if not isinstance(qb, dict):
                qb = {}
                obj["qqBot"] = qb
            qb.setdefault("appid", "")
            qb.setdefault("secret", "")
            obj.setdefault("theme", "parchment")
            return obj
    except Exception:  # noqa: BLE001
        pass
    return empty


def _default_settings():
    """构造默认设置：theme 兼容旧 ui_config.json，bot 凭证兼容旧代码/环境变量。"""
    theme = "parchment"
    try:
        with open(UI_CONFIG_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict) and old.get("theme"):
            theme = old["theme"]
    except Exception:  # noqa: BLE001
        pass
    return {"version": 2, "appVersion": APP_VERSION, "theme": theme,
            "qqBot": {"appid": QQ_BOT_DEFAULT_APPID, "secret": QQ_BOT_DEFAULT_SECRET}}


def save_settings(obj):
    """把全局设置写入 settings.json（原子写），写入前自动备份旧版（前缀 settings_）。"""
    if not isinstance(obj, dict):
        obj = {}
    obj.setdefault("version", 2)
    obj.setdefault("appVersion", APP_VERSION)
    qb = obj.get("qqBot")
    if not isinstance(qb, dict):
        qb = {}
        obj["qqBot"] = qb
    qb.setdefault("appid", "")
    qb.setdefault("secret", "")
    obj.setdefault("theme", "parchment")
    _backup_old(SETTINGS_FILE, obj, "settings")
    tmp = SETTINGS_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, SETTINGS_FILE)


def get_qq_credentials():
    """返回当前生效的 QQ 机器人凭证 (appid, secret)，来自 settings.json。"""
    s = load_settings()
    qb = s.get("qqBot") or {}
    return qb.get("appid", ""), qb.get("secret", "")


def load_ui_config():
    """返回当前配色主题（读取 settings.json 的 theme 字段，兼容旧 /api/ui/load 接口）。"""
    return {"version": 1, "theme": load_settings().get("theme", "parchment")}


def save_ui_config(obj):
    """把配色 theme 写进 settings.json（兼容旧 /api/ui/save 接口）。"""
    theme = (obj or {}).get("theme", "parchment")
    s = load_settings()
    s["theme"] = theme
    save_settings(s)


def _backup_old(file_path, new_obj, prefix="data"):
    """写入前把旧的 json 文件备份一份（仅当旧内容确实存在且与新版不同）。"""
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            old = f.read()
    except Exception:
        return
    new = json.dumps(new_obj, ensure_ascii=False, indent=2)
    if old.strip() == new.strip() or not old.strip():
        return  # 内容没变或原本为空，不产生冗余备份
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(BACKUP_DIR, "%s_%s.json" % (prefix, ts))
        if not os.path.exists(dst):
            with open(file_path, "r", encoding="utf-8") as src, open(dst, "w", encoding="utf-8") as out:
                out.write(src.read())
        # 只保留最近 MAX_BACKUPS 份，超出删除最老的
        files = sorted(glob.glob(os.path.join(BACKUP_DIR, "%s_*.json" % prefix)))
        while len(files) > MAX_BACKUPS:
            try:
                os.remove(files.pop(0))
            except OSError:
                break
    except Exception:
        pass


def ensure_data_file():
    """启动时自动创建空的 data.json 骨架（若不存在）。"""
    if not os.path.exists(DATA_FILE):
        save_data(load_data())


def ensure_qa_data_file():
    """启动时自动创建空的 qa_data.json 骨架（若不存在）。"""
    if not os.path.exists(QA_DATA_FILE):
        save_qa_data(load_qa_data())


def ensure_ui_config_file():
    """启动时自动创建 ui_config.json 骨架（若不存在）。"""
    if not os.path.exists(UI_CONFIG_FILE):
        save_ui_config(load_ui_config())


def ensure_quickref_data_file():
    """启动时自动创建 quickref_data.json 骨架（若不存在）。"""
    if not os.path.exists(QUICKREF_DATA_FILE):
        save_quickref_data(load_quickref_data())


# ---------------------------------------------------------------------------
# 访问凭证门禁（仅针对公网 IPv6）
# ---------------------------------------------------------------------------
def _is_pure_v6(ip):
    """判断某来源 IP 是否为「纯 IPv6」（排除了 IPv4 mapped 与回环 ::1）。

    双栈监听时，IPv4 客户端接入会显示为 ::ffff:1.2.3.4（非纯 IPv6），
    这类（即 127.0.0.1 / 局域网 IPv4）保持原有免凭证访问；只有纯公网 IPv6
    访问需要有效 Token。
    """
    if not ip:
        return False
    low = (ip or "").lower()
    if low.startswith("::ffff:") or low == "::1":
        return False
    return ":" in low


def _parse_cookies(header_value):
    """把 Cookie 头解析为 dict（简单实现，够用）。"""
    out = {}
    if not header_value:
        return out
    for part in header_value.split(";"):
        part = part.strip()
        if "=" in part:
            k, _, v = part.partition("=")
            out[k.strip()] = v.strip()
    return out


class TimelineHandler(SimpleHTTPRequestHandler):
    """静态文件服务 + 两条数据接口。"""

    def translate_path(self, path):
        """让静态文件从 static/ 目录提供。"""
        # 基础解算
        path = path.split("?", 1)[0].split("#", 1)[0]
        path = unquote(path)
        rel = path.lstrip("/")
        # 根路径映射到 index.html
        if rel == "" or rel.endswith("/"):
            rel = rel + "index.html"
        full = os.path.join(WEB_ROOT, rel)
        # 防止目录穿越
        full = os.path.abspath(full)
        if not full.startswith(os.path.abspath(WEB_ROOT)):
            full = os.path.join(WEB_ROOT, "index.html")
        return full

    def _v6_access_allowed(self):
        """公网 IPv6 访问门禁。

        规则：纯 IPv6 来源必须有本端口的有效 AccessToken（URL 参数或 Cookie）；
        通过后把 Token 写入 HttpOnly Cookie，后续页面/API 请求免带参数即可通过。
        非 IPv6（127.0.0.1 / 局域网 IPv4 / ::1）维持原样，无需凭证。
        """
        remote = (self.client_address[0] or "")
        if not _is_pure_v6(remote):
            return True

        purpose = PURPOSE_READONLY if getattr(self.server, "readonly", False) else PURPOSE_EDIT
        mgr = get_token_manager()

        # 1) 取出 Token：优先 URL 参数，其次 Cookie
        token = self._request_token()
        if not token or not mgr.verify(token, purpose):
            return False

        # 2) 已通过：若浏览器还没存 Cookie，则补发 HttpOnly Cookie（有效期=Token剩余时长）
        cookie_tok = _parse_cookies(self.headers.get("Cookie", "")).get(TOKEN_PARAM)
        if cookie_tok != token:
            exp = mgr.expiry(token)
            max_age = max(1, int(exp - time.time())) if exp else 1
            self._set_token_cookie(token, max_age)
        return True

    def _request_token(self):
        """从 URL 查询参数或 Cookie 中取出 AccessToken。"""
        token = ""
        try:
            parsed = urlparse(self.path)
            token = (parse_qs(parsed.query).get(TOKEN_PARAM) or [""])[0]
        except Exception:  # noqa: BLE001
            token = ""
        if not token:
            token = _parse_cookies(self.headers.get("Cookie", "")).get(TOKEN_PARAM, "")
        return token

    def _set_token_cookie(self, token, max_age):
        # 仅记录待种 Cookie；真正的 Set-Cookie 头在 end_headers() 里写入。
        # 注意：send_header() 必须在 send_response() 填好响应缓冲之后调用，
        # 否则会抛 HeadersNotSent；此前在 do_GET 一开始调用导致 Cookie 从未真正发出。
        self._pending_cookie = (TOKEN_PARAM, token, max_age)

    def _deny_v6_access(self):
        mode = "只读(8424)" if getattr(self.server, "readonly", False) else "编辑(100)"
        self._send_json(
            {"ok": False,
             "error": "IPv6 访问需要有效的 AccessToken（端口用途：%s）。"
                      "凭证无效/已过期/用途不符，请通过 QQ 机器人私聊『地址』重新获取后访问。" % mode},
            status=403)

    def do_GET(self):
        if not self._v6_access_allowed():
            self._deny_v6_access()
            return
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/api/load":
            self._send_json({"ok": True, "data": load_data()})
            return
        if parsed.path.rstrip("/") == "/api/qa/load":
            self._send_json({"ok": True, "data": load_qa_data()})
            return
        if parsed.path.rstrip("/") == "/api/ui/load":
            self._send_json({"ok": True, "data": load_ui_config()})
            return
        if parsed.path.rstrip("/") == "/api/settings/load":
            s = load_settings()
            qb = s.get("qqBot") or {}
            self._send_json({"ok": True, "data": {
                "appVersion": s.get("appVersion", APP_VERSION),
                "theme": s.get("theme", "parchment"),
                "qqBot": {"appid": qb.get("appid", ""), "hasSecret": bool(qb.get("secret"))},
            }})
            return
        if parsed.path.rstrip("/") == "/api/quickref/load":
            self._send_json({"ok": True, "data": load_quickref_data()})
            return
        if parsed.path.rstrip("/") == "/api/health":
            self._send_json({"ok": True})
            return
        # 其余按静态文件处理
        try:
            super().do_GET()
        except (ConnectionError, OSError):
            # 客户端中途断开连接（如刷新/取消）时写响应失败，忽略即可，不影响其它请求
            pass

    def do_POST(self):
        if not self._v6_access_allowed():
            self._deny_v6_access()
            return
        # 只读端口：任何写入（保存数据）一律拒绝，保证“不能更改内容”
        if getattr(self.server, "readonly", False):
            self._send_json({"ok": False, "error": "read-only port: 该端口为只读，禁止写入。"}, status=403)
            return
        parsed = urlparse(self.path)
        if parsed.path.rstrip("/") == "/api/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_data(obj)
                self._send_json({"ok": True})
            except Exception as e:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/qa/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_qa_data(obj)
                self._send_json({"ok": True})
            except Exception as e:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/ui/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_ui_config(obj)
                self._send_json({"ok": True})
            except Exception as e:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/settings/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                s = load_settings()
                # 主题（可选）
                if isinstance(obj.get("theme"), str) and obj["theme"].strip():
                    s["theme"] = obj["theme"].strip()
                # 机器人凭证：appid 填了才更新；secret 留空则不修改（避免显示为空就被清掉）
                qb = s.setdefault("qqBot", {})
                qb.setdefault("appid", "")
                qb.setdefault("secret", "")
                appid = (obj.get("qqBot") or {}).get("appid")
                if isinstance(appid, str):
                    qb["appid"] = appid.strip()
                secret = (obj.get("qqBot") or {}).get("secret")
                if isinstance(secret, str) and secret.strip():
                    qb["secret"] = secret.strip()
                save_settings(s)
                # 保存后自动重启机器人（用新凭证，免手动重启服务）
                restarted = _restart_qq_bot()
                self._send_json({"ok": True, "botRestarted": restarted})
            except Exception as e:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/quickref/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_quickref_data(obj)
                self._send_json({"ok": True})
            except Exception as e:  # noqa: BLE001
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        self._send_json({"ok": False, "error": "not found"}, status=404)

    def _send_json(self, payload, status=200):
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def end_headers(self):
        # 禁用缓存，保证浏览器每次刷新都拿到最新的 index.html，避免“改了却看不到”。
        try:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        except Exception:
            pass
        # 若有待种 Cookie（IPv6 Token 首次校验通过），在此追加 Set-Cookie 头。
        # 这里 end_headers 一定在 send_response 之后调用，send_header 可安全使用。
        pc = getattr(self, "_pending_cookie", None)
        if pc:
            try:
                name, tok, ma = pc
                self.send_header(
                    "Set-Cookie",
                    "%s=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d"
                    % (name, tok, ma),
                )
            except Exception:  # noqa: BLE001
                pass
        super().end_headers()

    def log_message(self, fmt, *args):
        # 显示每次访问：来源(客户端)IP -> 本机被访问的网卡IP:端口，便于看清是谁/从哪里访问的
        remote = "?"
        local = "?"
        try:
            remote = "%s:%s" % (self.client_address[0], self.client_address[1])
        except Exception:
            pass
        try:
            sock = self.request.getsockname()
            local = "%s:%s" % (sock[0], sock[1])
        except Exception:
            pass
        # 还原 IPv4 经双栈端口的 ::ffff: 前缀，便于阅读
        remote = remote.replace("::ffff:", "")
        local = local.replace("::ffff:", "")
        print("[timeline] %-24s -> %-28s %s" % (remote, local, fmt % args), flush=True)


class V6HTTPServer(ThreadingHTTPServer):
    """IPv6（双栈）HTTP 服务器：同一端口同时监听 IPv4 与 IPv6，可供公网 IPv6 访问。"""

    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            # IPv6 双栈：同时接受 IPv4 与 IPv6 连接
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def _build_address_reply():
    """构造报发给 QQ 私聊的「访问地址 + Token」文本。

    每次收到『地址』指令都会签发新的 Token：
      - 编辑端口(100)凭证：EDIT_TOKEN_TTL（10 分钟）
      - 只读端口(8424)凭证：READONLY_TOKEN_TTL（1 小时）
      - 列出**所有**公网 IPv6 地址及其编辑/只读链接（避免只返回第一个、误中虚拟网卡）
    """
    mgr = get_token_manager()
    ipv6s = _ipv6_addrs()
    lines = ["【服务端访问凭证】生成于 %s"
             % datetime.now().strftime("%Y-%m-%d %H:%M:%S")]
    if not ipv6s:
        lines.append("未检测到公网 IPv6 地址，当前无法通过公网 IPv6 访问。")
        return "\n".join(lines)

    edit_tok = mgr.issue(PURPOSE_EDIT, EDIT_TOKEN_TTL)
    ro_tok = mgr.issue(PURPOSE_READONLY, READONLY_TOKEN_TTL)
    lines.append("共 %d 个公网 IPv6 地址，请用你的真实网卡地址：" % len(ipv6s))
    for ip in ipv6s:
        lines.append("IPv6 地址：%s" % ip)
        lines.append("  编辑：http://[%s]:%d/?%s=%s（%d 分钟内有效）"
                     % (ip, PORT, TOKEN_PARAM, edit_tok, EDIT_TOKEN_TTL // 60))
        lines.append("  只读：http://[%s]:%d/?%s=%s（%d 分钟内有效）"
                     % (ip, READ_ONLY_PORT, TOKEN_PARAM, ro_tok, READONLY_TOKEN_TTL // 60))
    lines.append("提示：Token 一次性、到期自动失效；两端口通用，勿转发。")
    return "\n".join(lines)


def _restart_qq_bot():
    """保存设置后调用：用 settings.json 里的新凭证重启 QQ 机器人线程（免手动重启服务）。"""
    _appid, _secret = get_qq_credentials()
    if not _appid or not _secret:
        qq_restart_bot("", "", _build_address_reply)  # 无凭证则仅停止，不再启动
        return False
    return qq_restart_bot(_appid, _secret, _build_address_reply)


def main():
    # 启动时若还没有 data.json / qa_data.json / settings.json(含配色) / quickref_data.json，则自动创建空骨架（便于用户直接看到该文件）
    ensure_data_file()
    ensure_qa_data_file()
    ensure_ui_config_file()
    ensure_quickref_data_file()

    # 可读写：0100（即 100），多线程（避免单个慢连接阻塞其它访问）。
    # 改为 IPv6 双栈监听：局域网 IPv4 仍可访问（免凭证）；公网 IPv6 访问需有效 Token。
    rw = V6HTTPServer(("::", PORT), TimelineHandler)
    rw.readonly = False
    # 只读：8424（只能查看 / 导出 / 保存离线网页，禁止写入）。
    # IPv6 双栈监听，局域网 IPv4 仍可访问（免凭证）；公网 IPv6 需有效 Token。
    ro = V6HTTPServer(("::", READ_ONLY_PORT), TimelineHandler)
    ro.readonly = True

    # 本机/局域网访问地址（监听双栈，因此提供不同地址给用户）
    lan_ips = _lan_ips()
    local_url = "http://%s:%d/" % (LOOPBACK, PORT)
    local_ro = "http://%s:%d/" % (LOOPBACK, READ_ONLY_PORT)

    print("=" * 62)
    print("  世界历史学习 · 时间轴应用已启动")
    print("  本机 编辑端口(读写)：%s   —— 可查看/添加/修改/导入导出" % local_url)
    print("  本机 只读端口(查看)：%s —— 只能查看/导出/保存离线网页" % local_ro)
    if lan_ips:
        print("  局域网访问（其他设备用以下地址，须为本机 IPv4，免凭证）：")
        for ip in lan_ips:
            print("     编辑：http://%s:%d/      只读：http://%s:%d/" % (ip, PORT, ip, READ_ONLY_PORT))
    ipv6s = _ipv6_addrs()
    if ipv6s:
        print("  公网 IPv6（需通过 QQ 机器人私聊『地址』获取 Token，无 Token 一律拦截）：")
        for ip in ipv6s:
            print("     编辑：http://[%s]:%d/?%s=<Token>     只读：http://[%s]:%d/?%s=<Token>"
                  % (ip, PORT, TOKEN_PARAM, ip, READ_ONLY_PORT, TOKEN_PARAM))
    else:
        print("  未检测到全局(公网) IPv6 地址（仅缩略了本机检查）。若你有公网 IPv6 请自行配置。")
    print("  数据文件：%s" % DATA_FILE)
    print("  问答数据：%s" % QA_DATA_FILE)
    print("  全局配色/设置：%s（版本 %s）" % (SETTINGS_FILE, APP_VERSION))
    print("  速查数据：%s" % QUICKREF_DATA_FILE)

    # QQ 机器人：settings.json 配置了 AppID / AppSecret 则后台启动，私聊『地址』分发访问 Token
    _appid, _secret = get_qq_credentials()
    if _appid and _secret:
        qq_start_bot(_appid, _secret, _build_address_reply)
    else:
        print("[qq_bot] 未配置 QQ_BOT_APPID / QQ_BOT_SECRET，机器人未启动；IPv6 访问默认一律拦截。")

    print("  按 Ctrl+C 停止服务")
    print("=" * 62)

    # 两个端口各自独立线程运行
    threads = [threading.Thread(target=srv.serve_forever, daemon=True) for srv in (rw, ro)]
    for t in threads:
        t.start()

    # 尝试自动打开本机编辑端口（失败也不影响服务）
    # 设置环境变量 NO_BROWSER=1 可跳过自动打开浏览器（调试用）
    if os.environ.get("NO_BROWSER"):
        print("  [NO_BROWSER=1] 已跳过自动打开浏览器")
    else:
        threading.Timer(0.6, lambda: _open(local_url)).start()

    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[timeline] 已停止服务。")
        rw.server_close()
        ro.server_close()


def _lan_ips():
    """尽力获取本机局域网 IP 列表（用于打印访问地址）。"""
    ips = []
    try:
        name = socket.gethostname()
        for ip in socket.gethostbyname_ex(name)[2]:
            if not ip.startswith("127."):
                ips.append(ip)
    except Exception:
        pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        if ip not in ips:
            ips.append(ip)
        s.close()
    except Exception:
        pass
    return ips


def _should_skip_ip_v6(ip):
    """判断某个全局 IPv6 是否应被忽略（命中 SKIP_IPV6 中任一子串即忽略）。"""
    if not SKIP_IPV6 or not ip:
        return False
    low = ip.lower()
    for tok in SKIP_IPV6.split(","):
        tok = tok.strip().lower()
        if tok and tok in low:
            return True
    return False


def _ipv6_addrs():
    """尽力获取本机可路由(非 link-local)的全局 IPv6 地址，用于打印/回报公网访问地址。

    会剔除回环、link-local 以及命中 SKIP_IPV6 的地址（如虚拟网卡的错误全局地址）。
    """
    out = []
    try:
        name = socket.gethostname()
        for res in socket.getaddrinfo(name, None, socket.AF_INET6):
            ip = res[4][0].split("%")[0]
            low = ip.lower()
            if low == "::1" or low.startswith("fe80"):
                continue
            if _should_skip_ip_v6(ip):
                continue
            if ip not in out:
                out.append(ip)
    except Exception:
        pass
    return out


def _open(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


if __name__ == "__main__":
    main()