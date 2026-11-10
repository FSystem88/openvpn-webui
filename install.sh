#!/bin/bash
set -e

# ============================================================
# Проверка прав суперпользователя и рабочей директории
# ============================================================
if [[ "$EUID" -ne 0 ]]; then
    echo "[-] Ошибка: Этот скрипт должен быть запущен с правами root (sudo)."
    exit 1
fi

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SERVER_CONF="/etc/openvpn/server/server.conf"
DB_PATH="/etc/openvpn/panel.db"

# ============================================================
# Вспомогательные функции
# ============================================================

# Создание безопасного scrypt-хэша с солью
hash_password() {
    local raw_pass="$1"
    ADMIN_RAW_PASS="$raw_pass" python3 -c '
import os, hashlib, secrets
pwd = os.environ.get("ADMIN_RAW_PASS", "")
salt = secrets.token_bytes(16)
derived = hashlib.scrypt(pwd.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
print(f"scrypt${salt.hex()}${derived.hex()}")
'
}

# Принудительная запись логина/хэша в SQLite базу
sync_db_credentials() {
    local login="$1"
    local hash="$2"
    if [[ -f "$DB_PATH" ]]; then
        ADMIN_LOGIN_ARG="$login" ADMIN_HASH_ARG="$hash" python3 -c '
import os, sqlite3
conn = sqlite3.connect("/etc/openvpn/panel.db")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
cur.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("admin_login", os.environ["ADMIN_LOGIN_ARG"]))
cur.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", ("admin_password_hash", os.environ["ADMIN_HASH_ARG"]))
conn.commit()
conn.close()
'
    fi
}

# Создание обязательного резервного архива
create_backup() {
    local date_str
    date_str=$(date +%Y-%m-%d_%H-%M-%S)
    local backup_file="/root/openvpn_backup_${date_str}.tar.gz"
    echo ""
    echo "[*] Создание резервной копии перед операцией..."
    
    local temp_backup_dir
    temp_backup_dir=$(mktemp -d)

    [[ -d "/etc/openvpn" ]] && cp -r /etc/openvpn "$temp_backup_dir/openvpn"
    [[ -d "/etc/wireguard" ]] && cp -r /etc/wireguard "$temp_backup_dir/wireguard"
    [[ -d "/etc/dnsmasq.d" ]] && cp -r /etc/dnsmasq.d "$temp_backup_dir/dnsmasq.d"
    [[ -f "$REPO_DIR/.env" ]] && cp "$REPO_DIR/.env" "$temp_backup_dir/.env"
    [[ -f "$DB_PATH" ]] && cp "$DB_PATH" "$temp_backup_dir/panel.db"

    tar -czf "$backup_file" -C "$temp_backup_dir" .
    rm -rf "$temp_backup_dir"

    chmod 600 "$backup_file"
    echo "[+] Резервная копия успешно сохранена:"
    echo "    -> $backup_file"
    echo ""
}

# ============================================================
# Процедуры удаления
# ============================================================

uninstall_panel_only() {
    create_backup

    echo "[*] Остановка и удаление службы веб-панели..."
    systemctl stop openvpn-webui.service 2>/dev/null || true
    systemctl disable openvpn-webui.service 2>/dev/null || true
    rm -f /etc/systemd/system/openvpn-webui.service
    systemctl daemon-reload

    echo "[*] Очистка окружения веб-панели..."
    rm -rf "$REPO_DIR/venv" "$REPO_DIR/.env" "$DB_PATH"

    # Удаление правил iptables блокировки торрентов и редиректа DNS
    iptables -t nat -D PREROUTING -i tun0 -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || true
    iptables -t nat -D PREROUTING -i tun0 -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || true

    echo "=================================================="
    echo "  Веб-панель успешно удалена!                    "
    echo "  OpenVPN сервер продолжает работать штатно.     "
    echo "=================================================="
}

uninstall_full() {
    create_backup

    echo "[*] Остановка всех служб..."
    systemctl stop openvpn-webui.service 2>/dev/null || true
    systemctl disable openvpn-webui.service 2>/dev/null || true
    rm -f /etc/systemd/system/openvpn-webui.service

    systemctl stop openvpn-server@server 2>/dev/null || true
    systemctl disable openvpn-server@server 2>/dev/null || true

    systemctl stop wg-quick@wg0 2>/dev/null || true
    systemctl disable wg-quick@wg0 2>/dev/null || true

    systemctl daemon-reload

    echo "[*] Удаление конфигураций и баз данных..."
    rm -rf /etc/openvpn
    rm -rf /etc/wireguard
    rm -f /etc/dnsmasq.d/00-ovpn-base.conf
    rm -f /etc/dnsmasq.d/99-ovpn-adblock.conf
    rm -rf /var/run/openvpn-server
    rm -rf "$REPO_DIR/venv" "$REPO_DIR/.env" "$DB_PATH"

    echo "[*] Очистка правил iptables..."
    iptables -t nat -D PREROUTING -i tun0 -p udp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || true
    iptables -t nat -D PREROUTING -i tun0 -p tcp --dport 53 -j REDIRECT --to-ports 53 2>/dev/null || true

    echo "=================================================="
    echo "  Полное удаление завершено!                      "
    echo "  OpenVPN, WireGuard-сплит и веб-панель удалены. "
    echo "=================================================="
}

# ============================================================
# Быстрый сброс пароля администратора
# ============================================================

reset_password_menu() {
    echo ""
    echo "--- Сброс учетных данных администратора ---"
    read -rp "Новый логин [admin]: " NEW_LOGIN
    NEW_LOGIN=${NEW_LOGIN:-admin}

    read -rp "Новый пароль [Enter для автогенерации]: " NEW_PASS
    if [[ -z "$NEW_PASS" ]]; then
        NEW_PASS=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 12)
    fi

    local new_hash
    new_hash=$(hash_password "$NEW_PASS")

    # Обновление в .env
    if [[ -f "$REPO_DIR/.env" ]]; then
        sed -i "s|^ADMIN_LOGIN=.*|ADMIN_LOGIN=$NEW_LOGIN|" "$REPO_DIR/.env"
        sed -i "s|^ADMIN_PASSWORD_HASH=.*|ADMIN_PASSWORD_HASH=$new_hash|" "$REPO_DIR/.env"
    fi

    # Обновление напрямую в SQLite
    sync_db_credentials "$NEW_LOGIN" "$new_hash"

    systemctl restart openvpn-webui.service 2>/dev/null || true

    echo ""
    echo "[+] Учетные данные успешно обновлены!"
    echo "    Логин:  $NEW_LOGIN"
    echo "    Пароль: $NEW_PASS"
    exit 0
}

# ============================================================
# ГЛАВНОЕ МЕНЮ (если система уже установлена)
# ============================================================

echo "=================================================="
echo "    Управление OpenVPN & Web UI                  "
echo "=================================================="

if [[ -f "$SERVER_CONF" || -f "/etc/systemd/system/openvpn-webui.service" ]]; then
    echo "Обнаружены установленные компоненты."
    echo "1) Установить / Обновить Web UI"
    echo "2) Сбросить пароль администратора Web UI"
    echo "3) Создать резервную копию (Backup)"
    echo "4) Удалить только Web-панель (оставить OpenVPN)"
    echo "5) Полное удаление (OpenVPN + Web-панель)"
    echo "6) Выход"
    read -rp "Выберите действие [1-6]: " MENU_CHOICE

    case "$MENU_CHOICE" in
        2) reset_password_menu ;;
        3) create_backup; exit 0 ;;
        4) uninstall_panel_only; exit 0 ;;
        5) uninstall_full; exit 0 ;;
        6) exit 0 ;;
        *) echo "[*] Переход к процессу установки/обновления..." ;;
    esac
fi

# ============================================================
# ПРОЦЕСС УСТАНОВКИ
# ============================================================

echo "[*] Обновление пакетов и установка системных зависимостей..."
apt-get update
DEBIAN_FRONTEND=noninteractive apt-get install -y \
    python3 python3-pip python3-venv iptables ipset curl wget tar dnsmasq openssl

SERVER_IP=$(curl -s4 https://api.ipify.org || curl -s4 https://ifconfig.me || ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | head -n1)

INSTALL_OVPN=true
if [[ -f "$SERVER_CONF" ]]; then
    CURRENT_PORT=$(grep -E '^\s*port\s+' "$SERVER_CONF" | awk '{print $2}' || echo "1984")
    CURRENT_PROTO=$(grep -E '^\s*proto\s+' "$SERVER_CONF" | awk '{print $2}' || echo "udp")
    CURRENT_SUBNET=$(grep -E '^\s*server\s+' "$SERVER_CONF" | awk '{print $2, $3}' || echo "10.8.0.0 255.255.255.0")

    echo "[!] Обнаружен существующий OpenVPN сервер ($CURRENT_PROTO:$CURRENT_PORT, $CURRENT_SUBNET)."
    INSTALL_OVPN=false
    OVPN_PORT="$CURRENT_PORT"
    OVPN_PROTO="$CURRENT_PROTO"
else
    echo "[?] OpenVPN сервер не обнаружен."
    read -rp "Установить OpenVPN сервер скриптом Nyr? [Y/n]: " PROCEED_INSTALL
    PROCEED_INSTALL=${PROCEED_INSTALL:-Y}
    if [[ ! "$PROCEED_INSTALL" =~ ^[Yy]$ ]]; then
        echo "[-] Отмена."
        exit 0
    fi
fi

echo ""
echo "Выберите адрес для клиентских конфигураций:"
echo "1) Внешний IP ($SERVER_IP)"
echo "2) Домен (например, vpn.example.com)"
read -rp "Выбор [1]: " HOST_TYPE_CHOICE
HOST_TYPE_CHOICE=${HOST_TYPE_CHOICE:-1}

if [[ "$HOST_TYPE_CHOICE" == "2" ]]; then
    while true; do
        read -rp "Введите домен: " OVPN_DOMAIN
        OVPN_DOMAIN=$(echo "$OVPN_DOMAIN" | tr -d '[:space:]')
        [[ -z "$OVPN_DOMAIN" ]] && continue
        RESOLVED_IP=$(getent ahosts "$OVPN_DOMAIN" | awk '{print $1}' | head -n1 || true)
        if [[ -z "$RESOLVED_IP" ]]; then
            echo "[-] Домен не резолвится!"
            continue
        fi
        break
    done
else
    OVPN_DOMAIN="$SERVER_IP"
fi

if [[ "$INSTALL_OVPN" == "true" ]]; then
    echo ""
    echo "--- Параметры OpenVPN ---"
    read -rp "Протокол: 1) UDP  2) TCP [1]: " PROTO_INPUT
    PROTO_INPUT=${PROTO_INPUT:-1}
    OVPN_PROTO="udp"
    [[ "$PROTO_INPUT" == "2" ]] && OVPN_PROTO="tcp"

    read -rp "Порт OpenVPN [1984]: " PORT_INPUT
    OVPN_PORT=${PORT_INPUT:-1984}

    read -rp "DNS: 1) Системный  2) Google  3) Cloudflare [3]: " DNS_INPUT
    DNS_INPUT=${DNS_INPUT:-3}
    case "$DNS_INPUT" in
        1) NYR_DNS="1" ;;
        2) NYR_DNS="2" ;;
        *) NYR_DNS="3" ;;
    esac

    read -rp "Имя первого клиента [client]: " FIRST_CLIENT
    FIRST_CLIENT=${FIRST_CLIENT:-client}
fi

echo ""
echo "--- Параметры Web UI ---"
read -rp "Порт панели [8080]: " PANEL_PORT
PANEL_PORT=${PANEL_PORT:-8080}

read -rp "Логин администратора [admin]: " ADMIN_LOGIN
ADMIN_LOGIN=${ADMIN_LOGIN:-admin}

read -rp "Пароль администратора [Enter для автогенерации]: " ADMIN_PASSWORD
if [[ -z "$ADMIN_PASSWORD" ]]; then
    ADMIN_PASSWORD=$(openssl rand -base64 12 | tr -dc 'a-zA-Z0-9' | head -c 12)
fi

ADMIN_PASSWORD_HASH=$(hash_password "$ADMIN_PASSWORD")
SECRET_KEY=$(openssl rand -hex 32)
SESSION_SECRET=$(openssl rand -hex 32)

