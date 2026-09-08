# 小白机器人 (astrbot_plugin_xbbot) — 核心速查与环境状态卡 (AIINFO)

## 📌 项目基本元数据

| 项目属性 | 当前值 |
| :--- | :--- |
| **插件名称** | `astrbot_plugin_xbbot` (小白统一模块) |
| **当前版本** | `v0.7.12` (已发布并在 GitHub 与本地保持对齐) |
| **项目作者** | Light (`faxlight@faxt.top`) |
| **开源仓库** | `https://github.com/imsuperone/xb` |
| **经济基线 (v0.68.28)** | 接龙 20金币+0魅力全局锁定；WebDAV 持久兜底防丢 |
| **主代码目录** | `c:\Users\Light\Desktop\DRxb\astrbot_plugins\astrbot_plugin_xbbot` |
| **离线发行包** | `C:\Users\Light\Desktop\DRxb\astrbot_plugin_xbbot_v0.7.12.zip` |
| **平台依赖** | AstrBot >= 3.4.0, Python >= 3.10 (支持 3.14t/自由线程) |
| **底层协议端** | OneBot v11 (aiocqhttp), NapCat, Lagrange 原生图文 |

---

## 🚦 系统运行状态与核心机制指标 (至 v0.7.12)

- **Python 模块语法解析**：41/41 语法解析通过 (100%)。
- **版本号命名与迭代规范 (0.7.xx 规范)**：当前基准版本 `0.7.12`，严格遵循 `0.7.xx`（`0.7.0`~`0.7.99`）后置补丁递增规则；仅在补丁位满 99 或用户明确要求时才更迭前段大版本（`0.8.xx`/`1.0.xx`）。
- **9 处版本强一致校验**：每次发版必须同步以下 9 处：
  `metadata.yaml`, `main.py`, `core/api/updater.py`, `core/api/users.py`, `engines/superadmin.py`, `pages/admin/index.html`, `pages/admin/app.js`, `CHANGELOG.md`, `README.md`。
- **图片诊断 (v0.7.12)**：
  - `测试图片` 双路径同发诊断，非超管静默；元组字符串路径加固。
- **图鉴交互 (v0.7.11)**：
  - 总览武器/宝物/坐骑分类切换；孤儿精灵分配进图；添加坐骑表单窗（名称/价格/图片）。
- **商城空白修复 (v0.7.10)**：
  - 商城解析兼容 dict/串/空三形态；精灵用 `_meta.configured` 判定；抽奖池加载隔离。
- **图鉴可用性 (v0.7.9)**：
  - 商城导入导出含武器；孤儿精灵独立成区；自定义宝物通用效果；宝物走保存流；进化下拉；精灵形象图。
- **备份跨进程去重与商城类目 (v0.7.8)**：
  - 文件锁 + busy 预约 + sidecar 30 秒窗口，多进程/重载只出一份；商城预填内置为起点；武器商城接入抽奖池；`商城/图鉴` 分家，可视化工坊删除。
- **图鉴自助与空回退 (v0.7.7)**：
  - `cfg()` dict 走 JSON 序列化，自定义商城生产链路生效；空图鉴自动回退内置；编辑器如实展示 + 删光提示。
- **三件套彻底删除 (v0.7.6)**：
  - 帮派武器/女仆坐骑/起名：引擎/预设/schema/前端零残留（27 节 741 项）。
- **平衡与指令体系 (v0.7.5)**：
  - 一键平衡真备份（`pre_balance_*` 快照 + 冷备）；指令启用/回复播种 236；休闲档预选回显 + 真实文案。
- **性能三连击 (v0.7.4)**：
  - `NOTE_NAMES_REV` 反向索引（@反查精确 O(1)）；大屏统计 SQL 聚合下推；空投批量单事务。
- **备份串行化与双端修剪 (v0.7.3)**：
  - `_BACKUP_GEN_LOCK` + 在途复用根治并发双份；`xb-auto-backup` 线程名单例防重载累积；`backups/prune` 按保留数修剪本地 + 云端（仅 `xbbot_*.db`）；云端列表 10 份/页。
- **分群昵称隔离与删除用户修复 (v0.7.2)**：
  - `NOTE_NAMES_BY_GROUP[(gid, qq)]` 根治多群同人串昵称；WebUI 删除用户改用 `uiConfirm/uiPrompt` + 统一事件委托。
