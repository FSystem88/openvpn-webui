import asyncio
import base64
import hashlib
import hmac
import ipaddress
import json
import os
import re
import secrets
import shutil
import socket
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import uvicorn

from database import (
    ADBLOCK_DNS_IP,
    CCD_DIR,
    DB_PATH,
    DNSMASQ_ADBLOCK_CONF,
    DOMAIN,
    INLINE_DIR,
    OVPN_PORT,
    PANEL_PORT,
    SERVER_CONF_PATH,
    get_admin_login,
    get_admin_password_hash,
    get_all_client_meta,
    get_all_settings,
    get_current_domain,
    get_current_mgmt,
    get_current_port,
    get_current_proto,
    get_db,
    get_domain_retention,
    get_ovpn_subnet_cidr,
    get_session_max_age,
    get_setting,
    hash_password,
    init_db,
    set_bulk_client_speed_limits,
    set_setting,
    set_settings_bulk,
    upsert_client_meta,
    verify_password,
)
from openvpn_manager import (
    apply_bidirectional_speed_limits_sync,
    client_exists,
    create_client_sync,
    delete_client_completely_sync,
    domain_tracker,
    flush_traffic_deltas_to_db,
    generate_config,
    get_pki_clients_fast,
    get_server_status,
    invalidate_pki_cache,
    invalidate_server_status_cache,
    parse_existing_server_conf_into_db,
    reload_sniffer_ignored_cache,
    revoke_client_sync,
    speed_monitor,
    sync_openvpn_server_conf_from_settings,
    unrevoke_client_sync,
)
from network_manager import (
    apply_adblock_state_sync,
    apply_quic_block_sync,
    apply_routing_mode_sync,
    apply_torrent_block_sync,
    ensure_dnsmasq_installed_sync,
    ensure_system_configs,
    fetch_and_parse_adlist,
    get_system_stats,
    parse_adlist_content,
    rebuild_dnsmasq_adblock_conf_sync,
    reload_ipset_sync,
    setup_remote_tunnel_sync,
    task_tracker,
)
from ui_templates import LANDING_HTML, LOGIN_HTML, MAIN_HTML

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
SESSION_COOKIE = "openvpn_session"


async def live_speed_worker() -> None:
    db_counter = 0
    while True:
        try:
            await speed_monitor.update_tick()
            db_counter += 1
            if db_counter >= 15:
                await asyncio.to_thread(flush_traffic_deltas_to_db)
                db_counter = 0
        except Exception:
            pass
        await asyncio.sleep(1.0)


@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    reload_sniffer_ignored_cache()
    CCD_DIR.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(ensure_system_configs)
    task_speed = asyncio.create_task(live_speed_worker())
    from openvpn_manager import domain_sniffer_worker

    task_sniffer = asyncio.create_task(domain_sniffer_worker())
    yield
    task_speed.cancel()
    task_sniffer.cancel()
    await asyncio.to_thread(flush_traffic_deltas_to_db)


app = FastAPI(
    title="OpenVPN Control Center",
    version="9.0.0",
    lifespan=lifespan,
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)


def verify_login(username: str, password: str) -> bool:
    if not hmac.compare_digest(
        username.encode("utf-8"), get_admin_login().encode("utf-8")
    ):
        return False
    stored = get_admin_password_hash()
    if stored.startswith("scrypt$"):
        return verify_password(password, stored)
    pwd_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(pwd_hash, stored)


def create_session() -> str:
    session_id = secrets.token_urlsafe(24)
    ts = str(int(time.time()))
    payload = f"{session_id}:{ts}"
    sig = hmac.new(
        SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{payload}.{sig}"


def verify_session(session: Optional[str]) -> bool:
    if not session:
        return False
    try:
        payload, sig = session.rsplit(".", 1)
        expected = hmac.new(
            SESSION_SECRET.encode(), payload.encode(), hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(sig, expected):
            return False
        _, ts_str = payload.split(":", 1)
        if time.time() - int(ts_str) > get_session_max_age():
            return False
        return True
    except Exception:
        return False


def is_authenticated(request: Request) -> bool:
    return verify_session(request.cookies.get(SESSION_COOKIE))


@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if path in ["/login", "/logout"] or path.startswith("/d/"):
        return await call_next(request)

    if not is_authenticated(request):
        if path.startswith("/api/"):
            return Response(
                content=json.dumps({"success": False, "message": "Unauthorized"}),
                status_code=401,
                media_type="application/json",
            )
        return RedirectResponse("/login", status_code=303)

    return await call_next(request)


def encode_client_name(client_name: str) -> str:
    timestamp = str(int(time.time() / 3600))
    data = f"{client_name}:{timestamp}"
    sig = hmac.new(SECRET_KEY.encode(), data.encode(), hashlib.sha256).hexdigest()[:16]
    combined = f"{sig}:{client_name}:{timestamp}"
    return base64.urlsafe_b64encode(combined.encode()).decode()[::-1]


def decode_client_name(encoded: str) -> Optional[str]:
    try:
        combined = encoded[::-1]
        decoded = base64.urlsafe_b64decode(combined.encode()).decode()
        sig, client_name, timestamp = decoded.split(":", 2)
        expected = hmac.new(
            SECRET_KEY.encode(), f"{client_name}:{timestamp}".encode(), hashlib.sha256
        ).hexdigest()[:16]
        if not hmac.compare_digest(sig, expected):
            return None
        ts = int(timestamp) * 3600
        if abs(time.time() - ts) > 86400 * 30:
            return None
        return client_name
    except Exception:
        return None


def _run_tracked_task(task_id: str, title: str, fn, *args, **kwargs) -> None:
    task_tracker.start(task_id, title, progress=10, message="Выполняется...")
    try:
        res = fn(*args, **kwargs)
        if isinstance(res, tuple) and len(res) >= 2:
            ok, msg = bool(res[0]), str(res[1])
        else:
            ok, msg = bool(res), "OK"
        task_tracker.finish(task_id, ok=ok, message=msg)
    except Exception as e:
        task_tracker.finish(task_id, ok=False, message=str(e))


@app.get("/api/tasks/status")
async def api_tasks_status(task_id: Optional[str] = Query(None)):
    if task_id:
        return {"success": True, "task": task_tracker.get(task_id)}
    return {"success": True, "tasks": task_tracker.all()}


# ============================================================
# ADBLOCK API
# ============================================================

@app.get("/api/adblock/status")
async def api_adblock_status():
    def _get():
        enabled = get_setting("adblock_enabled", "0") == "1"
        dns_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
        res = subprocess.run(
            ["systemctl", "is-active", "dnsmasq"], capture_output=True, text=True
        )
        dnsmasq_active = res.stdout.strip() == "active"

        blocked_total = 0
        if DNSMASQ_ADBLOCK_CONF.exists():
            try:
                blocked_total = sum(
                    1
                    for line in DNSMASQ_ADBLOCK_CONF.read_text(
                        encoding="utf-8", errors="ignore"
                    ).splitlines()
                    if line.startswith("address=/")
                )
            except Exception:
                pass

        with get_db() as conn:
            lists = [
                dict(r)
                for r in conn.execute(
                    "SELECT id, url, list_type, domains_count, created_at FROM adblock_lists ORDER BY id DESC"
                ).fetchall()
            ]
            domains = [
                dict(r)
                for r in conn.execute(
                    "SELECT id, domain, list_type, created_at FROM adblock_domains ORDER BY id DESC"
                ).fetchall()
            ]

        return {
            "enabled": enabled,
            "dnsmasq_active": dnsmasq_active,
            "dns_ip": dns_ip,
            "blocked_total": blocked_total,
            "lists": lists,
            "domains": domains,
        }

    data = await asyncio.to_thread(_get)
    return {"success": True, "data": data}


@app.post("/api/adblock/toggle")
async def api_adblock_toggle(request: Request):
    try:
        data = await request.json()
        enable = bool(data.get("enable", False))
    except Exception:
        return {"success": False, "message": "Invalid JSON"}

    asyncio.create_task(
        asyncio.to_thread(
            _run_tracked_task,
            "adblock_toggle",
            "DNS AdBlock",
            apply_adblock_state_sync,
            enable,
            lambda p, m: task_tracker.update("adblock_toggle", p, m),
        )
    )
    return {
        "success": True,
        "async": True,
        "task_id": "adblock_toggle",
        "enabled": enable,
    }


@app.post("/api/adblock/lists")
async def api_adblock_add_list(request: Request):
    try:
        data = await request.json()
        url = str(data.get("url", "")).strip()
        list_type = "white" if data.get("list_type") == "white" else "black"
    except Exception:
        return {"success": False, "message": "Invalid JSON"}

    if not url.startswith(("http://", "https://")):
        return {
            "success": False,
            "message": "URL должен начинаться с http:// или https://",
        }

    def _download_and_store():
        ok_inst, msg_inst = ensure_dnsmasq_installed_sync(
            lambda p, m: task_tracker.update("adblock_list", p, m)
        )
        if not ok_inst:
            return False, msg_inst

        task_tracker.update("adblock_list", 55, "Скачивание списка доменов...")
        ok_fetch, domains, msg_fetch = fetch_and_parse_adlist(url)
        if not ok_fetch:
            return False, msg_fetch

        task_tracker.update("adblock_list", 75, "Сохранение в кэш и БД...")
        with get_db() as conn:
            cursor = conn.execute(
                "INSERT INTO adblock_lists (url, list_type, domains_count, created_at) VALUES (?, ?, ?, ?) "
                "ON CONFLICT(url) DO UPDATE SET list_type=excluded.list_type, domains_count=excluded.domains_count RETURNING id",
                (url, list_type, len(domains), int(time.time())),
            )
            row = cursor.fetchone()
            list_id = row["id"] if row else None

        if not list_id:
            with get_db() as conn:
                list_id = conn.execute(
                    "SELECT id FROM adblock_lists WHERE url=?", (url,)
                ).fetchone()["id"]

        cache_dir = Path("/var/cache/ovpn_adblock")
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"list_{list_id}.txt").write_text(
            "\n".join(domains), encoding="utf-8"
        )

        rebuild_dnsmasq_adblock_conf_sync(
            lambda p, m: task_tracker.update("adblock_list", p, m)
        )
        return True, f"Список загружен ({len(domains)} правил)"

    asyncio.create_task(
        asyncio.to_thread(
            _run_tracked_task, "adblock_list", "Загрузка AdList", _download_and_store
        )
    )
    return {"success": True, "async": True, "task_id": "adblock_list"}


@app.delete("/api/adblock/lists/{list_id}")
async def api_adblock_delete_list(list_id: int):
    def _del():
        with get_db() as conn:
            conn.execute("DELETE FROM adblock_lists WHERE id=?", (list_id,))
        cache_file = Path(f"/var/cache/ovpn_adblock/list_{list_id}.txt")
        cache_file.unlink(missing_ok=True)
        rebuild_dnsmasq_adblock_conf_sync()
        return True

    await asyncio.to_thread(_del)
    return {"success": True}


@app.post("/api/adblock/domains")
async def api_adblock_add_domain(request: Request):
    try:
        data = await request.json()
        raw_dom = str(data.get("domain", "")).strip().lower()
        list_type = "white" if data.get("list_type") == "white" else "black"
    except Exception:
        return {"success": False, "message": "Invalid JSON"}

    raw_dom = re.sub(r"^https?://", "", raw_dom).split("/")[0].strip()
    if raw_dom.startswith("www."):
        raw_dom = raw_dom[4:]

    parsed = parse_adlist_content(raw_dom)
    if not parsed:
        return {"success": False, "message": "Некорректный формат домена"}
    domain = parsed[0]

    def _add_dom():
        ok_inst, msg_inst = ensure_dnsmasq_installed_sync()
        if not ok_inst:
            return False, msg_inst

        with get_db() as conn:
            conn.execute(
                "INSERT INTO adblock_domains (domain, list_type, created_at) VALUES (?, ?, ?) "
                "ON CONFLICT(domain) DO UPDATE SET list_type=excluded.list_type",
                (domain, list_type, int(time.time())),
            )
        rebuild_dnsmasq_adblock_conf_sync()
        return (
            True,
            f"Домен {domain} добавлен в {'белый' if list_type == 'white' else 'черный'} список",
        )

    ok, msg = await asyncio.to_thread(_add_dom)
    return {"success": ok, "message": msg}


@app.delete("/api/adblock/domains/{dom_id}")
async def api_adblock_delete_domain(dom_id: int):
    def _del():
        with get_db() as conn:
            conn.execute("DELETE FROM adblock_domains WHERE id=?", (dom_id,))
        rebuild_dnsmasq_adblock_conf_sync()
        return True

    await asyncio.to_thread(_del)
    return {"success": True}


# ============================================================
# SYSTEM, INFOGRAPHICS, SETTINGS & SPEED LIMITS API
# ============================================================

@app.get("/api/system/stats")
async def api_system_stats():
    stats = await asyncio.to_thread(get_system_stats)
    return {"success": True, "stats": stats}


@app.get("/api/infographics")
async def api_infographics():
    def _calc():
        pki = get_pki_clients_fast()
        valid_c = sum(1 for v in pki.values() if v["status"] == "valid")
        revoked_c = sum(1 for v in pki.values() if v["status"] == "revoked")
        online_c = len(speed_monitor.online_clients)

        with get_db() as conn:
            paused_c = conn.execute(
                "SELECT COUNT(*) as c FROM client_meta WHERE is_paused=1"
            ).fetchone()["c"]
            top_clients_rows = conn.execute(
                "SELECT client_name, (bytes_recv + bytes_sent) as total, bytes_recv, bytes_sent "
                "FROM traffic ORDER BY total DESC LIMIT 10"
            ).fetchall()
            tot_row = conn.execute(
                "SELECT SUM(bytes_recv) as r, SUM(bytes_sent) as s FROM traffic"
            ).fetchone()
            cutoff = int(time.time()) - get_domain_retention()
            top_domains_rows = conn.execute(
                "SELECT domain, COUNT(*) as cnt FROM domain_logs WHERE visited_at >= ? "
                "GROUP BY domain ORDER BY cnt DESC LIMIT 10",
                (cutoff,),
            ).fetchall()

        offline_c = max(0, valid_c - online_c - paused_c)
        return {
            "status_counts": {
                "online": online_c,
                "offline": offline_c,
                "paused": paused_c,
                "revoked": revoked_c,
            },
            "total_recv": tot_row["r"] or 0,
            "total_sent": tot_row["s"] or 0,
            "top_clients": [
                {
                    "name": r["client_name"],
                    "total": r["total"],
                    "recv": r["bytes_recv"],
                    "sent": r["bytes_sent"],
                }
                for r in top_clients_rows
            ],
            "top_domains": [
                {"domain": r["domain"], "count": r["cnt"]} for r in top_domains_rows
            ],
        }

    data = await asyncio.to_thread(_calc)
    return {"success": True, "data": data}


@app.get("/api/settings")
async def api_get_settings():
    s = await asyncio.to_thread(get_all_settings)
    s.pop("admin_password_hash", None)
    return {"success": True, "settings": s}


@app.post("/api/settings")
async def api_update_settings(request: Request):
    try:
        data = await request.json()
        updates = {}

        new_login = str(data.get("admin_login", "")).strip()
        if new_login:
            if not re.match(r"^[a-zA-Z0-9_\u0400-\u04FF-]+$", new_login):
                return {"success": False, "message": "Invalid login format"}
            updates["admin_login"] = new_login

        new_pass = str(data.get("admin_password", "")).strip()
        if new_pass:
            if len(new_pass) < 4:
                return {"success": False, "message": "Password too short"}
            updates["admin_password_hash"] = hash_password(new_pass)

        int_fields = {
            "session_max_age": (300, 31536000),
            "panel_port": (1, 65535),
            "mgmt_port": (1, 65535),
            "domain_retention": (60, 2592000),
        }
        for k, (mn, mx) in int_fields.items():
            if k in data and str(data[k]).strip() != "":
                val = int(data[k])
                if mn <= val <= mx:
                    updates[k] = str(val)

        str_fields = [
            "tun_iface",
            "mgmt_host",
            "ovpn_domain",
        ]
        for k in str_fields:
            if k in data:
                updates[k] = str(data[k]).strip()

        bool_fields = [
            "enable_sniffer",
            "enable_speed_monitor",
            "enable_traffic_stats",
            "enable_infographics",
            "enable_hardware_bar",
            "torrent_block",
            "quic_block",
            "enable_ip_history",
        ]
        for k in bool_fields:
            if k in data:
                updates[k] = "1" if str(data[k]) in ("1", "true", "True") else "0"

        await asyncio.to_thread(set_settings_bulk, updates)

        if "quic_block" in updates:
            await asyncio.to_thread(apply_quic_block_sync, updates["quic_block"] == "1")
        if "torrent_block" in updates:
            await asyncio.to_thread(
                apply_torrent_block_sync, updates["torrent_block"] == "1"
            )

        if data.get("apply_to_ovpn"):
            await asyncio.to_thread(sync_openvpn_server_conf_from_settings, True)
            invalidate_server_status_cache()

        s_out = await asyncio.to_thread(get_all_settings)
        s_out.pop("admin_password_hash", None)
        return {"success": True, "message": "OK", "settings": s_out}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/speed-limits")
async def api_set_speed_limits(request: Request):
    try:
        data = await request.json()
        mode = str(data.get("speed_limit_mode", "none")).strip()
        if mode not in ("none", "global", "selected", "per_client"):
            return {"success": False, "message": "Invalid speed limit mode"}

        global_kbps = max(0, int(data.get("global_speed_limit_kbps", 0) or 0))
        selected_clients = data.get("selected_limit_clients", [])
        if not isinstance(selected_clients, list):
            selected_clients = []
        clean_selected = [
            str(x).strip()
            for x in selected_clients
            if re.match(r"^[a-zA-Z0-9_-]+$", str(x).strip())
        ]

        per_client_map = data.get("per_client_limits", {})
        clean_per_client = {}
        if isinstance(per_client_map, dict):
            for cname, val in per_client_map.items():
                s_name = str(cname).strip()
                if re.match(r"^[a-zA-Z0-9_-]+$", s_name):
                    clean_per_client[s_name] = max(0, int(val or 0))

        await asyncio.to_thread(
            set_settings_bulk,
            {
                "speed_limit_mode": mode,
                "global_speed_limit_kbps": str(global_kbps),
                "selected_limit_clients": json.dumps(
                    clean_selected, ensure_ascii=False
                ),
            },
        )
        if clean_per_client:
            await asyncio.to_thread(set_bulk_client_speed_limits, clean_per_client)

        speed_monitor._last_tc_signature = None
        await asyncio.to_thread(
            apply_bidirectional_speed_limits_sync, speed_monitor.active_sessions
        )
        return {"success": True, "message": "OK"}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/service/{action}")
async def api_service_control(action: str):
    if action not in ("restart", "stop", "start", "reload"):
        return {"success": False, "message": "Invalid action"}

    def _do():
        r = subprocess.run(
            ["systemctl", action, "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        invalidate_server_status_cache()
        return r.returncode == 0, r.stderr.strip() or "OK"

    ok, msg = await asyncio.to_thread(_do)
    return {"success": ok, "message": msg}


@app.post("/api/database/action")
async def api_database_action(request: Request):
    try:
        data = await request.json()
        act = data.get("action", "")
        with get_db() as conn:
            if act == "clear_domains":
                conn.execute("DELETE FROM domain_logs")
            elif act == "clear_traffic":
                speed_monitor.pending_deltas.clear()
                conn.execute("DELETE FROM traffic")
            elif act == "clear_ip_history":
                conn.execute("DELETE FROM client_connections")
            elif act == "vacuum":
                conn.execute("VACUUM")
            else:
                return {"success": False, "message": "Unknown action"}
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


# ============================================================
# CLIENTS, DOMAINS & IPS API
# ============================================================

@app.get("/api/clients/speeds")
async def api_clients_speeds():
    return {
        "success": True,
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "speeds": speed_monitor.current_speeds,
    }


@app.get("/api/clients/speeds/history")
async def api_clients_speeds_history(seconds: int = Query(30, ge=10, le=300)):
    return {
        "success": True,
        "window_seconds": seconds,
        "history": speed_monitor.get_history_window(seconds=seconds),
    }


@app.get("/api/clients/{name}/domains")
async def api_get_client_domains(
    name: str, q: str = Query(""), limit: int = Query(300, ge=10, le=1000)
):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False, "domains": []}
    domains = await asyncio.to_thread(
        domain_tracker.get_client_domains, name, q.strip(), limit
    )
    top_domains = await asyncio.to_thread(
        domain_tracker.get_client_top_domains, name, 10
    )
    return {
        "success": True,
        "client": name,
        "domains": domains,
        "top_domains": top_domains,
    }


@app.delete("/api/clients/{name}/domains")
async def api_clear_client_domains(name: str):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False}
    await asyncio.to_thread(domain_tracker.clear_client_domains, name)
    return {"success": True}


@app.get("/api/clients/{name}/ips")
async def api_get_client_ips(name: str, limit: int = Query(100, ge=10, le=1000)):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False, "ips": []}
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT real_ip, MAX(virt_ip) as virt_ip, MAX(connected_at) as connected_at, "
                "MAX(disconnected_at) as disconnected_at, COUNT(*) as repeat_count "
                "FROM client_connections "
                "WHERE client_name = ? "
                "GROUP BY real_ip "
                "ORDER BY connected_at DESC LIMIT ?",
                (name, limit),
            ).fetchall()
        return {
            "success": True,
            "client": name,
            "ips": [
                {
                    "real_ip": r["real_ip"],
                    "virt_ip": r["virt_ip"] or "—",
                    "connected_at": r["connected_at"],
                    "disconnected_at": r["disconnected_at"],
                    "repeat_count": r["repeat_count"],
                    "connected_fmt": datetime.fromtimestamp(r["connected_at"]).strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "disconnected_fmt": (
                        datetime.fromtimestamp(r["disconnected_at"]).strftime(
                            "%Y-%m-%d %H:%M:%S"
                        )
                        if r["disconnected_at"]
                        else "—"
                    ),
                }
                for r in rows
            ],
        }
    except Exception:
        return {"success": True, "client": name, "ips": []}


@app.get("/api/clients")
async def api_clients():
    pki_clients = await asyncio.to_thread(get_pki_clients_fast)
    meta_data = await asyncio.to_thread(get_all_client_meta)
    traffic_data = {}

    try:
        with get_db() as conn:
            for row in conn.execute(
                "SELECT client_name, bytes_recv, bytes_sent FROM traffic"
            ):
                traffic_data[row["client_name"]] = {
                    "recv": row["bytes_recv"],
                    "sent": row["bytes_sent"],
                }
    except Exception:
        pass

    active_sessions = speed_monitor.active_sessions
    current_speeds = speed_monitor.current_speeds
    pending = speed_monitor.pending_deltas
    clients = []

    for name in sorted(pki_clients.keys()):
        meta = pki_clients[name]
        m_info = meta_data.get(
            name,
            {
                "note": "",
                "limit": 0,
                "expires": 0,
                "is_paused": 0,
                "speed_limit_kbps": 0,
                "last_connected_at": 0,
                "last_disconnected_at": 0,
                "last_real_ip": "",
                "last_virt_ip": "",
            },
        )
        is_paused = bool(m_info["is_paused"])
        is_online = name in active_sessions and not is_paused
        sess = active_sessions.get(name, {})
        spd = current_speeds.get(name, {})
        t_data = traffic_data.get(name, {"recv": 0, "sent": 0})
        pend = pending.get(name, [0, 0])

        clients.append(
            {
                "name": name,
                "status": meta["status"],
                "is_online": is_online,
                "is_paused": is_paused,
                "note": m_info["note"],
                "traffic_limit": m_info["limit"],
                "expires_at": m_info["expires"],
                "speed_limit_kbps": m_info["speed_limit_kbps"],
                "last_connected_at": m_info["last_connected_at"],
                "last_disconnected_at": m_info["last_disconnected_at"],
                "real_ip": (
                    sess.get("real_ip", "—")
                    if is_online
                    else (m_info["last_real_ip"] or "—")
                ),
                "virt_ip": (
                    sess.get("virt_ip", "—")
                    if is_online
                    else (m_info["last_virt_ip"] or "—")
                ),
                "connected_since": sess.get("connected_since", "—") if is_online else "—",
                "speed_down": spd.get("down", 0) if is_online else 0,
                "speed_up": spd.get("up", 0) if is_online else 0,
                "speed_down_fmt": (
                    spd.get("down_fmt", "0 B/s") if is_online else "0 B/s"
                ),
                "speed_up_fmt": spd.get("up_fmt", "0 B/s") if is_online else "0 B/s",
                "traffic_recv": t_data["recv"] + pend[0],
                "traffic_sent": t_data["sent"] + pend[1],
                "created": meta.get("created", "—"),
                "expires": meta.get("expires", "—"),
                "share_token": (
                    encode_client_name(name) if meta["status"] == "valid" else ""
                ),
            }
        )

    server_stat = await asyncio.to_thread(get_server_status)
    return {"clients": clients, "server": server_stat}


@app.post("/api/clients")
async def api_create_client(request: Request):
    try:
        data = await request.json()
    except Exception:
        return {"success": False, "message": "Invalid JSON"}

    name = str(data.get("name", "")).strip()
    note = str(data.get("note", "")).strip()
    limit_gb = float(data.get("limit_gb", 0) or 0)
    ttl_days = int(data.get("ttl_days", 0) or 0)

    ok, msg = await asyncio.to_thread(create_client_sync, name, note, limit_gb, ttl_days)
    return {"success": ok, "message": msg}


@app.post("/api/clients/{name}/pause")
async def api_toggle_pause_client(name: str):
    if not client_exists(name):
        return {"success": False, "message": "Not found"}

    try:
        meta_map = await asyncio.to_thread(get_all_client_meta)
        cur_paused = meta_map.get(name, {}).get("is_paused", 0)
        new_paused = 0 if cur_paused == 1 else 1
        await asyncio.to_thread(upsert_client_meta, name, is_paused=new_paused)

        ccd_path = CCD_DIR / name
        CCD_DIR.mkdir(parents=True, exist_ok=True)
        if new_paused == 1:
            ccd_path.write_text("disable\n", encoding="utf-8")
            await speed_monitor.kick_client(name)
        else:
            ccd_path.unlink(missing_ok=True)

        return {"success": True, "is_paused": new_paused}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/clients/{name}/kick")
async def api_kick_client(name: str):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False}
    ok = await speed_monitor.kick_client(name)
    return {"success": ok}


@app.delete("/api/clients/{name}/traffic")
async def api_reset_client_traffic(name: str):
    if not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False}
    speed_monitor.pending_deltas.pop(name, None)
    with get_db() as conn:
        conn.execute("DELETE FROM traffic WHERE client_name=?", (name,))
        conn.execute(
            "UPDATE client_meta SET is_paused = 0 WHERE client_name = ? AND traffic_limit_bytes > 0",
            (name,),
        )
    (CCD_DIR / name).unlink(missing_ok=True)
    return {"success": True}


@app.delete("/api/clients/{name}")
async def api_revoke_or_delete_client(name: str, permanent: bool = Query(False)):
    if not client_exists(name):
        return {"success": False, "message": "Client not found"}

    if permanent:
        await speed_monitor.kick_client(name)
        ok, msg = await asyncio.to_thread(delete_client_completely_sync, name)
        return {"success": ok, "message": msg}

    ok, msg = await asyncio.to_thread(revoke_client_sync, name)
    if ok:
        await speed_monitor.kick_client(name)
    return {"success": ok, "message": msg}


@app.post("/api/clients/{name}/restore")
async def api_restore_client(name: str):
    ok, msg = await asyncio.to_thread(unrevoke_client_sync, name)
    return {"success": ok, "message": msg}


