# -*- coding: utf-8 -*-
"""游戏画像 API — 奴隶 / 精灵 用户画像 + 精灵图鉴 + 身价校准 + 抽奖武器池文件管理"""
import base64
import json
import os as _os
import re
import shutil as _shutil
from astrbot.api.web import json_response

from .helpers import _err, get_req_query, get_req_json

try:
    from ... import store as ST
    from ...engines import slave
except ImportError:
    import store as ST
    try:
        from engines import slave
    except ImportError:
        import slave  # type: ignore


async def handle_slave_users(request):
    try:
        gid = get_req_query(request, "gid", "").strip()
        if not gid:
            j = await get_req_json(request, default={})
            if isinstance(j, dict) and j.get("gid"):
                gid = str(j.get("gid")).strip()

        default_init_price = ST.cfgi("费用配置", "初始身价", 500) if hasattr(ST, "cfgi") else 500
        if default_init_price <= 0: default_init_price = 500

        # 从 groups, wallet, accounts 聚合所有玩家
        out = []
        seen = set()

        if gid and gid.isdigit():
            st = slave.state(gid)
            _all_secs = [s for s in st.sections() if s.isdigit()]
            _owner_cnt = {}
            for _s in _all_secs:
                try:
                    _o = st[_s].get("owner", "") or ""
                except Exception:
                    _o = ""
                if _o:
                    _owner_cnt[_o] = _owner_cnt.get(_o, 0) + 1
            for qq in _all_secs:
                if not qq.isdigit(): continue
                u = slave.U(st, qq)
                p = int(u.get("price", "0") or 0)
                if p <= 0:
                    p = default_init_price
                    u["price"] = str(p)
                    st.mark_dirty(qq)
                seen.add((gid, str(qq)))
                out.append({
                    "gid": gid,
                    "qq": str(qq),
                    "name": slave.NOTE_NAMES.get(str(qq), u.get("name", "") or str(qq)),
                    "price": p,
                    "owner": u.get("owner", "") or "",
                    "owner_name": slave.NOTE_NAMES.get(u.get("owner", ""), u.get("owner", "")) if u.get("owner") else "",
                    "protect": u.get("protect_until", ""),
                    "slaves": _owner_cnt.get(str(qq), 0),
                    "weapons": u.get("weapon", ""),
                    "treasures": u.get("treasure", ""),
                })
            # 补该群 wallet 中有资产但尚未初始化的用户
            if ST._DB:
                w_rows = ST._DB.execute("SELECT qq FROM wallet WHERE gid=?", (int(gid),)).fetchall()
                for (w_qq,) in w_rows:
                    w_qq = str(w_qq)
                    if (gid, w_qq) in seen: continue
                    u = slave.U(st, w_qq)
                    p = int(u.get("price", "0") or 0) or default_init_price
                    seen.add((gid, w_qq))
                    out.append({
                        "gid": gid, "qq": w_qq,
                        "name": slave.NOTE_NAMES.get(w_qq, w_qq),
                        "price": p, "owner": "", "owner_name": "",
                        "protect": "", "slaves": 0, "weapons": "", "treasures": ""
                    })
            slave.save(gid)
        else:
            gids = set()
            if ST._DB:
                for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM groups").fetchall():
                    if str(g_id).isdigit(): gids.add(str(g_id))
                for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM wallet").fetchall():
                    if str(g_id).isdigit(): gids.add(str(g_id))
                for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM accounts").fetchall():
                    if str(g_id).isdigit(): gids.add(str(g_id))

            for g in gids:
                try:
                    st = slave.state(g)
                    _all_secs = [s for s in st.sections() if s.isdigit()]
                    _owner_cnt = {}
                    for _s in _all_secs:
                        try:
                            _o = st[_s].get("owner", "") or ""
                        except Exception:
                            _o = ""
                        if _o:
                            _owner_cnt[_o] = _owner_cnt.get(_o, 0) + 1
                    for qq in _all_secs:
                        if not qq.isdigit(): continue
                        u = slave.U(st, qq)
                        p = int(u.get("price", "0") or 0)
                        if p <= 0:
                            p = default_init_price
                            u["price"] = str(p)
                            st.mark_dirty(qq)
                        seen.add((g, str(qq)))
                        out.append({
                            "gid": g,
                            "qq": str(qq),
                            "name": slave.NOTE_NAMES.get(str(qq), u.get("name", "") or str(qq)),
                            "price": p,
                            "owner": u.get("owner", "") or "",
                            "owner_name": slave.NOTE_NAMES.get(u.get("owner", ""), u.get("owner", "")) if u.get("owner") else "",
                            "protect": u.get("protect_until", ""),
                            "slaves": _owner_cnt.get(str(qq), 0),
                            "weapons": u.get("weapon", ""),
                            "treasures": u.get("treasure", ""),
                        })
                    slave.save(g)
                except Exception:
                    continue

        out.sort(key=lambda x: -x["price"])
        return json_response(out[:500])
    except Exception as e:
        return _err(f"slave users failed: {e}", 500)


