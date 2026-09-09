# 小白机器人 (astrbot_plugin_xbbot) — 全代码架构文档 (aiall.md)

> 版本：`v0.7.32` ｜ 对象：想从头到尾看懂这份代码的人（函数行号仍以 v0.7.28 为准，v0.7.29~32  printing 偏移：slave.py 查询块 -15 行、app.js +80 行、game.py +25 行左右）
> 规模：103 个文件，文本约 3.4 万行（图片等二进制除外）
> 定位：AstrBot 群互动大插件（奴隶/签到/银行/娱乐/私聊/精灵/坐骑/超管/帮派/冒险 10 引擎 + WebUI 管理台）
> 配套文档：`AIINFO.md`（状态卡：十二红线+铁律+交付流程，红线唯一出处）、`AIREADME.md`（交接手册：分层/存储/指令/数值/隔离矩阵/版本史）
> 本文件只讲“代码是什么、怎么转”，规则类结论以 AIINFO 为准，不复述红线。

---

## 0. 总览：一句话、目录树、分层、数据流

### 0.1 一句话

用户在群里发一句话 → `main.py` 的 `_dispatch` 收到 → `core/router.py` 按 11 层流水线判定 → 某个 `engines/*.py` 算出回复（纯文本或“文本+图片”元组）→ `core/platform.py` 转成消息链发出去；数据全部落在 `store.py` 的 SQLite 里；`pages/admin` 的网页通过 `core/api/*.py` 的 68 个 HTTP 接口管一切。

### 0.2 目录树（插件根 `astrbot_plugins/astrbot_plugin_xbbot/`）

```
astrbot_plugin_xbbot/
├── metadata.yaml          # 插件身份证：名字/版本0.7.28/作者/仓库（9处版本对齐的基准）
├── main.py                # 975行：插件入口。消息分发 + 68个Web API注册 + 后台备份线程
├── store.py               # 2047行：唯一存储内核。SQLite WAL + 备份防重 + 密钥分存 + 三源投票
├── _conf_schema.json      # 29节901项配置字典（v0.7.29 起；删9查询前为4797行928项，所有可调项的家）
├── verify_plugin.py       # 119行：交付自检（语法/版本9处/schema/武器文件数）
├── AIINFO.md / AIREADME.md / aiall.md / CHANGELOG.md / README.md  # 文档（本文件是代码卷）
├── .gitignore             # 忽略规则
├── core/                  # 核心层（单向依赖，不碰 engines 和 pages）
│   ├── config.py          # 234行：配置归一 + 指令采集器（206条规范指令的唯一来源，v0.7.29 删9查询）
│   ├── router.py          # 672行：11层指令流水线 + 自定义/禁用/权限/回复四元索引
│   ├── platform.py        # 415行：消息链/元组发图/@补段/昵称前缀/禁言踢人熔断
│   ├── webdav.py          # 580行：纯标准库WebDAV客户端（坚果云/Alist/群晖通用）
│   ├── dispatch.py        # 81行：旧导入兼容垫片（转调 test_harness）
│   ├── test_harness.py    # 627行：测试testxb 探针矩阵 + 超管列表实现
│   ├── logger.py          # 194行：xb.log 日志引擎（2MB轮转）
│   ├── en_map.py          # 194行：中英键映射（中文存英文，提高DB效率，显示仍中文）
│   └── api/               # Web API 薄路由层（68接口，耗时走 asyncio.to_thread）
│       ├── analytics.py   # 149行：大屏聚合
│       ├── backup.py      # 749行：备份/恢复/快照/体检/WebDAV全套
│       ├── config_api.py  # 577行：配置读写 + 三档智能平衡 + 漂移检测
│       ├── game.py        # 929行：奴隶/精灵画像 + 图鉴CRUD + 武器池文件管理
│       ├── groups.py      # 117行：总开关/群开关
│       ├── helpers.py     # 244行：取参/报错/下载跨框架兼容
│       ├── images.py      # 348行：图片文件库（插件根为牢笼防穿越）
│       ├── legacy.py      # 698行：旧库导入（db/ini/json/zip四态）
│       ├── logs.py        # 76行：日志查看/清空/导出
│       ├── stats.py       # 144行：总览 + 排行榜
│       ├── updater.py     # 在线更新检测（纪元算法隔离旧版；v0.7.30 起 3 镜像+在途共享+分级缓存）
│       └── users.py       # 875行：用户增删改查 + 空投
├── engines/               # 业务引擎层（只读 store，不碰 core/pages）
│   ├── slave.py           # 2281行：奴隶买卖RPG + 抽奖 + 排行 + 昵称中枢（最大文件）
│   ├── ent.py             # 1160行：娱乐会话游戏（接龙/急转弯/猜数/答题/二四点/猜拳/抽签/炸弹）
│   ├── bank.py            # 1114行：银行经济 + 监狱（存款/赌博/打劫/红包/保释越狱）
│   ├── spirit.py          # 801行：精灵领养/冒险/收服/进化/PVP
│   ├── guild.py           # 640行：帮派创建/贡献/福利/帮战
│   ├── sign.py            # 634行：签到/抽奖/新手/点赞/排行
│   ├── superadmin.py      # 611行：27条超管精确指令，非超管全静默
│   ├── ride.py            # 548行：坐骑商城 + 欢迎坐骑
│   ├── adventure.py       # 322行：14秘境文字冒险
│   ├── chat.py            # 73行：私聊词库陪聊
│   ├── spirit_data.py     # 159行：精灵图鉴静态数据（权威基线）
│   ├── slave_text.py      # 283行：奴隶系统文案常量库
│   └── adventure_text.py  # 167行：冒险叙事文本库
├── pages/admin/
│   ├── index.html         # 2262行：14个Tab + 双弹窗 + Toast骨架 + 全套CSS
│   └── app.js             # 约5450行：无构建原生单页应用（桥接/14页/商城/图鉴/备份/指令编辑器）
├── scripts/
│   ├── stress_24h.py      # 197行：24h加速压测（4800消息+80并发API）
│   └── test_fix.py        # 94行：四项历史修复回归
└── data/                  # 运行时数据（随包只带种子，首次启动自愈播种）
    ├── config.json        # 持久配置快照
    └── img/               # 图片池：gacha/{SSR,SR,R} 抽奖武器（文件即池）+ rides/ 坐骑 + spirits/ 精灵
```

