import asyncio
import json
import os
import re
import shutil
import socket
import subprocess
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from database import (
    CCD_DIR,
    DB_PATH,
    IFB_IFACE,
    INDEX_TXT_PATH,
    INLINE_DIR,
    ISSUED_DIR,
    MGMT_HOST,
    MGMT_PORT,
    OVPN_DIR,
    OVPN_PORT,
    PKI_DIR,
    PRIVATE_DIR,
    PROTOCOL,
    REQ_DIR,
    SERVER_CONF_PATH,
    SERVER_DIR,
    STATUS_LOG_PATH,
    TLS_KEY_FILE,
    TUN_IFACE,
    get_all_client_meta,
    get_all_settings,
    get_current_domain,
    get_current_port,
    get_current_proto,
    get_db,
    get_ovpn_subnet_cidr,
    get_setting,
    record_connection_events,
    set_setting,
    upsert_client_meta,
)

_pki_cache: Dict[str, Any] = {"mtime": 0.0, "clients": {}}
_server_status_cache: Dict[str, Any] = {
    "ts": 0.0,
    "data": {"status": "inactive", "domain": "127.0.0.1", "port": 1984, "proto": "udp"},
}


def _format_asn1_date(raw_date: str) -> str:
    raw = raw_date.strip().rstrip("Z")
    try:
        if len(raw) == 12:
            dt = datetime.strptime(raw, "%y%m%d%H%M%S")
        elif len(raw) == 14:
            dt = datetime.strptime(raw, "%Y%m%d%H%M%S")
        else:
            return "—"
        return dt.strftime("%Y-%m-%d")
    except Exception:
        return "—"


def get_pki_clients_fast() -> Dict[str, Dict[str, str]]:
    idx_mtime = INDEX_TXT_PATH.stat().st_mtime if INDEX_TXT_PATH.exists() else 0.0
    issued_mtime = ISSUED_DIR.stat().st_mtime if ISSUED_DIR.exists() else 0.0
    combined_mtime = idx_mtime + issued_mtime

    if combined_mtime > 0 and _pki_cache["mtime"] == combined_mtime:
        return _pki_cache["clients"]

    result: Dict[str, Dict[str, str]] = {}

    if INDEX_TXT_PATH.exists():
        try:
            for line in INDEX_TXT_PATH.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines():
                parts = line.strip().split("\t")
                if len(parts) >= 6:
                    state_flag = parts[0]
                    exp_date = _format_asn1_date(parts[1])
                    dn = parts[5]
                    cn_match = re.search(r"/CN=([^/\s]+)", dn)
                    if not cn_match:
                        continue
                    cn = cn_match.group(1)
                    if cn in ("server", "README") or cn.startswith("server_"):
                        continue

                    status = "valid" if state_flag == "V" else "revoked"
                    created_str = "—"
                    crt_path = ISSUED_DIR / f"{cn}.crt"
                    if crt_path.exists():
                        created_str = datetime.fromtimestamp(
                            crt_path.stat().st_mtime
                        ).strftime("%Y-%m-%d")

                    result[cn] = {
                        "status": status,
                        "created": created_str,
                        "expires": exp_date,
                    }
        except Exception:
            pass

    for folder, ext in ((ISSUED_DIR, "*.crt"), (INLINE_DIR, "*.inline")):
        if folder.exists():
            for f in folder.glob(ext):
                if f.stem not in ("server", "README") and not f.stem.startswith("server_"):
                    if f.stem not in result:
                        created_str = datetime.fromtimestamp(
                            f.stat().st_mtime
                        ).strftime("%Y-%m-%d")
                        result[f.stem] = {
                            "status": "valid",
                            "created": created_str,
                            "expires": "—",
                        }

    _pki_cache["mtime"] = combined_mtime
    _pki_cache["clients"] = result
    return result


def invalidate_pki_cache() -> None:
    _pki_cache["mtime"] = 0.0


