# 小白机器人 (astrbot_plugin_xbbot) — 核心速查与环境状态卡 (AIINFO)

## 📌 元数据

| 属性 | 值 |
| :--- | :--- |
| 插件 | `astrbot_plugin_xbbot`（小白统一模块） |
| 当前版本 | `v0.7.36` |
| 作者 | Light (`faxlight@faxt.top`) |
| 仓库 | `https://github.com/imsuperone/xb`（main） |
| 主目录 | `astrbot_plugins/astrbot_plugin_xbbot` |
| 发行包 | `astrbot_plugin_xbbot_v0.7.36.zip`（仓库根 / astrbot_plugins / backup 三端同步） |
| 依赖 | AstrBot >= 3.4.0，Python >= 3.10 |
| 规模 | 41 模块 / 29 节 907 配置项 / 68 Web API / app.js 约 5450 行 / 179 DOM（0 重复） |
| 本卡与手册 | 根与插件目录各一份，内容同步；改一处必须同步另一处 |

## 🛡️ 十二大红线（1~7 为初版，8~12 为 v0.7.14~22 血泪新增，违反即回滚）

1. **主循环零阻塞**：`_dispatch` 无同步 I/O、落盘、网络；落盘走后台线程，网络走 `asyncio.to_thread`。
2. **严禁跨线程 rollback**：`_ensure_db()` 内禁 `rollback()`；只许业务 `except` → `_safe_rollback()`。
3. **写入安全降级**：`store.py` 写入异常一律降级返回安全值，禁裸抛。
4. **娱乐 30 秒自愈**：接龙等全系 30s 超时；【重置接龙】【结束接龙】秒释；接龙 20 金币 + 0 魅力。
5. **版本 0.7.xx + 9 处强对齐**：`0.7.0`~`0.7.99` 递增，满 99 或用户明示才升段；9 处（`metadata.yaml`、`main.py`、`core/api/updater.py`、`core/api/users.py`、`engines/superadmin.py`、`pages/admin/index.html`、`pages/admin/app.js`、`CHANGELOG.md`、`README.md`）必须同值；比对走纪元算法 `(epoch, major, minor, patch)`。
6. **WebDAV 安全**：OPTIONS 探测防 429；上海时区中文时间；删除二次确认 + 防抖；上传 5 秒防抖。
7. **【超管全静默 BY DESIGN】非超管命中任何超管指令（含 `版本/检查更新`，v0.7.27 起不再公开）及权限=超管的指令一律 `return None`，无任何提示。普通用户发了没反应 = 正常，绝不“修复”成有提示。超管指令一令一名，禁冗余别名。**
8. **【图片元组直传】引擎发图一律 `(text, [path])` 元组，原生绝对路径直传；禁拼 `[CQ:image,…]` 字符串**（中文+斜杠在适配器侧不稳定，v0.7.13 实测 CQ 图丢失而元组正常）。`_build_chain` 的 CQ 解析仅为自定义回复兼容而保留。
9. **【恢复默认按页隔离 + 硬清理】任何“恢复默认”只动本页范围，必须二次确认，旧数据不保留**（数据库自有备份可回滚）。禁全量重置；禁“删光保留 multiline 软恢复”式含糊文案。**唯一例外（v0.7.29，经用户明确指令）**：必要配置页“🧹 全部设置恢复默认”可跨节，但白名单排除备份配置（含 WebDAV/自动备份开关/间隔/保留数）、商城图鉴、精灵图鉴、自定义指令、群组开关，不动用户数据（钱包/账户/群档案），且依赖保存前自动快照可回滚。
10. **【WebDAV 密钥分存】地址/用户名/应用密码只存数据目录独立 `webdav_secret.json`**，永不进 `_CONFIG`/DB 镜像/快照/备份/导出/回执。`ST.cfg` 运行时透明叠加；`config/get` 回填显示（密码恒空）；密码留空 = 保持不变。历史备份文件中的旧密钥洗不掉，新备份不再含。
11. **【状态显示禁硬编码】徽标/徽章/模式文案必须读运行时，禁写死**（v0.7.22 教训：徽标写死“休闲”误导用户，实际跑的是 schema 默认）。数值档位以 `config/balance_state` 漂移检测为准。
12. **【上传走 base64-JSON】iframe 桥 `postMessage` 克隆不了 `FormData`**，前端上传一律 `postFile()`（base64 JSON），后端双受理（multipart 兼容保留）。禁裸 `FormData` 走桥。

## 🧭 语义铁律（违反即 bug）

- **空 = 未自定义 = 运行时用内置**（精灵/坐骑/池/宝物/地图皆如此；编辑器未自定义预填内置并打标）。
- **保留数只删不增**（修剪留新删旧；云端文件少于保留数 = 正常）。
- **指令启用默认真 / 回复默认空 = 零行为变化**。
- **文件即池**：抽奖武器 = 图片文件本身；改名改文件名，稀有度改目录；删文件即下架。
- **保存走内存状态**：禁从过滤后的 DOM 收集保存（v0.7.17 教训：搜后保存丢地图）。
- **三源投票**：持久文件 + DB 镜像一致时覆盖内存（防启动参数陈旧回滚保留数等）。