- **WebDAV 中文日期与上海时区 (v0.7.1)**：
  - `format_shanghai_time(dt_str, filename)`：解析 RFC 1123 HTTP-date / ISO 8601，转换为标准 UTC+8 上海时区中文日期（如 `2026年09月06日 13:25:30`）。
  - 内置文件名正则提取兜底策略（自动从 `xbbot_YYYYMMDD_HHMMSS` 推导）。
- **WebDAV 云端归档直接物理删除 (v0.7.1)**：
  - `delete_remote_file(remote_name)`：纯标准库 HTTP `DELETE` 远端物理删除。
  - WebUI 集成 `uiConfirm` 二次危险确认与 `⏳ 删除中...` 忙态，删除成功即时无感热刷新列表。
- **版本比较纪元引擎 (v0.7.0)**：
  - `(epoch, major, minor, patch)` 算法：历史版本 `0.10.x`~`0.68.x` 划入旧纪元 `epoch=0`，`0.7.x` 划入新纪元 `epoch=1`，彻底杜绝云端旧版倒流误判。
- **全局模态弹窗 Emoji 智能去重 (v0.7.0)**：
  - `_normalizeModalTitleAndIcon` 自动剥离标题中的前导 Emoji，根除所有双重图标堆叠（`🚀 🚀`、`✅ ☁️`、`⚠️ ❌`、`ℹ️ 🩺` 等）。
- **WebDAV 远端归档展示与热恢复 (v0.7.0)**：
  - PROPFIND Depth 1 XML 解析远端目录，WebUI 备份卡片直接查看云端备份、一键快捷热恢复与本地下载。
- **彻底根除双份备份 (v0.7.0 → v0.7.3 串行锁升级)**：
  - `_BACKUP_GEN_LOCK` 串行锁 + 在途备份等待复用 + `xb-auto-backup` 线程名单例，杜绝并发/重叠/重载累积生成多份冗余备份。
- **WebUI 视觉反馈与自愈 Toast (v0.7.0)**：
  - 补全 `#toast` 容器 DOM，按钮点击即刻进入忙态锁定，弹窗具备明确确定/关闭按钮。
- **WebDAV 频控与 DB 自包含 (v0.68.36)**：
  - OPTIONS 轻量探测根治 HTTP 429；DB `kv` 表自包含全部 28 大系统配置与用户资产。
- **插件桥接与 Quart 异步 (v0.68.35)**：
  - 彻底根治 `Plugin bridge endpoint is invalid.` 与 `未能读取到有效配置数据(请求体为空或解析失败)`。
- **检查更新全方位回显 (v0.68.34)**：
  - 检测按钮直显状态，jsDelivr CDN + GitHub API 双通道 1.5s 极速响应，带防缓存时间戳 `?_t=...`。
- **24h 等效压测 (`scripts/stress_24h.py`)**：
  - 4800 ops 群聊风暴 p50 9.38ms，DB 零泄漏零逃逸异常；WebAPI 80/80；接龙 30s 自愈与资金守恒断言 100% 通过。
- **主事件循环延迟 (Lag)**：0ms 纯内存极速分发（已根除旧版 56s 阻塞）。
- **配置项定义模式**：28 个系统，298 个配置项解析通过 (100%)。
- **WebUI 前端元素检查**：179 个 DOM ID 无重复；58 个 API 端点（53 逻辑 + 5 别名兼容）100% 对齐后置路由。

---

## 🗂️ 核心文件及职责速查