### 0.3 分层与依赖方向（单向，不许反向）

```
pages/admin（网页）
   ↓ HTTP
main.py（入口：分发 + 注册表 + 薄委托）
   ↓ 调用
core/（config → platform → router → webdav，api 薄路由）
   ↓ 调用                ↓ 调用
engines/（10业务引擎）   store.py（SQLite唯一真相）
```

- `pages` 只能调 `main` 注册的 HTTP 接口，不能直连 DB。
- `engines` 只能读 `store`，不能 `import core`（除 superadmin 调 updater 这种显式回退）。
- `core` 不许 `import engines`（platform 拿 slave 是运行时 `bind()` 注入，不是 import）。

### 0.4 一条消息的完整旅程（群聊发“签到”）

1. AstrBot 调 `main.XbBot.on_message` → `_dispatch(event)`（`main.py:409`）。
2. 取群号QQ、同步群名片、补 `@` 段、判超管身份。
3. `router.handle()` 11 层流水线：总开关→群开关→维护→私聊→主菜单→自定义→禁用→**权限**→8 引擎→超管。
4. `sign.handle` 命中“签到”，读 `store` 算奖励，写回钱包，返回文本。
5. `platform._build_chain` 包成消息链 → 发群。

### 0.5 一个网页操作的完整旅程（商城改坐骑价格点保存）

1. 输入框 `input` 事件立刻写内存 `SHOP_RIDE`（绝不从 DOM 收集，防搜后丢数）。
2. 点保存 → `saveShops()` 只打包 `商城图鉴.ride_shop` → `POST config/save`。
3. `config_api.handle_cfg_save` 归一 → 写内存 `_CONFIG` → `save_config` 落 `config.json` + DB 镜像。

---

## 1. 根文件（插件根目录）

### 1.1 `metadata.yaml`（10行）——插件身份证

AstrBot 认插件就认它。字段：`name: astrbot_plugin_xbbot`（也是网页桥接前缀）、`display_name: 小白`、`version: 0.7.28`（9 处版本对齐的**基准**，发版时先改它）、`author: Light`、`repo: https://github.com/imsuperone/xb`、`support_platforms: [aiocqhttp]`、`astrbot_version: >=3.4.0`。

### 1.2 `main.py`（975行）——入口，分发+注册表+委托

**职责**：插件类 `XbBot(Star)` 的家；三件事：收消息分发、注册 68 个网页接口、起后台备份线程。

**顶层符号**：

| 符号 | 行 | 作用 |
|---|---|---|
| `_err` | 82 | 统一报错，兼容三种响应签名 |
| `_raw_file_response` | 91 | aiohttp→quart→starlette 三通道文件下载 |
| `PLUGIN_ID/VERSION` 等 | 109-113 | `astrbot_plugin_xbbot` / `0.7.28`，主菜单尾行版本同源 |
| `_MAIN_MENU` | 117 | 复用 `router._MAIN_MENU`，core 挂了才用硬编码兜底 |
| `_ENGINES` | 135 | 10 引擎模块单例，防每消息重建 |
| `handle()` | 141 | 薄包装，转调 `router.handle` |
| `_load_api_handler` | 158 | 双通道导入 API 函数（包内相对优先，顶层绝对回退） |
| `_XB_API_ROUTES` | 170 | 60 条路由表 `(路径后缀, 方法, 处理器名, 说明)`，改路由只改表 |
| `_XB_WEBDAV_ROUTES` | 232 | 5 条 WebDAV 表，`backup/backups` 双前缀展开成 10 路由 |
| `class XbBot` | 241 | 唯一插件类 |

**`XbBot.__init__`（242）**：归一配置→定数据目录→`ST.init` 建库→持久配置回填→`wd_cfg_restore`→接龙奖励锁死 20 金币→起 `xb-auto-backup` 守护线程（重名不另起，防热重载多线程）→循环注册路由表。

**`_dispatch(event, is_private)`（409，核心中的核心）**：

1. 存 bot 单例、自动填机器人 QQ；
2. 取群号QQ（私聊群号强制 `dm`），空 QQ 直接丢；
3. 群名片同步（变了才写，扔后台 2 线程池）；
4. `@` 段补全、空消息丢、取 `is_admin`；
5. `测试testxb`：非超管全静默；超管拼 8 系统合并转发；
6. `超管列表`：非超管全静默；超管走后台线程查库+30 秒缓存；
7. 主业务扔线程池跑 `router.handle + 坐骑欢迎检查`（主循环零阻塞就靠这句）；
8. 平台动作（禁言/踢人）走 8 秒熔断执行；
9. 发图元组/纯文本四选一发送，异常降级纯文本；
10. 全程异常只记日志不回聊（防刷屏）。

**`_call_api`（737，统一委托，5 种模式）**：60 个 `page_*` 都是它的一行调用——`none` 无参（总览）、`request` 原透（多数）、`req` 严格取参（排行/武器池/日志类）、`get_req` 智能回退（配置读写）、`with_base` 加插件根目录（备份/图片类）、`use_context` 加上下文（仅清退群）、`fallback` 本地兜底（仅 schema/指令表）。异常归一 500。

**后台线程（346）**：`xb-auto-backup` 每 60 秒 `maybe_auto_backup()`，每小时顺带按保留数修剪。

### 1.3 `store.py`（2047行）——唯一存储内核

**职责**：所有数据进出的唯一口。SQLite WAL + 五把锁 + 三级缓存 + 备份防重 + 密钥分存 + 三源投票。

**表结构**（`_SQL_INIT`，173）：`wallet(群,QQ,钱)` / `accounts(群,QQ,data大JSON)` / `groups(群,QQ,data大JSON)` / `redpacks(群,QQ,口令,金额,时间)` / `kv(键,值)`，WAL 模式 + 30 秒忙等待 + 64MB 缓存。

**锁（5 把，各管各）**：

