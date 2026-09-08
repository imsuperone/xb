# 小白机器人 (astrbot_plugin_xbbot) — AI 开发者架构与交接手册 (AIREADME)

> **当前版本**：`v0.7.11`  
> **适用对象**：接手本项目的 AI 编程助手（Claude, GPT, Gemini, DeepSeek 等）与核心维护者  
> **定位**：AstrBot 平台大型统一群互动旗舰插件（奴隶/签到/银行/娱乐/私聊/精灵/坐骑/超管/帮派/冒险 等 28 大子系统 + 现代 WebUI 管理控制台）

---

## 1. 核心架构与模块分层设计

整个插件采用三层解耦与单向依赖设计（`pages/` WebUI → `main.py` 调度入口 → `core/` 基础层 / `engines/` 业务层 → `store.py` 数据层）：

```
astrbot_plugin_xbbot/
├── metadata.yaml             # AstrBot 插件元数据（版本号 9 处强校验点之一）
├── _conf_schema.json         # 28 个系统、298 项配置定义模式，WebUI 与 AstrBot 原生配置渲染驱动
├── main.py                   # 插件 Star 主入口，事件监听分发、50+ Web API 注册、后台定时备份守护线程
├── store.py                  # 现代 SQLite (WAL 模式) 存储引擎，原子事务、内存 LRU/全局缓存、只读副本、自动备份与保留修剪
├── verify_plugin.py          # 语法解析、版本 9 处一致性、配置模式合法性全量自动化校验脚本
├── scripts/stress_24h.py     # 24h 等效压测：群聊风暴+WebAPI 风暴+自愈/守恒断言
├── core/                     # 核心基础设施层
│   ├── config.py             # 配置规范化、双向转换、默认值兜底
│   ├── platform.py           # 跨平台适配、消息链装配、原生成分解析、@提及与名片提取
│   ├── router.py             # 统一指令路由调度机、主菜单生成、子系统分发、自定义指令索引、守卫缓存
│   ├── webdav.py             # 纯标准库零依赖 WebDAV 客户端（支持坚果云/Alist/NAS等，RFC 4918、上海时区转换、DELETE删除）
│   ├── logger.py             # 统一日志收口输出
│   ├── en_map.py             # 中英文字段双向映射表
│   └── api/                  # WebUI 后端 API 端点（12 大 Tab × 50+ 路由，薄路由）
│       ├── backup.py         # 备份列表、恢复、导出、清理、数据库整理体检、WebDAV 测试与云备份、云端文件列表与删除
│       ├── updater.py        # GitHub Releases / main 分支双通道纪元版本检测与在线更新
│       ├── users.py          # 用户资产、封禁、编辑、清空、一键空投
│       ├── groups.py         # 群聊开关管理与状态切换
│       ├── images.py         # 根目录与抽卡图鉴资源文件管理器
│       └── ...
├── engines/                  # 28 大群互动游戏与业务系统
│   ├── slave.py              # 奴隶系统（买卖、打工、折磨、讨好、赎身、身价校准）
│   ├── sign.py               # 签到系统（首签、连签阶梯奖励、新手礼包、点赞）
│   ├── bank.py               # 银行系统（存取款、利息结算、转账、财富榜）
│   ├── ent.py                # 娱乐系统（成语接龙 20 金币+0 魅力锁定、急转弯、猜字谜、猜数字、24点等，全系30秒超时）
│   ├── spirit.py             # 精灵系统（精灵捕捉、图鉴、培养、战力计算）
│   ├── ride.py               # 坐骑系统（抓捕、合成、属性成长、迎新进群播报）
│   ├── superadmin.py         # 超级管理员系统（备份、WebDAV测试、维护模式、清空、封禁）
│   ├── guild.py              # 帮派系统
│   ├── adventure.py          # 冒险系统
│   └── chat.py               # 词库私聊与唤醒词过滤
└── pages/admin/              # 现代化 WebUI 管理控制台
    ├── index.html            # 单页面控制台骨架（13 大 Tab 视图、深浅色模式、自愈 Toast 容器）
    └── app.js                # 前端控制台主逻辑（Bridge 封装、API 通信、Emoji 智能去重、WebDAV 列表/删除/恢复、零静默更新检测）
```

---

## 2. 必须严守的“六大黄金法则”（严防退化 Bug）

在后续迭代或修复时，**切勿违反以下原则**，这是多次线上高并发调优与故障复盘得出的血泪教训：