| 文件路径 | 核心职责与关键维护点 |
| :--- | :--- |
| `main.py` | 插件主入口。`__init__` 中守护线程 `xb-auto-backup` 运行后台冷备与清理；`_dispatch` 纯内存异步分发（0ms）；注册 50+ 个 Web API；启动时持久配置叠加+接龙奖励锁定 |
| `store.py` | 现代 SQLite WAL 模式。全局锁 `_LOCK`；`clean_old_backups` 默认保留 30 份数据；`_safe_commit` 与 `_safe_rollback` 优雅降级；高频只读副本分离 |
| `core/webdav.py` | 纯标准库 WebDAV 备份客户端。支持 Alist/坚果云/NAS；探测超时 8s，上传超时 25s；PROPFIND 目录解析、上海时区时间转换、DELETE 物理删除 |
| `core/platform.py` | 消息链跨平台构建，原生成分转换，群名片异步后台落盘 |
| `core/router.py` | 统一主路由分发中心，主菜单生成，双分支测试探针，守卫缓存 |
| `core/api/backup.py` | WebUI 备份相关 API。包含 WebDAV 连通性测试、立即云备份、远端文件列表、云备份恢复与物理删除接口 |
| `core/api/updater.py`| GitHub 云端版本检测。纪元比较引擎 `(epoch, major, minor, patch)`，双通道择优，`asyncio.to_thread` 异步执行 |
| `core/api/users.py` | 用户资产、封禁、编辑、清空、一键空投 |
| `pages/admin/index.html` | Web 管理控制台前端骨架。13 大 Tab 视图、深浅色主题、自愈 Toast 容器 |
| `pages/admin/app.js` | Web 控制台核心 JS 逻辑。Bridge 通信、Emoji 去重、WebDAV 测试/上传/恢复/删除、更新检测弹窗 |
| `engines/sign.py` | 签到与新手礼包。原子加币、首签历史记录 GC 纳入全局互斥 |
| `engines/ent.py` | 接龙等娱乐互动玩法。成语接龙 20金币+0魅力全局锁定，全系 30 秒超时自愈机制，支持【重置接龙】、【结束接龙】 |
| `engines/superadmin.py`| 超级管理员指令。支持【测试webdav】、【备份xb】、【清空群数据】等 |

---

## ⚡ 核心数据接口 (Web API) 速查

- **GET `/astrbot_plugin_xbbot/stats`**：全系统游戏资产宏观统计大屏
- **GET `/astrbot_plugin_xbbot/config/get`** & **POST `/config/save`**：配置中心读取与实时保存
- **GET `/astrbot_plugin_xbbot/backups/list`**：本地备份目录结构及文件树
- **POST `/astrbot_plugin_xbbot/backup/webdav/test`**：测试 WebDAV 连通性与账号认证
- **POST `/astrbot_plugin_xbbot/backup/webdav/upload`**：立即执行本地冷备并上传至 WebDAV（5秒防抖）
- **GET/POST `/astrbot_plugin_xbbot/backup/webdav/files`**：读取 WebDAV 远端备份文件归档列表（上海时区中文时间）
- **POST `/astrbot_plugin_xbbot/backup/webdav/restore`**：从 WebDAV 远端备份一键快捷热恢复
- **POST `/astrbot_plugin_xbbot/backup/webdav/delete`**：物理删除 WebDAV 远端备份文件（RFC 4918 DELETE）
- **POST `/astrbot_plugin_xbbot/backups/doctor`**：SQLite 碎片整理 (VACUUM) 与健康体检
- **POST `/astrbot_plugin_xbbot/backups/prune`**：按保留数量一键修剪本地 + 云端旧备份
- **GET `/astrbot_plugin_xbbot/gacha/weapons`**：抽奖武器池（SSR/SR/R 文件名，供武器商城对照同步）
- **GET `/astrbot_plugin_xbbot/version/check`**：云端 Release 与 main 分支更新探测（防缓存双通道）

---

## 🛡️ 应急指令与排障清单

1. **若用户反馈群聊消息完全不回复**：
   - 查看 AstrBot 控制台是否开启了【总开关配置】（发送【开启总开关】）；
   - 查看是否开启了【维护模式】（超管发送【关闭维护】）；
   - 查看群是否被单独关闭（发送【开启本群】）。
2. **若用户反馈接龙卡死**：
   - 在群内发送【重置接龙】或【结束接龙】，秒级重置全部对局状态。30 秒超时自动解锁。
3. **若 WebDAV 云端备份报 401、404 或 429**：
   - 在 WebUI 控制台「备份管理」Tab 点击【☁️ 测试 WebDAV】查看清晰报错；
   - 坚果云需使用专用应用密码（非登录密码）；Alist 路径需以 `/dav/...` 规范填写；
   - 429 报错已由轻量 OPTIONS 嗅探根治，若服务商限制请拉长自动备份间隔（默认 1440 分钟/每天一次）。
4. **若在线更新检测异常**：
   - 前端已集成 20 秒超时熔断保护，无论网络状况均有明确弹窗回显；
   - 纪元引擎已彻底隔离 `0.68.x` 历史版本，绝不会产生降级误提示。