| 锁 | 行 | 管什么 |
|---|---|---|
| `_LOCK` | 113 | 全局写锁，一切落盘必经 |
| `_DB_R + _RLOCK` | 117 | 只读副本，查钱查缓存不排队 |
| `_BACKUP_GEN_LOCK + _IN_PROGRESS` | 1254 | 备份串行+在途复用 |
| 文件锁 `_BackupFileLock` | 1371 | 跨进程互斥（Windows msvcrt / Linux fcntl） |
| `_AT_NAMES_LOCK / _KV_CACHE_LOCK` | 40/1700 | 昵称索引 / KV 内存 |

**主要 API**：`coins_get/coins_add`（钱包，钳制 0~1 千亿）、`txn_two_wallets`（原子转账）、`acct/acct_add/acct_save`（账户键值+脏标记）、`group/group_user/save_group`（群档案，千人群只刷脏用户，1000 人全量 3.44 秒→单人 0.02 秒）、`recall_set/recall_get`（KV，CD/锁/开关全靠它）、`register_name/parse_at`（昵称与 @ 解析）、`rank_batch`（统一排行）。

**备份全流程**（`backup_user_data`，1452）：5 秒内存防抖 → 30 秒跨进程 sidecar 复用 → 在途 90 秒等待复用 → 60 秒节流 → 开关+间隔（默认 3 小时）→ **共享时钟收敛**（内存/DB/目录三取最大，多进程同节拍）→ 空库拒备 → 文件锁预约 → 落配置 → 按天目录 `xbbot_年月日_时分秒.db` 独立读连接冷备 → 更新时钟+写 sidecar+清 busy → 按保留数删旧 → 异步传 WebDAV。

**防重三件套**：`.xb_last_backup.json`（最近备份，跨重载共享）+ `.xb_backup.busy`（在途中，120 秒新鲜）+ `.xb_backup.lock`（互斥）。删哪个都不心疼，会自己长回来。

**密钥分存**：WebDAV 地址/用户名/密码只存数据目录独立 `webdav_secret.json`，运行时 `cfg()` 透明叠加，DB 镜像/快照/备份/导出永远不含；密码框留空=保持不变。

**三源投票**：内存/文件/DB 镜像三方对账，文件==镜像≠内存时以持久侧覆盖内存，专治“重启后配置变回旧值”。

### 1.4 `verify_plugin.py`（119行）——交付自检

5 项：`metadata` 必填字段 → 全 `.py` 语法解析 → **9 处版本号强一致**（metadata/main/updater/users/superadmin/index.html/app.js/CHANGELOG/README）→ schema 每项有 type → 武器图片文件数。发版/改完必跑，贴 ALL OK。

### 1.5 `_conf_schema.json`——29 节 901 项配置字典（v0.7.29 起；删 9 查询前为 4797 行 928 项）

所有可调项的家。每节 `{type, description, items: {键: {type, default, description}}}`。29 节见 §5.6（WebUI 章节里有全表）。三大动态节：`指令启用配置` 215 开关（默认真）、`指令回复配置` 215 场景（默认空）、`指令权限配置` 215 位（默认所有人，30 键默认超管）。

### 1.6 `scripts/` 与根文档

- `scripts/stress_24h.py`（197行）：三阶段压测——接龙 30 秒自愈+冒险过期+双钱包守恒 → 16 线程×300=4800 条混合消息（零 DB 关键字泄漏、p95<500ms）→ 80 并发 Web API 零失败。
- `scripts/test_fix.py`（94行）：四项历史回归（冒险长叙事/精灵用户链/导出链路/超管对齐；其中 2 条是 HEAD 陈旧断言，已知）。
- `CHANGELOG.md`（425行）：v0.7.x 逐版更新日志。
- `README.md`（112行）：对外介绍 + 当前版特性。
- `.gitignore`（61行）：标准忽略。

---

## 2. `core/` 核心层：路由、配置、平台、云

### 2.1 `core/router.py`（672行）——11 层指令流水线

**链路顺序**（`handle`，519）：总开关（含超管，最高优）→ 群开关（含超管）→ 维护（拦非超管）→ 私聊直走 chat → 主菜单 → 自定义（最长命中）→ **禁用拦截**（给提示）→ **超管权限拦截**（非超管直接静默）→ 8 引擎轮询 → 超管 → 无命中回空。

**四元索引**（`_custom_idx`，330）：`cmds` 自定义触发词 / `dis` 值为假的禁用键 / `ovr` 非空的回复键 / `adm` 值为超管的权限键，全部按长度降序（首命中即最长），`_CONFIG_VER` 命中零开销，另有内容指纹防 stale。

**空格无关 vs 精确**：`_norm_cmd`（38，去内部空格）只用于内置三表（禁用/权限/回复/引擎匹配）——`查询坐骑≡查询 坐骑`；**用户自定义触发词保持精确匹配**，一个字都不归一。

**守卫**：系统总开关 + 按群开关 + 5 秒/2 秒两级缓存；超管直放。引擎异常分级：DB 关键字→“繁忙稍后重试”，其他→“处理异常（原因）”，没命中的引擎静默跳过。

**函数全表**：`_resolve_reply:28` 占位符替换 / `_norm_cmd:38` 去空格 / `apply_reply_override:47` 回复覆盖（索引降序首命中即最长）/ `_sys_off:97` 群开关 / `_cfg_sys_off:126` 全局开关 / `_guard:148` 双层守卫 / `clear_guard_cache:159` / `_batch_guard_map:171` 9 引擎批量守卫 / `_engine_cache_ver:199` mtime 节流 / `_get_engine_cmds:230` 指令缓存 / `_matches_engine:264` 唤醒精确+指令规范前缀 / `_multi_reply:286` 多选一 / `_render_vars:294` 变量渲染 / `_custom_fp:332` 四表指纹 / `_custom_idx:353` 四元索引构建 / `_custom_cmd:413` 自定义精确最长（用户触发词不归一）/ `_cmd_disabled:459` 禁用 / `_cmd_need_admin:489` 权限（空直接放行）。

### 2.2 `core/config.py`（234行）——归一 + 指令采集器