async def handle_slave_calibrate(request):
    """一键校准全员奴隶身价：将全库所有 <=0 的身价批量修复为最新初始身价"""
    try:
        data = await get_req_json(request, default={})

        init_price = int(data.get("price", 0) or 0)
        if init_price <= 0:
            init_price = ST.cfgi("费用配置", "初始身价", 500) if hasattr(ST, "cfgi") else 500
        if init_price <= 0:
            init_price = 500

        fixed_count = 0
        gids = set()
        if ST._DB:
            for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM groups").fetchall():
                if str(g_id).isdigit(): gids.add(str(g_id))
            for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM wallet").fetchall():
                if str(g_id).isdigit(): gids.add(str(g_id))
            for (g_id,) in ST._DB.execute("SELECT DISTINCT gid FROM accounts").fetchall():
                if str(g_id).isdigit(): gids.add(str(g_id))

        for g in gids:
            try:
                st = slave.state(g)
                # 检查已开户用户
                for qq in list(st.sections()):
                    if not qq.isdigit(): continue
                    u = st[qq]
                    p = int(u.get("price", "0") or 0)
                    if p <= 0:
                        u["price"] = str(init_price)
                        st.mark_dirty(qq)
                        fixed_count += 1
                # 检查该群 wallet 玩家
                if ST._DB:
                    w_rows = ST._DB.execute("SELECT qq FROM wallet WHERE gid=?", (int(g),)).fetchall()
                    for (w_qq,) in w_rows:
                        w_qq = str(w_qq)
                        if not st.has_section(w_qq):
                            u = slave.U(st, w_qq)
                            u["price"] = str(init_price)
                            st.mark_dirty(w_qq)
                            fixed_count += 1
                slave.save(g)
            except Exception:
                continue

        ST.flush_all()
        return json_response({
            "ok": True,
            "fixed_count": fixed_count,
            "initial_price": init_price,
            "msg": f"已成功校准 {fixed_count} 名用户的奴隶身价为 {init_price} {ST.coin_name() if hasattr(ST, 'coin_name') else '金币'}！"
        })
    except Exception as e:
        return _err(f"slave calibrate failed: {e}", 500)


