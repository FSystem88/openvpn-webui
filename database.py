import hashlib
import hmac
import ipaddress
import os
import secrets
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

DOMAIN = os.getenv("OVPN_DOMAIN", "127.0.0.1")
OVPN_PORT = int(os.getenv("OVPN_PORT", "1984"))
PROTOCOL = os.getenv("OVPN_PROTO", "udp")
PANEL_PORT = int(os.getenv("PANEL_PORT", "8080"))
TUN_IFACE = os.getenv("OVPN_TUN_IFACE", "tun0")
IFB_IFACE = os.getenv("OVPN_IFB_IFACE", "ifb0")
DOMAIN_RETENTION_SECONDS = 86400

MGMT_HOST = os.getenv("OVPN_MGMT_HOST", "127.0.0.1")
MGMT_PORT = int(os.getenv("OVPN_MGMT_PORT", "7505"))

OVPN_DIR = Path("/etc/openvpn/server/easy-rsa")
SERVER_DIR = Path("/etc/openvpn/server")
PKI_DIR = OVPN_DIR / "pki"
INDEX_TXT_PATH = PKI_DIR / "index.txt"
ISSUED_DIR = PKI_DIR / "issued"
PRIVATE_DIR = PKI_DIR / "private"
INLINE_DIR = PKI_DIR / "inline" / "private"
REQ_DIR = PKI_DIR / "reqs"
CCD_DIR = SERVER_DIR / "ccd"
TLS_KEY_FILE = SERVER_DIR / "tc.key"
SERVER_CONF_PATH = SERVER_DIR / "server.conf"

STATUS_LOG_PATH = Path("/var/run/openvpn-server/status-server.log")
DB_PATH = Path(os.getenv("DB_PATH", "/etc/openvpn/panel.db"))

ADBLOCK_DNS_IP = os.getenv("ADBLOCK_DNS_IP", "10.8.0.1")
DNSMASQ_MAIN_CONF = Path("/etc/dnsmasq.d/00-ovpn-base.conf")
DNSMASQ_ADBLOCK_CONF = Path("/etc/dnsmasq.d/99-ovpn-adblock.conf")

_settings_cache: Dict[str, str] = {}


@contextmanager
def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-4000;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _ensure_column(
    conn: sqlite3.Connection, table: str, column: str, col_def: str
) -> None:
    cols = [
        row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
    ]
    if column not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_def}")


