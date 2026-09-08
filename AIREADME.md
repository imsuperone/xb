# 小白机器人 (astrbot_plugin_xbbot) — AI 开发者架构与交接手册 (AIREADME)

> **当前版本**：`v0.7.13`
> **对象**：接手本项目的 AI 编程助手与核心维护者
> **定位**：AstrBot 大型群互动插件（奴隶/签到/银行/娱乐/私聊/精灵/坐骑/超管/帮派/冒险 10 引擎 + WebUI）

---

## 1. 分层（单向依赖：pages → main → core/engines → store）

```
astrbot_plugin_xbbot/
├── metadata.yaml / main.py / store.py / verify_plugin.py
├── _conf_schema.json      # 27 节 741 项（指令启用/回复由采集器播种）
├── core/config.py         # 归一 + 指令采集器（元组/表驱动，防 min( 误报，去注释）
├── core/router.py         # 主路由；引擎指令缓存（mtime 10s 节流）；自定义/禁用/回复索引（版本命中零序列化）
├── core/platform.py       # 消息链（CQ/元组双路径，字符串路径防炸）；@卡片单任务落盘；平台动作 8s 熔断
├── core/webdav.py         # 上传/列表/恢复/删除/修剪（远端只动 xbbot_*.db）
├── core/api/              # 薄路由；耗时走 asyncio.to_thread
├── core/dispatch.py + core/test_harness.py  # 测试探针（超管可用，非超管静默）
├── engines/*              # 10 业务引擎；昵称分群表 NOTE_NAMES_BY_GROUP + 反向索引 NOTE_NAMES_REV
└── pages/admin/           # WebUI：13 Tab；商城/图鉴；自研弹窗（禁原生 confirm/prompt）
```

## 2. 法则

七大黄金法则见 `AIINFO.md`（唯一出处，不复述）。补充说明：

- **法则 7 全静默**：`superadmin.handle` / `main._dispatch`（超管列表/测试testxb）/ `dispatch` / `test_harness` 中所有 `is_admin=False` 分支一律 `return None`（保留 `stop_event`），禁任何“无权限”文案。`版本/检查更新`是公开只读例外。
- **法则 5**：9 处版本号 + `verify_plugin.py` 强校验；`updater._parse_version_tuple` 纪元比较。

## 3. 存储与备份（store.py）

- SQLite WAL（`busy_timeout=30s`）；写走 `_LOCK`（RLock），高频读走只读副本；`_KV_CACHE` + `_GROUP/_ACC_CACHE`（LRU）。
- 配置三级防丢：文件 ↔ DB kv 镜像（`wd_cfg_backup`）↔ 快照（`cfgsnap__*`）。
- 备份：`data/backups/YYYY-MM-DD/xbbot_*.db`；`_BACKUP_GEN_LOCK` 进程内串行 + 在途复用；**跨进程**：文件锁（msvcrt/fcntl）+ busy 预约 + sidecar（30 秒窗口，重载/多进程复用）；`clean_old_backups` 按保留数清本地；上传成功后台按保留数修剪远端（只删 `xbbot_*.db`，留新删旧）；`backups/prune` 一键双端修剪。
- 自动备份：`xb-auto-backup` 线程（60s tick，线程名单例防重载累积）+ 每小时修剪。

## 4. 指令体系（router.py）

- 总开关 → 群开关 → 维护 → 私聊直走 chat → 主菜单 → 自定义（最长命中）→ 禁用拦截 → 9 引擎 → 超管。
- `指令启用配置` 236 开关（默认真=行为不变）；`指令回复配置` 236 场景（默认空=内置回复）；`_collect_commands` 为唯一采集源，改引擎指令写法后重跑播种脚本（`Temp/opencode/seed_schema_075.py` 思路）。
- 昵称：`set/get/clear_note_name` + `find_qq_by_name`（精确 O(1)，模糊限本群）；`_AT_NAMES` 全局辅助。