`_normalize_cfg`（29，把 `节__键`/嵌套/裸值三种形态统一成 `{节:{键:值}}`）、`_load_schema`（65，读 schema 文件转分组+默认值两表）、`_collect_commands`（106，**206 条规范指令的唯一来源**，v0.7.29 起；删 9 查询前为 215 条）：扫 10 引擎源码的 `startswith/==/in/_need/_ADMIN_CMDS` 字面 → 去注释 → 去内部空格 → 扔噪音（`我要/自我/开始/加入/退出`是否定守卫里的路由词、单字选项`一/二/三`作开关会误伤）→ 去重 → 前插唤醒词。注意：`slave._QUERY_SILENT` 刻意用变量引用 + 避开 `_need/_ADMIN_CMDS/_ROUTE_EXACT` 命名，使 9 退役查询不被收录。

### 2.3 `core/platform.py`（415行）——消息链与平台动作

`_build_chain`（34）：纯文本 0ms 直回；引擎发图一律 `(文本, [绝对路径])` 元组（禁拼 CQ 字符串，中文路径在适配器侧不稳定）；CQ 解析只为兼容用户自定义回复保留。`_append_at_segments`（103）：补 @ 段 + 名片后台落盘。`_name_prefix`（199）：`[昵称]` 前缀，已有不 double。`_do_platform`（268）：禁言/踢人，8 秒熔断 + 双向鉴权（自己不是管理不能执，对方是管理不能动）。`bind:17` 外部注入 Image 类防循环导入。`fetch_group_member_qqs:357` 多适配器拉群成员（退群清理用）。

### 2.4 `core/webdav.py`（580行）——纯标准库 WebDAV

零第三方依赖，只用 `urllib/ssl/ET`，坚果云/Alist/Nextcloud/群晖通用。`OPTIONS` 轻探测优先（防 429）→ `PROPFIND` 回退；`MKCOL` 递归建目录（内存去重再防 429）；上传 PUT 成功后异步按保留数修剪远端（只删 `xbbot_*.db`，留新删旧）；下载 `.part` 原子替换；时间统一上海时区中文显示。

**函数全表**：`format_shanghai_time:21` 三源时间格式化 / `is_enabled:69` 开关+地址门控 / `_clean_url:78` 补 https / `_get_auth_header:87` Basic / `_make_ssl_context:92` 兼容自签（有 MITM 风险，已知）/ `_ensure_remote_dir:103` 逐级建目录 / `upload_backup:132` 同步 PUT / `test_connection:204` 双探细分 401/403/404/429 / `async_upload_backup:271` 后台线程 / `list_remote_files:284` 按名降序（时间戳天然有序）/ `download_remote_file:402` 防穿越+原子落盘 / `delete_remote_file:484` 404 幂等成功 / `prune_remote_backups:531` 留新删旧 / `async_prune_remote_backups:567` 后台线程。

### 2.5 `core/dispatch.py`（81行）+ `core/test_harness.py`（627行）

dispatch 是旧导入兼容垫片（重导出探针表+超管列表）。test_harness 是 `测试testxb` 探针矩阵：`_TEST_PROBES:15`（2~9 号分系统、1~8 单指令、all 全量）→ `_setup_user:77`（虚拟富/贫用户：满钱满体满球 vs 三空，精灵/坐骑/帮派/奴隶/监狱全预置）→ `handle_test_probes:344`（执行+群合并转发+事后删档）→ `handle_admin_list:565`（超管列表查询）。超管可用，非超管静默。

### 2.6 `core/logger.py`（194行）+ `core/en_map.py`（194行）+ `core/api/helpers.py`（244行）

日志：`logs/xb.log`，2MB 轮转只留 1 备份（`_rotate_if_needed:59`），读只读尾部 512KB/1000 行（`get_logs:123` 逆向块读+级别/关键字过滤），`clear_logs:104` 留一条“已手动清空”。中英映射：`BASE_CN_TO_EN:6` 账户键英文化 + `PROP_CN_TO_EN:78` 道具拼音化，显示仍中文，`cn_to_en:171` 热点 LRU 4096。helpers：取 query（`get_req_query:56`）/取 JSON（`get_req_json:98` 七阶兼容）+ 统一报错 + 禁缓存头 + 三通道文件下载。

---

## 3. `core/api/` 网页接口层：68 接口一览

> 全挂在 `/astrbot_plugin_xbbot/…` 下（WebDAV 另有 `backup/`+`backups/` 双前缀别名）。耗时的一律 `asyncio.to_thread`，不堵消息循环。（异步=后台线程执行，不卡群聊）

