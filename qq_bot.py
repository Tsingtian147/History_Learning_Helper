# -*- coding: utf-8 -*-
"""
QQ 机器人 · 安全访问凭证分发服务（独立文件）
================================================
作用：
    通过 QQ 官方机器人（qq-botpy SDK）的**私聊(C2C)**渠道，向服务器管理员安全地
    分发用于公网 IPv6 访问的 AccessToken（一次性、到期自动失效）。避免把可写端口
    的凭证直接硬编码或公开，走私聊渠道仅供本人获取。

核心能力：
    1. TokenManager：
       - issue(token purpose, ttl)  签发一个「尽可能长」的随机 Token（96 位十六进制），
         到期自动失效（懒清理 + 线程安全）。
       - verify(token, purpose)      校验 Token 是否有效且属于指定用途。
       - expiry(token)               返回 Token 过期时间戳（用于下发 Cookie 的 Max-Age）。
    2. 机器人客户端：
       - 使用官方鉴权方式 AppID + AppSecret（内部先换 Access Token 再连 WebSocket）。
       - 仅订阅 C2C（QQ 用户与机器人单聊）消息事件：intents.public_messages = True。
       - 收到「地址」指令时，回调 server 提供的 address_builder()，把返回文本私聊回复。

外部依赖：
    pip install qq-botpy        # QQ 官方 Python SDK（本文件使用官方通道接入）
    其余全部使用 Python 标准库。

机器人凭证通过环境变量注入（不在代码 / 仓库里存密钥）：
    QQ_BOT_APPID        机器人 AppID
    QQ_BOT_SECRET       机器人 AppSecret

安全约定：
    - Token 仅通过私聊渠道返回，初始访问时附在 URL 请求参数 AccessToken=... 上，
      服务器校验通过后写入 HttpOnly Cookie，后续页面请求免刷新携带。
    - 没有有效 Token 的 IPv6 访问一律被 server.py 拦截（返回 403）。
"""

import os
import sys
import json
import time
import threading
import secrets as _secrets

# 私有/默认用途定义（与 server.py 一致）
PURPOSE_EDIT = "edit"          # 编辑端口（100）访问凭证
PURPOSE_READONLY = "readonly"  # 只读端口（8424）访问凭证

# 凭证在 URL / Cookie 中的参数名（与官方文档示例一致，尽量不改）
TOKEN_PARAM = "AccessToken"

# Token 持久化文件：让已签发的 Token 在服务重启后仍有效（在各自有效期内），
# 避免「重启后此前分配的 Token 全部失效」导致 403。到期即自动被清理并移除。
TOKEN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tokens.json")


# ---------------------------------------------------------------------------
# Token 管理器（线程安全，懒清理过期项，支持跨重启持久化）
# ---------------------------------------------------------------------------
class TokenManager:
    """签发 / 校验用于访问服务端的随机 AccessToken。

    内部维护 token -> (expire_timestamp, purpose)。签发时生成的 Token 尽可能长
    （96 位十六进制），并满足「随机生成、自动过期」，不同用途对应不同有效期。

    每次签发/清理都会把仍有效的 Token 持久化到 TOKEN_FILE，这样服务重启后，
    尚未过期的 Token 依旧可用（不会再因重启而集体失效）。
    """

    def __init__(self):
        self._tokens = {}
        self._lock = threading.Lock()
        self._load()

    # ---- 持久化 ----
    def _load(self):
        try:
            with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            now = time.time()
            for tok, rec in data.items():
                exp, p = rec.get("exp"), rec.get("purpose")
                if isinstance(exp, (int, float)) and isinstance(p, str) and exp > now:
                    self._tokens[tok] = (float(exp), p)
        except Exception:  # noqa: BLE001
            pass

    def _persist(self):
        try:
            obj = {t: {"exp": e, "purpose": p} for t, (e, p) in self._tokens.items()}
            tmp = TOKEN_FILE + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(obj, f, ensure_ascii=False)
            os.replace(tmp, TOKEN_FILE)
        except Exception:  # noqa: BLE001
            pass

    # ---- 签发 / 校验 ----
    def issue(self, purpose, ttl):
        """签发一个新的 Token。

        Args:
            purpose (str): 用途（PURPOSE_EDIT / PURPOSE_READONLY）。
            ttl (int): 有效期，单位秒。
        Returns:
            str: 随机生成的 Token。
        """
        token = _secrets.token_hex(48)  # 96 位十六进制，够长且熵高
        expire = time.time() + max(1, int(ttl))
        with self._lock:
            self._prune_locked()
            self._tokens[token] = (expire, purpose)
            self._persist()
        return token

    def verify(self, token, purpose, now=None):
        """校验 Token 是否有效且属于指定用途。

        Returns:
            bool: True 表示有效，False 表示缺失 / 过期 / 用途不符。
        """
        if not token:
            return False
        now = time.time() if now is None else now
        with self._lock:
            removed = self._prune_locked(now)
            rec = self._tokens.get(token)
            ok = bool(rec) and rec[1] == purpose and rec[0] > now
            if removed:
                self._persist()
            return ok

    def expiry(self, token, now=None):
        """返回某 Token 的过期时间戳；无效 / 不存在返回 None。

        用于下发 HttpOnly Cookie 时计算剩余有效时长（Max-Age）。
        """
        if not token:
            return None
        now = time.time() if now is None else now
        with self._lock:
            removed = self._prune_locked(now)
            rec = self._tokens.get(token)
            exp = rec[0] if rec else None
            if removed:
                self._persist()
            return exp

    def _prune_locked(self, now=None):
        now = time.time() if now is None else now
        expired = [k for k, (e, _p) in self._tokens.items() if e <= now]
        for k in expired:
            self._tokens.pop(k, None)
        return bool(expired)