## 5. 数值平衡（config_api.py PRESETS）

- 三档 standard/casual/hardcore 全量键（键名一致、仅值不同）；`设置.平衡模式` + 顶层 `_active_balance_mode` 双记；写入后 `_bump_config_ver()`。
- 应用前真备份：`pre_balance_{mode}_{ts}` 快照（备份页可恢复）+ 全库冷备；身价校准走 `group/save_group`，**仅补零**（正身价保留防双轨）。
-  modal 文案必须与预设真实值一致（曾全错，v0.7.5 已按真实值重写）；打开预选中当前档。
- 死键原则：预设写了引擎必须读，否则从预设删除（v0.7.5 已清理 10 组；`F3/I` 类废弃键删干净）。

## 6. 图鉴与商城

- 语义：**空 = 未自定义 = 运行时用内置**。精灵（`spirit_data.py`）、坐骑（RIDES）、武器（抽奖池合并）皆如此；编辑器未自定义预填内置并打标，保存即转自定义；删光有二次确认 + 回退提示。
- `store.cfg()` 对 dict 走 JSON 序列化（repr 单引号曾致自定义全回退，v0.7.7 已修）。
- 精灵接口：`spirits` 下发有效数据 + `_raw` + `_builtin` + `_meta.configured`；`spirits/save` 入库整形；`gacha/weapons` 供武器商城对照同步。
- 已删除功能（勿恢复）：帮派武器、女仆坐骑、起名、可视化工坊。

## 7. WebUI 要点（app.js）

- Bridge 优先 + fetch 回退；`uiConfirm/uiPrompt/uiAlert`（iframe 下禁原生弹窗）；按钮忙态锁。
- 用户表事件委托；WebDAV 列表 10/页；远端删除二次确认 + 热刷新。
- 更新检测 20 秒熔断；`_normalizeModalTitleAndIcon` 去重 Emoji。

## 8. 发布流程

```powershell
python -X utf8 verify_plugin.py
python -X utf8 scripts/stress_24h.py
node --check pages/admin/app.js
# 纯净包（排除 .git/.github/__pycache__/*.pyc/*.db*/data/backups）同步 根/astrbot_plugins/backup
git add -A; git commit -m "..."; git push origin main; git tag vx.y.z -f; git push origin vx.y.z -f
```

## 9. 版本史（ condensation：v0.7.x 详细，史前一句话）

| 版本 | 主题 |
| :--- | :--- |
| v0.7.13 | 超管指令全静默（BY DESIGN） |
| v0.7.12 | 超管测试图片双路径诊断；元组路径加固 |
| v0.7.11 | 总览分类切换；孤儿分配；坐骑添加窗 |
| v0.7.10 | 商城 dict 兼容；configured 判定；抽奖加载隔离 |
| v0.7.9 | 商城导入导出完整；孤儿可见；宝物通用效果；精灵形象图 |
| v0.7.8 | 备份跨进程去重；商城默认回显；武器接抽奖；商城/图鉴分家；删工坊 |
| v0.7.7 | cfg dict 序列化修复；图鉴空回退；编辑器如实化 |
| v0.7.6 | 删帮派武器/女仆/起名（零残留） |
| v0.7.5 | 平衡真备份；指令播种 236；休闲档修复；死键接入；热路径节流 |
| v0.7.4 | @反查 O(1)；大屏 SQL 聚合；空投单事务 |
| v0.7.3 | 排序货币化；备份串行锁；保留数双端修剪；云端分页 |
| v0.7.2 | 分群昵称隔离；删除用户修复（uiConfirm + 委托） |
| v0.7.1 | WebDAV 上海时区；远端 DELETE |
| v0.7.0 | 纪元引擎；Emoji 去重；远端归档/热恢复；防双份备份 |
| v0.68.22~36 | 锁串行化；WAL/读副本；429 根治；kv 自包含；bridge 问号修复 |