| 文件 | 接口与函数 | 作用 |
|---|---|---|
| `stats.py` | `stats`→`handle_stats:18`（异步）、`rank`→`handle_rank:54`（异步） | 总览聚合（小库兜底重算存款）/ 5 维排行（昵称批量预取防 N+1，fetch_card 已移除） |
| `analytics.py` | `analytics/overview`→`handle_analytics_overview:16`（异步+3 秒缓存） | 大屏：三表 SQL 聚合（钱包/银行/奴隶/签到/精灵）+ 财富四阶 + 伪 24h 曲线 |
| `users.py` | `users`→`handle_users:49`（异步）/`user/edit:119`/`user/clear:567`/`user/export:??`/`user/import`/`users/export:234`/`users/import`/`clean_left`/`airdrop:661`（集目标+批量双异步） | 分页列表 / 单改（差值语义）/ 单导（b64）/ 全量导 / 退群清理（平台活名单为准）/ 单清 / 空投（单事务批量+脏缓存降级逐发） |
| `groups.py` | `groups/list:12`（异步）/`toggle:47`/`delete:86` | 总开关 + 按群开关列表/切换/删除 |
| `config_api.py` | `config/schema:20`/`get:39`/`save:59`、`commands`、`config/auto_balance:437`（备份+校准双异步）、`config/balance_state` | schema 下发 / 配置读写（WebDAV 密钥分流：密码留空=不变）/ 指令采集 / **三档智能平衡**（标准/休闲/硬核+真备份+身价联动校准）/ 漂移检测（13 签名键） |
| `game.py`（3 重接口 v0.7.30 起异步，其余同步毫秒级） | `slave/users:23`/`calibrate:139`、`spirit/users:197`、`spirits:308`、`spirits/save:336`、`gacha/weapons:414`、`weapons/pool`+`rename/move/delete/upload/img/attrs/replace_path` | 奴隶画像（身价≤0 自动补）/ 校准 / 精灵画像（战力公式）/ 图鉴三键读写（入库清洗脏条目）/ 武器名对照 / **池文件管理**（改名/移稀有度/删除/上传/单图预览/属性另存/内置选图） |
| `images.py` | `list:36`（异步）/`upload:74`/`delete`/`rename`/`mkdir`/`copy`/`thumb`/`export:291`（异步） | 插件根为牢笼的文件库；上传 base64 双受理；预览单张≤200KB；导出 zip 硬排除备份/DB/密钥 |
| `backup.py` | `backups/list:40`/`restore:86`（异步）/`delete`/`export:164`（异步）/`doctor:261`（双异步）/`prune`、快照 3 个、`backup/webdav/*` 5 个×2 前缀（异步）、`admin/clear:214`（异步，需双重确认） | 列表禁自动触发 / 热恢复清三缓存 / 体检锁内只查+VACUUM 锁外 60 秒熔断 / 远端下载验 SQLite 魔数+归档 |
| `legacy.py`（全同步，大包慎点） | `import/legacy:334` | 旧库导入：db/ini/json/zip 四态，群号 QQ 推断，中英键翻译，文件读兼容各种编码 |
| `logs.py`（v0.7.30 起异步） | `logs:20`/`clear:47`/`export:58` | 日志分页查 / 清 / 导出（JSON 包文本） |
| `updater.py` | `version/check:160`（异步+成功 5 分钟/失败 1 分钟缓存+在途共享，v0.7.30 起） | 双通道（3 源码镜像+Releases API，最坏 10 秒）择优 + **纪元算法**（0.7.x 恒大于旧版） |

---

## 4. `engines/` 业务引擎：10 个玩法 + 3 个数据库

> 统一入口 `handle(gid, qq, raw)`，返回 文本 / `(文本, [图])` / None。`gid` 分群隔离。

### 4.1 `slave.py`（2281行，最大文件）——奴隶买卖 RPG + 抽奖 + 排行 + 昵称中枢

指令：奴隶系统/我的信息/查询（@QQ/昵称/我）/补偿/买下/折磨/保护/释放/赎身/我要自由/买奴隶位/打架/抽武器/十/三十/五十连抽/升星/升阶/打工/收工/造反/讨好/学习/祈福/武器菜单/宝物菜单/身价榜/签到榜/排行榜/直接发武器宝物名查详情。

**入口链**：`handle:1852`（包 try，尾部统一 `save` 落盘，元组带图也落盘）→ `_route:1882` → `_cmd_lock` 串行 → `_route_locked:1889`（分群开关假直接回空；`_ROUTE_EXACT:1867` 精确快路；`store.wake` 唤醒）。

**函数全表**：

| 函数 | 行 | 作用 |
|---|---|---|
| `cmd_menu` | 640 | 回菜单文本 |
| `cmd_myinfo` | 644 | 全量档案：资产/存款/身价/体力魅力奖券经验/主人保护/签到/武器星级/宝物/奴隶数；机器人QQ拒绝；异常兜底完整版 |
| `cmd_query` | 756 | 空给“你要查询谁”，机器人QQ拒绝，否则自动建档展示 |
| `cmd_compensate` | 765 | 打赏转账：打赏间隔 CD + 打赏上限 10000 + 余额校验 |
| `cmd_buy_slave` | 786 | 买奴隶：验存在/非己/非机器人/未被他人拥有/主人不是己/保护中/槽位/余额/购买间隔；成交涨 1.25 倍，旧主获利 |
| `cmd_torture` | 856 | 折磨：单奴隶 300 秒被折磨 CD + 折磨间隔 CD，成功率 75，四类事件按概率叠加 |
| `cmd_protect` | 926 | 保护：仅主人，已保护拒绝，保护间隔 CD，时长 12 小时费用 1000 |
| `cmd_release` | 957 | 释放：仅主人，释放间隔 CD，清主人/保护 |
| `cmd_ransom` | 976 | 代赎他人：空/自己转自赎，赎身间隔 30，价=身价×1.5 |
| `cmd_freedom` | 1002 | 自赎：自由间隔 30，价 1.5 倍，不足提示差额 |
| `cmd_buyslot` | 1024 | 买槽位：上限 15，价=`5000×2^(现有-5)` 指数翻倍 |
| `cmd_flatter` | 1072 | 讨好主人：需有主+间隔 CD+身价不超主人，概率 80，赏 `50~min(主人钱,500)` |
| `cmd_study` | 1110 | 学习：间隔 CD，学费 100~800（主人付/无主自付），经验 20~150，6% 出宝物 |
| `cmd_pray` | 1161 | 祈福：中午12点后+日一次+间隔 CD，15% 爆 30000 / 25% 丢 50~300 / 30% 奖 1000~6000，否则半档 |
| `cmd_work_dispatch` | 1200 | 打工派发：每奴 `w=100~500+身价//50` 快照，需有奴隶 |
| `cmd_work_collect` | 1225 | 收工：到点结算，工资比例 50，奴隶得、主人得总额减已付，新买无快照跳过 |
| `cmd_revolt` | 1267 | 造反：间隔 CD，需 `max(500,身价//10)` 费用；酒神葫芦攻必胜/守必败；否则镇压判定+20% 险胜，抢 500~5000 |
| `cmd_fight` | 1373 | 奴隶群战：验主奴/敌奴/恢复 CD/3 倍拒战/注金，上限 5 万；5 星暴击战力翻倍，胜率=战力比，胜夺奴/赎金 |
| `cmd_gacha` | 1504 | 抽武器 1/10/30/50 连：空池拒→扣费→R50/SR38/SSR2掷骰→SSR新的入库/重复转经验，R/SR聚合转经验，返回图文元组 |
| `cmd_starup` | 1597 | 升星 0→5：需同名武器 lv+1 张/费 5555/率 50%/经验 999（键按一..五星），失败扣材扣经验 |
| `cmd_treasure_up` | 1635 | 宝物升阶 0→3：需阶数+1/费 77777/率 50%，失败只扣材 |
| `cmd_weapon_menu` | 1739 | 武器图鉴：SSR 池+商城合并，显攻击+配装+持有星级+价格+缺图标记 |
| `cmd_treasure_menu` | 1790 | 宝物图鉴：持有数+阶数+效果 |
| `cmd_rank_price/sign/rank` | 1815/1826/1847 | 身价榜/签到榜/双榜拼接 |

