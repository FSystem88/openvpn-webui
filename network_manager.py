import asyncio
import base64
import ipaddress
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from database import (
    ADBLOCK_DNS_IP,
    DNSMASQ_ADBLOCK_CONF,
    DNSMASQ_MAIN_CONF,
    TUN_IFACE,
    get_db,
    get_ovpn_subnet_cidr,
    get_setting,
    set_setting,
)
from openvpn_manager import (
    CCD_DIR,
    SERVER_CONF_PATH,
    invalidate_server_status_cache,
    parse_existing_server_conf_into_db,
    sync_openvpn_server_conf_from_settings,
)

try:
    import paramiko
except ImportError:
    paramiko = None


# ============================================================
# ТРЕКЕР СТАТУСА И ПРОГРЕССА ФОНОВЫХ ЗАДАЧ
# ============================================================

class BackgroundTaskTracker:
    def __init__(self) -> None:
        self._tasks: Dict[str, Dict[str, Any]] = {}

    def start(self, task_id: str, title: str, progress: int = 5, message: str = "") -> None:
        self._tasks[task_id] = {
            "id": task_id,
            "title": title,
            "status": "running",
            "progress": max(0, min(100, int(progress))),
            "message": message,
            "updated_at": time.time(),
        }

    def update(self, task_id: str, progress: int, message: str = "") -> None:
        t = self._tasks.get(task_id)
        if not t:
            return
        t["progress"] = max(0, min(100, int(progress)))
        if message:
            t["message"] = message
        t["updated_at"] = time.time()

    def finish(self, task_id: str, ok: bool = True, message: str = "") -> None:
        t = self._tasks.get(task_id)
        if not t:
            t = {
                "id": task_id,
                "title": task_id,
                "progress": 100 if ok else 0,
                "message": "",
            }
            self._tasks[task_id] = t
        t["status"] = "done" if ok else "error"
        t["progress"] = 100 if ok else t.get("progress", 0)
        if message:
            t["message"] = message
        t["updated_at"] = time.time()

    def get(self, task_id: str) -> Dict[str, Any]:
        return self._tasks.get(
            task_id,
            {
                "id": task_id,
                "title": task_id,
                "status": "idle",
                "progress": 0,
                "message": "",
                "updated_at": time.time(),
            },
        )

    def all(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._tasks)


task_tracker = BackgroundTaskTracker()


# ============================================================
# СИСТЕМНЫЕ МЕТРИКИ (CPU / RAM / DISK / WG PING)
# ============================================================

_sys_stats_cache: Dict[str, Any] = {
    "ts": 0.0,
    "prev_idle": 0.0,
    "prev_total": 0.0,
    "data": None,
}


