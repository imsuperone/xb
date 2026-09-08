# 小白机器人 (astrbot_plugin_xbbot) — AI 开发者架构与交接手册 (AIREADME)

> **当前版本**：`v0.7.27`
> **对象**：接手本项目的 AI 编程助手与核心维护者
> **定位**：AstrBot 大型群互动插件（奴隶/签到/银行/娱乐/私聊/精灵/坐骑/超管/帮派/冒险 10 引擎 + WebUI）
> **红线唯一出处**：`AIINFO.md` 十二大红线 + 六条语义铁律，本手册只讲实现位置，不复述。

---

## 1. 分层（单向依赖：pages → main → core/engines → store）

```
astrbot_plugin_xbbot/
├── metadata.yaml / main.py / store.py / verify_plugin.py
├── _conf_schema.json      # 27 节 741 项（指令启用/回复由采集器播种）
├── core/config.py         # 归一 + 指令采集器（元组/表驱动，防 min( 误报，去注释）
├── core/router.py         # 主路由；引擎指令缓存（mtime 10s 节流）；自定义/禁用/回复索引（版本命中零序列化）
├── core/platform.py       # 消息链（元组优先，CQ 仅兼容）；@卡片单任务落盘；平台动作 8s 熔断
├── core/webdav.py         # 上传/列表/恢复/删除/修剪（远端只动 xbbot_*.db；读配置走 ST.cfg 叠加层）
├── core/api/              # 薄路由；耗时走 asyncio.to_thread；game.py 兼池文件管理；images.py 兼缩略图
├── core/dispatch.py + core/test_harness.py  # 测试探针（超管可用，非超管静默）
├── engines/*              # 10 业务引擎；昵称分群表 NOTE_NAMES_BY_GROUP + 反向索引 NOTE_NAMES_REV
└── pages/admin/           # WebUI：14 Tab；商城/图鉴隔离；自研弹窗（禁原生 confirm/prompt）
```

- **法则 7 全静默**：`superadmin.handle` / `main._dispatch`（超管列表/测试testxb）/ `dispatch` / `test_harness` 中所有 `is_admin=False` 分支一律 `return None`（保留 `stop_event`），禁任何“无权限”文案。v0.7.27 起`版本/检查更新`不再公开；`router._cmd_need_admin` 对权限=超管的指令同样静默；超管指令一令一名禁别名。
- **法则 5**：9 处版本号 + `verify_plugin.py` 强校验；`updater._parse_version_tuple` 纪元比较。

## 2. 存储、备份与隐私（store.py）

- SQLite WAL（`busy_timeout=30s`）；写走 `_LOCK`（RLock），高频读走只读副本；`_KV_CACHE` + `_GROUP/_ACC_CACHE`（LRU）。
- 落盘口径：账户/钱包类用 `acct_save`/`coins_add`/`recall_set`（即时写）；**奴隶群档案必须经 `slave.handle` 尾部 `save(gid)`，字符串与元组回复一律保存**（v0.7.18 教训：元组漏保存致抽武器丢档）。
- 配置三级防丢：文件 ↔ DB kv 镜像（`wd_cfg_backup`，**跳过密钥**）↔ 快照（`cfgsnap__*`，内存已脱敏故天然干净）。
- 密钥分存：`webdav_secret.json`（`_WD_SECRET_KEYS` 三键）+ `wd_secret_load/set` + `cfg()` 叠加 + `config/save` 分流 + `config/get` 回填（密码恒空，留空保持不变）+ 启动 `_wd_secret_migrate()`。
- 三源投票 `_vote_backup_cfg()`：持久文件 == DB 镜像 != 内存时以持久侧为准（防启动参数陈旧回滚）。
- 备份：`data/backups/YYYY-MM-DD/xbbot_*.db`；`_BACKUP_GEN_LOCK` 进程内串行 + 在途复用 + 5 秒防抖；**跨进程**：文件锁（msvcrt/fcntl）+ busy 预约 + sidecar（30 秒窗口；内容含 `note: 此文件为防重文件，无需删除`）；`clean_old_backups` 按保留数清本地；上传成功后台按保留数修剪远端（只删 `xbbot_*.db`，留新删旧）；`backups/prune` 一键双端修剪。
- 自动备份：`xb-auto-backup` 线程（60s tick，线程名单例防重载累积）+ 每小时修剪。手动备份/平衡/立即上传均为 force 立刻出一份并上传——频繁即人为连点，不是 bug。
- 自愈播种**仅全新时一次**（`get_persistent_data_dir` 内）：已存在则不动，禁覆盖用户改池/删图。

