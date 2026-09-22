@echo off
rem ============================================================
rem  启动历史学习服务（含 QQ 机器人访问凭证分发）
rem  双击本文件即可：设置机器人凭证 -> 运行 server.py
rem ============================================================
title 历史学习服务（QQ 机器人已启用）
cd /d "%~dp0"

rem ---- QQ 机器人凭证（AppID + AppSecret，从环境变量注入 server.py）----
rem 如需启用 QQ 机器人，请在此填写你自己的凭证（AppID + AppSecret）
set QQ_BOT_APPID=
set QQ_BOT_SECRET=

rem ---- 可选：本地/局域网不需要 QQ 机器人时，可把下行下一行取消注释（机器人不启动）----
rem set QQ_BOT_APPID=
rem set QQ_BOT_SECRET=

python server.py
pause