# Установка OpenVPN через Nyr с корректным распознаванием NAT
if [[ "$INSTALL_OVPN" == "true" ]]; then
    echo "[*] Запуск установки OpenVPN..."
    curl -sSL https://raw.githubusercontent.com/Nyr/openvpn-install/master/openvpn-install.sh -o /tmp/openvpn-install.sh
    chmod +x /tmp/openvpn-install.sh

    IS_NAT=$(ip -4 addr show scope global | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -E '^(10\.|172\.(1[6-9]|2[0-9]|3[0-1])\.|192\.168\.)' | head -n1 || true)

    if [[ -n "$IS_NAT" ]]; then
        printf "\n%s\n%s\n%s\n%s\n%s\n\n" \
            "$OVPN_DOMAIN" \
            "$PROTO_INPUT" \
            "$OVPN_PORT" \
            "$NYR_DNS" \
            "$FIRST_CLIENT" | bash /tmp/openvpn-install.sh
    else
        printf "\n%s\n%s\n%s\n%s\n\n" \
            "$PROTO_INPUT" \
            "$OVPN_PORT" \
            "$NYR_DNS" \
            "$FIRST_CLIENT" | bash /tmp/openvpn-install.sh
    fi
    rm -f /tmp/openvpn-install.sh
fi

# Конфигурация Management сокета и директорий OpenVPN
echo "[*] Настройка параметров Management и CCD..."
mkdir -p /etc/openvpn/server/ccd
mkdir -p /var/run/openvpn-server

if ! grep -qE '^\s*management\s+' "$SERVER_CONF"; then
    echo -e "\nmanagement 127.0.0.1 7505" >> "$SERVER_CONF"
fi
if ! grep -qE '^\s*client-config-dir\s+' "$SERVER_CONF"; then
    echo -e "\nclient-config-dir /etc/openvpn/server/ccd" >> "$SERVER_CONF"
fi
if ! grep -qE '^\s*status\s+' "$SERVER_CONF"; then
    echo -e "\nstatus /var/run/openvpn-server/status-server.log 1\nstatus-version 2" >> "$SERVER_CONF"
fi

systemctl daemon-reload
systemctl enable --now openvpn-server@server
systemctl restart openvpn-server@server

# Настройка виртуального окружения Python
echo "[*] Настройка окружения Python..."
cd "$REPO_DIR"
[[ ! -d "venv" ]] && python3 -m venv venv
./venv/bin/pip install --upgrade pip
./venv/bin/pip install -r requirements.txt

# Запись .env
cat <<EOF > "$REPO_DIR/.env"
OVPN_DOMAIN=$OVPN_DOMAIN
OVPN_PORT=$OVPN_PORT
OVPN_PROTO=$OVPN_PROTO
PANEL_PORT=$PANEL_PORT
OVPN_TUN_IFACE=tun0

ADMIN_LOGIN=$ADMIN_LOGIN
ADMIN_PASSWORD_HASH=$ADMIN_PASSWORD_HASH
SECRET_KEY=$SECRET_KEY
SESSION_SECRET=$SESSION_SECRET

OVPN_MGMT_HOST=127.0.0.1
OVPN_MGMT_PORT=7505
DB_PATH=/etc/openvpn/panel.db
ADBLOCK_DNS_IP=10.8.0.1
EOF
chmod 600 "$REPO_DIR/.env"

# Принудительная синхронизация с базой SQLite (если она уже была создана ранее)
sync_db_credentials "$ADMIN_LOGIN" "$ADMIN_PASSWORD_HASH"

# Открытие порта в UFW
if command -v ufw >/dev/null 2>&1 && ufw status | grep -q "Status: active"; then
    ufw allow "$PANEL_PORT"/tcp >/dev/null 2>&1 || true
fi

# Настройка службы systemd
echo "[*] Регистрация службы openvpn-webui..."
cat <<EOF > /etc/systemd/system/openvpn-webui.service
[Unit]
Description=OpenVPN Web UI Control Center
After=network.target openvpn-server@server.service
Wants=openvpn-server@server.service

[Service]
Type=simple
User=root
WorkingDirectory=$REPO_DIR
EnvironmentFile=$REPO_DIR/.env
ExecStart=$REPO_DIR/venv/bin/python3 $REPO_DIR/panel.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now openvpn-webui.service
systemctl restart openvpn-webui.service

echo ""
echo "=================================================="
echo "          УСТАНОВКА УСПЕШНО ЗАВЕРШЕНА!            "
echo "=================================================="
echo "Панель управления доступна по адресу:"
echo "  URL:      http://$OVPN_DOMAIN:$PANEL_PORT/"
echo "  Логин:    $ADMIN_LOGIN"
echo "  Пароль:   $ADMIN_PASSWORD"
echo "=================================================="