def init_db() -> None:
    with get_db() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS traffic (
                client_name TEXT PRIMARY KEY,
                bytes_recv INTEGER DEFAULT 0,
                bytes_sent INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS domain_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                domain TEXT NOT NULL,
                visited_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS client_meta (
                client_name TEXT PRIMARY KEY,
                note TEXT DEFAULT '',
                traffic_limit_bytes INTEGER DEFAULT 0,
                expires_at INTEGER DEFAULT 0,
                is_paused INTEGER DEFAULT 0,
                speed_limit_kbps INTEGER DEFAULT 0,
                last_connected_at INTEGER DEFAULT 0,
                last_disconnected_at INTEGER DEFAULT 0,
                last_real_ip TEXT DEFAULT '',
                last_virt_ip TEXT DEFAULT ''
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS split_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                resolved_ip TEXT DEFAULT '',
                route_via TEXT DEFAULT 'split',
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS client_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                client_name TEXT NOT NULL,
                real_ip TEXT NOT NULL,
                virt_ip TEXT,
                connected_at INTEGER NOT NULL,
                disconnected_at INTEGER
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adblock_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL DEFAULT 'black',
                domains_count INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS adblock_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL DEFAULT 'black',
                created_at INTEGER NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sniffer_ignored (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                created_at INTEGER NOT NULL
            )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_domain_client_time ON domain_logs(client_name, visited_at DESC)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_domain_visited_at ON domain_logs(visited_at)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_conn_client ON client_connections(client_name, connected_at DESC)"
        )

        # Мягкая миграция колонок при обновлении существующей БД
        _ensure_column(conn, "client_meta", "speed_limit_kbps", "INTEGER DEFAULT 0")
        _ensure_column(conn, "client_meta", "last_connected_at", "INTEGER DEFAULT 0")
        _ensure_column(conn, "client_meta", "last_disconnected_at", "INTEGER DEFAULT 0")
        _ensure_column(conn, "client_meta", "last_real_ip", "TEXT DEFAULT ''")
        _ensure_column(conn, "client_meta", "last_virt_ip", "TEXT DEFAULT ''")

        default_settings = {
            "admin_login": os.getenv("ADMIN_LOGIN", "admin"),
            "admin_password_hash": os.getenv(
                "ADMIN_PASSWORD_HASH",
                hashlib.sha256(secrets.token_urlsafe(16).encode("utf-8")).hexdigest(),
            ),
            "session_max_age": "86400",
            "ovpn_domain": os.getenv("OVPN_DOMAIN", DOMAIN),
            "ovpn_port": str(OVPN_PORT),
            "ovpn_proto": PROTOCOL,
            "panel_port": str(PANEL_PORT),
            "tun_iface": TUN_IFACE,
            "mgmt_host": MGMT_HOST,
            "mgmt_port": str(MGMT_PORT),
            "ovpn_dns1": "1.1.1.1",
            "ovpn_dns2": "8.8.8.8",
            "ovpn_cipher": "AES-256-GCM",
            "ovpn_auth": "SHA256",
            "ovpn_mtu": "1420",
            "ovpn_subnet": "10.8.0.0 255.255.255.0",
            "ovpn_max_clients": "100",
            "ovpn_duplicate_cn": "1",
            "ovpn_client_to_client": "0",
            "ovpn_redirect_gw": "1",
            "ovpn_verb": "3",
            "enable_sniffer": "1",
            "enable_speed_monitor": "1",
            "enable_traffic_stats": "1",
            "enable_infographics": "1",
            "enable_hardware_bar": "1",
            "enable_ip_history": "1",
            "domain_retention": str(DOMAIN_RETENTION_SECONDS),
            "cidr_url": "https://plitw.github.io/ros-country-ips/cidr_lists/ru_ipv4",
            "routing_mode": "split",
            "custom_cidrs": "",
            "torrent_block": "0",
            "quic_block": "1",
            "split_link_ips": "",
            "adblock_enabled": "0",
            "adblock_dns_ip": ADBLOCK_DNS_IP,
            "global_speed_limit_kbps": "0",
            "speed_limit_mode": "none",
            "selected_limit_clients": "[]",
        }
        for k, v in default_settings.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

        retention = int(default_settings["domain_retention"])
        try:
            row = conn.execute(
                "SELECT value FROM settings WHERE key='domain_retention'"
            ).fetchone()
            if row and row["value"]:
                retention = int(row["value"])
        except Exception:
            pass
        cutoff = int(time.time()) - retention
        conn.execute("DELETE FROM domain_logs WHERE visited_at < ?", (cutoff,))


def get_setting(key: str, default: str = "") -> str:
    if not _settings_cache:
        get_all_settings()
    return _settings_cache.get(key, default)


def get_all_settings() -> Dict[str, str]:
    if _settings_cache:
        return _settings_cache.copy()
    try:
        with get_db() as conn:
            rows = conn.execute("SELECT key, value FROM settings").fetchall()
            data = {r["key"]: r["value"] for r in rows if r["value"] is not None}
            _settings_cache.update(data)
            return data.copy()
    except Exception:
        return {}


def invalidate_settings_cache() -> None:
    _settings_cache.clear()


def set_setting(key: str, value: str) -> None:
    val_str = str(value)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, val_str),
        )
    _settings_cache[key] = val_str


def set_settings_bulk(data: Dict[str, Any]) -> None:
    items = [(k, str(v)) for k, v in data.items()]
    with get_db() as conn:
        conn.executemany(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            items,
        )
    for k, v in items:
        _settings_cache[k] = v


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
    return f"scrypt${salt.hex()}${derived.hex()}"


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash:
        return False
    if stored_hash.startswith("scrypt$"):
        try:
            _, salt_hex, hash_hex = stored_hash.split("$")
            salt = bytes.fromhex(salt_hex)
            derived = hashlib.scrypt(
                password.encode("utf-8"), salt=salt, n=16384, r=8, p=1
            )
            return hmac.compare_digest(derived.hex(), hash_hex)
        except Exception:
            return False
    legacy_sha = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy_sha, stored_hash)


def get_admin_login() -> str:
    return get_setting("admin_login", "admin")


def get_admin_password_hash() -> str:
    return get_setting("admin_password_hash", "")


def get_session_max_age() -> int:
    try:
        return int(get_setting("session_max_age", "86400"))
    except Exception:
        return 86400


def get_current_domain() -> str:
    return get_setting("ovpn_domain", DOMAIN)


def get_current_port() -> int:
    try:
        return int(get_setting("ovpn_port", str(OVPN_PORT)))
    except Exception:
        return OVPN_PORT


def get_current_proto() -> str:
    return get_setting("ovpn_proto", PROTOCOL)


def get_current_tun_iface() -> str:
    return get_setting("tun_iface", TUN_IFACE)


def get_current_mgmt() -> Tuple[str, int]:
    h = get_setting("mgmt_host", MGMT_HOST)
    try:
        p = int(get_setting("mgmt_port", str(MGMT_PORT)))
    except Exception:
        p = MGMT_PORT
    return h, p


def get_ovpn_subnet_cidr() -> str:
    raw = get_setting("ovpn_subnet", "10.8.0.0 255.255.255.0").strip().split()
    if len(raw) == 2:
        try:
            return str(ipaddress.IPv4Network(f"{raw[0]}/{raw[1]}", strict=False))
        except Exception:
            pass
    return "10.8.0.0/24"


def get_domain_retention() -> int:
    try:
        return max(
            60, int(get_setting("domain_retention", str(DOMAIN_RETENTION_SECONDS)))
        )
    except Exception:
        return DOMAIN_RETENTION_SECONDS