### 规则一：主事件循环（Event Loop）绝对零阻塞
- **绝不在 `main.py` 的 `_dispatch` 或消息分发路径中调用同步 I/O**！
- 定时备份必须在 `__init__` 中启动的独立守护线程（`xb-auto-backup`）中定期执行；
- 群名片/昵称提取时，先在纯内存字典（`slave.NOTE_NAMES`）中同步更新（0ms），涉及 `ST.register_name` 或 `slave.save(gid)` 的数据库落盘必须切入后台线程或线程池执行；
- 所有网络调用（如 `core/webdav.py`、`core/api/updater.py`）必须设置适度超时（探测 <= 8s，上传 <= 25s），且在 Web API 接口中必须使用 `await asyncio.to_thread(...)` 执行，严防事件循环延迟（如 `Event loop lag detected: 56.067s`）。

### 规则二：禁止在 `_ensure_db()` 中跨线程强行 rollback
- `_ensure_db()` 是全局读写连接的健康探测函数，**绝不可在此处根据 `in_transaction` 强行执行 `rollback()`**！
- 跨线程并发执行时，线程 B 若强行 rollback 线程 A 正在进行的写入，会导致 SQLite 抛出 `cannot rollback - no transaction is active` 并使数据库连接陷入假死。
- 所有事务的回滚只能在具体的业务操作捕获异常后的 `except` 块中通过 `_safe_rollback()` 执行。

### 规则三：底层存储写入全面安全降级，禁止裸调 `raise`
- `store.py` 中的核心操作方法（如 `coins_add`、`acct_save`、`save_group`、`txn_coins_acct`、`flush_all` 等），在捕获异常后必须安全执行 `_safe_rollback()` 并返回安全降级值（如原数值或 False），**禁止向外层重新 `raise` 原始数据库异常**；
- 杜绝群聊前台向普通用户暴露“【系统】处理指令时出现异常（原因: ...）”此类崩溃信息。

### 规则四：娱乐游戏与会话全系 30 秒超时自愈
- 接龙、急转弯、猜字谜等全系互动游戏超时统一设为 30 秒；
- 接龙支持 `【重置接龙】` 与 `【结束接龙】` 指令，任何群员均可发送一键释放对局；
- 30 秒无人作答后，下一条互动指令或 `开始接龙` 自动静默清理并秒级重开，杜绝死锁。

### 规则五：版本纪元演进与 9 处强一致性对齐
- **版本号迭代规范（0.7.xx 序列）**：当前遵循 `0.7.0` ~ `0.7.99` 补丁位递增规则。只有当补丁位达到 99 或用户明确指示时，前段大版本才更新为 `0.8.xx`、`1.0.xx`。
- **纪元比较算法**：在 `core/api/updater.py` 中使用 `(epoch, major, minor, patch)` 算法，将旧版本 `0.10.x`~`0.68.x` 划入 `epoch=0`，新版本划入 `epoch=1`，严防旧版本倒流。
- **9 处版本号强一致**：每次发版必须同步以下 9 处：
  1. `metadata.yaml`: `version: "x.y.z"`
  2. `main.py`: `PLUGIN_VERSION = "x.y.z"`
  3. `core/api/updater.py`: `return "x.y.z"`
  4. `core/api/users.py`: `PLUGIN_VERSION = "x.y.z"`
  5. `engines/superadmin.py`: `ver = "x.y.z"`
  6. `pages/admin/index.html`: `<span class="ver">vx.y.z</span>`
  7. `pages/admin/app.js`: `version: res.version || "x.y.z"`
  8. `CHANGELOG.md`: `## vx.y.z`
  9. `README.md`: `vX.Y.Z`

### 规则六：WebDAV 规范与云端操作安全防线
- **探测防频控**：使用 RFC 4918 轻量 `OPTIONS` 嗅探，禁止无节制发送重型 `PROPFIND`，根除 HTTP 429。
- **时间上海时区规范**：远端归档时间必须转换为 UTC+8 上海时区中文日期（`YYYY年MM月DD日 HH:MM:SS`），禁止向用户抛出原生英文 GMT 串。
- **破坏性操作二次确认**：云端文件删除（`DELETE`）等危险操作必须由前端 `uiConfirm` 二次确认拦截，并在操作期间提供明确的忙态提示与实时无感列表刷新。
- **防重复备份防抖**：`store.backup_user_data` 全程 `_BACKUP_GEN_LOCK` 串行 + 在途复用 + 5 秒路径复用，`xb-auto-backup` 线程名单例防重载累积；立即上传云端传 `auto_upload=False`，严禁连续并发触发生成多份重复冷备。