@app.get("/api/clients/{name}/download")
async def api_download_config(name: str):
    if not client_exists(name):
        raise HTTPException(status_code=404, detail="Client not found")
    try:
        content = await asyncio.to_thread(generate_config, name)
        return Response(
            content=content,
            media_type="application/x-openvpn-profile",
            headers={"Content-Disposition": f'attachment; filename="{name}.ovpn"'},
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Error generating config")


@app.get("/d/{token}")
async def public_landing_page(token: str, request: Request):
    name = decode_client_name(token)
    if not name or not client_exists(name):
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    pki = await asyncio.to_thread(get_pki_clients_fast)
    if pki.get(name, {}).get("status") != "valid":
        raise HTTPException(status_code=403, detail="Certificate revoked")

    scheme = request.url.scheme
    host = request.headers.get("host", get_current_domain())
    raw_url = f"{scheme}://{host}/d/{token}/raw"

    html = (
        LANDING_HTML.replace("{client_name}", name)
        .replace("{token}", token)
        .replace("{raw_url}", raw_url)
    )
    return HTMLResponse(html)


@app.get("/d/{token}/raw")
async def public_download_config_raw(token: str):
    name = decode_client_name(token)
    if not name or not client_exists(name):
        raise HTTPException(status_code=403, detail="Invalid or expired link")
    pki = await asyncio.to_thread(get_pki_clients_fast)
    if pki.get(name, {}).get("status") != "valid":
        raise HTTPException(status_code=403, detail="Certificate revoked")
    try:
        content = await asyncio.to_thread(generate_config, name)
        return Response(
            content=content,
            media_type="application/x-openvpn-profile",
            headers={"Content-Disposition": f'attachment; filename="{name}.ovpn"'},
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Config generation error")


# ============================================================
# CONFIG, BACKUP, ROUTING & DOMAINS API
# ============================================================

@app.get("/api/config")
async def api_get_config():
    if SERVER_CONF_PATH.exists():
        return {
            "success": True,
            "config": SERVER_CONF_PATH.read_text(encoding="utf-8", errors="ignore"),
        }
    return {"success": False, "message": "Config file not found"}


@app.post("/api/config")
async def api_save_config(request: Request):
    try:
        data = await request.json()
        raw_conf = str(data.get("config", ""))
        restart = bool(data.get("restart", True))
        if not raw_conf.strip():
            return {"success": False, "message": "Empty config"}

        def _save():
            SERVER_CONF_PATH.write_text(raw_conf, encoding="utf-8")
            parse_existing_server_conf_into_db()
            if restart:
                subprocess.run(
                    ["systemctl", "restart", "openvpn-server@server"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            invalidate_server_status_cache()
            return True

        await asyncio.to_thread(_save)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/backup")
async def api_backup():
    def _make():
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        filename = f"openvpn_backup_{date_str}.tar.gz"
        tmp_path = Path(tempfile.gettempdir()) / filename
        env_file = Path(__file__).resolve().parent / ".env"
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            if Path("/etc/openvpn").exists():
                shutil.copytree(
                    "/etc/openvpn",
                    base_dir / "openvpn",
                    ignore=shutil.ignore_patterns(
                        "*.log", "*.socket", "*.pid", "status*"
                    ),
                )
            if Path("/etc/wireguard").exists():
                shutil.copytree(
                    "/etc/wireguard", base_dir / "wireguard", dirs_exist_ok=True
                )
            if Path("/etc/dnsmasq.d").exists():
                shutil.copytree(
                    "/etc/dnsmasq.d", base_dir / "dnsmasq.d", dirs_exist_ok=True
                )
            if DB_PATH.exists():
                shutil.copy2(DB_PATH, base_dir / "panel.db")
            if env_file.exists():
                shutil.copy2(env_file, base_dir / ".env")

            with tarfile.open(tmp_path, "w:gz") as tar:
                tar.add(base_dir, arcname="backup_data")
        content = tmp_path.read_bytes()
        tmp_path.unlink(missing_ok=True)
        return content, filename

    try:
        content, filename = await asyncio.to_thread(_make)
        return Response(
            content=content,
            media_type="application/gzip",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/restore")
async def api_restore(file: UploadFile = File(...)):
    try:
        raw_bytes = await file.read()
        if not raw_bytes:
            return {"success": False, "message": "Empty file"}

        def _do_restore():
            tmp_path = Path(tempfile.gettempdir()) / "restore_backup.tar.gz"
            tmp_path.write_bytes(raw_bytes)
            env_target = Path(__file__).resolve().parent / ".env"

            with tempfile.TemporaryDirectory() as tmpdir:
                base_dest = Path(tmpdir).resolve()
                with tarfile.open(tmp_path, "r:gz") as tar:
                    for member in tar.getmembers():
                        member_path = (base_dest / member.name).resolve()
                        if not str(member_path).startswith(str(base_dest)):
                            tmp_path.unlink(missing_ok=True)
                            return False, "Unsafe path traversal detected in archive"
                    tar.extractall(path=base_dest)

                src_root = base_dest / "backup_data"
                if not src_root.exists():
                    src_root = base_dest

                if (src_root / "openvpn").exists():
                    shutil.copytree(
                        src_root / "openvpn", Path("/etc/openvpn"), dirs_exist_ok=True
                    )
                if (src_root / "wireguard").exists():
                    shutil.copytree(
                        src_root / "wireguard",
                        Path("/etc/wireguard"),
                        dirs_exist_ok=True,
                    )
                if (src_root / "dnsmasq.d").exists():
                    shutil.copytree(
                        src_root / "dnsmasq.d",
                        Path("/etc/dnsmasq.d"),
                        dirs_exist_ok=True,
                    )
                db_src = (
                    src_root / "panel.db"
                    if (src_root / "panel.db").exists()
                    else (src_root / "traffic.db")
                )
                if db_src.exists():
                    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(db_src, DB_PATH)
                if (src_root / ".env").exists():
                    shutil.copy2(src_root / ".env", env_target)
                    os.chmod(env_target, 0o600)

            tmp_path.unlink(missing_ok=True)
            invalidate_pki_cache()
            parse_existing_server_conf_into_db()
            ensure_system_configs()
            subprocess.run(
                ["systemctl", "restart", "openvpn-server@server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(
                ["systemctl", "restart", "dnsmasq"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True, "OK"

        ok, msg = await asyncio.to_thread(_do_restore)
        return {"success": ok, "message": msg}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/routing/status")
async def api_routing_status():
    def _get_status():
        wg_up = (
            subprocess.run(
                ["ip", "link", "show", "wg0"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        )
        ipset_count = 0
        try:
            out = subprocess.check_output(
                ["ipset", "list", "ru_ips", "-t"], text=True, stderr=subprocess.DEVNULL
            )
            m = re.search(r"Number of entries:\s*(\d+)", out)
            if m:
                ipset_count = int(m.group(1))
        except Exception:
            pass

        wg_endpoint = None
        wg_conf = Path("/etc/wireguard/wg0.conf")
        if wg_conf.exists():
            try:
                content = wg_conf.read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"^\s*Endpoint\s*=\s*([^:\s]+):", content, re.MULTILINE)
                if m:
                    wg_endpoint = m.group(1).strip()
            except Exception:
                pass

        cidr_url = get_setting("cidr_url")
        custom_cidrs = get_setting("custom_cidrs")
        routing_mode = get_setting("routing_mode")
        torrent_block = get_setting("torrent_block") == "1"
        if not wg_up and routing_mode != "off":
            routing_mode = "off"

        return {
            "wg_up": wg_up,
            "wg_endpoint": wg_endpoint,
            "ipset_count": ipset_count,
            "cidr_url": cidr_url,
            "custom_cidrs": custom_cidrs,
            "routing_mode": routing_mode,
            "torrent_block": torrent_block,
        }

    return await asyncio.to_thread(_get_status)


@app.post("/api/routing/settings")
async def api_routing_settings(request: Request):
    try:
        data = await request.json()
        new_url = data.get("cidr_url", "").strip()
        new_mode = data.get("routing_mode", "split")
        custom_cidrs = data.get("custom_cidrs", "").strip()
        torrent_block = bool(data.get("torrent_block", False))

        if new_url:
            set_setting("cidr_url", new_url)
        set_setting("custom_cidrs", custom_cidrs)
        set_setting("torrent_block", "1" if torrent_block else "0")

        await asyncio.to_thread(apply_torrent_block_sync, torrent_block)

        if new_mode in ["off", "split", "all", "cidr_wg"]:
            set_setting("routing_mode", new_mode)
            ok, msg = await asyncio.to_thread(apply_routing_mode_sync, new_mode)
            if not ok:
                return {"success": False, "message": msg}

        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/routing/update_ips")
async def api_routing_update_ips():
    def _download():
        url = (
            get_setting("cidr_url")
            or "https://plitw.github.io/ros-country-ips/cidr_lists/ru_ipv4"
        )
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=12) as response:
            data = response.read().decode("utf-8", errors="ignore")

        os.makedirs("/etc/wireguard", exist_ok=True)
        Path("/etc/wireguard/ru.txt").write_text(data, encoding="utf-8")
        reload_ipset_sync()
        return True, "CIDR обновлены"

    asyncio.create_task(
        asyncio.to_thread(
            _run_tracked_task, "cidr_update", "Обновление CIDR", _download
        )
    )
    return {"success": True, "async": True, "task_id": "cidr_update"}


@app.post("/api/routing/setup")
async def api_routing_setup(request: Request):
    data = await request.json()
    remote_ip = str(data.get("remote_ip", "")).strip()
    remote_pass = str(data.get("remote_pass", ""))

    if not remote_ip or not remote_pass:
        return {"success": False, "message": "IP and password required"}

    asyncio.create_task(
        asyncio.to_thread(
            _run_tracked_task,
            "wg_setup",
            "Настройка WireGuard туннеля",
            setup_remote_tunnel_sync,
            remote_ip,
            remote_pass,
            lambda p, m: task_tracker.update("wg_setup", p, m),
        )
    )
    return {"success": True, "async": True, "task_id": "wg_setup"}


@app.post("/api/routing/resolve-link")
async def api_resolve_link(request: Request):
    try:
        data = await request.json()
        url = data.get("url", "").strip()
        if not url:
            return {"success": False, "message": "URL required"}
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        parsed = urllib.request.urlparse(url)
        hostname = parsed.hostname
        if not hostname:
            return {"success": False, "message": "Invalid URL"}

        def _resolve():
            try:
                found = sorted(set(socket.gethostbyname_ex(hostname)[2]))
            except Exception:
                found = []
            conflicts = []
            for ip in found:
                res = subprocess.run(
                    ["ipset", "test", "ru_ips", ip],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                if res.returncode == 0:
                    conflicts.append(ip)
            return found, conflicts

        ips, conflict_ips = await asyncio.to_thread(_resolve)
        return {
            "success": True,
            "hostname": hostname,
            "ips": ips,
            "url": url,
            "has_conflict": len(conflict_ips) > 0,
            "conflict_ips": conflict_ips,
        }
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.post("/api/routing/save-link")
async def api_save_split_link(request: Request):
    try:
        data = await request.json()
        url = data.get("url", "").strip()
        route_via = data.get("route_via", "split")
        resolved_ips = data.get("resolved_ips", "")

        if not url:
            return {"success": False, "message": "URL required"}

        with get_db() as conn:
            conn.execute(
                "INSERT INTO split_links (url, resolved_ip, route_via, created_at) VALUES (?, ?, ?, ?)",
                (url, resolved_ips, route_via, int(time.time())),
            )
        await asyncio.to_thread(reload_ipset_sync)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/routing/links")
async def api_get_split_links():
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT id, url, resolved_ip, route_via, created_at FROM split_links ORDER BY created_at DESC"
            ).fetchall()
        return {"success": True, "links": [dict(r) for r in rows]}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.delete("/api/routing/links/{link_id}")
async def api_delete_split_link(link_id: int):
    try:
        with get_db() as conn:
            conn.execute("DELETE FROM split_links WHERE id = ?", (link_id,))
        await asyncio.to_thread(reload_ipset_sync)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.get("/api/domains/global")
async def api_get_global_domains(q: str = Query(""), limit: int = Query(300, ge=10, le=2000)):
    domains = await asyncio.to_thread(
        domain_tracker.get_all_global_domains, q.strip(), limit
    )
    return {"success": True, "domains": domains}


@app.get("/api/sniffer/ignored")
async def api_get_sniffer_ignored():
    def _get():
        with get_db() as conn:
            return [
                dict(r)
                for r in conn.execute(
                    "SELECT id, domain, created_at FROM sniffer_ignored ORDER BY id DESC"
                ).fetchall()
            ]

    data = await asyncio.to_thread(_get)
    return {"success": True, "ignored": data}


@app.post("/api/sniffer/ignored")
async def api_add_sniffer_ignored(request: Request):
    try:
        body = await request.json()
        raw_dom = str(body.get("domain", "")).strip().lower()
        raw_dom = re.sub(r"^https?://", "", raw_dom).split("/")[0].strip()
        if raw_dom.startswith("www."):
            raw_dom = raw_dom[4:]
        if not raw_dom or "." not in raw_dom:
            return {"success": False, "message": "Некорректный домен"}

        def _add():
            with get_db() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO sniffer_ignored (domain, created_at) VALUES (?, ?)",
                    (raw_dom, int(time.time())),
                )
                conn.execute(
                    "DELETE FROM domain_logs WHERE domain = ? OR domain LIKE ?",
                    (raw_dom, f"%.{raw_dom}"),
                )
            reload_sniffer_ignored_cache()
            return True

        await asyncio.to_thread(_add)
        return {"success": True, "domain": raw_dom}
    except Exception as e:
        return {"success": False, "message": str(e)}


@app.delete("/api/sniffer/ignored/{item_id}")
async def api_del_sniffer_ignored(item_id: int):
    def _del():
        with get_db() as conn:
            conn.execute("DELETE FROM sniffer_ignored WHERE id = ?", (item_id,))
        reload_sniffer_ignored_cache()
        return True

    await asyncio.to_thread(_del)
    return {"success": True}


# ============================================================
# LOGIN, LOGOUT & INDEX
# ============================================================

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse("/", status_code=303)
    return HTMLResponse(LOGIN_HTML.replace("{{ERROR}}", ""))


@app.post("/login")
async def login(request: Request):
    try:
        form = await request.form()
        username = str(form.get("username", "")).strip()
        password = str(form.get("password", ""))
    except Exception:
        return HTMLResponse(
            LOGIN_HTML.replace(
                "{{ERROR}}", '<div class="error-box">Ошибка формы / Form error</div>'
            ),
            status_code=400,
        )

    if not verify_login(username, password):
        return HTMLResponse(
            LOGIN_HTML.replace(
                "{{ERROR}}",
                '<div class="error-box">Неверные данные / Invalid credentials</div>',
            ),
            status_code=401,
        )

    session = create_session()
    is_secure = request.url.scheme == "https"
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session,
        max_age=get_session_max_age(),
        httponly=True,
        secure=is_secure,
        samesite="lax",
    )
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/login", status_code=303)
    response.delete_cookie(SESSION_COOKIE)
    return response


@app.get("/", response_class=HTMLResponse)
async def index():
    html = (
        MAIN_HTML.replace("{{ domain }}", get_current_domain())
        .replace("{{ port }}", str(get_current_port()))
        .replace("{{ proto }}", get_current_proto())
    )
    return HTMLResponse(html)


if __name__ == "__main__":
    init_db()
    INLINE_DIR.mkdir(parents=True, exist_ok=True)
    CCD_DIR.mkdir(parents=True, exist_ok=True)
    try:
        listen_port = int(get_setting("panel_port", str(PANEL_PORT)))
    except Exception:
        listen_port = PANEL_PORT
    uvicorn.run(
        app, host="0.0.0.0", port=listen_port, log_level="critical", access_log=False
    )