# 全局唯一的 Token 管理器实例（server.py 与 qq_bot.py 共用同一份）
_token_manager = TokenManager()


def get_token_manager():
    """获取全局唯一 TokenManager 实例。"""
    return _token_manager


# ---------------------------------------------------------------------------
# 机器人启动封装（独立线程，不阻塞 server.py 主服务；支持保存设置后自动重启）
# ---------------------------------------------------------------------------
_bot_lock = threading.Lock()        # 保护 _bot_thread / _bot_holder 的并发访问
_bot_thread = None
_bot_holder = {"loop": None}        # 承载机器人线程内创建的事件循环，供 stop_bot 关闭用


def _runner(appid, secret, address_builder, holder):
    """机器人线程主体：创建专属事件循环，启动 botpy 客户端并保持运行。"""
    try:
        import botpy  # 延迟导入，避免未安装时影响 server.py 主流程
    except Exception as e:  # noqa: BLE001
        print("[qq_bot] 未安装 qq-botpy，无法启动机器人：%s" % e)
        return
    # botpy.Client 在构造时会调用 asyncio.get_event_loop()，线程内需先建事件循环
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    holder["loop"] = loop
    loop.run_until_complete(asyncio.sleep(0))
    try:
        intents = botpy.Intents.none()
        intents.public_messages = True  # 订阅公域群/C2C 消息（含 C2C 私聊）
        builder = address_builder

        class _Bot(botpy.Client):
            def __init__(self):
                super().__init__(intents=intents)
                self._builder = builder or (lambda: "qq_bot 未配置 address_builder。")

            async def on_c2c_message_create(self, message):
                content = (getattr(message, "content", None) or "").strip()
                try:
                    if content == "地址":
                        text = self._builder()
                        if text:
                            await message.reply(content=text)
                except Exception:
                    import traceback
                    traceback.print_exc()

        bot = _Bot()
        # 官方鉴权方式：AppID + AppSecret（SDK 内部先换 Access Token 再连 WebSocket）
        bot.run(appid, secret)
    except Exception:  # noqa: BLE001
        import traceback
        traceback.print_exc()


def start_bot(appid, secret, address_builder=None):
    """以后台守护线程启动 QQ 机器人。

    Args:
        appid (str): 机器人 AppID。
        secret (str): 机器人 AppSecret。
        address_builder (callable): 收到「地址」指令时用于构造回复文本的回调；
            由 server.py 注入（含 IPv6 地址与 Token 链接）。
    Returns:
        bool: 是否成功启动（已在运行则返回 False）。
    """
    global _bot_thread
    with _bot_lock:
        if _bot_thread is not None and _bot_thread.is_alive():
            return False
        if not appid or not secret:
            print("[qq_bot] 缺少 QQ_BOT_APPID / QQ_BOT_SECRET，机器人未启动。")
            return False
        holder = _bot_holder
        holder["loop"] = None
        tr = threading.Thread(target=_runner, args=(appid, secret, address_builder, holder),
                              name="qq_bot", daemon=True)
        _bot_thread = tr
        tr.start()
    print("[qq_bot] 机器人线程已启动（私聊发送『地址』可获取访问凭证）。")
    return True


def stop_bot():
    """停止当前 QQ 机器人线程（关闭其事件循环；守护线程，容忍未完全退出）。"""
    global _bot_thread
    with _bot_lock:
        loop = _bot_holder.get("loop")
        th = _bot_thread
        _bot_thread = None
        _bot_holder["loop"] = None
    if loop is not None:
        try:
            loop.call_soon_threadsafe(loop.stop)
        except Exception:  # noqa: BLE001
            pass
    if th is not None and th.is_alive():
        th.join(3)
    return True


def restart_bot(appid, secret, address_builder=None):
    """停止旧机器人并用新凭证重启（用于设置页保存后自动生效）。

    Returns:
        bool: 有凭证且成功重启返回 True；无凭证（仅停止）返回 False。
    """
    stop_bot()
    if not appid or not secret:
        print("[qq_bot] 未配置 QQ_BOT_APPID / QQ_BOT_SECRET，机器人仅停止不再启动。")
        return False
    return start_bot(appid, secret, address_builder)


if __name__ == "__main__":
    # 顶层直接运行时不启动，仅打印说明（由 server.py 负责调用 start_bot）
    print("[qq_bot] 本文件由 server.py 导入调用，请勿单独直接运行。")