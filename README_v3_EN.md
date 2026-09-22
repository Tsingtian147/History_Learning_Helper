<div align="center">

# 🏛️ World History · Timeline Learning Web App

**A framework-only history learning platform for "World History, Grade 9, Volume 1" — Timeline · Quiz · Quick-Reference in one**

<a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white" alt="Python"/></a>
<a href="https://docs.python.org/3/library/http.server.html"><img src="https://img.shields.io/badge/Zero--deps-Standard%20Library-green" alt="Zero Dependencies"/></a>
<a href="https://q.qq.com/"><img src="https://img.shields.io/badge/Dual%20Port-Edit%20100%20%2F%20Readonly%208424-blue" alt="Dual Port"/></a>
<a href="https://q.qq.com/"><img src="https://img.shields.io/badge/Remote-QQ%20Bot%20Token-9cf" alt="QQ Bot Token"/></a>
<a href="#4-data-format-reference"><img src="https://img.shields.io/badge/Storage-Server%20JSON-purple" alt="Server JSON"/></a>

<br/>

**Zero dependencies · Zero build · Just run** — a tool that turns scattered historical facts into a **visual timeline + learn-then-test** closed loop.

<br/>**AI-friendly · One-click data generation**

<a href="https://chat.deepseek.com/"><img src="https://img.shields.io/badge/DeepSeek-Generate%20Data-1F77B4?logo=deepseek&logoColor=white" alt="DeepSeek"/></a>
<a href="https://www.qianwen.com/chat/"><img src="https://img.shields.io/badge/Qwen-Tongyi-615CED?logo=alibaba&logoColor=white" alt="Qwen"/></a>
<a href="https://chatglm.cn/"><img src="https://img.shields.io/badge/GLM-Zhipu-3859FF" alt="GLM"/></a>
<a href="https://kimi.moonshot.cn/"><img src="https://img.shields.io/badge/Kimi-Moonshot-4B7BEC" alt="Kimi"/></a>

</div>

---

## 📑 Table of Contents