def client_exists(client_name: str) -> bool:
    if not re.match(r"^[a-zA-Z0-9_-]+$", client_name):
        return False
    return client_name in get_pki_clients_fast()


def extract_pem_cert(raw_text: str) -> str:
    m = re.search(
        r"(-----BEGIN CERTIFICATE-----.*?-----END CERTIFICATE-----)",
        raw_text,
        re.DOTALL,
    )
    return m.group(1) if m else raw_text.strip()


def generate_config(client_name: str) -> str:
    dom = get_current_domain()
    port = get_current_port()
    proto = get_current_proto()
    cipher = get_setting("ovpn_cipher", "AES-256-GCM")
    auth = get_setting("ovpn_auth", "SHA256")
    verb = get_setting("ovpn_verb", "3")

    ca_cert = (PKI_DIR / "ca.crt").read_text(encoding="utf-8", errors="ignore").strip()
    raw_cert = (ISSUED_DIR / f"{client_name}.crt").read_text(
        encoding="utf-8", errors="ignore"
    )
    client_cert = extract_pem_cert(raw_cert)
    client_key = (
        (PRIVATE_DIR / f"{client_name}.key")
        .read_text(encoding="utf-8", errors="ignore")
        .strip()
    )

    tls_key = None
    tls_tag = "tls-crypt"
    if TLS_KEY_FILE.exists():
        tls_key = TLS_KEY_FILE.read_text(encoding="utf-8", errors="ignore").strip()
    elif (PKI_DIR / "ta.key").exists():
        tls_key = (
            (PKI_DIR / "ta.key").read_text(encoding="utf-8", errors="ignore").strip()
        )
        tls_tag = "tls-auth"

    config = (
        f"client\ndev tun\nproto {proto}\nremote {dom} {port}\n"
        "resolv-retry infinite\nnobind\npersist-key\npersist-tun\n"
        f"remote-cert-tls server\ncipher {cipher}\nauth {auth}\nverb {verb}\n"
    )
    if tls_key:
        direction = "key-direction 1\n" if tls_tag == "tls-auth" else ""
        config += (
            f"\n{direction}<ca>\n{ca_cert}\n</ca>\n<cert>\n{client_cert}\n</cert>\n"
            f"<key>\n{client_key}\n</key>\n<{tls_tag}>\n{tls_key}\n</{tls_tag}>\n"
        )
    else:
        config += (
            f"\n<ca>\n{ca_cert}\n</ca>\n<cert>\n{client_cert}\n</cert>\n"
            f"<key>\n{client_key}\n</key>\n"
        )
    return config