## ✅ 交付前三自检（必跑，贴结果）

```powershell
python -X utf8 verify_plugin.py
python -X utf8 scripts/stress_24h.py
node --check pages/admin/app.js
```

发版：三端 zip（`Temp/opencode/pack_xb0714.py` 改 VER 后跑，排除 `.git/.github/__pycache__/*.pyc/*.db*/data/backups` **+ 顶层文档（AIINFO/AIREADME/aiall/CHANGELOG/README）+ `scripts/`**，内容为插件目录顶层平铺）→ 同步 根/`astrbot_plugins`/`backup` → `git add -A; git commit; git push origin main; git tag vx.y.z -f; git push origin vx.y.z -f`。纯文档提交可只 push 不移动 tag/zip。

## 🗂️ 文件职责

| 文件 | 职责 |
| :--- | :--- |
| `main.py` | Star 入口；`_dispatch` 分发；Web API 注册；`xb-auto-backup` 守护线程 |
| `store.py` | SQLite WAL；`_LOCK`；备份生成/串行/修剪/投票；kv/钱包/账户/群档案；密钥分存；sidecar |
| `core/webdav.py` | 纯标准库 WebDAV（上传/列表/恢复/删除/修剪；读配置走 `ST.cfg` 叠加层，零改动） |
| `core/router.py` | 指令路由；守卫；自定义/禁用/回复索引 |
| `core/config.py` | 配置归一；指令采集器 |
| `core/api/*.py` | WebUI 薄路由（耗时走 `asyncio.to_thread`）；`game.py` 兼抽奖池文件管理；`images.py` 兼缩略图 |
| `engines/*` | slave/sign/bank/ent/chat/spirit/ride/superadmin/guild/adventure |
| `pages/admin/` | WebUI（`index.html` + `app.js`，14 Tab：概览/排行/用户/奴隶/精灵用户/群聊/配置/指令/商城/图鉴/备份/根目录/日志/关于） |

## 🔌 API 分组速查（前缀 `/astrbot_plugin_xbbot/`）

- 备份：`backups/list|restore|delete|export|prune|doctor`，`backup/webdav/test|upload|files|restore|delete`（+ `backups/webdav/*` 别名）
- 用户：`users`（limit/offset/gid），`user/edit|clear|export|import`，`users/export|import|clean_left|airdrop`
- 配置：`config/schema|get|save`，`commands`，`config/auto_balance`，`config/balance_state`
- 游戏：`stats`，`rank`，`slave/users|calibrate`，`spirit/users`，`spirits|spirits/save`，`gacha/weapons`，`weapons/pool|rename|move|delete|upload|img|attrs|replace_path`
- 其他：`groups/list|toggle|delete`，`images/list|upload|delete|rename|mkdir|copy|export|thumb`，`logs|logs/clear|logs/export`，`import/legacy`，`analytics/overview`，`version/check`，`admin/clear`

## 🛠️ 排障

1. 群聊不回复 → 总开关 / 维护模式 / 本群开关。
2. 接龙卡死 → 【重置接龙】/【结束接龙】；30 秒自愈。
3. WebDAV 401/404/429 → 测试按钮；坚果云用应用密码；429 拉长备份间隔。
4. 云端文件数少于保留数 → **正常**：修剪只删不增，被删的不会回来，新备份攒到保留数为止。
5. 非超管发超管指令无响应 → **正常（法则 7），不是 bug**。
6. 更新检测 → 20 秒熔断；纪元算法隔离 `0.68.x` 旧版。
7. 商城/图鉴空白 → 未自定义显示内置并打标；删光自动回退内置。
8. 保留数/配置无故变旧值 → 已加三源投票自愈；仍出现则重做一次保存并截图。
9. 打劫金额忽大忽小 → **正常**：`金额=min(受害人持有, 随机区间)`，受害人穷就少；失败是独立概率。
10. 关押时间与档位不符 → 徽标若显示偏离，重应用一次平衡档。
11. 宝物不掉落/无效果 → 查 `设置.宝物` 名单（`_treasure_names` 双键合并）+ `treasure_effects`。
12. 上传报 nofile/postMessage 克隆失败 → 已改 base64 直传；仍失败则看浏览器控制台实际回执。
13. `.xb_last_backup.json` → **正常**：防重文件，无需删除。

## 🗑️ 已退役（勿恢复）

帮派武器 / 女仆坐骑 / 起名 / 可视化工坊 / **武器商城（v0.7.16 起改抽奖池直管）**。
退役指令（v0.7.29）：查询更新 / 查询版本 / 查询维护 / 查询坐骑 / 查询精灵 / 查询帮派 / 查询冒险 / 查询地图 / 查询菜单（越权转发清除，一律静默；勿恢复）。