---

## 3. 存储与并发控制模型 (`store.py`)

- **模式**：SQLite WAL 模式（`PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;`），千群并发读完全并行，写串行化；
- **锁机制**：使用全局互斥可重入锁 `_LOCK = threading.RLock()` 保护所有写事务；高频读（`coins_get`/`recall_get`）走 `query_only` 只读副本 + 独立细锁，不排队等写锁；
- **内存预热与加速**：
  - `kv` 表使用 `_KV_CACHE` 内存字典预热缓存，包含 28 大系统配置与用户资产；
  - 群组与用户配置通过 `_GROUP_CACHE` 维护，采用 `_dirty` 脏标记和 `_dirty_qqs` 增量提交；`group()` 全量解析在锁外执行 + 双检回填；
- **配置三级防丢**：WebUI 保存即写 kv 镜像（含清空语义）→ 启动时文件→DB 逐级回填；全量配置自动快照，备份管理一键恢复；
- **自动备份与清理策略**：
  - 备份目录：`data/backups/YYYY-MM-DD/xbbot_YYYYMMDD_HHMMSS.db`；
  - 自动清理：`clean_old_backups(max_keep=None)`，默认保留最新 30 份（可在配置项 `保留备份数量` 调节），超出自动清除最旧文件并回收空目录；
  - 增量冷备：使用 SQLite 原生 `_DB.backup(bck)` API，支持 `PASSIVE` 检查点。

---

## 4. WebDAV 自动云备份与归档管理 (`core/webdav.py`)

- **实现特性**：零外部依赖（纯标准库 `urllib.request` + `ssl` + `base64`），兼容任意标准 WebDAV 服务端（坚果云、Alist、群晖、Nextcloud 等）；
- **时间处理引擎 (`format_shanghai_time`)**：
  - 支持 RFC 1123 HTTP-date（`email.utils.parsedate_to_datetime`）与 ISO 8601；
  - 转换为 `timezone(timedelta(hours=8))` 上海时区；
  - 文件名兜底正则推导（`xbbot_YYYYMMDD_HHMMSS`）。
- **云端归档管理**：
  - `list_remote_files()`：PROPFIND Depth 1 XML 解析远端目录，输出结构化文件列表；
  - `restore_remote_file(remote_name)`：下载远端归档文件并执行热恢复；
  - `delete_remote_file(remote_name)`：向 WebDAV 发送标准 RFC 4918 `DELETE` 请求，拦截 404/429 并提供友好中文反馈。
- **接口与 WebUI 交互**：
  - Web 控制台「备份管理」Tab 专属卡片：包含开关/地址/账号/目录/间隔/保留数配置；
  - 交互按钮：【☁️ 测试 WebDAV】、【☁️ 立即上传云端】（带 5 秒防抖）、远端归档列表中每个文件的【📥 恢复】与【🗑️ 删除】按钮。

---

## 5. 前端 WebUI 架构与交互设计 (`pages/admin/app.js`)

- **Bridge 通信与降级**：
  - 优先调用 AstrBot 原生 `window.astrabot.callApi`，降级时自动匹配原生 Fetch；
  - 严谨处理 API 基础路径，彻底杜绝带问号或双斜杠的端点异常。
- **Emoji 全局智能去重**：
  - 全局封装 `_normalizeModalTitleAndIcon(title, icon)`：
    ```javascript
    const emojiRegex = /^([\p{Extended_Pictographic}\uFE0E\uFE0F\u200D\u20E3\u2600-\u27BF]|\s)+/u;
    ```
  - 自动剥离 `title` 开头的前导 Emoji，根绝所有模态弹窗图标重复堆叠现象。
- **视觉反馈与防抖锁**：
  - 按钮操作点击即刻置为 `disabled` 并呈现 `⏳ 正在执行...` 状态，彻底避免多次重复点击；
  - DOM 补全 `#toast` 容器，支持非侵入式轻量自愈通知。

---

## 6. 校验与打包发布标准工作流

在提交任何更改前，请在终端执行以下标准流程：

