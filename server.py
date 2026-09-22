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
PORT = int(os.environ.get("PORT", "0100"))
READ_ONLY_PORT = int(os.environ.get("READ_ONLY_PORT", "8424"))
HOST = os.environ.get("HOST", "0.0.0.0")
LOOPBACK = os.environ.get("LOOPBACK", "127.0.0.1")
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data.json")
QA_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "qa_data.json")
UI_CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ui_config.json")
QUICKREF_DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "quickref_data.json")
BACKUP_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backups")
MAX_BACKUPS = int(os.environ.get("MAX_BACKUPS", "30"))
WEB_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

EDIT_TOKEN_TTL = int(os.environ.get("EDIT_TOKEN_TTL", "600"))
READONLY_TOKEN_TTL = int(os.environ.get("READONLY_TOKEN_TTL", "3600"))

APP_VERSION = "v2.10"
SETTINGS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "settings.json")
QQ_BOT_DEFAULT_APPID = os.environ.get("QQ_BOT_APPID", "").strip()
QQ_BOT_DEFAULT_SECRET = os.environ.get("QQ_BOT_SECRET", "").strip()

SKIP_IPV6 = os.environ.get("SKIP_IPV6", "").strip()


def _read_body(handler):
    length = int(handler.headers.get("Content-Length", 0) or 0)
    if length <= 0:
        return b""
    return handler.rfile.read(length)


def load_data():
    empty = {"version": 2, "docs": []}
    if not os.path.exists(DATA_FILE):
        return empty
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)
        if isinstance(obj, dict) and isinstance(obj.get("docs"), list):
            return obj
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
    _backup_old(DATA_FILE, obj)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def load_qa_data():
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
    _backup_old(QA_DATA_FILE, obj, "qa")
    tmp = QA_DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QA_DATA_FILE)


def load_quickref_data():
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
    _backup_old(QUICKREF_DATA_FILE, obj, "quickref")
    tmp = QUICKREF_DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
    os.replace(tmp, QUICKREF_DATA_FILE)


def load_settings():
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
    except Exception:
        pass
    return empty


def _default_settings():
    theme = "parchment"
    try:
        with open(UI_CONFIG_FILE, "r", encoding="utf-8") as f:
            old = json.load(f)
        if isinstance(old, dict) and old.get("theme"):
            theme = old["theme"]
    except Exception:
        pass
    return {"version": 2, "appVersion": APP_VERSION, "theme": theme,
            "qqBot": {"appid": QQ_BOT_DEFAULT_APPID, "secret": QQ_BOT_DEFAULT_SECRET}}


def save_settings(obj):
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
    s = load_settings()
    qb = s.get("qqBot") or {}
    return qb.get("appid", ""), qb.get("secret", "")


def load_ui_config():
    return {"version": 1, "theme": load_settings().get("theme", "parchment")}


def save_ui_config(obj):
    theme = (obj or {}).get("theme", "parchment")
    s = load_settings()
    s["theme"] = theme
    save_settings(s)


def _backup_old(file_path, new_obj, prefix="data"):
    if not os.path.exists(file_path):
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            old = f.read()
    except Exception:
        return
    new = json.dumps(new_obj, ensure_ascii=False, indent=2)
    if old.strip() == new.strip() or not old.strip():
        return
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = os.path.join(BACKUP_DIR, "%s_%s.json" % (prefix, ts))
        if not os.path.exists(dst):
            with open(file_path, "r", encoding="utf-8") as src, open(dst, "w", encoding="utf-8") as out:
                out.write(src.read())
        files = sorted(glob.glob(os.path.join(BACKUP_DIR, "%s_*.json" % prefix)))
        while len(files) > MAX_BACKUPS:
            try:
                os.remove(files.pop(0))
            except OSError:
                break
    except Exception:
        pass


def ensure_data_file():
    if not os.path.exists(DATA_FILE):
        save_data(load_data())


def ensure_qa_data_file():
    if not os.path.exists(QA_DATA_FILE):
        save_qa_data(load_qa_data())


def ensure_ui_config_file():
    if not os.path.exists(UI_CONFIG_FILE):
        save_ui_config(load_ui_config())


def ensure_quickref_data_file():
    if not os.path.exists(QUICKREF_DATA_FILE):
        save_quickref_data(load_quickref_data())


def _is_pure_v6(ip):
    if not ip:
        return False
    low = (ip or "").lower()
    if low.startswith("::ffff:") or low == "::1":
        return False
    return ":" in low