async def handle_spirit_users(request):
    try:
        gid = get_req_query(request, "gid", "").strip()
        if not gid:
            j = await get_req_json(request, default={})
            if isinstance(j, dict) and j.get("gid"):
                gid = str(j.get("gid")).strip()
        out = []
        q = "SELECT gid, qq, data FROM accounts"
        args = ()
        if gid and gid.isdigit():
            q += " WHERE gid=?"
            args = (int(gid),)
        elif gid and not gid.isdigit():
            rows = []
            return json_response([])
        rows = ST._DB.execute(q, args).fetchall() if ST._DB else []
        for g, qq, data in rows:
            g = str(g); qq = str(qq)
            try:
                kv = json.loads(data or "{}")
            except Exception:
                kv = {}
            sp_raw = kv.get("spirits", "")
            sp = {}
            if isinstance(sp_raw, dict):
                sp = sp_raw
            elif isinstance(sp_raw, str) and sp_raw.strip():
                try:
                    sp = json.loads(sp_raw)
                except Exception:
                    sp = {}
            if not isinstance(sp, dict) or not sp.get("list"):
                continue
            lst = sp.get("list") if isinstance(sp.get("list"), list) else []
            if not lst:
                continue

            def _power(it):
                try:
                    return int(it.get("level", 1)) * (int(it.get("hp", 0)) + int(it.get("atk", 0)) + int(it.get("def", 0)) + int(it.get("spa", 0)) + int(it.get("spd", 0))) // 5
                except Exception:
                    return 0

            active = str(sp.get("active", "") or "")
            bag = sp.get("bag", {}) if isinstance(sp.get("bag"), dict) else {}
            total_power = sum(_power(it) for it in lst)
            best = max(lst, key=_power) if lst else {}
            best_name = best.get("name", "") if isinstance(best, dict) else ""
            max_lv = max((int(it.get("level", 1)) for it in lst), default=1)
            out.append({
                "gid": g,
                "qq": qq,
                "name": getattr(slave, "NOTE_NAMES", {}).get(qq, kv.get("name", "") or qq),
                "count": len(lst),
                "active": active,
                "best": best_name,
                "max_level": max_lv,
                "total_power": total_power,
                "bag_count": len(bag),
                "bag": bag,
            })
        out.sort(key=lambda x: -x["total_power"])
        return json_response(out[:300])
    except Exception as e:
        return _err(f"spirit users failed: {e}", 500)


def _raw_spirit_cfg(key):
    """读精灵图鉴原始配置（未配置/非法返回 {}，不回退内置；回退由引擎 _SPIRITS/_MAPS/_SHOP 负责）"""
    try:
        try:
            from ...engines import spirit  # noqa
        except ImportError:
            pass
        v = ST.cfg("精灵图鉴", key, "")
    except Exception:
        return {}
    if isinstance(v, dict):
        return v
    if v:
        try:
            d = json.loads(v)
            if isinstance(d, dict):
                return d
        except Exception:
            pass
    return {}


def _load_spirit_data():
    try:
        try:
            from ...engines import spirit
        except ImportError:
            import spirit  # type: ignore
        sp = dict(spirit._SPIRITS() or {})  # type: ignore
        mp = dict(spirit._MAPS() or {})
        sh = dict(spirit._SHOP() or {})
        return {"spirits": sp, "maps": mp, "shop": sh}
    except Exception:
        try:
            try:
                from ...engines import spirit_data as SD  # type: ignore
            except ImportError:
                import spirit_data as SD  # type: ignore
            return {"spirits": dict(getattr(SD, "SPIRITS", {})), "maps": dict(getattr(SD, "MAPS", {})), "shop": dict(getattr(SD, "SHOP", {}))}
        except Exception:
            return {"spirits": {}, "maps": {}, "shop": {}}


async def handle_spirits_get(request):
    data = _load_spirit_data()
    # 下发原始配置 + 内置基线：前端如实展示“未自定义/已自定义”，空即内置回退
    try:
        raw = {k: _raw_spirit_cfg(k) for k in ("spirits", "maps", "shop")}
        data = dict(data)
        data["_raw"] = raw
        try:
            try:
                from ...engines import spirit_data as _SDB  # type: ignore
            except ImportError:
                import spirit_data as _SDB  # type: ignore
            data["_builtin"] = {
                "spirits": dict(getattr(_SDB, "SPIRITS", {}) or {}),
                "maps": dict(getattr(_SDB, "MAPS", {}) or {}),
                "shop": dict(getattr(_SDB, "SHOP", {}) or {}),
            }
        except Exception:
            data["_builtin"] = {"spirits": {}, "maps": {}, "shop": {}}
        data["_meta"] = {
            "configured": {k: bool(raw.get(k)) for k in ("spirits", "maps", "shop")},
            "builtin": {k: len((data.get("_builtin") or {}).get(k) or {}) for k in ("spirits", "maps", "shop")},
        }
    except Exception:
        pass
    return json_response(data)