def create_client_sync(name: str, note: str = "", ttl_days: int = 0) -> Tuple[bool, str]:
    if not name or not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return False, "Invalid name"
    if len(name) > 64:
        return False, "Name too long"
    if client_exists(name):
        return False, "Client already exists"

    r = subprocess.run(
        ["./easyrsa", "--batch", "build-client-full", name, "nopass"],
        cwd=str(OVPN_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if r.returncode != 0:
        return False, "Easy-RSA error"
    subprocess.run(
        ["./easyrsa", "--batch", "inline", name],
        cwd=str(OVPN_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    expires_at = int(time.time() + (ttl_days * 86400)) if ttl_days > 0 else 0
    upsert_client_meta(name, note=note, expires_at=expires_at, is_paused=0)
    invalidate_pki_cache()
    return True, "OK"


def revoke_client_sync(client_name: str) -> Tuple[bool, str]:
    if not re.match(r"^[a-zA-Z0-9_-]+$", client_name):
        return False, "Invalid name"
    try:
        r1 = subprocess.run(
            ["./easyrsa", "--batch", "revoke", client_name],
            cwd=str(OVPN_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if r1.returncode != 0:
            return False, "Easy-RSA error"

        subprocess.run(
            ["./easyrsa", "--batch", "gen-crl"],
            cwd=str(OVPN_DIR),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        crl_file = PKI_DIR / "crl.pem"
        target_crl = SERVER_DIR / "crl.pem"
        if crl_file.exists():
            shutil.copy2(str(crl_file), str(target_crl))
            os.chmod(str(target_crl), 0o644)

        (INLINE_DIR / f"{client_name}.inline").unlink(missing_ok=True)
        (CCD_DIR / client_name).unlink(missing_ok=True)
        invalidate_pki_cache()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def delete_client_completely_sync(client_name: str) -> Tuple[bool, str]:
    if not re.match(r"^[a-zA-Z0-9_-]+$", client_name):
        return False, "Invalid name"
    try:
        for p in [
            ISSUED_DIR / f"{client_name}.crt",
            PRIVATE_DIR / f"{client_name}.key",
            INLINE_DIR / f"{client_name}.inline",
            REQ_DIR / f"{client_name}.req",
            CCD_DIR / client_name,
        ]:
            p.unlink(missing_ok=True)

        if INDEX_TXT_PATH.exists():
            lines = INDEX_TXT_PATH.read_text(
                encoding="utf-8", errors="ignore"
            ).splitlines()
            filtered = [
                l
                for l in lines
                if not re.search(rf"/CN={re.escape(client_name)}(?:$|/|\s)", l)
            ]
            INDEX_TXT_PATH.write_text(
                "\n".join(filtered) + ("\n" if filtered else ""), encoding="utf-8"
            )

        with get_db() as conn:
            conn.execute("DELETE FROM client_meta WHERE client_name=?", (client_name,))

        invalidate_pki_cache()
        return True, "OK"
    except Exception as e:
        return False, str(e)


def get_server_status() -> Dict[str, Any]:
    now = time.time()
    dom = get_current_domain()
    port = get_current_port()
    proto = get_current_proto()
    if now - _server_status_cache["ts"] < 5.0:
        d = _server_status_cache["data"].copy()
        d["domain"] = dom
        d["port"] = port
        d["proto"] = proto
        return d
    try:
        res = subprocess.run(
            ["systemctl", "is-active", "openvpn-server@server"],
            capture_output=True,
            text=True,
            timeout=2,
        )
        is_active = res.stdout.strip() == "active"
    except Exception:
        is_active = False
    data = {
        "status": "active" if is_active else "inactive",
        "domain": dom,
        "port": port,
        "proto": proto,
    }
    _server_status_cache["ts"] = now
    _server_status_cache["data"] = data
    return data


def invalidate_server_status_cache() -> None:
    _server_status_cache["ts"] = 0.0


def sync_openvpn_server_conf_from_settings(
    restart_service: bool = False,
) -> Tuple[bool, str]:
    if not SERVER_CONF_PATH.exists():
        return False, "server.conf not found"
    try:
        s = get_all_settings()
        lines = SERVER_CONF_PATH.read_text(
            encoding="utf-8", errors="ignore"
        ).splitlines()

        port = s.get("ovpn_port", str(OVPN_PORT))
        proto = s.get("ovpn_proto", PROTOCOL)
        cipher = s.get("ovpn_cipher", "AES-256-GCM")
        auth = s.get("ovpn_auth", "SHA256")
        mtu = s.get("ovpn_mtu", "1420")
        subnet = s.get("ovpn_subnet", "10.8.0.0 255.255.255.0")
        max_clients = s.get("ovpn_max_clients", "100")
        verb = s.get("ovpn_verb", "3")
        dns1 = s.get("ovpn_dns1", "1.1.1.1").strip()
        dns2 = s.get("ovpn_dns2", "8.8.8.8").strip()
        dup_cn = s.get("ovpn_duplicate_cn", "1") == "1"
        c2c = s.get("ovpn_client_to_client", "0") == "1"
        redir_gw = s.get("ovpn_redirect_gw", "1") == "1"

        managed_prefixes = (
            "port ",
            "proto ",
            "cipher ",
            "auth ",
            "tun-mtu ",
            "server ",
            "max-clients ",
            "verb ",
            "duplicate-cn",
            "client-to-client",
            "client-config-dir ",
            "management ",
            'push "dhcp-option DNS',
            'push "redirect-gateway',
        )

        clean_lines = []
        for l in lines:
            stripped = l.strip()
            if any(stripped.startswith(p) for p in managed_prefixes):
                continue
            clean_lines.append(l)

        clean_lines.append(f"port {port}")
        clean_lines.append(f"proto {proto}")
        clean_lines.append(f"server {subnet}")
        clean_lines.append(f"cipher {cipher}")
        clean_lines.append(f"auth {auth}")
        clean_lines.append(f"tun-mtu {mtu}")
        clean_lines.append(f"max-clients {max_clients}")
        clean_lines.append(f"verb {verb}")
        clean_lines.append(f"client-config-dir {CCD_DIR}")
        clean_lines.append(f"management {MGMT_HOST} {MGMT_PORT}")

        if redir_gw:
            clean_lines.append('push "redirect-gateway def1 bypass-dhcp"')

        adblock_on = s.get("adblock_enabled", "0") == "1"
        adblock_ip = s.get("adblock_dns_ip", "10.8.0.1").strip()

        if adblock_on and adblock_ip:
            clean_lines.append(f'push "dhcp-option DNS {adblock_ip}"')
        else:
            if dns1:
                clean_lines.append(f'push "dhcp-option DNS {dns1}"')
            if dns2:
                clean_lines.append(f'push "dhcp-option DNS {dns2}"')

        if dup_cn:
            clean_lines.append("duplicate-cn")
        if c2c:
            clean_lines.append("client-to-client")

        SERVER_CONF_PATH.write_text("\n".join(clean_lines) + "\n", encoding="utf-8")

        if restart_service:
            subprocess.run(
                ["systemctl", "restart", "openvpn-server@server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return True, "OK"
    except Exception as e:
        return False, str(e)


def parse_existing_server_conf_into_db() -> None:
    if not SERVER_CONF_PATH.exists():
        return
    try:
        content = SERVER_CONF_PATH.read_text(encoding="utf-8", errors="ignore")
        m_port = re.search(r"^\s*port\s+(\d+)", content, re.MULTILINE)
        if m_port:
            set_setting("ovpn_port", m_port.group(1))
        m_proto = re.search(r"^\s*proto\s+(\S+)", content, re.MULTILINE)
        if m_proto:
            set_setting("ovpn_proto", m_proto.group(1))
        m_cipher = re.search(r"^\s*cipher\s+(\S+)", content, re.MULTILINE)
        if m_cipher:
            set_setting("ovpn_cipher", m_cipher.group(1))
        m_auth = re.search(r"^\s*auth\s+(\S+)", content, re.MULTILINE)
        if m_auth:
            set_setting("ovpn_auth", m_auth.group(1))
        m_mtu = re.search(r"^\s*tun-mtu\s+(\d+)", content, re.MULTILINE)
        if m_mtu:
            set_setting("ovpn_mtu", m_mtu.group(1))
        m_srv = re.search(
            r"^\s*server\s+(\d+\.\d+\.\d+\.\d+\s+\d+\.\d+\.\d+\.\d+)",
            content,
            re.MULTILINE,
        )
        if m_srv:
            set_setting("ovpn_subnet", m_srv.group(1))
        m_verb = re.search(r"^\s*verb\s+(\d+)", content, re.MULTILINE)
        if m_verb:
            set_setting("ovpn_verb", m_verb.group(1))
        adblock_ip = get_setting("adblock_dns_ip", "10.8.0.1")
        dns_list = [
            d
            for d in re.findall(r'push\s+"dhcp-option\s+DNS\s+([^"]+)"', content)
            if d != adblock_ip
        ]
        if len(dns_list) >= 1:
            set_setting("ovpn_dns1", dns_list[0])
        if len(dns_list) >= 2:
            set_setting("ovpn_dns2", dns_list[1])
        set_setting(
            "ovpn_duplicate_cn",
            "1" if re.search(r"^\s*duplicate-cn\b", content, re.MULTILINE) else "0",
        )
        set_setting(
            "ovpn_client_to_client",
            "1" if re.search(r"^\s*client-to-client\b", content, re.MULTILINE) else "0",
        )
    except Exception:
        pass


# ============================================================
# ДВУСТОРОННЕЕ ОГРАНИЧЕНИЕ СКОРОСТИ ЧЕРЕЗ TC + IFB
# ============================================================

def _run_tc(args: List[str]) -> bool:
    try:
        r = subprocess.run(
            ["tc"] + args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5
        )
        return r.returncode == 0
    except Exception:
        return False


def _ensure_ifb_device() -> bool:
    if not Path(f"/sys/class/net/{IFB_IFACE}").exists():
        subprocess.run(
            ["modprobe", "ifb"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        subprocess.run(
            ["ip", "link", "add", IFB_IFACE, "type", "ifb"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    subprocess.run(
        ["ip", "link", "set", "dev", IFB_IFACE, "up"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return Path(f"/sys/class/net/{IFB_IFACE}").exists()


def _clear_tc_rules_sync() -> None:
    if Path(f"/sys/class/net/{TUN_IFACE}").exists():
        _run_tc(["qdisc", "del", "dev", TUN_IFACE, "root"])
        _run_tc(["qdisc", "del", "dev", TUN_IFACE, "ingress"])
    if Path(f"/sys/class/net/{IFB_IFACE}").exists():
        _run_tc(["qdisc", "del", "dev", IFB_IFACE, "root"])


def get_effective_speed_limits_map(
    active_sessions: Dict[str, Dict[str, Any]],
) -> Dict[str, Tuple[str, int]]:
    """
    Возвращает словарь {virt_ip: (client_name, limit_kbps)} для активных клиентов,
    у которых задан ненулевой лимит скорости.
    Режимы:
      - none: лимиты отключены
      - global: global_speed_limit_kbps для всех активных клиентов
      - selected: global_speed_limit_kbps для выбранных в selected_limit_clients
      - per_client: индивидуальный speed_limit_kbps из client_meta (с fallback на global, если задан)
    """
    mode = get_setting("speed_limit_mode", "none")
    if mode == "none":
        return {}

    try:
        global_kbps = max(0, int(get_setting("global_speed_limit_kbps", "0") or "0"))
    except Exception:
        global_kbps = 0

    try:
        selected_raw = json.loads(get_setting("selected_limit_clients", "[]") or "[]")
        selected_set = set(selected_raw) if isinstance(selected_raw, list) else set()
    except Exception:
        selected_set = set()

    meta_map = get_all_client_meta()
    result: Dict[str, Tuple[str, int]] = {}

    for name, sess in active_sessions.items():
        vip = (sess.get("virt_ip") or "").strip()
        if not vip or vip == "—":
            continue
        # Берём только IPv4 адрес клиента
        ip_part = vip.split("/")[0].strip()
        if not re.match(r"^\d{1,3}(?:\.\d{1,3}){3}$", ip_part):
            continue

        limit_kbps = 0
        if mode == "global":
            limit_kbps = global_kbps
        elif mode == "selected":
            if name in selected_set:
                limit_kbps = global_kbps
        elif mode == "per_client":
            c_lim = int(meta_map.get(name, {}).get("speed_limit_kbps", 0) or 0)
            limit_kbps = c_lim if c_lim > 0 else global_kbps

        if limit_kbps > 0:
            result[ip_part] = (name, limit_kbps)

    return result


def apply_bidirectional_speed_limits_sync(
    active_sessions: Optional[Dict[str, Dict[str, Any]]] = None,
) -> None:
    """
    Применяет двусторонний лимит скорости:
      - egress на TUN_IFACE (трафик от сервера/интернета к клиенту)
      - ingress на TUN_IFACE -> зеркалируется на IFB_IFACE (трафик от клиента в сеть)
    """
    _clear_tc_rules_sync()

    sessions = active_sessions if active_sessions is not None else speed_monitor.active_sessions
    ip_limits = get_effective_speed_limits_map(sessions)
    if not ip_limits:
        return

    if not Path(f"/sys/class/net/{TUN_IFACE}").exists():
        return
    if not _ensure_ifb_device():
        return

    # Корневые HTB qdisc на tun0 (egress) и ifb0 (ingress)
    if not _run_tc(["qdisc", "add", "dev", TUN_IFACE, "root", "handle", "1:", "htb", "default", "9999"]):
        return
    if not _run_tc(["qdisc", "add", "dev", IFB_IFACE, "root", "handle", "1:", "htb", "default", "9999"]):
        return

    # Безлимитный класс по умолчанию (1000mbit)
    _run_tc(["class", "add", "dev", TUN_IFACE, "parent", "1:", "classid", "1:9999", "htb", "rate", "1000mbit", "ceil", "1000mbit"])
    _run_tc(["class", "add", "dev", IFB_IFACE, "parent", "1:", "classid", "1:9999", "htb", "rate", "1000mbit", "ceil", "1000mbit"])

    # Зеркалируем входящий трафик с tun0 на ifb0
    _run_tc(["qdisc", "add", "dev", TUN_IFACE, "ingress"])
    _run_tc([
        "filter", "add", "dev", TUN_IFACE, "parent", "ffff:", "protocol", "ip",
        "u32", "match", "u32", "0", "0",
        "action", "mirred", "egress", "redirect", "dev", IFB_IFACE,
    ])

    class_idx = 10
    for vip, (_, kbps) in ip_limits.items():
        rate_str = f"{max(16, kbps)}kbit"
        burst_bytes = max(16384, kbps * 128 // 8)
        cid = f"1:{class_idx}"

        # Download (сервер -> клиент): dst == vip на tun0
        _run_tc(["class", "add", "dev", TUN_IFACE, "parent", "1:", "classid", cid, "htb", "rate", rate_str, "ceil", rate_str, "burst", str(burst_bytes)])
        _run_tc(["qdisc", "add", "dev", TUN_IFACE, "parent", cid, "handle", f"{class_idx}:", "fq_codel"])
        _run_tc(["filter", "add", "dev", TUN_IFACE, "protocol", "ip", "parent", "1:0", "prio", "1", "u32", "match", "ip", "dst", f"{vip}/32", "flowid", cid])

        # Upload (клиент -> сервер): src == vip на ifb0
        _run_tc(["class", "add", "dev", IFB_IFACE, "parent", "1:", "classid", cid, "htb", "rate", rate_str, "ceil", rate_str, "burst", str(burst_bytes)])
        _run_tc(["qdisc", "add", "dev", IFB_IFACE, "parent", cid, "handle", f"{class_idx}:", "fq_codel"])
        _run_tc(["filter", "add", "dev", IFB_IFACE, "protocol", "ip", "parent", "1:0", "prio", "1", "u32", "match", "ip", "src", f"{vip}/32", "flowid", cid])

        class_idx += 1


class SpeedMonitor:
    def __init__(self, history_len: int = 300):
        self.prev_traffic: Dict[str, Dict[str, Any]] = {}
        self.current_speeds: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.virt_ip_to_client: Dict[str, str] = {}
        self.online_clients: set = set()
        self.history: deque = deque(maxlen=history_len)
        self._last_tc_signature: Optional[str] = None

    @staticmethod
    def format_bytes_speed(bytes_per_sec: float) -> str:
        if bytes_per_sec <= 0:
            return "0 B/s"
        units = ["B/s", "KB/s", "MB/s", "GB/s"]
        i = 0
        speed = bytes_per_sec
        while speed >= 1024 and i < len(units) - 1:
            speed /= 1024.0
            i += 1
        return f"{speed:.1f} {units[i]}"

    @staticmethod
    def _extract_ip(raw_addr: str) -> str:
        if not raw_addr:
            return "—"
        s = raw_addr.strip()
        if s.startswith("["):
            end = s.find("]")
            if end > 0:
                s = s[1:end]
        m = re.match(r"^(?:udp|tcp)\d?:(.+)$", s, re.IGNORECASE)
        if m:
            s = m.group(1).strip()
            if s.startswith("["):
                end = s.find("]")
                if end > 0:
                    s = s[1:end]
        if s.lower().startswith("::ffff:"):
            s = s[7:]
        m4 = re.match(r"^(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})(?::\d+)?$", s)
        if m4:
            return m4.group(1)
        if s.count(":") >= 2:
            return s
        parts = s.rsplit(":", 1)
        if len(parts) == 2 and parts[1].isdigit():
            return parts[0]
        return s or "—"

    async def send_command(self, cmd: str) -> List[str]:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(MGMT_HOST, MGMT_PORT), timeout=1.0
        )
        try:
            await asyncio.wait_for(reader.readuntil(b"\n"), timeout=0.5)
            writer.write(f"{cmd}\n".encode("utf-8"))
            await writer.drain()

            lines = []
            while True:
                line = await asyncio.wait_for(reader.readline(), timeout=1.0)
                if not line:
                    break
                decoded = line.decode("utf-8", errors="ignore").strip()
                if (
                    decoded == "END"
                    or decoded.startswith("SUCCESS:")
                    or decoded.startswith("ERROR:")
                ):
                    lines.append(decoded)
                    break
                if decoded:
                    lines.append(decoded)

            writer.write(b"quit\n")
            await writer.drain()
            return lines
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    @classmethod
    def _parse_status_lines(cls, lines: List[str]) -> Dict[str, Dict[str, Any]]:
        clients_data = {}
        for line in lines:
            if line.startswith("CLIENT_LIST"):
                parts = line.split(",")
                if len(parts) > 7 and parts[1] != "Common Name":
                    name = parts[1]
                    real_addr = cls._extract_ip(parts[2]) if parts[2] else "—"
                    virt_addr = parts[3] or "—"
                    try:
                        recv_b = int(parts[5])
                        sent_b = int(parts[6])
                    except ValueError:
                        continue
                    connected_since = parts[7] if len(parts) > 7 else "—"
                    clients_data[name] = {
                        "recv": recv_b,
                        "sent": sent_b,
                        "real_ip": real_addr,
                        "virt_ip": virt_addr,
                        "connected_since": connected_since,
                    }
        return clients_data

    async def query_management_status(self) -> Dict[str, Dict[str, Any]]:
        try:
            raw_lines = await self.send_command("status 2")
            return self._parse_status_lines(raw_lines)
        except Exception:
            return self._read_status_log_fallback()

    def _read_status_log_fallback(self) -> Dict[str, Dict[str, Any]]:
        if not STATUS_LOG_PATH.exists():
            return {}
        try:
            with open(STATUS_LOG_PATH, "r", encoding="utf-8", errors="ignore") as f:
                return self._parse_status_lines([line.strip() for line in f])
        except Exception:
            return {}

    async def kick_client(self, client_name: str) -> bool:
        try:
            res = await self.send_command(f"kill {client_name}")
            return any("SUCCESS:" in r for r in res)
        except Exception:
            return False

    async def update_tick(self) -> None:
        speed_enabled = get_setting("enable_speed_monitor", "1") == "1"
        current_data = await self.query_management_status()
        now = time.time()
        time_str = datetime.now().strftime("%H:%M:%S")
        new_speeds = {}
        ip_map = {}

        prev_online = set(self.online_clients)
        curr_online = set(current_data.keys())

        newly_connected = [
            {
                "name": cname,
                "real_ip": current_data[cname].get("real_ip", ""),
                "virt_ip": current_data[cname].get("virt_ip", ""),
            }
            for cname in (curr_online - prev_online)
        ]
        newly_disconnected = list(prev_online - curr_online)

        if newly_connected or newly_disconnected:
            await asyncio.to_thread(
                record_connection_events, newly_connected, newly_disconnected
            )

        self.online_clients = curr_online
        self.active_sessions = current_data

        for name, data in current_data.items():
            vip = data.get("virt_ip")
            if vip and vip != "—":
                ip_map[vip] = name

            if name in self.prev_traffic:
                prev = self.prev_traffic[name]
                dt = max(0.2, now - prev["time"])
                if data["recv"] < prev["recv"] or data["sent"] < prev["sent"]:
                    delta_up = max(0, data["recv"])
                    delta_down = max(0, data["sent"])
                else:
                    delta_up = max(0, data["recv"] - prev["recv"])
                    delta_down = max(0, data["sent"] - prev["sent"])

                speed_down = (delta_down / dt) if speed_enabled else 0.0
                speed_up = (delta_up / dt) if speed_enabled else 0.0
            else:
                speed_down = 0.0
                speed_up = 0.0

            self.prev_traffic[name] = {
                "recv": data["recv"],
                "sent": data["sent"],
                "time": now,
            }

            tot = speed_down + speed_up
            new_speeds[name] = {
                "down": round(speed_down),
                "up": round(speed_up),
                "total": round(tot),
                "down_fmt": self.format_bytes_speed(speed_down),
                "up_fmt": self.format_bytes_speed(speed_up),
                "total_fmt": self.format_bytes_speed(tot),
                "real_ip": data.get("real_ip", "—"),
                "virt_ip": data.get("virt_ip", "—"),
            }

        for old_client in list(self.prev_traffic.keys()):
            if old_client not in current_data:
                del self.prev_traffic[old_client]

        self.virt_ip_to_client = ip_map
        self.current_speeds = new_speeds
        if speed_enabled:
            self.history.append({"time": time_str, "ts": now, "speeds": new_speeds})

        # Обновляем tc только если изменился состав активных IP/лимитов
        limits_map = get_effective_speed_limits_map(current_data)
        sig = json.dumps(sorted(limits_map.items()), ensure_ascii=False)
        if sig != self._last_tc_signature:
            self._last_tc_signature = sig
            await asyncio.to_thread(apply_bidirectional_speed_limits_sync, current_data)

    def get_history_window(self, seconds: int = 300) -> List[Dict[str, Any]]:
        min_ts = time.time() - seconds
        return [pt for pt in self.history if pt["ts"] >= min_ts]


speed_monitor = SpeedMonitor(history_len=300)


def check_expired_clients_sync() -> None:
    try:
        now = int(time.time())
        with get_db() as conn:
            rows = conn.execute(
                "SELECT client_name FROM client_meta WHERE is_paused = 0 AND expires_at > 0 AND ? > expires_at",
                (now,),
            ).fetchall()
            for r in rows:
                cn = r["client_name"]
                conn.execute(
                    "UPDATE client_meta SET is_paused = 1 WHERE client_name = ?", (cn,)
                )
                ccd_path = CCD_DIR / cn
                CCD_DIR.mkdir(parents=True, exist_ok=True)
                ccd_path.write_text("disable\n", encoding="utf-8")
                try:
                    with socket.create_connection((MGMT_HOST, MGMT_PORT), timeout=1.0) as s:
                        s.recv(512)
                        s.sendall(f"kill {cn}\nquit\n".encode("utf-8"))
                except Exception:
                    pass
    except Exception:
        pass