**查询静默守卫**（v0.7.29 起；此前为查询转发：`查询更新/版本→更新检测`、`查询维护→维护信息`经超管转发、`查询坐骑/精灵/帮派/冒险/地图→放行`，已全部退役）：`查询更新/版本/维护/坐骑/精灵/帮派/冒险/地图/菜单` 一律静默 `None`（空格无关；此前更新/版本越权转发与全静默红线冲突，查询菜单无空格版/查询地图有空格版漏放行会误查用户，顺带修复）。其余查询：空/我查自己、余下三级反查（分群精确→全局→AT→档案）。

**昵称体系**（183）：分群表（真相）+ 全局表（兜底）+ 反向索引 O(1) + 上限淘汰；`set/get/clear_note_name`、`find_qq_by_name`（精确 O(1)，模糊限本群）、`fetch_card`、`mark_known`，全引擎共用。

**武器池**：`_gacha_pool` 四目录候选 + 60 秒缓存；`_weapon_attrs_raw` 读商城属性、旧商城只读；`_sync_weapon_shop` 已退役空函数；抽中配图，详情图文元组。

**宝物效果链**：名单=设置.宝物+旧 treasure 去重；效果优先级 自定义 > 酒神/四象专属 > 通用镇宅；战斗四象盾免夺、造反酒神攻守必胜必败。

### 4.2 `bank.py`（1114行）——银行 + 监狱

指令：银行系统/存款/强制取款/取款/转账/赌博/打劫银行/打劫/发红包/抢红包（或直发口令）/进监狱/出狱/越狱/劫狱/保释/自我保释。入口 `handle:1013` 先解析 @ 目标和末尾数字金额。

**函数全表**：

| 函数 | 行 | 作用 |
|---|---|---|
| `cmd_deposit` | 307 | 存款：耗体力 1，先结旧息再转入，提示利率与 1 小时期限 |
| `cmd_withdraw` | 351 | 取款：本金减、利息照发，未到期也给取并明示潜在利息 |
| `cmd_force_withdraw` | 391 | 强取：无息、不重置计时，原子到账 |
| `cmd_transfer` | 414 | 转账：@昵称/CQ/QQ/纯名全兼容归一，最小 50、耗体力 2、单笔上限 1 千亿，接收方爆 cap 截断 |
| `cmd_gamble` | 488 | 赌博：100~10 万、耗体力 10、日 5 次，成功率 60% 赢 1.8 倍，败扣魅力 20、50% 蹲 5 分钟，同事务 |
| `cmd_rob_zone` | 566 | 打劫银行：耗体力 5、间隔 10 分钟，本群随机受害人（v0.7.30 起有界 `RANDOM() LIMIT 8`+自过滤，仍均匀），成功率 70%，抢 6000~12000，败罚 500+魅力 3+蹲 5 分钟 |
| `cmd_sell_slave` | 923 | 打劫个人（名存实亡的老名字）：双方余额门槛+体力 20+CD，成功率 65%，抢 1000~10 万 |
| `cmd_redpack` | 627 | 发红包：2000~1 千亿、耗体力 2、间隔 60 秒，口令随机 5 位或自定义 |
| `cmd_recv_red` | 699 | 抢红包：禁自抢/重复，耗体力 1，抢总额 1/20~1/3，魅力+11 |
| `cmd_bail` | 801 | 保释/劫狱/自保释三合一：劫狱免费耗体力 5，保释随机 5000~10000+体力 15+魅力 20 |
| `cmd_out_jail` | 856 | 出狱：到期自动释，未到期指路越狱/保释 |
| `cmd_jailbreak` | 867 | 越狱：15 秒间隔+单次 10 次上限，耗体力 5，成功率 25%，失败只扣魅力不加刑 |
| `cmd_go_jail` | 903 | 主动蹲 10 分钟+体力 10，日限 8 次（银行配置.进监狱次数，三档皆 8） |

**利息公式**：`利息=存款×利率3%×min(1,经过小时数/1小时)`，上限 10 万。打劫金额=`min(受害人持有, 随机区间)`——受害人穷就少抢，是设计不是 bug。

### 4.3 `ent.py`（1160行）——娱乐会话游戏

指令：抽签/扔炸弹/开始接龙/加入/当前/结束/重置/退出接龙/开始急转弯/猜字谜/猜数/答题/二四点/猜拳/退出系/接龙进度。入口 `handle:582` 先自愈再分发，作答走 `_play:863`。

**函数全表**：

| 函数 | 行 | 作用 |
|---|---|---|
| `cmd_bomb` | 518 | 扔炸弹：需 30000+体力 20，1~2 个，70% 禁言 5~10 分钟（真执行平台动作），败扣魅力 5 |
| `_start_24` | 566 | 二四点开局：扣费 + 生成必可解题目 + 写盘 |
| `_join_game` | 874 | 通用加入：无主拒、开局超 30 秒拒 |
| `_quit_game` | 893 | 通用退出：开局者退=整局解散 |
| `_play` | 921 | 作答分发：答题/字谜/急转弯/猜数/二四点/接龙六分支，30 秒超时清局发奖 |

**单群单局 + 30 秒自愈**：`ent_game_群` 存 owner/players/start；超时局自动清；重置/结束秒释；接龙奖励 20 金币 + 0 魅力锁死。抽签按点数分大吉 888/上签 388/中签 88；猜拳 50% 胜率；二四点须用全题数且等于 24（安全求值禁幂运算）。

### 4.4 `sign.py`（634行）——签到成长

指令：签到（/打卡）/抽奖/买体力魅力/新手礼包/点赞/财富榜/签到榜/体力榜/魅力榜/个人排行。入口 `handle:598`，排行优先防误判。