async def handle_spirits_save(request):
    payload = await get_req_json(request, default={})
    if not isinstance(payload, dict):
        return _err("payload must be dict", 400)
    saved = []
    for key in ("spirits", "maps", "shop"):
        if key not in payload:
            continue
        val = payload[key]
        if not isinstance(val, dict):
            return _err(f"{key} must be dict", 400)
        # 入库整形：只保留结构合法的条目，脏数据就地清洗，保证自助添加不炸运行时
        try:
            if key == "spirits":
                _num_fields = ("hp", "atk", "def", "spa", "spd", "spe", "lv")
                _clean = {}
                for _n, _it in val.items():
                    if not isinstance(_it, dict):
                        continue
                    _o = {"type": str(_it.get("type", "") or "")}
                    for _f in _num_fields:
                        try:
                            _o[_f] = int(float(_it.get(_f, 0) or 0))
                        except Exception:
                            _o[_f] = 0
                    _o["evolve"] = str(_it.get("evolve", "") or "")
                    _o["img"] = str(_it.get("img", "") or "")
                    _clean[str(_n)] = _o
                val = _clean
            elif key == "maps":
                _clean = {}
                for _n, _m in val.items():
                    if not isinstance(_m, dict):
                        continue
                    try:
                        _lv = int(float(_m.get("lv", 1) or 1))
                    except Exception:
                        _lv = 1
                    _drops = _m.get("drops", [])
                    if isinstance(_drops, str):
                        _drops = [s.strip() for s in re.split(r"[,，]", _drops) if s.strip()]
                    if not isinstance(_drops, list):
                        _drops = []
                    _clean[str(_n)] = {"lv": _lv if _lv >= 1 else 1,
                                       "drops": [str(x) for x in _drops if str(x).strip()]}
                val = _clean
            elif key == "shop":
                _clean = {}
                for _n, _it in val.items():
                    if not isinstance(_it, dict):
                        continue
                    try:
                        _price = int(float(_it.get("price", 0) or 0))
                    except Exception:
                        _price = 0
                    try:
                        _effect = int(float(_it.get("effect", 0) or 0))
                    except Exception:
                        _effect = 0
                    _clean[str(_n)] = {"price": _price if _price >= 0 else 0,
                                       "attr": str(_it.get("attr", "") or ""),
                                       "effect": _effect if _effect >= 0 else 0}
                val = _clean
        except Exception:
            pass
        ST.set_ini("精灵图鉴", key, json.dumps(val, ensure_ascii=False))
        saved.append(key)
    if not saved:
        return _err("no data (want spirits/maps/shop)", 400)
    try:
        ST.save_config()
        st_cfg = dict(ST._CONFIG or {})
        ST.sync_astrbot_config(st_cfg)
    except Exception:
        pass
    return json_response({"saved": True, "keys": saved})


async def handle_gacha_weapons(request):
    """抽奖武器池（img/gacha SSR/SR/R 文件名去扩展名；附精确图片路径供自动匹配预览）"""
    try:
        try:
            from ...engines import slave as _sl
        except ImportError:
            import slave as _sl  # type: ignore
        try:
            _base = _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
        except Exception:
            _base = ""
        out, img = {}, {}
        for rar in ("SSR", "SR", "R"):
            try:
                names = []
                for p in (_sl._gacha_pool(rar) or []):
                    try:
                        nm = _os.path.splitext(_os.path.basename(p))[0]
                        names.append(nm)
                        try:
                            rp = _os.path.relpath(p, _base).replace(_os.sep, "/") if _base else ""
                            if rp and not rp.startswith(".."):
                                img.setdefault(nm, rp)
                        except Exception:
                            pass
                    except Exception:
                        pass
                out[rar] = sorted(set(names))
            except Exception:
                out[rar] = []
        return json_response({"ok": True, "pool": out, "img": img})
    except Exception as e:
        return _err(f"gacha weapons failed: {e}", 500)


_POOL_RARS = ("SSR", "SR", "R")
_POOL_IMG_EXTS = (".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp")
_POOL_THUMB_MAX = 200 * 1024


def _pool_slave():
    try:
        from ...engines import slave as _sl
        return _sl
    except ImportError:
        import slave as _sl  # type: ignore
        return _sl


def _pool_base():
    try:
        return _os.path.dirname(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))))
    except Exception:
        return ""


def _pool_dir(rar):
    """生效稀有度目录（与引擎 _gacha_pool 同口径：持久化优先）"""
    _sl = _pool_slave()
    try:
        files = _sl._gacha_pool(rar) or []
        if files:
            return _os.path.dirname(_os.path.abspath(files[0]))
    except Exception:
        pass
    base = _pool_base()
    try:
        pers = ST.get_persistent_data_dir(base) if hasattr(ST, "get_persistent_data_dir") else ""
    except Exception:
        pers = ""
    d = _os.path.join(pers or _os.path.join(base, "data"), "img", "gacha", rar)
    try:
        _os.makedirs(d, exist_ok=True)
    except Exception:
        pass
    return d


def _pool_bust(rar=""):
    try:
        _sl = _pool_slave()
        if hasattr(_sl, "_GACHA_CACHE"):
            if rar:
                _sl._GACHA_CACHE.pop(rar, None)
                try:
                    _sl._GACHA_CACHE_TS.pop(rar, None)
                except Exception:
                    pass
            else:
                _sl._GACHA_CACHE.clear()
                try:
                    _sl._GACHA_CACHE_TS.clear()
                except Exception:
                    pass
    except Exception:
        pass


def _pool_clean_stem(s):
    s = str(s or "").strip()
    if not s or len(s) > 64 or s in (".", ".."):
        return ""
    if re.search(r'[\/\\:*?"<>|\x00-\x1f]', s):
        return ""
    return s


def _pool_find(stem):
    """按武器名找生效文件，返回 (rar, abspath) 或 (None, None)"""
    _sl = _pool_slave()
    want = str(stem or "")
    for rar in _POOL_RARS:
        try:
            for p in (_sl._gacha_pool(rar) or []):
                try:
                    if _os.path.splitext(_os.path.basename(p))[0] == want and _os.path.isfile(p):
                        return rar, _os.path.abspath(p)
                except Exception:
                    continue
        except Exception:
            continue
    return None, None


def _pool_thumb(p):
    try:
        sz = _os.path.getsize(p)
    except Exception:
        return ""
    if not (0 < sz <= _POOL_THUMB_MAX):
        return ""
    try:
        with open(p, "rb") as f:
            raw = f.read()
        ext = _os.path.splitext(p)[1].lower().lstrip(".") or "png"
        if ext == "jpg":
            ext = "jpeg"
        return "data:image/%s;base64,%s" % (ext, base64.b64encode(raw).decode("ascii"))
    except Exception:
        return ""


def _pool_item(rar, p, base):
    try:
        fn = _os.path.basename(p)
        nm = _os.path.splitext(fn)[0]
        try:
            sz = _os.path.getsize(p)
        except Exception:
            sz = 0
        try:
            rp = _os.path.relpath(p, base).replace(_os.sep, "/") if base else ""
            if rp.startswith(".."):
                rp = ""
        except Exception:
            rp = ""
        return {"name": nm, "file": fn, "rar": rar, "img": rp, "size": sz}
    except Exception:
        return None


def _pool_write_file(rar, stem, data, ext):
    """写池文件：先清同名旧文件（扩展名可能不同），再写入；返回 abspath"""
    d = _pool_dir(rar)
    try:
        for fn in _os.listdir(d):
            try:
                if _os.path.splitext(fn)[0] == stem and _os.path.isfile(_os.path.join(d, fn)):
                    _os.remove(_os.path.join(d, fn))
            except Exception:
                continue
    except Exception:
        pass
    dst = _os.path.join(d, stem + ext)
    with open(dst, "wb") as w:
        w.write(data)
    _pool_bust(rar)
    return dst


async def handle_pool_list(request):
    """抽奖武器池列表（生效目录，附可配属性；无缩略图，预览按需取）"""
    try:
        _sl = _pool_slave()
        base = _pool_base()
        try:
            _attrs = _sl._weapon_attrs_raw() if hasattr(_sl, "_weapon_attrs_raw") else {}
            if not isinstance(_attrs, dict):
                _attrs = {}
        except Exception:
            _attrs = {}
        try:
            _legacy = _sl._weapon_shop() if hasattr(_sl, "_weapon_shop") else {}
            if not isinstance(_legacy, dict):
                _legacy = {}
        except Exception:
            _legacy = {}
        out = {}
        for rar in _POOL_RARS:
            items = []
            try:
                for p in (_sl._gacha_pool(rar) or []):
                    it = _pool_item(rar, p, base)
                    if not it:
                        continue
                    try:
                        a = _attrs.get(it["name"]) or {}
                        if not isinstance(a, dict):
                            a = {}
                        atk = a.get("atk", "")
                        desc = a.get("desc", "")
                        if (atk in ("", None)) and isinstance(_legacy.get(it["name"]), dict):
                            atk = _legacy[it["name"]].get("atk", "")
                        if (not desc) and isinstance(_legacy.get(it["name"]), dict):
                            desc = _legacy[it["name"]].get("desc", "")
                        try:
                            atk = int(float(atk or 0))
                        except Exception:
                            atk = 0
                        it["attrs"] = {"atk": atk, "desc": str(desc or "")}
                    except Exception:
                        it["attrs"] = {"atk": 0, "desc": ""}
                    items.append(it)
            except Exception:
                pass
            items.sort(key=lambda x: x["name"])
            out[rar] = items
        return json_response({"ok": True, "pool": out})
    except Exception as e:
        return _err(f"pool list failed: {e}", 500)


async def handle_pool_attrs(request):
    """抽奖武器属性保存（{attrs: {名: {atk, desc}}, full: 0/1}，只写 weapon_attrs，不碰文件；
    默认合并：只更新 payload 出现的名；full=1 时全量替换（恢复默认用））"""
    try:
        data = await get_req_json(request, default={})
        if not isinstance(data, dict):
            return _err("bad payload", 400)
        raw = data.get("attrs", data)
        if not isinstance(raw, dict):
            return _err("attrs must be dict", 400)
        full = bool(data.get("full", False)) if isinstance(data, dict) else False
        try:
            _sl0 = _pool_slave()
            base0 = _sl0._weapon_attrs_raw() if hasattr(_sl0, "_weapon_attrs_raw") else {}
            merged = dict(base0) if isinstance(base0, dict) else {}
        except Exception:
            merged = {}
        if full:
            merged = {}
        for name, v in raw.items():
            name = str(name or "").strip()
            if not name:
                continue
            if not isinstance(v, dict):
                continue
            try:
                atk = int(float(v.get("atk", 0) or 0))
            except Exception:
                atk = 0
            if atk < 0:
                atk = 0
            desc = str(v.get("desc", "") or "").strip()
            if atk or desc:
                merged[name] = {"atk": atk, "desc": desc}
            elif name in merged:
                merged.pop(name, None)
        clean = {k: v for k, v in merged.items() if isinstance(v, dict)}
        ST.set_ini("商城图鉴", "weapon_attrs", json.dumps(clean, ensure_ascii=False))
        try:
            ST.save_config()
        except Exception:
            pass
        try:
            st_cfg = dict(ST._CONFIG or {})
            ST.sync_astrbot_config(st_cfg)
        except Exception:
            pass
        return json_response({"ok": True, "count": len(clean)})
    except Exception as e:
        return _err(f"pool attrs failed: {e}", 500)


async def handle_pool_replace_path(request):
    """内置选图：用服务器已有图片文件覆盖池武器图（{name, src}，src 须在插件/数据目录内）"""
    try:
        try:
            from .images import _safe_path as _img_safe
        except ImportError:
            from images import _safe_path as _img_safe  # type: ignore
        data = await get_req_json(request, default={})
        if not isinstance(data, dict):
            return _err("bad payload", 400)
        name = str(data.get("name", "") or "").strip()
        src = str(data.get("src", "") or data.get("path", "") or "").strip()
        if not name or not src:
            return _err("name/src required", 400)
        name = _pool_clean_stem(name)
        if not name:
            return _err("name invalid", 400)
        rar, _old = _pool_find(name)
        if not _old:
            # 新建模式（添加武器用内置图）：rar 必传
            rar = str(data.get("rar", "") or "").strip().upper()
            if rar not in _POOL_RARS:
                return _err("not found, rar required to create", 404)
            _old = None
        fp = _img_safe(src, _pool_base())
        if not fp or not _os.path.isfile(fp):
            return _err("源文件不存在或越界", 400)
        ext = _os.path.splitext(fp)[1].lower()
        if ext not in _POOL_IMG_EXTS:
            return _err("源文件非图片", 400)
        with open(fp, "rb") as f:
            blob = f.read()
        if not blob:
            return _err("源文件为空", 400)
        _pool_write_file(rar, name, blob, ext)
        return json_response({"ok": True, "name": name})
    except Exception as e:
        return _err(f"pool replace failed: {e}", 500)


async def handle_pool_rename(request):
    """抽奖武器改名（仅改文件名主干，扩展名保留）"""
    try:
        data = await get_req_json(request, default={})
        if not isinstance(data, dict):
            return _err("bad payload", 400)
        old = str(data.get("old", "") or data.get("name", "") or "").strip()
        new = _pool_clean_stem(data.get("new", ""))
        if not old or not new:
            return _err("old/new required", 400)
        rar, src = _pool_find(old)
        if not src:
            return _err("not found", 404)
        if new == old:
            return json_response({"ok": True, "name": new})
        dst = _os.path.join(_os.path.dirname(src), new + _os.path.splitext(src)[1])
        if _os.path.exists(dst):
            return _err("同名文件已存在", 400)
        _os.rename(src, dst)
        _pool_bust(rar)
        return json_response({"ok": True, "name": new})
    except Exception as e:
        return _err(f"pool rename failed: {e}", 500)


async def handle_pool_move(request):
    """抽奖武器改稀有度（跨目录移动文件）"""
    try:
        data = await get_req_json(request, default={})
        if not isinstance(data, dict):
            return _err("bad payload", 400)
        name = str(data.get("name", "") or "").strip()
        to = str(data.get("to", "") or data.get("rar", "") or "").strip().upper()
        if not name or to not in _POOL_RARS:
            return _err("name/to required", 400)
        rar, src = _pool_find(name)
        if not src:
            return _err("not found", 404)
        if rar == to:
            return json_response({"ok": True, "rar": to})
        d = _pool_dir(to)
        dst = _os.path.join(d, _os.path.basename(src))
        if _os.path.exists(dst):
            return _err("目标稀有度已存在同名文件", 400)
        _shutil.move(src, dst)
        _pool_bust(rar)
        _pool_bust(to)
        return json_response({"ok": True, "rar": to})
    except Exception as e:
        return _err(f"pool move failed: {e}", 500)


async def handle_pool_delete(request):
    """抽奖武器删除（删文件，需前端二次确认）"""
    try:
        data = await get_req_json(request, default={})
        if not isinstance(data, dict):
            return _err("bad payload", 400)
        name = str(data.get("name", "") or "").strip()
        if not name:
            return _err("name required", 400)
        rar, src = _pool_find(name)
        if not src:
            return _err("not found", 404)
        _os.remove(src)
        _pool_bust(rar)
        return json_response({"ok": True})
    except Exception as e:
        return _err(f"pool delete failed: {e}", 500)


async def handle_pool_img(request):
    """抽奖武器单张预览（按需取缩略图，列表不再批量下发）"""
    try:
        data = await get_req_json(request, default={})
        name = ""
        if isinstance(data, dict):
            name = str(data.get("name", "") or "").strip()
        if not name:
            name = (get_req_query(request, "name", "") or "").strip()
        if not name:
            return _err("name required", 400)
        _, src = _pool_find(name)
        if not src:
            return _err("not found", 404)
        thumb = _pool_thumb(src)
        if not thumb:
            return _err("too large or unreadable", 400)
        return json_response({"ok": True, "name": name, "thumb": thumb})
    except Exception as e:
        return _err(f"pool img failed: {e}", 500)


async def handle_pool_upload(request):
    """抽奖武器上传（multipart file + ?rar=SSR&replace=0&name=，存生效目录；replace=1 时覆盖同名）"""
    try:
        rar = (get_req_query(request, "rar", "") or "").strip().upper()
        replace = (get_req_query(request, "replace", "") or "").strip().lower() in ("1", "true")
        fixname = (get_req_query(request, "name", "") or "").strip()
        if rar not in _POOL_RARS:
            try:
                p = await get_req_json(request, default={})
                if isinstance(p, dict):
                    rar = str(p.get("rar", "") or "").strip().upper()
            except Exception:
                pass
        if rar not in _POOL_RARS:
            return _err("rar required (SSR/SR/R)", 400)
        try:
            form = await request.files()
        except Exception:
            form = {}
        f = None
        if isinstance(form, dict):
            f = form.get("file")
            if not f:
                for _k in ("files", "fileUpload", "upload", "data"):
                    if _k in form:
                        f = form.get(_k)
                        if f:
                            break
        elif hasattr(form, "filename") or hasattr(form, "read"):
            f = form
        # base64 直传（iframe 桥 postMessage 无法克隆 FormData 时用）
        b64_name, b64_data = "", b""
        if not f:
            try:
                pj = await get_req_json(request, default={})
                if isinstance(pj, dict):
                    b64_name = str(pj.get("filename", "") or "").strip()
                    _b64s = str(pj.get("file_base64", "") or pj.get("data", "") or "")
                    if "," in _b64s:
                        _b64s = _b64s.split(",", 1)[1]
                    if _b64s.strip():
                        b64_data = base64.b64decode(_b64s.strip())
            except Exception:
                b64_data = b""
        if not f and not b64_data:
            return _err("no file", 400)
        if b64_data:
            filename = _os.path.basename(b64_name or "upload.bin")
            stem, ext = _os.path.splitext(filename)
            stem = _pool_clean_stem(stem)
            ext = ext.lower()
            if not stem or ext not in _POOL_IMG_EXTS:
                return _err("仅支持图片文件", 400)
            data = bytes(b64_data)
            if not data:
                return _err("empty file", 400)
        else:
            filename = str(getattr(f, "filename", None) or getattr(f, "name", None) or "").strip()
            filename = _os.path.basename(filename)
            stem, ext = _os.path.splitext(filename)
            stem = _pool_clean_stem(stem)
            ext = ext.lower()
            if not stem or ext not in _POOL_IMG_EXTS:
                return _err("仅支持图片文件", 400)
            data = b""
            try:
                val = f.read() if hasattr(f, "read") else None
                if val is not None:
                    import inspect
                    data = await val if inspect.isawaitable(val) else val
                if not data and hasattr(f, "file"):
                    try:
                        ff = getattr(f, "file")
                        if hasattr(ff, "read"):
                            data = ff.read()
                    except Exception:
                        pass
            except Exception:
                data = b""
            if isinstance(data, str):
                data = data.encode("utf-8", errors="ignore")
            if not data:
                return _err("empty file", 400)
        if fixname:
            stem = _pool_clean_stem(fixname) or stem
        if not stem:
            return _err("文件名无效", 400)
        if replace:
            _pool_write_file(rar, stem, data, ext)
            return json_response({"ok": True, "name": stem, "rar": rar})
        dst = _os.path.join(_pool_dir(rar), stem + ext)
        if _os.path.exists(dst):
            return _err("同名文件已存在", 400)
        with open(dst, "wb") as w:
            w.write(data)
        _pool_bust(rar)
        return json_response({"ok": True, "name": stem, "rar": rar})
    except Exception as e:
        return _err(f"pool upload failed: {e}", 500)