def get_system_stats() -> Dict[str, Any]:
    now = time.time()
    if _sys_stats_cache["data"] and (now - _sys_stats_cache["ts"] < 3.0):
        return _sys_stats_cache["data"]

    cpu_pct = 0.0
    try:
        with open("/proc/stat", "r", encoding="utf-8") as f:
            fields = [float(x) for x in f.readline().split()[1:]]
        idle = fields[3]
        total = sum(fields)
        prev_idle = _sys_stats_cache["prev_idle"]
        prev_total = _sys_stats_cache["prev_total"]
        if prev_total > 0 and total > prev_total:
            cpu_pct = round(
                max(
                    0.0,
                    min(
                        100.0, 100.0 * (1.0 - (idle - prev_idle) / (total - prev_total))
                    ),
                ),
                1,
            )
        _sys_stats_cache["prev_idle"] = idle
        _sys_stats_cache["prev_total"] = total
    except Exception:
        pass

    ram_used_mb, ram_total_mb = 0, 0
    try:
        meminfo: Dict[str, int] = {}
        with open("/proc/meminfo", "r", encoding="utf-8") as f:
            for line in f:
                parts = line.split(":")
                if len(parts) == 2:
                    meminfo[parts[0].strip()] = int(parts[1].split()[0])
        total_kb = meminfo.get("MemTotal", 0)
        avail_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        ram_total_mb = round(total_kb / 1024)
        ram_used_mb = round((total_kb - avail_kb) / 1024)
    except Exception:
        pass

    disk_used_gb, disk_total_gb = 0.0, 0.0
    try:
        st = shutil.disk_usage("/")
        disk_total_gb = round(st.total / (1024**3), 1)
        disk_used_gb = round(st.used / (1024**3), 1)
    except Exception:
        pass

    wg_ping = "—"
    try:
        if Path("/sys/class/net/wg0").exists():
            res = subprocess.run(
                ["ping", "-c", "1", "-W", "1", "10.200.0.2"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            if res.returncode == 0:
                m = re.search(r"time=([\d.]+)\s*ms", res.stdout)
                if m:
                    wg_ping = f"{m.group(1)} ms"
    except Exception:
        pass

    res_data = {
        "cpu": cpu_pct,
        "ram_used": ram_used_mb,
        "ram_total": ram_total_mb,
        "disk_used": disk_used_gb,
        "disk_total": disk_total_gb,
        "wg_ping": wg_ping,
    }
    _sys_stats_cache["ts"] = now
    _sys_stats_cache["data"] = res_data
    return res_data


# ============================================================
# DNS ADBLOCK / DNSMASQ
# ============================================================

def ensure_dnsmasq_installed_sync(
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, str]:
    try:
        if on_progress:
            on_progress(15, "Проверка конфликтов DNS...")

        if Path("/opt/AdGuardHome").exists() or Path("/etc/systemd/system/AdGuardHome.service").exists():
            subprocess.run(
                ["/opt/AdGuardHome/AdGuardHome", "-s", "uninstall"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            subprocess.run(["systemctl", "stop", "AdGuardHome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "disable", "AdGuardHome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree("/opt/AdGuardHome", ignore_errors=True)
            Path("/etc/systemd/system/AdGuardHome.service").unlink(missing_ok=True)

        if shutil.which("dnsmasq") is None:
            if on_progress:
                on_progress(30, "Установка dnsmasq...")
            subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=90)
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            r = subprocess.run(
                ["apt-get", "install", "-y", "dnsmasq"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=150,
            )
            if r.returncode != 0 and shutil.which("dnsmasq") is None:
                return False, "Failed to install dnsmasq"

        if on_progress:
            on_progress(50, "Запись конфигурации dnsmasq...")

        for conflict_file in [
            Path("/etc/dnsmasq.d/ubuntu-fan"),
            Path("/etc/dnsmasq.d/ovpn_adblock.hosts"),
            Path("/etc/dnsmasq.d/ovpn_custom.conf"),
        ]:
            conflict_file.unlink(missing_ok=True)

        dns_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
        up1 = get_setting("ovpn_dns1", "1.1.1.1").strip() or "1.1.1.1"
        up2 = get_setting("ovpn_dns2", "8.8.8.8").strip() or "8.8.8.8"
        if up1 in (dns_ip, "127.0.0.1"):
            up1 = "1.1.1.1"
        if up2 in (dns_ip, "127.0.0.1"):
            up2 = "8.8.8.8"

        Path("/etc/dnsmasq.d").mkdir(parents=True, exist_ok=True)
        base_conf = (
            "port=53\n"
            f"listen-address=127.0.0.1,{dns_ip}\n"
            "bind-interfaces\n"
            "no-resolv\n"
            f"server={up1}\n"
            f"server={up2}\n"
            "cache-size=10000\n"
            "min-cache-ttl=300\n"
        )
        DNSMASQ_MAIN_CONF.write_text(base_conf, encoding="utf-8")
        if not DNSMASQ_ADBLOCK_CONF.exists():
            DNSMASQ_ADBLOCK_CONF.write_text("", encoding="utf-8")

        subprocess.run(["systemctl", "enable", "dnsmasq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["systemctl", "restart", "dnsmasq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, "OK"
    except Exception as e:
        return False, str(e)


def parse_adlist_content(raw_text: str) -> List[str]:
    domains = set()
    ignore = {
        "localhost",
        "localhost.localdomain",
        "local",
        "broadcasthost",
        "ip6-localhost",
        "ip6-loopback",
        "0.0.0.0",
        "127.0.0.1",
    }
    domain_re = re.compile(r"^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$")

    for line in raw_text.splitlines():
        line = line.strip().lower()
        if not line or line.startswith(("#", "!", "/", "[")):
            continue
        if "#" in line:
            line = line.split("#", 1)[0].strip()

        if line.startswith("||"):
            dom = line[2:].split("^")[0].split("$")[0].split("/")[0].strip()
        else:
            parts = line.split()
            if len(parts) >= 2 and parts[0] in ("0.0.0.0", "127.0.0.1", "::1"):
                dom = parts[1].strip()
            elif len(parts) == 1:
                dom = parts[0].strip()
            else:
                continue

        if dom.startswith("www."):
            dom = dom[4:]
        if dom in ignore or len(dom) > 253:
            continue
        if domain_re.match(dom):
            domains.add(dom)

    return sorted(domains)


def fetch_and_parse_adlist(url: str) -> Tuple[bool, List[str], str]:
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0 (OpenVPN-Panel-AdBlock)"}
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            raw = resp.read(100 * 1024 * 1024).decode("utf-8", errors="ignore")
        if "<html" in raw[:500].lower():
            return False, [], "Invalid list content"
        domains = parse_adlist_content(raw)
        if not domains:
            return False, [], "No valid domains"
        return True, domains, "OK"
    except Exception as e:
        return False, [], str(e)


def rebuild_dnsmasq_adblock_conf_sync(
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, int, str]:
    ok, msg = ensure_dnsmasq_installed_sync(on_progress=on_progress)
    if not ok:
        return False, 0, msg

    adblock_on = get_setting("adblock_enabled", "0") == "1"
    if not adblock_on:
        DNSMASQ_ADBLOCK_CONF.write_text("", encoding="utf-8")
        subprocess.run(
            ["systemctl", "kill", "-s", "SIGHUP", "dnsmasq"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True, 0, "OK"

    if on_progress:
        on_progress(65, "Сборка списков доменов...")

    black_set = set()
    white_set = set()
    cache_dir = Path("/var/cache/ovpn_adblock")
    cache_dir.mkdir(parents=True, exist_ok=True)

    with get_db() as conn:
        lists = conn.execute("SELECT id, list_type FROM adblock_lists").fetchall()
        customs = conn.execute("SELECT domain, list_type FROM adblock_domains").fetchall()

    for row in lists:
        cache_file = cache_dir / f"list_{row['id']}.txt"
        if cache_file.exists():
            try:
                doms = [
                    line.strip()
                    for line in cache_file.read_text(
                        encoding="utf-8", errors="ignore"
                    ).splitlines()
                    if line.strip()
                ]
                if row["list_type"] == "white":
                    white_set.update(doms)
                else:
                    black_set.update(doms)
            except Exception:
                pass

    for row in customs:
        d = row["domain"].strip().lower()
        if row["list_type"] == "white":
            white_set.add(d)
        else:
            black_set.add(d)

    final_black = sorted(black_set - white_set)
    if on_progress:
        on_progress(80, f"Запись {len(final_black)} правил в dnsmasq...")

    lines = [f"address=/{dom}/0.0.0.0" for dom in final_black]
    DNSMASQ_ADBLOCK_CONF.write_text(
        "\n".join(lines) + ("\n" if lines else ""), encoding="utf-8"
    )
    subprocess.run(
        ["systemctl", "restart", "dnsmasq"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return True, len(final_black), "OK"


def apply_dns_redirect_iptables_sync(enable: bool, dns_ip: str) -> None:
    for proto in ("udp", "tcp"):
        rule = [
            "PREROUTING",
            "-i",
            TUN_IFACE,
            "-p",
            proto,
            "--dport",
            "53",
            "-j",
            "REDIRECT",
            "--to-ports",
            "53",
        ]
        while (
            subprocess.run(
                ["iptables", "-t", "nat", "-D"] + rule,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            ).returncode
            == 0
        ):
            pass
        if enable:
            subprocess.run(
                ["iptables", "-t", "nat", "-I", "PREROUTING", "1"] + rule[1:],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )


def apply_adblock_state_sync(
    enable: bool,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, str]:
    dns_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
    set_setting("adblock_enabled", "1" if enable else "0")

    ok, _, msg = rebuild_dnsmasq_adblock_conf_sync(on_progress=on_progress)
    if not ok:
        set_setting("adblock_enabled", "0")
        return False, msg

    if on_progress:
        on_progress(90, "Обновление правил iptables и OpenVPN...")

    apply_dns_redirect_iptables_sync(enable, dns_ip)
    ok_conf, msg_conf = sync_openvpn_server_conf_from_settings(restart_service=True)
    if not ok_conf:
        return False, msg_conf

    invalidate_server_status_cache()
    if on_progress:
        on_progress(100, "Готово")
    return True, "OK"


# ============================================================
# ТОРРЕНТЫ, IPSET И WIREGUARD СПЛИТ-ТУННЕЛЬ
# ============================================================

def apply_torrent_block_sync(enable: bool) -> None:
    subnet_cidr = get_ovpn_subnet_cidr()
    safe_signatures = [
        "BitTorrent protocol",
        "peer_id=",
        "info_hash",
        "announce.php?passkey=",
    ]
    for s in safe_signatures:
        rule_tcp = [
            "FORWARD",
            "-s",
            subnet_cidr,
            "-p",
            "tcp",
            "!",
            "--dport",
            "443",
            "-m",
            "string",
            "--algo",
            "bm",
            "--to",
            "180",
            "--string",
            s,
            "-j",
            "DROP",
        ]
        rule_udp = [
            "FORWARD",
            "-s",
            subnet_cidr,
            "-p",
            "udp",
            "!",
            "--dport",
            "443",
            "-m",
            "string",
            "--algo",
            "bm",
            "--to",
            "180",
            "--string",
            s,
            "-j",
            "DROP",
        ]
        for rule in (rule_tcp, rule_udp):
            chk = subprocess.run(
                ["iptables", "-C"] + rule,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if enable and chk.returncode != 0:
                subprocess.run(
                    ["iptables", "-I", "FORWARD", "1"] + rule[1:],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif not enable and chk.returncode == 0:
                subprocess.run(
                    ["iptables", "-D"] + rule,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )


def reload_ipset_sync() -> None:
    for set_name, max_elem in (
        ("ru_ips", "262144"),
        ("force_wg_ips", "65536"),
        ("force_direct_ips", "65536"),
    ):
        subprocess.run(
            ["ipset", "create", set_name, "hash:net", "maxelem", max_elem, "-exist"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    ru_file = Path("/etc/wireguard/ru.txt")
    custom_raw = get_setting("custom_cidrs")
    cidr_re = re.compile(r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:/[0-9]{1,2})?$")

    nets: List[str] = []
    if ru_file.exists():
        for line in ru_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and cidr_re.match(line):
                nets.append(line)

    if custom_raw:
        for line in custom_raw.splitlines():
            line = line.strip()
            if line and cidr_re.match(line):
                nets.append(line)

    force_wg_nets: List[str] = []
    force_direct_nets: List[str] = []

    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT resolved_ip, route_via FROM split_links"
            ).fetchall()
            for r in rows:
                target_list = (
                    force_wg_nets if r["route_via"] == "wg" else force_direct_nets
                )
                for ip in re.split(r"[,\s]+", r["resolved_ip"] or ""):
                    ip = ip.strip()
                    if ip and cidr_re.match(ip):
                        target_list.append(ip)
    except Exception:
        pass

    wg_override_set = set(force_wg_nets)
    nets = [n for n in nets if n not in wg_override_set]

    def _apply_set(name: str, items: List[str], max_elem: int = 262144) -> None:
        tmp = f"{name}_tmp"
        payload = f"create {tmp} hash:net maxelem {max_elem} -exist\nflush {tmp}\n"
        if items:
            payload += "\n".join(f"add {tmp} {n} -exist" for n in set(items)) + "\n"
        payload += f"swap {tmp} {name}\ndestroy {tmp}\n"
        subprocess.run(
            ["ipset", "restore"],
            input=payload.encode("utf-8"),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    _apply_set("ru_ips", nets, 262144)
    _apply_set("force_wg_ips", force_wg_nets, 65536)
    _apply_set("force_direct_ips", force_direct_nets, 65536)


def apply_routing_mode_sync(mode: str) -> None:
    wg_conf_path = Path("/etc/wireguard/wg0.conf")
    if mode == "off":
        subprocess.run(
            ["systemctl", "stop", "wg-quick@wg0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["systemctl", "disable", "wg-quick@wg0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return

    if not wg_conf_path.exists():
        return

    conf = wg_conf_path.read_text(encoding="utf-8", errors="ignore")
    ru_priv_m = re.search(r"PrivateKey\s*=\s*(.+)", conf)
    remote_pub_m = re.search(r"PublicKey\s*=\s*(.+)", conf)
    endpoint_m = re.search(r"Endpoint\s*=\s*(.+)", conf)

    if not (ru_priv_m and remote_pub_m and endpoint_m):
        return

    subprocess.run(
        ["systemctl", "stop", "wg-quick@wg0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    reload_ipset_sync()

    subnet_cidr = get_ovpn_subnet_cidr()
    priority_rules = [
        f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set force_direct_ips dst -j ACCEPT",
        f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set force_wg_ips dst -j MARK --set-mark 0x1",
        f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set force_wg_ips dst -j ACCEPT",
    ]
    priority_rules_del = [
        r.replace("-A PREROUTING", "-D PREROUTING") for r in priority_rules
    ]

    if mode == "all":
        base_rules = [
            f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -j MARK --set-mark 0x1"
        ]
        base_rules_del = [
            f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -j MARK --set-mark 0x1"
        ]
    elif mode == "cidr_wg":
        base_rules = [
            f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set ru_ips dst -j MARK --set-mark 0x1"
        ]
        base_rules_del = [
            f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -m set --match-set ru_ips dst -j MARK --set-mark 0x1"
        ]
    else:
        base_rules = [
            f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set ! --match-set ru_ips dst -j MARK --set-mark 0x1"
        ]
        base_rules_del = [
            f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -m set ! --match-set ru_ips dst -j MARK --set-mark 0x1"
        ]

    all_mangle_up = "\n".join(f"PostUp = {r}" for r in (priority_rules + base_rules))
    all_mangle_down = "\n".join(
        f"PostDown = {r}" for r in (priority_rules_del + base_rules_del)
    )

    mss_up = "iptables -t mangle -I FORWARD 1 -p tcp -m tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu"
    mss_down = "iptables -t mangle -D FORWARD -p tcp -m tcp --tcp-flags SYN,RST SYN -j TCPMSS --clamp-mss-to-pmtu"

    ru_conf = f"""[Interface]
Address = 10.200.0.1/30
PrivateKey = {ru_priv_m.group(1).strip()}
MTU = 1360
Table = off

PostUp = ip route add default dev wg0 table 100
{all_mangle_up}
PostUp = {mss_up}
PostUp = ip rule add fwmark 0x1 table 100 priority 100

PostDown = ip rule del fwmark 0x1 table 100 priority 100
PostDown = {mss_down}
{all_mangle_down}
PostDown = ip route del default dev wg0 table 100

[Peer]
PublicKey = {remote_pub_m.group(1).strip()}
AllowedIPs = 0.0.0.0/0
Endpoint = {endpoint_m.group(1).strip()}
PersistentKeepalive = 25
"""
    wg_conf_path.write_text(ru_conf, encoding="utf-8")
    os.chmod(wg_conf_path, 0o600)

    subprocess.run(
        ["systemctl", "enable", "wg-quick@wg0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["systemctl", "start", "wg-quick@wg0"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def setup_remote_tunnel_sync(
    remote_ip: str,
    remote_pass: str,
    on_progress: Optional[Callable[[int, str], None]] = None,
) -> Tuple[bool, str]:
    if not paramiko:
        return False, "paramiko not installed"
    try:
        ipaddress.ip_address(remote_ip)
    except ValueError:
        return False, "Invalid remote IP address"

    def _run_ssh(ssh_client: Any, cmd: str) -> str:
        _, stdout, _ = ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        return stdout.read().decode("utf-8", errors="ignore").strip()

    try:
        if on_progress:
            on_progress(15, "Подготовка SSH-ключа...")

        if not os.path.exists("/root/.ssh/id_ed25519"):
            os.makedirs("/root/.ssh", exist_ok=True)
            subprocess.run(
                [
                    "ssh-keygen",
                    "-t",
                    "ed25519",
                    "-f",
                    "/root/.ssh/id_ed25519",
                    "-N",
                    "",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
            )

        pub_key = Path("/root/.ssh/id_ed25519.pub").read_text(encoding="utf-8").strip()

        if on_progress:
            on_progress(35, f"Подключение к {remote_ip}...")

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(remote_ip, username="root", password=remote_pass, timeout=15)

        try:
            if on_progress:
                on_progress(55, "Установка WireGuard на удалённом сервере...")

            _run_ssh(
                client,
                "mkdir -p ~/.ssh && chmod 700 ~/.ssh && touch ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys",
            )
            sftp = client.open_sftp()
            try:
                with sftp.open("/root/.ssh/authorized_keys", "a") as f:
                    f.write(pub_key + "\n")
            finally:
                sftp.close()

            _run_ssh(
                client,
                "sysctl -w net.ipv4.ip_forward=1 && sed -i '/net.ipv4.ip_forward/d' /etc/sysctl.conf && echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf",
            )
            _run_ssh(
                client,
                "apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y wireguard iptables",
            )

            ext_iface = _run_ssh(
                client,
                "ip route get 8.8.8.8 | awk '{for(i=1;i<=NF;i++) if($i==\"dev\") print $(i+1); exit}'",
            )
            if not ext_iface:
                ext_iface = "eth0"

            remote_priv = _run_ssh(client, "wg genkey")
            remote_pub = _run_ssh(client, f"echo '{remote_priv}' | wg pubkey")

            ru_priv = subprocess.check_output(["wg", "genkey"]).decode().strip()
            ru_pub = (
                subprocess.check_output(["wg", "pubkey"], input=ru_priv.encode())
                .decode()
                .strip()
            )

            subnet_cidr = get_ovpn_subnet_cidr()
            remote_conf = f"""[Interface]
Address = 10.200.0.2/30
PrivateKey = {remote_priv}
ListenPort = 51820
MTU = 1360

PostUp = iptables -I INPUT 1 -i wg0 -s 10.200.0.0/30 -j ACCEPT
PostUp = iptables -I FORWARD 1 -i wg0 -s {subnet_cidr} -o {ext_iface} -j ACCEPT
PostUp = iptables -I FORWARD 1 -i {ext_iface} -o wg0 -d {subnet_cidr} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
PostUp = iptables -t nat -I POSTROUTING 1 -s {subnet_cidr} -o {ext_iface} -j MASQUERADE
PostUp = iptables -t mangle -A FORWARD -p tcp -m tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1320

PostDown = iptables -D INPUT -i wg0 -s 10.200.0.0/30 -j ACCEPT
PostDown = iptables -D FORWARD -i wg0 -s {subnet_cidr} -o {ext_iface} -j ACCEPT
PostDown = iptables -D FORWARD -i {ext_iface} -o wg0 -d {subnet_cidr} -m conntrack --ctstate ESTABLISHED,RELATED -j ACCEPT
PostDown = iptables -t nat -D POSTROUTING -s {subnet_cidr} -o {ext_iface} -j MASQUERADE
PostDown = iptables -t mangle -D FORWARD -p tcp -m tcp --tcp-flags SYN,RST SYN -j TCPMSS --set-mss 1320

[Peer]
PublicKey = {ru_pub}
AllowedIPs = {subnet_cidr}, 10.200.0.1/32
"""
            b64_conf = base64.b64encode(remote_conf.encode()).decode()
            _run_ssh(
                client,
                f"mkdir -p /etc/wireguard && echo '{b64_conf}' | base64 -d > /etc/wireguard/wg0.conf",
            )
            _run_ssh(
                client,
                "chmod 600 /etc/wireguard/wg0.conf && systemctl enable wg-quick@wg0 && systemctl restart wg-quick@wg0",
            )
        finally:
            client.close()

        if on_progress:
            on_progress(80, "Запуск локального интерфейса wg0...")

        os.makedirs("/etc/wireguard", exist_ok=True)
        ru_conf = f"""[Interface]
Address = 10.200.0.1/30
PrivateKey = {ru_priv}
MTU = 1360
Table = off

[Peer]
PublicKey = {remote_pub}
AllowedIPs = 0.0.0.0/0
Endpoint = {remote_ip}:51820
PersistentKeepalive = 25
"""
        Path("/etc/wireguard/wg0.conf").write_text(ru_conf, encoding="utf-8")
        os.chmod("/etc/wireguard/wg0.conf", 0o600)

        subprocess.run(
            ["systemctl", "stop", "wg-quick@wg0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        subprocess.run(
            ["ip", "link", "del", "dev", "wg0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        mode = get_setting("routing_mode") or "split"
        set_setting("routing_mode", mode)
        apply_routing_mode_sync(mode)

        if on_progress:
            on_progress(100, "Туннель развёрнут")
        return True, "OK"
    except Exception as e:
        return False, str(e)


def ensure_system_configs() -> None:
    parse_existing_server_conf_into_db()
    apply_torrent_block_sync(get_setting("torrent_block", "0") == "1")

    if get_setting("adblock_enabled", "0") == "1":
        try:
            apply_adblock_state_sync(True)
        except Exception:
            pass

    if not SERVER_CONF_PATH.exists():
        return
    try:
        content = SERVER_CONF_PATH.read_text(encoding="utf-8", errors="ignore")
        if "client-config-dir" not in content:
            with SERVER_CONF_PATH.open("a", encoding="utf-8") as f:
                f.write(f"\nclient-config-dir {CCD_DIR}\n")
        if not re.search(r"^\s*management\s+", content, re.MULTILINE):
            with SERVER_CONF_PATH.open("a", encoding="utf-8") as f:
                f.write("\nmanagement 127.0.0.1 7505\n")
            subprocess.run(
                ["systemctl", "reload-or-restart", "openvpn-server@server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass