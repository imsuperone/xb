# -*- coding: utf-8 -*-
"""
小白机器人 WebDAV 自动云备份模块 (零依赖纯标准库实现)
支持坚果云、Alist、InfiniCloud、Nextcloud、群晖/QNAP 等任意标准 WebDAV 服务
"""
import os
import ssl
import time
import base64
import threading
import urllib.request
import urllib.error

try:
    from .. import store as ST
    from . import logger as _logger
except ImportError:
    import store as ST
    try:
        from core import logger as _logger
    except ImportError:
        _logger = None


def is_enabled():
    """检查 WebDAV 自动备份是否启用且配置完整"""
    sw = ST.cfg("备份配置", "WebDAV备份开关", "假").strip().lower()
    if sw not in ("真", "true", "1", "on", "yes"):
        return False
    url = ST.cfg("备份配置", "WebDAV服务器地址", "").strip()
    return bool(url)


def _clean_url(url):
    u = str(url or "").strip()
    if not u:
        return ""
    if not (u.startswith("http://") or u.startswith("https://")):
        u = "https://" + u
    return u.rstrip("/")


def _get_auth_header(user, pwd):
    raw = f"{user}:{pwd}".encode("utf-8")
    return "Basic " + base64.b64encode(raw).decode("ascii")


def _make_ssl_context():
    ctx = ssl.create_default_context()
    # 兼容私有 NAS 或自签名证书
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


_VERIFIED_REMOTE_DIRS = set()


def _ensure_remote_dir(base_url, remote_dir, auth, timeout=6):
    """递归检查并创建 WebDAV 远端多级目录 (MKCOL)，带内存去重防触发服务商 429 频控"""
    cache_key = f"{base_url}|{remote_dir}|{auth}"
    if cache_key in _VERIFIED_REMOTE_DIRS:
        return True
    parts = [p for p in remote_dir.strip("/").split("/") if p]
    cur_url = base_url.rstrip("/")
    for part in parts:
        cur_url = f"{cur_url}/{part}"
        try:
            # WebDAV 集合标准规定集合 URL 须以斜杠结尾，避免 301 重定向将 MKCOL 变更为 GET 导致目录未创建
            req = urllib.request.Request(f"{cur_url}/", method="MKCOL")
            req.add_header("Authorization", auth)
            req.add_header("User-Agent", "XBBot-WebDAV-Backup/1.0")
            with urllib.request.urlopen(req, timeout=timeout, context=_make_ssl_context()):
                pass
        except urllib.error.HTTPError as e:
            # 405 Method Not Allowed / 301 / 409 通常表示目录已存在，属于正常情况
            if e.code in (405, 301, 409, 200, 201):
                pass
            elif e.code == 429:
                # 触发服务商频控，通常目录已就绪，跳过后续以保护配额
                break
        except Exception:
            pass
    _VERIFIED_REMOTE_DIRS.add(cache_key)
    return True


def upload_backup(local_path):
    """
    同步上传单个本地备份文件到 WebDAV 远端
    :param local_path: 本地 .db 备份文件路径
    :return: (bool, str) 是否成功及详情信息
    """
    if not os.path.isfile(local_path):
        return False, f"本地文件不存在: {local_path}"

    raw_url = ST.cfg("备份配置", "WebDAV服务器地址", "").strip()
    if not raw_url:
        return False, "未配置 WebDAV 服务器地址"
    base_url = _clean_url(raw_url)
    user = ST.cfg("备份配置", "WebDAV用户名", "").strip()
    pwd = ST.cfg("备份配置", "WebDAV应用密码", "").strip()
    rdir = ST.cfg("备份配置", "WebDAV远端目录", "/xbbot_backup/").strip() or "/xbbot_backup/"

    auth = _get_auth_header(user, pwd)

    try:
        _ensure_remote_dir(base_url, rdir, auth, timeout=6)
    except Exception:
        pass

    fname = os.path.basename(local_path)
    clean_rdir = rdir.strip("/")
    target_url = f"{base_url}/{clean_rdir}/{fname}" if clean_rdir else f"{base_url}/{fname}"

    try:
        with open(local_path, "rb") as f:
            data = f.read()

        req = urllib.request.Request(target_url, data=data, method="PUT")
        req.add_header("Authorization", auth)
        req.add_header("Content-Type", "application/x-sqlite3")
        req.add_header("User-Agent", "XBBot-WebDAV-Backup/1.0")
        req.add_header("Content-Length", str(len(data)))

        with urllib.request.urlopen(req, timeout=25, context=_make_ssl_context()) as resp:
            status = getattr(resp, "status", getattr(resp, "code", 200))
            if status in (200, 201, 204):
                sz_kb = len(data) // 1024
                msg = f"WebDAV 备份成功上传: {fname} ({sz_kb} KB) -> {target_url}"
                if _logger:
                    _logger.info(msg)
                return True, msg
            return False, f"WebDAV 服务器返回非预期状态码: {status}"
    except urllib.error.HTTPError as e:
        if e.code == 429:
            msg = "WebDAV 上传触发服务商频控 (HTTP 429 Too Many Requests: 坚果云等限制频次，凭证正常，请稍候再试)"
        else:
            msg = f"WebDAV 上传 HTTP 错误 {e.code}: {e.reason}"
        if _logger:
            _logger.error(msg)
        return False, msg
    except (urllib.error.URLError, TimeoutError) as e:
        msg = f"WebDAV 上传网络超时或连接失败: {getattr(e, 'reason', e)}"
        if _logger:
            _logger.error(msg)
        return False, msg
    except Exception as e:
        msg = f"WebDAV 上传异常: {e}"
        if _logger:
            _logger.error(msg)
        return False, msg


def test_connection(url=None, user=None, pwd=None, rdir=None):
    """测试 WebDAV 连接与鉴权有效性 (支持直接传参或回退读取当前配置)"""
    raw_url = str(url if url is not None else ST.cfg("备份配置", "WebDAV服务器地址", "")).strip()
    if not raw_url:
        return False, "请先填写 WebDAV 服务器地址"
    base_url = _clean_url(raw_url)
    user = str(user if user is not None else ST.cfg("备份配置", "WebDAV用户名", "")).strip()
    pwd = str(pwd if pwd is not None else ST.cfg("备份配置", "WebDAV应用密码", "")).strip()
    rdir = str(rdir if rdir is not None else (ST.cfg("备份配置", "WebDAV远端目录", "/xbbot_backup/").strip() or "/xbbot_backup/")).strip()

    auth = _get_auth_header(user, pwd)

    # 1. 优先采用 RFC 4918 标准 OPTIONS 轻量探测（几乎所有 WebDAV 均支持，且不消耗目录列表配额，防坚果云 429 频控）
    try:
        req = urllib.request.Request(f"{base_url}/", method="OPTIONS")
        req.add_header("Authorization", auth)
        req.add_header("User-Agent", "XBBot-WebDAV-Backup/1.0")
        with urllib.request.urlopen(req, timeout=8, context=_make_ssl_context()) as resp:
            status = getattr(resp, "status", getattr(resp, "code", 200))
            if status in (200, 204):
                _ensure_remote_dir(base_url, rdir, auth, timeout=6)
                return True, f"WebDAV 连接与鉴权成功！(服务器状态: {status}, 远端目录: {rdir})"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "WebDAV 用户名或应用密码错误 (HTTP 401 Unauthorized)"
        if e.code == 403:
            return False, "WebDAV 拒绝访问 (HTTP 403 Forbidden)"
        if e.code == 404:
            return False, "WebDAV 服务器路径不存在 (HTTP 404 Not Found)"
        if e.code == 429:
            return False, "WebDAV 连接与鉴权正常，但触发服务商频控限制 (HTTP 429 Too Many Requests: 坚果云等限制频次，请等待 1-2 分钟后再试)"
        # 405 Method Not Allowed 或 501，继续回退 PROPFIND
    except (urllib.error.URLError, TimeoutError) as e:
        reason = getattr(e, 'reason', e)
        return False, f"WebDAV 连接超时或目标主机无法连接（8秒超时）: {reason}"
    except Exception:
        pass

    # 2. 回退 PROPFIND 探测
    try:
        req = urllib.request.Request(f"{base_url}/", method="PROPFIND")
        req.add_header("Authorization", auth)
        req.add_header("Depth", "0")
        req.add_header("User-Agent", "XBBot-WebDAV-Backup/1.0")
        with urllib.request.urlopen(req, timeout=8, context=_make_ssl_context()) as resp:
            status = getattr(resp, "status", getattr(resp, "code", 200))
            if status in (200, 207):
                _ensure_remote_dir(base_url, rdir, auth, timeout=6)
                return True, f"WebDAV 连接与鉴权成功！(PROPFIND 响应: {status}, 远端目录: {rdir})"
            return False, f"WebDAV 响应非预期状态码: {status}"
    except urllib.error.HTTPError as e:
        if e.code == 401:
            return False, "WebDAV 用户名或应用密码错误 (HTTP 401 Unauthorized)"
        if e.code == 403:
            return False, "WebDAV 拒绝访问 (HTTP 403 Forbidden)"
        if e.code == 404:
            return False, "WebDAV 服务器路径不存在 (HTTP 404 Not Found)"
        if e.code == 429:
            return False, "WebDAV 连接与鉴权正常，但触发服务商频控限制 (HTTP 429 Too Many Requests: 坚果云等限制频次，请等待 1-2 分钟后再试)"
        return False, f"WebDAV HTTP 错误 {e.code}: {e.reason}"
    except (urllib.error.URLError, TimeoutError) as e:
        reason = getattr(e, 'reason', e)
        return False, f"WebDAV 连接超时或目标主机无法连接（8秒超时）: {reason}"
    except Exception as e:
        return False, f"WebDAV 连接异常: {e}"


def async_upload_backup(local_path):
    """异步后台上传备份文件，绝不阻塞主消息链路"""
    if not is_enabled():
        return
    def _worker():
        try:
            upload_backup(local_path)
        except Exception:
            pass
    t = threading.Thread(target=_worker, name="WebDAV-Upload", daemon=True)
    t.start()