**函数全表**：

| 函数 | 行 | 作用 |
|---|---|---|
| `cmd_sign` | 60 | 签到：重复拒；连签=昨天续+1否则 1；现金 base+连签加成×min(连签,30)；体/魅/券三属性批量到账；同步 slave + 每日顺序号 |
| `cmd_personal` | 150 | 个人信息：优先委派 slave 全量档案，兜底美化版 |
| `cmd_draw` | 191 | 抽奖：1~999 连抽，券不足拒，中奖率 70% + 5 连保底，现金/体力/魅力三选一 |
| `cmd_gift` | 260 | 买体力（30/点）/魅力（3/点），单次 999，现金不够存款自动抵 |
| `cmd_newbie` | 288 | 新手礼包：一次，现金+体力+魅力+奖券单事务 |
| `cmd_like` | 327 | 点赞：日一次，+5 并累计 |
| `cmd_rank` | 341 | 榜分发：财富=现金+存款，其余直取，批量 Top10 |
| `cmd_mine_rank` | 522 | 个人排行：一次取数算四列排名，失败逐榜回退 |

### 4.5 `spirit.py`（801行）——精灵宝可梦式

指令：领养精灵/礼包/我的精灵/查看精灵/精灵商城/买东西/精灵地图/查看地图/背包/精灵冒险/使用精灵球/出战/回收/携带/丢弃/进化/对战/挑战/排行。入口 `handle:728`，异常吞成“繁忙”。