```powershell
# 1. 语法与强一致性自检（确保 41 模块与 9 处版本全部 ALL OK）
python -X utf8 verify_plugin.py

# 2. 24h 等效高并发压测（4800 ops，确保 0 泄漏 0 错误 ALL OK）
python -X utf8 scripts/stress_24h.py

# 3. 前端语法抽查
node --check pages/admin/app.js

# 4. 构建纯净发布压缩包（排除 .git/.github/__pycache__/*.pyc/*.db*/data/backups）
#    同步归档三端：仓库根 / astrbot_plugins / backup 目录

# 5. Git 提交并打 Release 标签推送
git add -A
git commit -m "feat/fix: commit description (vx.y.z)"
git push origin main
git tag vx.y.z -f
git push origin vx.y.z -f
```

---

## 7. 完整版本演进史（v0.68.22 → v0.7.11）

| 版本 | 主题与核心突破 |
| :--- | :--- |
| **v0.7.11** | **总览分类切换；孤儿精灵分配进图；添加坐骑表单窗** |
| **v0.7.10** | **修复商城/图鉴空白：dict 形态兼容、configured 判定、抽奖加载隔离** |
| **v0.7.9** | **图鉴可用性整改：商城导入导出完整、孤儿精灵可见、自定义宝物有效、精灵形象图** |
| **v0.7.8** | **备份跨进程去重；商城默认回显；武器商城接入抽奖；商城/图鉴分家；删可视化工坊** |
| **v0.7.7** | **自定义商城生产链路修复；图鉴空=内置回退 + 入库整形；编辑器如实化与删光提示** |
| **v0.7.6** | **彻底删除帮派武器/女仆坐骑/起名功能（零残留）** |
| **v0.7.5** | **一键平衡真备份可回滚；指令启用/回复全量播种；休闲档真相修复；死键接入与 fallback 对齐；热路径节流** |
| **v0.7.4** | **@反查反向索引 O(1)；大屏统计 SQL 聚合下推；空投批量单事务** |
| **v0.7.3** | **排序统一货币文案；备份串行锁根治双份 + worker 单例；保留数双端修剪 + 云端 10 份/页分页** |
| **v0.7.2** | **根治多群同人昵称串群（分群昵称表隔离）；修复 WebUI 删除用户按钮无效（uiConfirm/uiPrompt + 统一事件委托 + 后端双兼容）** |
| **v0.7.1** | **WebDAV 远端归档上海时区中文时间格式化；远端文件直接物理删除（HTTP DELETE + 二次危险确认 + 热刷新）** |
| **v0.7.0** | **版本纪元比较引擎；全局模态弹窗 Emoji 去重；WebDAV 远端归档查看与热恢复；彻底杜绝双份备份；更新规范确立 (0.7.xx)** |
| v0.68.36 | WebDAV RFC 4918 OPTIONS 探测根治 429 频控；SQLite kv 表自包含 100% 配置与用户资产；WebUI 体验现代化重构 |
| v0.68.35 | 彻底根除 AstrBot 原生 bridge endpoint 带问号异常；全面适配 Quart 请求体异步解析与全局上下文代理 |
| v0.68.34 | 检测更新按钮直接承载状态与结果展示；接入 jsDelivr CDN 1.5s 极速检测；WebDAV 保存后端直接回显 |
| v0.68.33 | WebUI 版本双端卡片弹窗提示；WebDAV MKCOL 递归创建尾部斜杠修复与协议前缀自动规范化 |
| v0.68.32 | 交接文档同步现状（零逻辑变更） |
| v0.68.31 | WebDAV 迁备份管理专属卡片、全量配置快照一键恢复 |
| v0.68.30 | WebDAV DB 镜像三级防丢、检查更新零静默（20s 熔断） |
| v0.68.29 | WebDAV 空值回填、更新检测失败明确提示 |
| v0.68.28 | 仓库迁 `imsuperone/xb`、接龙锁定 20+0、WebDAV 保存防丢（文件兜底） |
| v0.68.27 | 三对齐：补 2 裸奔配置键（296→298 项） |
| v0.68.26 | 清空 kv 幽灵残留、旧库导入脱敏硬编码群号 |
| v0.68.25 | 复检回合：前后端对齐/索引一致性/投诉场景冒烟（零逻辑变更） |
| v0.68.24 | 读副本分离、自定义指令索引、VACUUM 出锁、`tabs/` 死亡代码移除 |
| v0.68.23 | 全库体检：P0×4/P1×8 修复、热路径提速、`scripts/stress_24h.py` 落地 |
| v0.68.22 | 根治 `database is locked`/接龙卡死：全引擎持锁串行化、备份非阻塞化 |