- [1. Project Overview](#1-project-overview)
  - [1.1 Development Background](#11-development-background)
  - [1.2 Problems Solved](#12-problems-solved)
  - [1.3 How It Works](#13-how-it-works)
  - [1.4 Standout Strengths](#14-standout-strengths)
- [2. Page Modules](#2-page-modules)
- [3. Quick Start](#3-quick-start)
  - [3.1 Prerequisites](#31-prerequisites)
  - [3.2 Start the Server](#32-start-the-server)
  - [3.3 LAN Access (Other Devices)](#33-lan-access-other-devices)
  - [3.4 QQ Bot Official Registration](#34-qq-bot-official-registration)
  - [3.5 Configure the QQ Bot](#35-configure-the-qq-bot)
  - [3.6 Get Public Access via QQ Private Chat](#36-get-public-access-via-qq-private-chat)
  - [3.7 Public IPv6 Access](#37-public-ipv6-access)
  - [3.8 Generate Complete JSON with AI](#38-generate-complete-json-with-ai)
- [4. Data Format Reference](#4-data-format-reference)
  - [4.1 data.json — Timeline Multi-doc Format](#41-datajson--timeline-multi-doc-format)
  - [4.2 Time Representation Rules](#42-time-representation-rules)
  - [4.3 Typed Detail Markers](#43-typed-detail-markers)
  - [4.4 qa_data.json — Q&A Data](#44-qadatajson--qa-data)
  - [4.5 settings.json — Global Settings](#45-settingsjson--global-settings)
  - [4.6 quickref_data.json — Quick-Reference Weak Points](#46-quickrefdatajson--quick-reference-weak-points)
- [5. Backend API Reference](#5-backend-api-reference)
- [6. Remote Access Security](#6-remote-access-security)
- [7. Troubleshooting](#7-troubleshooting)
- [8. Data Safety and Version Management](#8-data-safety-and-version-management)
- [9. License](#9-license)

---

# 1. Project Overview

## 1.1 Development Background

"World History, Grade 9, Volume 1" spans **from prehistoric humans to the eve of the modern era** — thousands of years across Europe, Asia, Africa and the Americas, carrying a huge volume of knowledge points. Studying it usually hits three pain points:

- 🕰️ Knowledge points are **scattered across different lessons**, lacking a single time spine running through everything;
- 🌍 Multiple civilizations (Egypt, Mesopotamia, India, Greece, Rome, Arabia, West Africa, the Americas…) **existed in different times and places**, so their order and connections are hard to see at a glance;
- 📝 You memorize and forget — there's no **active-recall** training that links **"event → place / person / significance"**.

This project starts from "a scrollable, zoomable, freely editable **history timeline**" and grows into a **Timeline + Quiz + Quick-Reference** all-in-one learning platform, with the ability to carry your data with you (LAN / public network) and review it anytime.

## 1.2 Problems Solved

| Pain Point | This Project's Solution |
| --- | --- |
| Confusing history timeline | **Parallel multi-civilization lanes**, ordered by time, with arrows linking events within a civilization |
| Civilians span thousands of years, browsers freeze | Canvas width **capped at 60,000px**; scale/relative layouts control density |
| Too many historical terms to remember | **Quick-Reference page**: look up events from "place / person", active-recall learning |
| Knowledge must be practiced as Q&A | **Quiz page**: import Markdown, auto-split into "unit → question → answer", answer first, reveal later |
| Data gets messy when switching devices | **Server JSON is the single source of truth**; pages never write to browser localStorage |
| Losing data after an accidental import/edit | **Auto-backup** before each write, keeping up to 30 versions, restorable anytime |
| Want to review on the phone while away | Public IPv6 + **QQ Bot securely distributing access tokens**, no public IP needed |
| Don't want to install a pile of dependencies | Backend **pure Python standard library**, frontend zero-framework zero-build, one command to run |

## 1.3 How It Works

```text
┌───────────────────────── Frontend (static/) ─────────────────────────┐
│  index.html        Home (entry / sidebar navigation)                 │
│  timeline.html     Timeline · multi-doc tabs · dual layout · toggles │
│  qa.html           Quiz · Markdown import · pagination · weak points │
│  quickref.html     Lookup · reverse-lookup events · active learning  │
│  settings.html     Global settings · QQ bot creds · theme · version  │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP (static pages + /api/* JSON)
┌──────────────────────────────▼───────────────────────────────────────┐
│  Backend server.py (Python standard-library http.server)             │
│  · Dual port: 0100(edit) / 8424(read-only) · IPv6 dual-stack + 0.0.0.0│
│  · Token gate (public IPv6 only) · auto backup + atomic write +       │
│    legacy auto-migration                                             │
│  · Optional qq_bot.py: QQ Bot distributes access tokens via chat     │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ Filesystem
        ┌──────────────────────┼─────────────────────┐
        ▼                      ▼                     ▼
   data.json             qa_data.json            settings.json
   (timeline multi-doc)   (Q&A + weak points)      (theme/creds/version)
             └─ backups/ auto-backup dir (up to 30 copies)
```

- **Frontend**: plain `HTML + CSS + JS`, no npm / bundler, refresh and go;
- **Backend**: Python standard-library `http.server` `ThreadingHTTPServer`, **zero third-party deps** (only the optional QQ Bot needs `qq-botpy`);
- **Network**: IPv6 dual-stack (`AF_INET6` + `IPV6_V6ONLY=0`) + bind `0.0.0.0`, so one port serves **LAN IPv4** and **public IPv6** simultaneously;
- **Security**: public IPv6 access requires a platform-issued `AccessToken` (URL param or HttpOnly Cookie); readonly/edit tokens are purpose-isolated;
- **Storage**: read/write split — the readonly port is **force-rejected at the server side** for all write endpoints.

## 1.4 Standout Strengths

✨ **Three hardcore highlights** that set this apart from a plain "static webpage":

| Capability | Technical Implementation | Value |
| --- | --- | --- |
| 🚀 **Zero deploy, zero deps** | Pure `http.server` standard library, zero frontend build | Runs on any machine with Python 3 in one command — great for study/demo |
| 🔐 **Read/write split dual ports** | Edit port `100` writable, readonly port `8424` read-only, writes force-rejected | Separates "showcase" and "editor", zero accidental-write risk, safe to share |
| 🌏 **Remote access without a public IP** | IPv6 dual-stack + one-time tokens distributed via QQ Bot private chat | View from your phone anywhere; no domain / no port forwarding |
| 🧠 **AI one-click data generation** | Standardized JSON format + ready prompt template | Throw a textbook / handwritten notes at AI, get usable data instantly |
| 🛡️ **Data never lost** | Backup only on content change + atomic write + legacy auto-migration | Rollback after mistakes, no data loss across version upgrades |

---

# 2. Page Modules

The app ships with 5 pages, switched via the left **sidebar** (hover to expand):

| Icon | Page | URL | Highlights |
| --- | --- | --- | --- |
| 🏠 | Home | `/` | Overall entry, reserved homepage placeholder |
| 🕰️ | Timeline | `/timeline.html` | Parallel civilizations, dual layout, visibility toggles, multi-docs, print PDF |
| 💬 | Quiz | `/qa.html` | Markdown import, unit/question/answer structure, pagination, weak points |
| 🔍 | Quick-Reference | `/quickref.html` | Reverse-lookup events by place/person, active learning, weak points, PDF |
| ⚙️ | Settings | `/settings.html` | QQ Bot creds, global theme, version number |

### 🕰️ Timeline (timeline.html)

- **Horizontal × Vertical**: the X axis is time (old left → recent right), the Y axis is civilizations/regions — one lane per civilization; nearby regions can share a lane;
- **Two overall alignments**:
  - `Scale (scale)`: strictly positions by year proportion;
  - `Relative (relative)`: all civilizations share one time axis, guaranteeing cross-civilization ordering while staying compact;
  - "pixels per hundred years" adjusts density; canvas width capped at **60,000px**;
- **Visibility toggles**: time text / event box / event text / detail box / detail symbol / detail text each independently toggleable; a whole civilization lane can be hidden with auto reflow;
- **Multiple timeline docs**: top tabs to create / switch / rename / delete multiple timelines with independent data;
- **Rich details**: plain text / `[Place]` / `(Person)` / `_bullet points_` typed markers, entered item by item;
- **Data panel**: import / export JSON, manual save / load from server;
- **Offline export**: one-click single-file `.offline.html`, double-click to view without a server;
- **Print PDF**: true WYSIWYG, supports landscape + fit-to-width.

### 💬 Quiz (qa.html)

- **Markdown import**: paste / upload Markdown, auto-parsed into "**unit → question → answer**";
  - Unit title: level-1 heading `# Unit X`;
  - Question: **only a numbered level-2 heading**, e.g. `## 1. Humen Opium Destruction significance`;
  - Answer: all body text under the question title, rendered as **Markdown** (bold / lists / tables);
- **Answer first, reveal later**: one "Show answer" button per question, plus **show-all / hide-all**;
- **Pagination**: 10 / 20 / 30 per page (default 30, capped to avoid mobile freezes);
- **Weak points**: ⭐ star a question to build weak-point lists, with create / switch / export / import;
- **Multi-doc + offline export**: multi-doc tabs, single-file `.offline.html`.

### 🔍 Quick-Reference (quickref.html)

- **Data source**: instant from timeline `data.json`; pick **one or more** timeline docs and choose the **person** or **place** dimension; same-name entities across docs auto-merge;
- **Info overview**: one column per "person / place", fully listing all related events, paginated by entity (10/20/30);
- **Active learning**: one entity per page, show the name first, expand events on demand, with **sequential / random** draw for retrieval training;
- **Weak points**: ★ marks an entity into a list, switch / rename / export / import;
- **Print PDF / offline export**.

---

# 3. Quick Start

> About **10 minutes** from nothing to having it running on your phone. Step by step below.

## 3.1 Prerequisites

| Item | Description | Check command |
| --- | --- | --- |
| **Python 3.x** | Backend runtime, **no dependencies to install** | `python --version` |
| **Browser** | Any modern browser (Chrome / Edge) | — |

> The core service is zero-dependency; only if you enable the QQ Bot remote access do you need `pip install qq-botpy` (see 3.5).

## 3.2 Start the Server

Put the project (containing `server.py`, `static/`, `data.json`) anywhere, then:

```bash
cd History_Learning
python server.py
```

It auto-opens the browser at `http://127.0.0.1:100`. The console prints:

```
世界历史学习 · 时间轴应用已启动
  本机 编辑端口(读写)：http://127.0.0.1:100/
  本机 只读端口(查看)：http://127.0.0.1:8424/
  局域网访问（其他设备）：
     编辑：http://192.168.x.x:100/    只读：http://192.168.x.x:8424/
```

- **Edit port `100`**: view / add / modify / import-export;
- **Read-only port `8424`**: view / export / save offline page only, **cannot modify content**;
- Stop the service with `Ctrl+C`;
- ⚠️ **Run only one `server.py` instance at a time**, to avoid port conflicts and mixing old/new code.

**Port in use?** Switch ports temporarily via environment variables:

```powershell
# Windows PowerShell
$env:PORT="8000"; python server.py
# The read-only port defaults to 8424, can also be changed:
$env:READ_ONLY_PORT="9000"; $env:PORT="8000"; python server.py
```

## 3.3 LAN Access (Other Devices)

The server binds `0.0.0.0` (all interfaces) by default, so **a phone/tablet on the same WiFi can directly use the LAN IPv4 address without a token — the most reliable option**:

- Read-only: `http://192.168.x.x:8424/`
- Edit: `http://192.168.x.x:100/`

> Find your LAN IP on Windows: `ipconfig`.
> If other devices can't connect, it's usually the **Windows Firewall** blocking Python's inbound traffic — allow Python (or ports 100 / 8424).

## 3.4 QQ Bot Official Registration

To access from the **public network (while away)**, you need a **QQ Bot** to privately distribute access credentials (no public IP / no port forwarding).

**Official registration entry:**

> 🔗 **QQ Bot Open Platform: https://q.qq.com/** (click to go directly)

Brief flow:

1. Open https://q.qq.com/ and log in with your **QQ account** (a commonly-used QQ is recommended);
2. Enter the **Open Platform console** and complete **developer real-name verification** as guided;
3. **Create a bot application** under "Bot Management";
4. After creation, grab two key credentials from the app detail page:
   - **AppID** — the bot's unique identifier;
   - **AppSecret** — used to exchange the platform Access Token (**keep it safe, never expose it**);
5. Follow the platform guide to **publish the bot and enable "private chat"** (this project's credential distribution relies on the private-chat / C2C channel).

> Official SDK & dev docs: 🔗 **https://q.qq.com/wiki/** (qq-botpy / API).
> The `qq-botpy` SDK used here: 🔗 **https://github.com/TencentQQBot/qq-botpy**

## 3.5 Configure the QQ Bot

With AppID / AppSecret in hand, pick one of two ways to configure:

**Method A: Web settings page (recommended, no restart)**

1. Open the edit page `http://127.0.0.1:100/settings.html`;
2. Fill in AppID / AppSecret under "QQ Bot Credentials" and save;
3. The server **restarts the bot thread automatically**, taking effect immediately.

**Method B: Environment variables (auto-carried on first startup)**

```powershell
# Windows PowerShell
$env:QQ_BOT_APPID="your bot AppID"
$env:QQ_BOT_SECRET="your bot AppSecret"
python server.py
```

> Install first: `pip install qq-botpy`.
> Credentials are persisted to `settings.json` (the settings page takes precedence over env vars).
> ⚠️ **AppSecret is confidential — never share it.**

## 3.6 Get Public Access via QQ Private Chat

1. Search for your bot in QQ and start a **private chat (C2C)**;
2. Send the text: **地址** (meaning "address");
3. The bot replies with a message containing:
   - The server's **public IPv6 address(es)** (a machine may have several — pick the one from your real NIC);
   - An **edit port `100`** link (embedded token, valid **10 minutes**);
   - A **read-only port `8424`** link (embedded token, valid **1 hour**);
4. Tap the matching link to access from the public network.

> **A token is regenerated on every command**, a random 96-hex string, auto-expiring, and persisted to `tokens.json` (tokens still valid after a restart remain usable).

## 3.7 Public IPv6 Access

Access links look like:

```
http://[publicIPv6]:100/?AccessToken=<Token>     # edit
http://[publicIPv6]:8424/?AccessToken=<Token>    # read-only
```

- On first valid-token visit, the server issues an **HttpOnly Cookie** (lifetime = remaining token time); subsequent page and `/api/*` requests are auto-carried, **no query param needed**;
- **Pure public IPv6 access without a valid token always returns 403**; local `127.0.0.1` / LAN IPv4 / loopback `::1` need no token;
- The edit port needs an **edit-purpose** token, the read-only port a **read-only-purpose** token; they are not interchangeable;
- On 403, the token is invalid / expired / wrong purpose — re-request with QQ private chat "地址";
- Public access requires a public IPv6 address (visible via `ipconfig`, e.g. `2001:` / `240e:`) and an open firewall;
- If unwanted IPv6 addresses (e.g. from virtual NICs) are picked up, exclude them: `$env:SKIP_IPV6="2409:xxxx"`

> 💡 **Prefer LAN IPv4 tokenless access on the same WiFi** (see 3.3). On the same network, hitting the public IPv6 may intermittent fail (e.g. `ERR_INVALID_HTTP_RESPONSE`) due to home-router loopback forwarding — that's a network-path matter, not a server fault.

## 3.8 Generate Complete JSON with AI

This project uses a **standardized JSON data format**, so you can **send this README, an existing `data.json` sample, and your textbook / handwritten notes to any AI assistant and get a complete, ready-to-use `data.json` back** — content production with zero barrier.

> 📌 Sample prompt (copy the template below to AI, replacing the placeholder materials. **Does not include the actual document text**):

```
You are an expert "structured-data organizer" for history teaching. Based on the
materials I provide, produce a timeline data file (data.json) that fully conforms
to the JSON format I specify.

[TASK]
Organize the historical knowledge points in the materials into timeline data with
the structure {version:2, docs:[...]}.

[OUTPUT FORMAT — MUST FOLLOW STRICTLY]
1. Top level must be: { "version": 2, "docs": [ { ... } ] };
2. The first item of docs is one "timeline document", required fields: id / name /
   created / title / globalOptions / lanes;
3. globalOptions must include layout("scale" or "relative"), pxPer100(a number),
   theme(one of four: parchment|ocean|forest|mono), and show (all six visibility
   toggles set to true);
4. Each item of lanes represents a "civilization/country", required fields: id /
   name / visible(true) / color(null) / events(an array);
5. Each event must include: id / timeText(human-readable original text, e.g.
   "circa 3100 BC") / startYear(a number; before Christ is always negative) /
   endYear(a number) / eventText(short event name) / details(an array);
6. Marker rules for each line of details (freely combinable):
   - 【Place】 marks a place, e.g. "【Nile River Valley】";
   - （Person） marks a person, e.g. "（Hammurabi）";
   - _point_、_point_ marks memorization points, multiple separated by Chinese
     comma (、);
7. Time conversion rules (be accurate):
   - N years BC → value -N;
   - the Nth century BC → start -(N*100-99), end -(N-1)*100;
   - the Nth century AD → start (N-1)*100+1, end N*100;
   - a single point-in-time event has endYear equal to startYear;
   - if timeText mentions a specific month/day, additionally give startMonth/
     startDay/(endMonth/endDay), otherwise omit or use null;
8. Use readable id prefixes (e.g. doc_xxx / lane_xxx / e_xxx), unique is enough;
9. Output JSON only, no explanations, no Markdown code fences, no ellipsis.

[MY MATERIALS]
(1) This project's data.json "format spec" — see the "Data Format Reference"
    section of this README;
(2) An existing data.json sample — paste it as a format reference;
(3) Textbook / e-textbook / handwritten notes content — paste the paragraphs.

Now please start. If a material lacks some info, fill that field with null or [],
do not fabricate.
```

**After you get the AI-generated JSON:**

1. Open the edit page `http://127.0.0.1:100/timeline.html`;
2. Click the top-right "⚙ Data" → **Import JSON**, paste the AI's full output → confirm;
3. The timeline refreshes immediately; if the format is wrong, the **auto-backup** provides a safe rollback.

---

# 4. Data Format Reference

This project stores data **only in server JSON files**; pages never write to browser `localStorage`, so **the same data is identical across every entry point / device**.

## 4.1 data.json — Timeline Multi-doc Format

> Top-level `version: 2`, multi-document structure. If a legacy single-doc format is read (top level has `lanes` but no `docs`), the backend **auto-migrates** it to the multi-doc format and writes it back, no data loss.

```jsonc
{
  "version": 2,                            // fixed to 2 (multi-doc format version)
  "docs": [
    {
      "id": "docxxx",                      // unique document id
      "name": "世界历史 九年级上册 时间线",    // name shown on the tab
      "created": "2026-09-16 19:52",       // creation time
      "title": "世界历史 九年级上册 时间线",  // big title at the top of the page
      "globalOptions": {
        "layout": "scale",                 // "scale" or "relative"(min spacing)
        "pxPer100": 30,                    // pixels per 100 years in scale mode
        "theme": "parchment",              // only parchment|ocean|forest|mono
        "customColors": { "bg": "#f5efe0", /* optional: custom colors */ },
        "show": {                          // visibility toggles (true=show)
          "timeText": true,     // time box text
          "eventBox": true,     // event box
          "eventText": true,    // event box text
          "detailBox": true,    // detail box
          "detailSymbol": true, // detail symbols
          "detailText": true    // detail text
        }
      },
      "lanes": [
        {
          "id": "lane_egypt",              // unique civilization-lane id
          "name": "古埃及",                 // civilization name (left label)
          "visible": true,                 // false hides the whole lane (reflow)
          "color": null,                   // optional lane color, null = default
          "events": [
            {
              "id": "e_egypt_1",            // unique event id
              "timeText": "公元前3100年前后",// original time text (for humans)
              "startYear": -3100,           // start year (BC as negative)
              "startMonth": null,           // optional start month 1-12
              "startDay": null,             // optional start day 1-31
              "endYear": -3100,             // end year (=start means a point)
              "endMonth": null,             // optional end month
              "endDay": null,               // optional end day
              "eventText": "埃及初步实现统一",// event name
              "details": [                  // detail lines (array, one line each)
                "【尼罗河流域】（那尔迈）_中央集权_、_文字_"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Event field quick-reference:**

| Field | Type | Required | Description |
| --- | --- | --- | --- |
| `id` | string | ✅ | Unique event id |
| `timeText` | string | ✅ | Original time text, e.g. "circa 3100 BC" |
| `startYear` | number | ✅ | Start year value, **BC as negative** |
| `endYear` | number | ✅ | End year; equal to start means a single point |
| `startMonth` / `startDay` | number\|null | ❌ | Precise to month/day |
| `endMonth` / `endDay` | number\|null | ❌ | End month/day |
| `eventText` | string | ✅ | Event name |
| `details` | string[] | ✅ | Detail lines (with typed markers) |

## 4.2 Time Representation Rules

- **Value and text are separate**: `timeText` is what humans read, `startYear`/`endYear` are what calculations use; they don't need to match exactly;
- **BC is always negative**:

| Time | startYear | endYear |
| --- | --- | --- |
| 3100 BC | `-3100` | `-3100` |
| 21st century BC | `-2099` | `-2000` |
| AD 476 | `476` | `476` |
| 1st century AD | `1` | `100` |

- **Month / day (optional)**: `startMonth`/`startDay` (and the end side), 1-12 / 1-31; leave blank for Jan 1. Sorting and scale positioning convert "year + month/12 + day/365" into a continuous value, so different month-days in the same year are still ordered;
- **Sorting / positioning rules**:
  - The start moment decides "where it goes" (left-right order within a civilization, cross-civilization order, and horizontal coordinate);
  - The end moment decides "how long it spans" (a range event's box width ≈ span × pixels-per-century; if too narrow, content width wins);
  - The canvas time range spans the min/max of all start/end moments; the axis ticks at whole years.

## 4.3 Typed Detail Markers

Freely combinable on the same line:

| Format | Meaning | Example |
| --- | --- | --- |
| `【Place】` | place | `【尼罗河流域】` |
| `（Person）` | person | `（汉谟拉比）` |
| `_point_、_point_` | memorization points (underscored items separated by 、) | `_中央集权_、_文字_、_多神_` |

Combined example: `【两河流域】（汉谟拉比）_法典_、_集权_`

> In the edit dialog, enter via "pick a type + fill the content"; markers are attached automatically on save, **no need to type symbols by hand**. Imported combined JSON is auto-split back into individual typed entries.

## 4.4 qa_data.json — Q&A Data

```jsonc
{
  "version": 1,
  "docs": [
    {
      "id": "docmu2saz0wxfnd3",
      "name": "八上历史",                 // doc name
      "created": "2026-09-15 22:45",
      "units": [
        {
          "title": "第一单元 中国开始沦为半殖民地半封建社会",  // unit title
          "questions": [
            {
              "id": "qmu2saz0vjqvhv",
              "title": "鸦片走私原因",      // question
              "answerMd": "…(Markdown original text)" // answer, Markdown-rendered
            }
          ]
        }
      ]
    }
  ],
  "weakLists": [                          // weak-point lists
    {
      "id": "wlxxx",
      "name": "我的薄弱点",
      "qids": ["qmu2saz0vjqvhv"],         // set of starred question ids
      "created": "2026-09-16 08:30"
    }
  ]
}
```

## 4.5 settings.json — Global Settings

```jsonc
{
  "version": 2,
  "appVersion": "v2.10",
  "theme": "parchment",                   // parchment|ocean|forest|mono
  "qqBot": { "appid": "your AppID", "secret": "your AppSecret" }
}
```

> Maintained by the settings page; `theme` is shared across the four pages; `secret` is not echoed back in the settings page. ⚠️ Contains secrets — do not commit to GitHub.

## 4.6 quickref_data.json — Quick-Reference Weak Points

Entities are identified by `entityKeys`: `p:person` (person), `l:place` (place).

```jsonc
{
  "version": 1,
  "weakLists": [
    {
      "id": "wlxxxx",
      "name": "易混人物",
      "entityKeys": ["p:汉谟拉比", "p:图特摩斯三世", "l:两河流域"],
      "created": "2026-09-17 20:00"
    }
  ]
}
```

> Entities themselves are not stored in this file — they are parsed from the timeline `data.json` at save time. This file only records "which name was marked as weak".

---

# 5. Backend API Reference

| Method | Path | Description | Read-only port (8424) |
| --- | --- | --- | --- |
| GET | `/api/load` | Load timeline data `data.json` | ✅ |
| GET | `/api/qa/load` | Load quiz data `qa_data.json` | ✅ |
| GET | `/api/quickref/load` | Load quickref weak points `quickref_data.json` | ✅ |
| GET | `/api/ui/load` | Load global theme (settings.json theme) | ✅ |
| GET | `/api/settings/load` | Load version/theme/AppID + whether Secret is set | ✅ |
| GET | `/api/health` | Health check | ✅ |
| POST | `/api/save` | Save timeline data | ❌ 403 |
| POST | `/api/qa/save` | Save quiz data | ❌ 403 |
| POST | `/api/quickref/save` | Save quickref weak points | ❌ 403 |
| POST | `/api/ui/save` | Save global theme | ❌ 403 |
| POST | `/api/settings/save` | Save settings + restart bot | ❌ 403 |
| GET | others | Static files (html/js/css) | ✅ |

> **IPv6 access gate**: all endpoints under a pure public-IPv6 source require a valid `AccessToken`, otherwise 403; local / LAN IPv4 need no token.

---

# 6. Remote Access Security

```text
       External device (public network)
        │  only public IPv6 reachable
        ▼
┌──────────────────────────────────────────────────┐
│  server.py  (IPv6 dual-stack + 0.0.0.0)          │
│                                                  │
│  GET in → is it "pure public IPv6"?              │
│     ├─ No (local/LAN) → allow (no token)         │
│     └─ Yes → validate AccessToken:               │
│          ├─ valid → issue HttpOnly Cookie → allow│
│          └─ invalid/expired → 403                │
└─────────────────▲────────────────────────────────┘
                  │ private-chat "address" issues token
        ┌─────────┴─────────┐
        │  QQ Bot (qq_bot.py) │
        └───────────────────┘
```

- **Double security**: public access requires the token from QQ Bot private chat; edit / read-only ports are **purpose-isolated**;
- **One-time token**: randomly generated, auto-exports, persisted to `tokens.json`;
- **Read/write split**: the read-only port intercepts all write endpoints server-side, ideal for long-term / public placement;
- **No public IP / DDNS / port forwarding needed**: relies on public IPv6 + local dual-stack listening.

---

# 7. Troubleshooting

| Symptom | How to fix |
| --- | --- |
| Browser won't open | Run `python server.py` first; the URL must include the port `http://127.0.0.1:100` |
| Pages still show old version | Make sure **only one** `python server.py` is running, then restart; hard refresh with `Ctrl+F5` after changes |
| "Save to server" fails | That feature depends on the backend — access the page via `server.py`, don't double-click the html file |
| Import JSON errors | Timeline: check top-level has a `docs` array (legacy `lanes` auto-migrates); Quiz: check `docs`/`weakLists` |
| Print too wide, split pages | In print preview choose **landscape** + "fit to page width" |
| Public access returns 403 | Re-request the token via QQ private chat "地址" (expired / wrong purpose) |
| Phone reports `ERR_INVALID_HTTP_RESPONSE` | On the same WiFi, switch to **LAN IPv4** tokenless access (see 3.3) |
| Restore overwritten data | Find a timestamped backup in `backups/`, rename it (e.g. `data.json`) and replace |

---

# 8. Data Safety and Version Management

- **Server JSON is the single source of truth**: timeline `data.json`, quiz `qa_data.json`, quickref `quickref_data.json`, settings `settings.json`; pages never write `localStorage`;
- **Auto-backup**: before writing **content-changed** new data, the old version is backed up to `backups/` (named `prefix_timestamp.json`), **keeping up to 30 copies**, deleting the oldest beyond that;
- **Atomic write**: writes to a temp file first, then `os.replace` swaps it, preventing half-written corruption;
- **Legacy auto-migration**: an old single-doc `data.json` auto-migrates to the multi-doc format on startup and is written back;
- **Version archives**: `Release/` snapshots each runnable stage by version for rollback and comparison.

---

# 9. License

This project is released under the **MIT License**. You are free to use, modify, and distribute it for study, personal projects, or course/assignment showcase.

> If used for competitions / extra credit / assignments, please keep the author's explanation of this project's technical approach (zero-dependency backend, IPv6 dual-stack + QQ Bot secure credential distribution, multi-doc data format with auto-backup), and comply with each platform's rules and agreements.

---

<div align="center">

**Made with 💙 for history learning — fitting thousands of years of civilization into one readable timeline.**

</div>