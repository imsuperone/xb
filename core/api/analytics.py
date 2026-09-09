# -*- coding: utf-8 -*-
"""小白机器人 - 群生态与宏观经济数据大屏分析引擎 (SQL 聚合 + 3s 轻量缓存)"""
import asyncio
import time
from astrbot.api.web import json_response
from .helpers import _err

try:
    from ... import store as ST
except ImportError:
    import store as ST

_CACHE_DATA = None
_CACHE_TIME = 0.0
_CACHE_TTL = 3.0

async def handle_analytics_overview(request):
    """返回群生态与宏观经济运行多维大屏数据（纯净统一无冗余）"""
    global _CACHE_DATA, _CACHE_TIME
    now = time.time()
    if _CACHE_DATA is not None and (now - _CACHE_TIME) < _CACHE_TTL:
        return json_response(_CACHE_DATA)

    def _work():
        if ST._DB is None:
            return {"ok": True, "summary": {}}

        _lock = getattr(ST, "_LOCK", None)
        if _lock is not None:
            _lock.acquire()
        try:
            cur = ST._DB.cursor()

            # 1. 钱包与资产统计
            cur.execute("SELECT SUM(money), COUNT(*), COUNT(DISTINCT gid) FROM wallet")
            row = cur.fetchone()
            total_wallet_money = int(row[0]) if row and row[0] is not None else 0
            total_users_count = int(row[1]) if row and row[1] is not None else 0
            total_groups_count = int(row[2]) if row and row[2] is not None else 0

            # 2. 银行储蓄与签到人次统计：SQL 侧聚合（原逐行 json.loads，百万行即秒级）
            #    语义与旧循环一致：deposit 按行取整累加；sign 取 sign_count 回退 total_sign_days；
            #    非法 JSON/非对象行整行跳过（旧 json.loads 抛错即跳过）；NULL data 视作 {}。
            #    注意 json_each 遇脏串会抛错（json_extract 只回 NULL），故 WHERE 先过滤。
            cur.execute("""
                SELECT
                    COALESCE(SUM(CAST(COALESCE(json_extract(data, '$.deposit'), '0') AS INTEGER)), 0),
                    COALESCE(SUM(CASE WHEN CAST(COALESCE(json_extract(data, '$.deposit'), '0') AS REAL) > 0 THEN 1 ELSE 0 END), 0),
                    COALESCE(SUM(CAST(COALESCE(json_extract(data, '$.sign_count'), json_extract(data, '$.total_sign_days'), '0') AS INTEGER)), 0)
                FROM accounts
                WHERE json_valid(COALESCE(data, '{}'))
            """)
            row = cur.fetchone()
            total_bank_deposit = int(row[0]) if row and row[0] is not None else 0
            total_bank_users = int(row[1]) if row and row[1] is not None else 0
            total_sign_count = int(row[2]) if row and row[2] is not None else 0

            # 3. 奴隶生态与总身价统计：SQL 侧聚合（原 groups 全表逐行解析）
            #    非法 JSON/非对象/NULL 行按旧逻辑处理（NULL 视作 {} 计默认身价，其余跳过）
            default_init_price = ST.cfgi("费用配置", "初始身价", 500) if hasattr(ST, "cfgi") else 500
            cur.execute("""
                SELECT
                    COALESCE(SUM(CAST(COALESCE(json_extract(data, '$.price'), json_extract(data, '$.worth'), ?) AS INTEGER)), 0),
                    COALESCE(SUM(CASE WHEN TRIM(COALESCE(json_extract(data, '$.owner'), '')) NOT IN ('', '0', 'None') THEN 1 ELSE 0 END), 0),
                    COUNT(DISTINCT CASE WHEN TRIM(COALESCE(json_extract(data, '$.owner'), '')) NOT IN ('', '0', 'None')
                                        THEN TRIM(json_extract(data, '$.owner')) END)
                FROM groups
                WHERE data IS NULL OR (json_valid(data) AND json_type(data) = 'object')
            """, (default_init_price,))
            row = cur.fetchone()
            total_slave_worth = int(row[0]) if row and row[0] is not None else 0
            total_slaves_count = int(row[1]) if row and row[1] is not None else 0
            total_masters_count = int(row[2]) if row and row[2] is not None else 0
        finally:
            if _lock is not None:
                try:
                    _lock.release()
                except Exception:
                    pass

        total_economy_pool = total_wallet_money + total_bank_deposit
        avg_money_per_user = int(total_economy_pool / max(1, total_users_count))

        result = {
            "ok": True,
            "summary": {
                "total_users": total_users_count,
                "total_groups": total_groups_count,
                "total_wallet_money": total_wallet_money,
                "total_bank_deposit": total_bank_deposit,
                "total_bank_users": total_bank_users,
                "total_sign_count": total_sign_count,
                "total_economy_pool": total_economy_pool,
                "avg_money_per_user": avg_money_per_user,
                "total_slave_worth": total_slave_worth,
                "total_slaves_count": total_slaves_count,
                "total_masters_count": total_masters_count
            }
        }
        return result

    try:
        result = await asyncio.to_thread(_work)
        _CACHE_DATA = result
        _CACHE_TIME = now
        return json_response(result)
    except Exception as e:
        return _err(f"analytics failed: {e}", 500)