## 3. 指令体系（router.py）

- 总开关 → 群开关 → 维护 → 私聊直走 chat → 主菜单 → 自定义（最长命中）→ 禁用拦截 → 超管权限拦截（非超管静默） → 9 引擎 → 超管。
- `指令启用配置` 215 开关（默认真=行为不变，v0.7.26 起空格变体合并规范键，匹配空格无关；v0.7.27 去超管别名/噪音）；`指令回复配置` 215 场景（默认空=内置回复）；`指令权限配置` 215 位（默认所有人，30 键默认超管）；`_collect_commands` 为唯一采集源，改引擎指令写法后重跑播种脚本（`Temp/opencode/seed_schema_075.py` 思路）。
- 昵称：`set/get/clear_note_name` + `find_qq_by_name`（精确 O(1)，模糊限本群）；`_AT_NAMES` 全局辅助。

## 4. 数值平衡（config_api.py PRESETS）

- 三档 standard/casual/hardcore 全量键（键名一致、仅值不同）；`设置.平衡模式` + 顶层 `_active_balance_mode` 双记；写入后 `_bump_config_ver()`。
- 应用前真备份：`pre_balance_{mode}_{ts}` 快照（备份页可恢复）+ 全库冷备；身价校准走 `group/save_group`，**仅补零**（正身价保留防双轨）。
- modal 文案必须与预设真实值一致（曾全错，v0.7.5 已按真实值重写）；打开预选中当前档；应用成功刷新 `loadConfig` + `loadCommands` + 徽标。
- **徽标与漂移**：徽标禁写死，`refreshBalanceBadges()` 读 `config/balance_state`（13 签名键抽检）；偏离置灰点名；徽标可点直达弹窗。
- 死键原则：预设写了引擎必须读，否则从预设删除（v0.7.5 已清理 10 组；`F3/I` 类废弃键删干净）。注意审计脚本对 f-string/拼接键有误报，结论以人工复核为准。
- 银行机制（防“被针对”误报）：打劫金额=`min(受害人持有, 随机区间)`；失败无成功CD是原设计（坐牢即代价）；越狱 Glasgow 式宽松是休闲档本意；要收紧只调配置不动代码。

## 5. 图鉴、商城与隔离矩阵

- 语义：**空 = 未自定义 = 运行时用内置**。精灵（`spirit_data.py`）、坐骑（RIDES）、池（文件即池）皆如此；宝物名单 `_treasure_names()` 双键合并（`设置.宝物`优先，兼容旧 `treasure`）。
- 保存只写各自范围（合并语义），跨页禁串写：

| 页/区 | 操作 | 写什么 |
| :--- | :--- | :--- |
| 商城·坐骑 | 保存 | `商城图鉴.ride_shop` |
| 商城·抽奖池 | 改名/稀有度/删/传/换图 | 池文件（即时） |
| 商城·抽奖池 | 保存武器属性/恢复默认 | `商城图鉴.weapon_attrs`（恢复=硬清） |
| 商城·道具 | 保存道具/恢复默认 | 精灵图鉴 `shop`（恢复=硬清即时） |
| 总览·武器/宝物/坐骑 | 同商城对应能力 | 同上（宝物名+效果即时） |
| 总览·精灵 | 保存地图/属性/恢复 | 精灵图鉴 `maps`/`spirits`（恢复=硬清即时） |
| 必要配置·恢复 | 仅本页已渲染节 + 二次确认 | 对应节 |

- `store.cfg()` 对 dict 走 JSON 序列化（repr 单引号曾致自定义全回退，v0.7.7 已修）。
- 精灵接口：`spirits` 下发有效数据 + `_raw` + `_builtin` + `_meta.configured`；`spirits/save` 入库整形（支持部分键）；导出固定干净三件套，导入只认这套。
- **保存禁从过滤 DOM 收集**：输入即时写回内存，保存直接存状态（v0.7.17 教训：搜后保存丢地图）。
- 已退役（勿恢复）：帮派武器、女仆坐骑、起名、可视化工坊、**武器商城（v0.7.16 起改池直管；`weapon_shop` 仅旧数据只读兼容，抽中不再写、预设已移除）**。

