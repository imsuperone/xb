# 小白机器人 (astrbot_plugin_xbbot) — 核心速查与环境状态卡 (AIINFO)

## 📌 元数据

| 属性 | 值 |
| :--- | :--- |
| 插件 | `astrbot_plugin_xbbot`（小白统一模块） |
| 当前版本 | `v0.7.13` |
| 作者 | Light (`faxlight@faxt.top`) |
| 仓库 | `https://github.com/imsuperone/xb`（main） |
| 主目录 | `astrbot_plugins/astrbot_plugin_xbbot` |
| 发行包 | `astrbot_plugin_xbbot_v0.7.13.zip`（仓库根 / astrbot_plugins / backup 三端同步） |
| 依赖 | AstrBot >= 3.4.0，Python >= 3.10 |
| 规模 | 41 模块 / 27 节 741 配置项 / 58 API（53 逻辑 + 5 别名）/ 181 DOM（0 重复） |

## 🛡️ 七大黄金法则（红线，第 7 条为 v0.7.13 新增）

1. **主循环零阻塞**：`_dispatch` 无同步 I/O、落盘、网络；落盘走后台线程，网络走 `asyncio.to_thread`。
2. **严禁跨线程 rollback**：`_ensure_db()` 内禁 `rollback()`；只许业务 `except` → `_safe_rollback()`。
3. **写入安全降级**：`store.py` 写入异常一律降级返回安全值，禁裸抛。
4. **娱乐 30 秒自愈**：接龙等全系 30s 超时；【重置接龙】【结束接龙】秒释；接龙 20 金币 + 0 魅力。
5. **版本 0.7.xx + 9 处强对齐**：`0.7.0`~`0.7.99` 递增，满 99 或用户明示才升段；9 处（`metadata.yaml`、`main.py`、`core/api/updater.py`、`core/api/users.py`、`engines/superadmin.py`、`pages/admin/index.html`、`pages/admin/app.js`、`CHANGELOG.md`、`README.md`）必须同值；比对走纪元算法 `(epoch, major, minor, patch)`。
6. **WebDAV 安全**：OPTIONS 探测防 429；上海时区中文时间；删除二次确认 + 防抖；上传 5 秒防抖。
7. **【超管全静默 BY DESIGN】非超管命中任何超管指令（超管系统/备份/禁言/踢人/清空/维护/测试/超管列表等）一律 `return None`，无任何提示。普通用户发了没反应 = 正常，绝不“修复”成有提示。仅 `版本/检查更新` 对所有人可查。**

## ✅ 交付前三自检

```powershell
python -X utf8 verify_plugin.py
python -X utf8 scripts/stress_24h.py
node --check pages/admin/app.js
```

## 🗂️ 文件职责

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | Star 入口；`_dispatch` 分发；58 Web API 注册；`xb-auto-backup` 守护线程 |
| `store.py` | SQLite WAL；`_LOCK`；备份生成/串行/修剪；kv/钱包/账户/群档案 |
| `core/webdav.py` | 纯标准库 WebDAV（上传/列表/恢复/删除/修剪） |
| `core/router.py` | 指令路由；守卫；自定义/禁用/回复索引 |
| `core/config.py` | 配置归一；指令采集器 |
| `core/api/*.py` | WebUI 薄路由（12 Tab） |
| `engines/*` | slave/sign/bank/ent/chat/spirit/ride/superadmin/guild/adventure |
| `pages/admin/` | WebUI（`index.html` + `app.js`） |

## 🔌 API 分组速查（前缀 `/astrbot_plugin_xbbot/`）

- 备份：`backups/list|restore|delete|export|prune|doctor`，`backup/webdav/test|upload|files|restore|delete`（+ `backups/webdav/*` 别名）
- 用户：`users`（limit/offset/gid），`user/edit|clear|export|import`，`users/export|import|clean_left|airdrop`
- 配置：`config/schema|get|save`，`commands`，`config/auto_balance`
- 游戏：`stats`，`rank`，`slave/users|calibrate`，`spirit/users`，`spirits|spirits/save`，`gacha/weapons`
- 其他：`groups/list|toggle|delete`，`images/*`，`logs|logs/clear|logs/export`，`import/legacy`，`analytics/overview`，`version/check`，`admin/clear`

## 🛠️ 排障

1. 群聊不回复 → 总开关 / 维护模式 / 本群开关。
2. 接龙卡死 → 【重置接龙】/【结束接龙】；30 秒自愈。
3. WebDAV 401/404/429 → 测试按钮；坚果云用应用密码；429 拉长备份间隔。
4. 云端文件数少于保留数 → **正常**：修剪只删不增，被删的不会回来，新备份攒到保留数为止。
5. 非超管发超管指令无响应 → **正常（法则 7），不是 bug**。
6. 更新检测 → 20 秒熔断；纪元算法隔离 `0.68.x` 旧版。
7. 商城/图鉴空白 → 未自定义显示内置并打标；删光自动回退内置。
