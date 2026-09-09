# -*- coding: utf-8 -*-
"""stats / rank API — 总览与排行榜"""
import asyncio
import json
from astrbot.api.web import json_response

try:
    from ... import store as ST
    from ...engines import slave
except ImportError:
    import store as ST
    try:
        from engines import slave
    except ImportError:
        import slave  # type: ignore


async def handle_stats(request=None):
    def _one(cur, sql, default=0):
        try:
            row = cur.execute(sql).fetchone()
            return row[0] if row and row[0] is not None else default
        except Exception:
            return default

    def _work():
        # 锁内只做 cursor 快照取数，json 解析放锁外，防大库 massive 解析卡住全局写锁
        _lock = getattr(ST, "_LOCK", None)
        if _lock is not None:
            _lock.acquire()
        try:
            if ST._DB is None:
                return {"players": {"wallet": 0, "accounts": 0, "groups": 0}, "total_money": 0, "total_deposit": 0, "total_sign": 0}
            cur = ST._DB.cursor()
            n_wallet = _one(cur, "SELECT COUNT(*) FROM wallet")
            n_acct = _one(cur, "SELECT COUNT(*) FROM accounts")
            n_group = _one(cur, "SELECT COUNT(DISTINCT gid) FROM wallet")
            total = _one(cur, "SELECT COALESCE(SUM(money),0) FROM wallet")
            total_dep = _one(cur, "SELECT COALESCE(SUM(CAST(COALESCE(json_extract(data,'$.deposit'), json_extract(data,'$.cunkuan'), json_extract(data,'$.\"存款总数\"'), '0') AS INTEGER)),0) FROM accounts")
            acct_rows = None
            if not total_dep and (n_acct or 0) < 100000:
                # 兜底全表仅小库执行，大库跳过防秒级阻塞
                try:
                    acct_rows = cur.execute("SELECT data FROM accounts").fetchall()
                except Exception:
                    acct_rows = None
            n_sign = _one(cur, "SELECT COALESCE(SUM(CAST(COALESCE(json_extract(data,'$.sign_count'), json_extract(data,'$.签到次数'), '0') AS INTEGER)),0) FROM accounts")
        finally:
            if _lock is not None:
                try:
                    _lock.release()
                except Exception:
                    pass
        if acct_rows:
            try:
                s = 0
                for (d,) in acct_rows:
                    try:
                        j = json.loads(d or "{}")
                        v = j.get("deposit") or j.get("cunkuan") or j.get("存款总数") or "0"
                        s += int(float(v or 0))
                    except Exception:
                        pass
                if s:
                    total_dep = s
            except Exception:
                pass
        return {
            "players": {"wallet": n_wallet, "accounts": n_acct, "groups": n_group},
            "total_money": total,
            "total_deposit": int(total_dep or 0),
            "total_sign": n_sign,
        }
    data = await asyncio.to_thread(_work)
    return json_response(data)


async def handle_rank(request=None):
    from .helpers import get_req_query
    rtype = get_req_query(request, "type", "money")
    if rtype == "tili":
        rtype = "stamina"
    if rtype == "meili":
        rtype = "charm"
    if rtype == "cunkuan":
        rtype = "deposit"

    def _work():
        # 锁内只做快照取数，昵称解析与组装放锁外
        _lock = getattr(ST, "_LOCK", None)
        if _lock is not None:
            _lock.acquire()
        try:
            sql = {
                "money": ("SELECT qq, money FROM wallet ORDER BY money DESC LIMIT 20", lambda r: (r[0], r[1])),
                "sign": ("SELECT qq, CAST(COALESCE(json_extract(data,'$.sign_count'), json_extract(data,'$.签到次数'), '0') AS INTEGER) "
                         "FROM accounts ORDER BY 2 DESC LIMIT 20", None),
                "stamina": ("SELECT qq, CAST(COALESCE(json_extract(data,'$.stamina'), json_extract(data,'$.tili'), '0') AS INTEGER) "
                         "FROM accounts ORDER BY 2 DESC LIMIT 20", None),
                "charm": ("SELECT qq, CAST(COALESCE(json_extract(data,'$.charm'), json_extract(data,'$.meili'), '0') AS INTEGER) "
                          "FROM accounts ORDER BY 2 DESC LIMIT 20", None),
                "deposit": ("SELECT qq, CAST(COALESCE(json_extract(data,'$.deposit'), json_extract(data,'$.cunkuan'), json_extract(data,'$.存款总数'), '0') AS INTEGER) "
                         "FROM accounts ORDER BY 2 DESC LIMIT 20", None),
            }.get(rtype)
            try:
                if not sql:
                    rows = ST._DB.execute("SELECT qq, data FROM accounts ORDER BY qq LIMIT 20").fetchall() if ST._DB else []
                else:
                    rows = ST._DB.execute(sql[0]).fetchall() if ST._DB else []
            except Exception:
                rows = []
            qq_list = [str(r[0]) for r in rows]
            g_rows, a_rows = [], []
            if qq_list:
                try:
                    placeholders = ",".join("?" for _ in qq_list)
                    g_rows = ST._DB.execute(f"SELECT qq, data FROM groups WHERE qq IN ({placeholders})", tuple(int(q) for q in qq_list)).fetchall()
                except Exception:
                    g_rows = []
                try:
                    placeholders = ",".join("?" for _ in qq_list)
                    a_rows = ST._DB.execute(f"SELECT qq, data FROM accounts WHERE qq IN ({placeholders})", tuple(int(q) for q in qq_list)).fetchall()
                except Exception:
                    a_rows = []
        finally:
            if _lock is not None:
                try:
                    _lock.release()
                except Exception:
                    pass
        nm = getattr(slave, "NOTE_NAMES", {}) or {}
        # 批量预取昵称，避免 N+1
        g_names, a_names = {}, {}
        for qq_, d in g_rows:
            try:
                j = json.loads(d or "{}")
                if j.get("name"):
                    g_names[str(qq_)] = j["name"]
            except Exception:
                pass
        for qq_, d in a_rows:
            try:
                j = json.loads(d or "{}")
                if j.get("name"):
                    a_names[str(qq_)] = j["name"]
            except Exception:
                pass
        out = []
        for r in rows:
            qq = str(r[0])
            name = nm.get(qq, "") or g_names.get(qq, "") or a_names.get(qq, "")
            out.append({"qq": qq, "name": name, "value": r[1]})
        return out
    out = await asyncio.to_thread(_work)
    return json_response(out)