def _parse_cookies(header_value):
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

    def translate_path(self, path):
        path = path.split("?", 1)[0].split("#", 1)[0]
        path = unquote(path)
        rel = path.lstrip("/")
        if rel == "" or rel.endswith("/"):
            rel = rel + "index.html"
        full = os.path.join(WEB_ROOT, rel)
        full = os.path.abspath(full)
        if not full.startswith(os.path.abspath(WEB_ROOT)):
            full = os.path.join(WEB_ROOT, "index.html")
        return full

    def _v6_access_allowed(self):
        remote = (self.client_address[0] or "")
        if not _is_pure_v6(remote):
            return True
        purpose = PURPOSE_READONLY if getattr(self.server, "readonly", False) else PURPOSE_EDIT
        mgr = get_token_manager()
        token = self._request_token()
        if not token or not mgr.verify(token, purpose):
            return False
        cookie_tok = _parse_cookies(self.headers.get("Cookie", "")).get(TOKEN_PARAM)
        if cookie_tok != token:
            exp = mgr.expiry(token)
            max_age = max(1, int(exp - time.time())) if exp else 1
            self._set_token_cookie(token, max_age)
        return True

    def _request_token(self):
        token = ""
        try:
            parsed = urlparse(self.path)
            token = (parse_qs(parsed.query).get(TOKEN_PARAM) or [""])[0]
        except Exception:
            token = ""
        if not token:
            token = _parse_cookies(self.headers.get("Cookie", "")).get(TOKEN_PARAM, "")
        return token

    def _set_token_cookie(self, token, max_age):
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
        try:
            super().do_GET()
        except (ConnectionError, OSError):
            pass

    def do_POST(self):
        if not self._v6_access_allowed():
            self._deny_v6_access()
            return
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
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/qa/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_qa_data(obj)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/ui/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_ui_config(obj)
                self._send_json({"ok": True})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/settings/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                s = load_settings()
                if isinstance(obj.get("theme"), str) and obj["theme"].strip():
                    s["theme"] = obj["theme"].strip()
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
                restarted = _restart_qq_bot()
                self._send_json({"ok": True, "botRestarted": restarted})
            except Exception as e:
                self._send_json({"ok": False, "error": str(e)}, status=400)
            return
        if parsed.path.rstrip("/") == "/api/quickref/save":
            try:
                body = _read_body(self)
                obj = json.loads(body)
                save_quickref_data(obj)
                self._send_json({"ok": True})
            except Exception as e:
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
        try:
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
        except Exception:
            pass
        pc = getattr(self, "_pending_cookie", None)
        if pc:
            try:
                name, tok, ma = pc
                self.send_header(
                    "Set-Cookie",
                    "%s=%s; Path=/; HttpOnly; SameSite=Strict; Max-Age=%d"
                    % (name, tok, ma),
                )
            except Exception:
                pass
        super().end_headers()

    def log_message(self, fmt, *args):
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
        remote = remote.replace("::ffff:", "")
        local = local.replace("::ffff:", "")
        print("[timeline] %-24s -> %-28s %s" % (remote, local, fmt % args), flush=True)


class V6HTTPServer(ThreadingHTTPServer):
    address_family = socket.AF_INET6

    def server_bind(self):
        try:
            self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_V6ONLY, 0)
        except (AttributeError, OSError):
            pass
        super().server_bind()


def _build_address_reply():
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
    _appid, _secret = get_qq_credentials()
    if not _appid or not _secret:
        qq_restart_bot("", "", _build_address_reply)
        return False
    return qq_restart_bot(_appid, _secret, _build_address_reply)


def main():
    ensure_data_file()
    ensure_qa_data_file()
    ensure_ui_config_file()
    ensure_quickref_data_file()

    rw = V6HTTPServer(("::", PORT), TimelineHandler)
    rw.readonly = False
    ro = V6HTTPServer(("::", READ_ONLY_PORT), TimelineHandler)
    ro.readonly = True

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

    _appid, _secret = get_qq_credentials()
    if _appid and _secret:
        qq_start_bot(_appid, _secret, _build_address_reply)
    else:
        print("[qq_bot] 未配置 QQ_BOT_APPID / QQ_BOT_SECRET，机器人未启动；IPv6 访问默认一律拦截。")

    print("  按 Ctrl+C 停止服务")
    print("=" * 62)

    threads = [threading.Thread(target=srv.serve_forever, daemon=True) for srv in (rw, ro)]
    for t in threads:
        t.start()

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
    if not SKIP_IPV6 or not ip:
        return False
    low = ip.lower()
    for tok in SKIP_IPV6.split(","):
        tok = tok.strip().lower()
        if tok and tok in low:
            return True
    return False


def _ipv6_addrs():
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
    main()aemon=True) for srv in (rw, ro)]\n    for t in threads:\n        t.start()\n\n    if os.environ.get(\"NO_BROWSER\"):\n        print(\"  [NO_BROWSER=1] 已跳过自动打开浏览器\")\n    else:\n        threading.Timer(0.6, lambda: _open(local_url)).start()\n\n    try:\n        while True:\n            import time\n            time.sleep(1)\n    except KeyboardInterrupt:\n        print(\"\\n[timeline] 已停止服务。\")\n        rw.server_close()\n        ro.server_close()\n\n\ndef _lan_ips():\n    ips = []\n    try:\n        name = socket.gethostname()\n        for ip in socket.gethostbyname_ex(name)[2]:\n            if not ip.startswith(\"127.\"):\n                ips.append(ip)\n    except Exception:\n        pass\n    try:\n        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)\n        s.connect((\"8.8.8.8\", 80))\n        ip = s.getsockname()[0]\n        if ip not in ips:\n            ips.append(ip)\n        s.close()\n    except Exception:\n        pass\n    return ips\n\n\ndef _should_skip_ip_v6(ip):\n    if not SKIP_IPV6 or not ip:\n        return False\n    low = ip.lower()\n    for tok in SKIP_IPV6.split(\",\"):\n        tok = tok.strip().lower()\n        if tok and tok in low:\n            return True\n    return False\n\n\ndef _ipv6_addrs():\n    out = []\n    try:\n        name = socket.gethostname()\n        for res in socket.getaddrinfo(name, None, socket.AF_INET6):\n            ip = res[4][0].split(\"%\")[0]\n            low = ip.lower()\n            if low == \"::1\" or low.startswith(\"fe80\"):\n                continue\n            if _should_skip_ip_v6(ip):\n                continue\n            if ip not in out:\n                out.append(ip)\n    except Exception:\n        pass\n    return out\n\n\ndef _open(url):\n    try:\n        webbrowser.open(url)\n    except Exception:\n        pass\n\n\nif __name__ == \"__main__\":\n    main()\n"}]