**函数全表**：领养 `cmd_adopt:195`（防重复，已有 list 即视为领养过）/ 礼包 `cmd_gift:216`（一次性，按配置发球和糖）/ 我的 `cmd_my:234` / 查看 `cmd_view:254`（带形象图元组）/ 商城 `cmd_shop:331` / 购买 `cmd_buy:340`（购买坐骑放行给 ride）/ 地图 `cmd_map:386` / 地图详情 `cmd_map_detail:395`（支持序号）/ 背包 `cmd_backpack:407` / 冒险 `cmd_adventure:420` / 收服 `cmd_catch:501` / 出战设置 `cmd_set_active:530` / 出战查看 `cmd_active:539` / 回收 `cmd_cancel_active:547` / 携带 `cmd_ride:556` / 丢弃 `cmd_discard:565`（至少留 1 只，同名只删首只，魅力-10）/ 进化 `cmd_evolve:589`（需等级+耗进化液）/ PVP `cmd_pvp:621`（战力比掷骰，注额=min(2000, 双方余额//10)，零和实扣实给）/ 排行 `cmd_rank:666`（单次查全群取最强一只）。

领养→地图冒险遭遇→扔球收服（概率=球效果−等级修正，大师球必中）→升级自动进化→出战/携带→PVP（战力比掷骰零和）。战力=`等级×(生命+攻击+防御+特攻+特防)÷5`（速度不计）。

### 4.6 `ride.py`（548行）——坐骑

菜单/我的坐骑/坐骑商城/购买/查看/丢弃/切换/设置欢迎/查看欢迎/回收欢迎/携带精灵。购买首购自动设欢迎；丢弃欢迎须先回收；`check_welcome` 进群 3 小时撒一次币（奖励=价格//5000，钳 10~500，缺省 20）。图片新旧目录双读兼容。

### 4.7 `guild.py`（640行）——帮派

帮派列表/排行/我的帮派/创建（限 12 字，耗钱体魅）/加入（限 30 人）/邀请/同意/退出（帮主须先出让）/成员列表/贡献（转帮贡）/修筑/福利（日一次）/帮战（战力比+日 5 次）/管理全套。数据寄存在成员账户里聚合，15 秒成员缓存（v0.7.30 起；成员变更主动失效）。

### 4.8 `adventure.py`（322行）+ `adventure_text.py`（167行）——文字冒险

14 秘境，开局扣体力金钱→`选择N`分支→复活币续命，30 分钟过期。选项 1 偏稳、3 高风险高回报。文本库：14 图长叙事 + 选项标签 + 26 全局事件 + 每图专属事件。

### 4.9 `superadmin.py`（611行）——超管中心

**27 条精确单触发词**（`_ADMIN_CMDS:459`，响应的别名必须同步进表）：群列表/应用统计/扣钱/充钱/清空/重置/禁言/踢人/备份/维护开关三件套/版本/**检查更新**/测试系（testxb/testxb1~8）/超管列表/测试图片/webdav测试。函数：`cmd_groups:105` 群列表 / `cmd_stats:125` 应用统计 / `cmd_deduct:216` 扣钱 / `cmd_recharge:227` 充钱 / `cmd_clear:264` 清空系 / `cmd_mute:332` 禁言 / `cmd_kick:365` 踢人 / `cmd_backup_xb:377` 备份 / `_maint_on/off/msg:405/411/417` 维护 / `_version:426` 版本 / `_cmd_imgtest:463` 双图诊断。

**非超管命中任何一条（含版本更新）一律静默无响应**；禁言踢人走平台元组；测试图片 diagnosis 双图元组。

### 4.10 `chat.py`（73行）——私聊陪聊

关键词命中回复 + 黑名单拦截 + @/# 前缀开关 + 5 秒限频 + 30% 随意回复率。

### 4.11 三个纯数据文件

- `spirit_data.py`（159行）：约 100 精灵六维 + 34 地图掉落 + 12 道具（5 球+强化+进化液），WebUI 自定义优先、空则回退到它。
- `slave_text.py`（283行）：奴隶系统全部文案常量。
- `adventure_text.py`（167行）：14 地图长叙事 + 选项标签 + 26 全局事件 + 每图专属事件。

---

## 5. `pages/admin/` 网页管理台：14 Tab 单页应用

> 无构建，原生 `index.html`（骨架+CSS）+ `app.js`（逻辑）。通信：iframe 桥优先 + fetch 回退；上传一律 base64-JSON（桥传不了 FormData）；弹窗自研（iframe 里原生 confirm 被拦）。

### 5.1 `index.html`（2262行）——14 Tab + 双弹窗

| Tab | 内容 |
|---|---|
| 概览大屏 | 6 KPI + 财富金字塔 + 24h 曲线 + 快捷配置 + 空投/校准/体检/更新 |
| 排行榜 | 5 维度 |
| 用户管理 | 8 维排序 + 单改/单清/导入导出/空投/清退群 |
| 奴隶用户 / 精灵用户 | 身价档案 / 精灵战力档案 |
| 群聊开关 | 总开关 + 按群开关 |
| 必要配置 | 5 个基础节（奖励数值不在此，在指令页逐条调） |
| 指令与玩法 | 206 条指令开关 + 唤醒词 + 自定义 + 回复 + 数值 + 超管锁 |
| 商城 | 坐骑栏 + 武器池栏 + 道具栏（各存各的） |
| 图鉴 | 武器/宝物/坐骑/精灵总览（改动即时存，只动各自范围） |
| 备份管理 | 本地备份 + WebDAV + 快照 + 旧库导入 |
| 根目录浏览 | 文件管理器 + 内置选图 |
| 运行日志 | 实时日志 + 级别过滤 |
| 关于 | 版本 + 仓库 |

弹窗：`#cmdModal`（指令编辑器：启用/超管锁/触发词/映射/回复/数值）、`#appModal`（通用确认/输入/平衡弹窗等复用）、`#lightbox`（看图）、`#toast`（提示）。CSS 断点 960/768/640，移动端单列。

### 5.2 `app.js`（约5450行）——按模块函数索引

- **桥接**：`getBridge:26`（桥优先+fetch 回退+前缀缓存）、`callApi:187`（GET 失败回退 POST）、`postFile:879`（base64 直传）、`uploadImage:885`、`triggerDownload:330`（三级下载破沙箱）。
- **弹窗**：`toast:166`、`uiAlert:453`、`uiConfirm:504`（危险词自动红按钮）、`uiPrompt:562`。
- **Tab 调度**：`bindTabs:897`（懒加载一次，概览每次重刷）、`TAB_LOADERS:710`（14 页→加载器映射）、`main:731`。
- **总览/排行/用户/群聊/日志/大屏**：`loadStats:973`、`loadRank:1337`、`loadUsers:1383`（8 维排序+单改单清导入导出空投）、`loadGroups:636`、`loadLogs:5182`（3 秒轮询，v0.7.30 起无变化跳过重渲染）、`loadAnalytics:4665`、`openAutoBalanceModal:1168`（三档弹窗，X/背景可关、失败可重试）、`saveConfig:1276`、`resetConfig:1304`（只动本页渲染节）、`resetAllConfig`（v0.7.29 新增：跨节恢复数值/开关设置，白名单排除备份/商城/图鉴/自定义/群开关，不动用户数据）。
- **指令页**：`loadCommands:1799`（分系统渲染 ●/🔒）、`openCmdEditor:1902`（启用+超管锁+触发词+映射+回复+数值）、`renderCmdNums:1944`（手配表优先，否则按系统关键词精准匹配前 6）、`saveCmdEditor:1978`（收开关+唤醒词+自定义+启用/权限/回复+数值）、`CMD_NUMS:1683`（40+ 手配）、`CMD_ENG/ENG_NUM_SECTIONS`（所属系统映射）。
- **商城三栏**：`renderShopRideBox:3348`（改名改价绑图，添加置顶，保存只写 ride_shop）、`renderPoolBox:3011`（SSR/SR/R 折叠+懒加载缩略，添加置顶）、`renderShop:2553`（道具类型下拉，添加置顶）、`loadShops:3813`（单次图鉴渲染）、`savePoolAttrs`、`openRideAddModal/openPoolAddModal/openShopItemAddModal/openSpiritAddModal`（四个添加弹窗，内外双上传）。三栏标题 v0.7.29 起只留“X商城 — N 件”；保存/恢复 v0.7.31 起与添加同栏置顶，坐骑独立小保存（`saveRideOnly`），顶部 `saveShops` 为全部保存（三栏各存各的）。
- **图鉴**：`loadSpirits:2101`（三态合并）、`renderAtlas:3594`（四分类总览）、`bindSpiritMapCards:2275`（整块事件委托一次绑定）、`saveSpiritKind/resetSpiritKind`（地图属性合并存、道具独立）。
- **备份**：`loadBackups:4001`、`renderBackups:4020`、`btnBackupNow`（立即冷备）、WebDAV 测试/上传/远端分页/恢复/删除、保留数一键修剪。
- **根目录**：`loadImages:755`、`renderImages`（内置选图模式）、`showLightbox` 看图。
- **关于**：`checkVersionUpdate:4928`（20 秒熔断）。

### 5.3 `_conf_schema.json` 29 节速查

设置/费用/间隔/概率/祈福（奴隶数值）/签到/抽奖/新手/点赞/银行/娱乐/私聊/精灵/坐骑/超管/帮派/冒险/唤醒词/`指令启用`215/`指令回复`215/`指令权限`215（30 默认超管）/自定义指令/商城图鉴/精灵图鉴/备份/总开关/群组开关/维护/系统开关。

---

## 6. 数据目录 `data/`、交付、排障

### 6.1 `data/`（运行时，备份只收 `.db`）

`config.json` 持久配置快照；`img/gacha/{SSR,SR,R}` 武器图=池本身；`img/rides` 坐骑图；`img/spirits` 精灵图；`backups/日期/xbbot_*.db` 本地备份 + `.xb_last_backup.json` 防重文件（正常，无需删除）。

### 6.2 发版流程

`verify_plugin.py` + `stress_24h.py` + `node --check app.js` 三自检（贴 ALL OK）→ 打包脚本改 VER 生成三端 zip（仓库根/`astrbot_plugins`/`backup`）→ `push main` + `tag vx.y.z`。纯文档提交只 push。

### 6.3 排障一句话

群不回看三开关；接龙卡用重置/结束（30 秒自愈兜底）；WebDAV 401 用应用密码、429 拉长间隔；云端文件少是“只删不增”正常现象；非超管发超管指令没反应是**正常设计**；打劫金额看受害人钱包；上传失败看浏览器控制台回执。

---

*（全文完。与代码不一致处以代码为准，欢迎对照行号逐条验证。）*