## 6. 图片链路

- 引擎发图一律元组 `(text, [abspath])`；`_build_chain` CQ 解析仅兼容自定义。
- 目录（英文化，旧布局双读兼容）：`data/img/gacha/{SSR,SR,R}`、`data/img/rides/`、`data/img/spirits/`；已存配置旧路径走别名解析。
- 池读写以引擎生效目录为准（持久优先）；上传/替换走 `weapons/pool/*`（文件名清洗、防穿越、防覆盖、改后清 `_GACHA_CACHE`）。
- 预览一律按需单张（`weapons/pool/img`、`images/thumb`，≤200KB），列表禁批量 base64（v0.7.17 卡顿教训）。
- 上传一律前端 `postFile()` base64-JSON，后端双受理（法则 12）。
- 武器属性 `weapon_attrs{atk,desc}`：加成计入 `atk_of` 战力、描述进详情；旧 `weapon_shop` 残留只读回退。
- 宝物效果优先级：自定义 `treasure_effects` > 酒神/四象专属 > 通用镇宅（常量缺失已回退补齐）。

## 7. WebUI 要点（app.js，~5000 行）

- Bridge 优先 + fetch 回退；`uiConfirm/uiPrompt/uiAlert`（iframe 下禁原生弹窗）；按钮忙态锁。
- 回执只说结果不 dump JSON；危险操作（删文件/删图/清属性/恢复默认）一律二次确认。
- 用户表/池表事件委托；WebDAV 列表 10/页；远端删除二次确认 + 热刷新；备份时间后 sidecar 可读时显示 🔒 防重保护中。
- 更新检测 20 秒熔断；`_normalizeModalTitleAndIcon` 去重 Emoji。
- 选图三流：外置上传（`postFile`）/内置选图（根目录 picker + `shopPickTip`）/预览（thumb + lightbox）；picker 共用 `SHOP_PICK_TARGET/KIND`，一次一流，用完清空。
- 响应式断点 `≤768px`：编辑行单列全宽；平板横屏走桌面布局（可接受）。
- 关于页：作者 Light / 仓库 `https://github.com/imsuperone/xb` / 当前版本（随 `version/check` 更新）。

## 8. 发布流程

```powershell
python -X utf8 verify_plugin.py
python -X utf8 scripts/stress_24h.py
node --check pages/admin/app.js
# 打包脚本 Temp/opencode/pack_xb0714.py 改 VER 后跑；同步 根/astrbot_plugins/backup
git add -A; git commit -m "..."; git push origin main; git tag vx.y.z -f; git push origin vx.y.z -f
```

纯文档提交可只 push 不移动 tag/zip。改引擎指令写法后记得重跑指令播种检查。

## 9. 版本史（v0.7.x 详细，史前一句话）

| 版本 | 主题 |
| :--- | :--- |
| v0.7.27 | 超管全锁；每指令权限+数值全覆盖；采集去噪；数值调整改回指令页 |
| v0.7.26 | 平衡弹窗可关；指令去空格重；必要配置放行数值节 |
| v0.7.25 | 主入口精简；表驱动+统一委托 |
| v0.7.24 | 全量审计修复；耗时异步化；存储加固 |
| v0.7.23 | 精灵保存合并；浏览+弹窗；道具类型化；坐骑补齐；目录隔离 |
| v0.7.22 | 徽标真实化；漂移检测 |
| v0.7.21 | base64 直传；图片英文化；保留数投票 |
| v0.7.20 | 图片链路对齐；坐骑上传修复；移动端适配 |
| v0.7.19 | 添加武器弹窗；坐骑同款；防重提示；宝物通用效果 |
| v0.7.18 | 元组落盘；宝物键合并；密钥分存；池对齐；每tab保存恢复 |
| v0.7.17 | 搜后保存保数据；保存恢复按系统；删重复编辑区；导出导入一套 |
| v0.7.16 | 武器商城改池直管；总览精灵可编辑；恢复隔离；回执精简 |
| v0.7.15 | 总览第四页签；未上架展开修复 |
| v0.7.14 | 武器商城对齐坐骑；维护精简；图鉴扩展；关于页 |
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