def get_all_client_meta() -> Dict[str, Dict[str, Any]]:
    result: Dict[str, Dict[str, Any]] = {}
    try:
        with get_db() as conn:
            rows = conn.execute(
                """
                SELECT client_name, note, traffic_limit_bytes, expires_at, is_paused,
                       speed_limit_kbps, last_connected_at, last_disconnected_at,
                       last_real_ip, last_virt_ip
                FROM client_meta
                """
            ).fetchall()
            for r in rows:
                result[r["client_name"]] = {
                    "note": r["note"] or "",
                    "limit": int(r["traffic_limit_bytes"] or 0),
                    "expires": int(r["expires_at"] or 0),
                    "is_paused": int(r["is_paused"] or 0),
                    "speed_limit_kbps": int(r["speed_limit_kbps"] or 0),
                    "last_connected_at": int(r["last_connected_at"] or 0),
                    "last_disconnected_at": int(r["last_disconnected_at"] or 0),
                    "last_real_ip": r["last_real_ip"] or "",
                    "last_virt_ip": r["last_virt_ip"] or "",
                }
    except Exception:
        pass
    return result


def upsert_client_meta(
    client_name: str,
    note: Optional[str] = None,
    traffic_limit_bytes: Optional[int] = None,
    expires_at: Optional[int] = None,
    is_paused: Optional[int] = None,
    speed_limit_kbps: Optional[int] = None,
) -> None:
    cur = get_all_client_meta().get(client_name, {})
    n_val = note if note is not None else cur.get("note", "")
    l_val = (
        traffic_limit_bytes
        if traffic_limit_bytes is not None
        else cur.get("limit", 0)
    )
    e_val = expires_at if expires_at is not None else cur.get("expires", 0)
    p_val = is_paused if is_paused is not None else cur.get("is_paused", 0)
    s_val = (
        speed_limit_kbps
        if speed_limit_kbps is not None
        else cur.get("speed_limit_kbps", 0)
    )
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO client_meta (
                client_name, note, traffic_limit_bytes, expires_at, is_paused, speed_limit_kbps
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(client_name) DO UPDATE SET
                note=excluded.note,
                traffic_limit_bytes=excluded.traffic_limit_bytes,
                expires_at=excluded.expires_at,
                is_paused=excluded.is_paused,
                speed_limit_kbps=excluded.speed_limit_kbps
            """,
            (client_name, n_val, int(l_val), int(e_val), int(p_val), int(s_val)),
        )


def set_bulk_client_speed_limits(limits_map: Dict[str, int]) -> None:
    if not limits_map:
        return
    with get_db() as conn:
        for name, kbps in limits_map.items():
            conn.execute(
                """
                INSERT INTO client_meta (client_name, speed_limit_kbps) VALUES (?, ?)
                ON CONFLICT(client_name) DO UPDATE SET speed_limit_kbps=excluded.speed_limit_kbps
                """,
                (name, max(0, int(kbps))),
            )


def record_connection_events(
    connected_clients: List[Dict[str, Any]],
    disconnected_names: List[str],
    track_ip_history: bool = True,
) -> None:
    now = int(time.time())
    if not connected_clients and not disconnected_names:
        return
    try:
        with get_db() as conn:
            for item in connected_clients:
                name = item["name"]
                real_ip = item.get("real_ip", "")
                virt_ip = item.get("virt_ip", "")
                conn.execute(
                    """
                    INSERT INTO client_meta (
                        client_name, last_connected_at, last_real_ip, last_virt_ip
                    ) VALUES (?, ?, ?, ?)
                    ON CONFLICT(client_name) DO UPDATE SET
                        last_connected_at=excluded.last_connected_at,
                        last_real_ip=CASE WHEN excluded.last_real_ip != '' THEN excluded.last_real_ip ELSE client_meta.last_real_ip END,
                        last_virt_ip=CASE WHEN excluded.last_virt_ip != '' AND excluded.last_virt_ip != '—' THEN excluded.last_virt_ip ELSE client_meta.last_virt_ip END
                    """,
                    (name, now, real_ip, virt_ip),
                )
                if track_ip_history:
                    conn.execute(
                        "INSERT INTO client_connections (client_name, real_ip, virt_ip, connected_at) VALUES (?, ?, ?, ?)",
                        (name, real_ip or "—", virt_ip or "—", now),
                    )
            for name in disconnected_names:
                conn.execute(
                    """
                    INSERT INTO client_meta (client_name, last_disconnected_at)
                    VALUES (?, ?)
                    ON CONFLICT(client_name) DO UPDATE SET
                        last_disconnected_at=excluded.last_disconnected_at
                    """,
                    (name, now),
                )
                if track_ip_history:
                    conn.execute(
                        "UPDATE client_connections SET disconnected_at = ? "
                        "WHERE client_name = ? AND disconnected_at IS NULL",
                        (now, name),
                    )
    except Exception:
        pass