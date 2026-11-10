<div align="center">

# 🛡️ OpenVPN Web UI Control Center
**Современная, безопасная и легковесная веб-панель управления OpenVPN**

[![GitHub Stars](https://img.shields.io/github/stars/fsystem88/openvpn-webui?style=flat-square&logo=github)](https://github.com/fsystem88/openvpn-webui/stargazers)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg?style=flat-square)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688?style=flat-square&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)

[**🇷🇺 Читать на русском**](#-русский) • [**🇬🇧 Read in English**](#-english)

---

</div>

<a id="ru"></a>
# 🇷🇺 Русский

<div align="center">

| 📌 [Возможности](#ru-features) | 🚀 [Установка](#ru-install) | 🛠️ [Управление](#ru-management) | 🔒 [Безопасность](#ru-security) | 📄 [Лицензия](#ru-license) |
| :---: | :---: | :---: | :---: | :---: |

</div>

**OpenVPN Web UI** — это готовое open-source решение для управления сервером OpenVPN с веб-интерфейсом. Панель не требует тяжелых баз данных, работает без фоновых снифферов и перехвата пользовательского трафика, легковесна и развертывается одной командой.

---

<a id="ru-features"></a>
### ✨ Возможности

* **👥 Управление клиентами (Easy-RSA PKI):**
  * Создание, удаление и отзыв сертификатов.
  * Заморозка доступа (пауза) одним кликом без удаления ключей.
  * Ограничение срока действия профиля по дням (TTL).
  * Скачивание готового `.ovpn`, генерация QR-кода и защищенной ссылки для быстрой настройки на iOS, Android, Windows и macOS.

* **📈 Мониторинг в реальном времени:**
  * Живой график скорости (Download / Upload) напрямую из оперативной памяти сокета OpenVPN.
  * Статус подключений (Онлайн / Офлайн / Пауза) и текущий выделенный IP.
  * Системные метрики сервера: CPU, RAM, Disk, пинг до шлюза WireGuard.

* **🔀 Сплит-туннель (WireGuard + ipset):**
  * Избирательная маршрутизация трафика клиентов через удаленную точку выхода (Dual-VPN).
  * Маршрутизация по географическим спискам подсетей (CIDR) или отдельным ссылкам/доменам.
  * Автоматический резолвинг IP доменов с проверкой конфликтов подсетей.

* **🛡️ Встроенный DNS AdBlock (dnsmasq):**
  * Блокировка рекламы, трекеров и вредоносных хостов на уровне сервера.
  * Импорт внешних списков (AdLists) по ссылкам и добавление собственных доменов в черный/белый списки.

* **🚫 Блокировка BitTorrent:**
  * Фильтрация торрент-протоколов на уровне iptables для предотвращения жалоб дата-центров.

* **📦 Резервное копирование и редактор конфигурации:**
  * Полный бэкап и восстановление всех настроек, ключей и баз данных в архив `.tar.gz`.
  * Встроенный редактор `server.conf` с возможностью быстрого применения и перезапуска службы.
  * Переключение светлой и темной темы интерфейса.

---

<a id="ru-install"></a>
### 🚀 Быстрая установка

#### Требования к системе:
* **ОС:** Ubuntu 22.04 / 24.04 LTS или Debian 11 / 12
* **Права:** root (sudo)
* Подходит как для чистого сервера, так и для сервера с уже установленным OpenVPN.

#### Установка одной командой:

```bash
git clone https://github.com/fsystem88/openvpn-webui.git /opt/openvpn-webui
cd /opt/openvpn-webui
chmod +x install.sh
sudo ./install.sh
```

В процессе работы установщик:
1. Автоматически определит параметры сети (NAT или публичный IP).
2. Настроит OpenVPN сервер (или подключит существующий).
3. Создаст виртуальное окружение Python, сгенерирует криптографические ключи и хэш пароля `scrypt`.
4. Зарегистрирует и запустит службу `openvpn-webui.service`.

---

<a id="ru-management"></a>
### 🛠️ Меню управления

Для изменения настроек, сброса пароля или деинсталляции просто запустите скрипт повторно:

```bash
cd /opt/openvpn-webui
sudo ./install.sh
```

Интерактивное меню предоставит доступ к следующим опциям:
```text
1) Установить / Обновить Web UI
2) Сбросить пароль администратора Web UI
3) Создать резервную копию (Backup)
4) Удалить только Web-панель (оставить OpenVPN)
5) Полное удаление (OpenVPN + Web-панель)
6) Выход
```

> **Безопасность:** перед выполнением удаления скрипт автоматически создает полный архив в каталоге `/root/openvpn_backup_*.tar.gz`.

#### Управление через systemd:

```bash
# Статус службы
systemctl status openvpn-webui

# Перезапуск панели
systemctl restart openvpn-webui

# Просмотр логов
journalctl -u openvpn-webui -f
```

---

<a id="ru-security"></a>
### 🔒 Безопасность

* **Пароли:** Хранятся исключительно в виде `scrypt`-хэша с уникальной солью.
* **Сессии:** Подписываются HMAC-SHA256 с динамически генерируемыми 256-битными ключами.
* **HTTPS / Reverse Proxy:** Для работы в продакшене рекомендуется проксировать панель через Nginx или Caddy с SSL-сертификатом (Let's Encrypt):

```nginx
server {
    server_name vpn.example.com;
    listen 443 ssl http2;
    # Настройки SSL сертификатов...

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

<a id="ru-license"></a>
### 📄 Лицензия

Проект распространяется под лицензией [MIT](LICENSE).

---
---

<a id="en"></a>
# 🇬🇧 English

<div align="center">

| 📌 [Features](#en-features) | 🚀 [Install](#en-install) | 🛠️ [Management](#en-management) | 🔒 [Security](#en-security) | 📄 [License](#en-license) |
| :---: | :---: | :---: | :---: | :---: |

</div>

**OpenVPN Web UI** is a complete, lightweight, and secure web control dashboard for managing OpenVPN servers. Built without heavy databases or invasive packet-sniffing tools, it operates purely via OpenVPN's memory management socket and deploys with a single command.

---

<a id="en-features"></a>
### ✨ Features

* **👥 Client Management (Easy-RSA PKI):**
  * Issue, delete, and revoke client certificates.
  * Pause/resume client access instantly without invalidating certificates.
  * Set expiration dates / TTL (Time to Live) in days.
  * Download `.ovpn` profiles, scan QR codes, or copy secure import links for iOS, Android, Windows, and macOS.

* **📈 Real-time Telemetry & Speed:**
  * Live bandwidth charts (Download / Upload) polled in-memory via OpenVPN management socket.
  * Status badges (Online / Offline / Paused) with active virtual IPs.
  * Server resource monitoring: CPU, RAM, Disk, and WireGuard exit-node ping.

* **🔀 Split Tunneling (WireGuard + ipset):**
  * Route selective traffic through a secondary remote exit server (Dual-VPN).
  * Flexible routing modes: Geo-CIDR lists, custom subnets, or domain-based bypass.
  * Built-in domain DNS resolver with subnet conflict detection.

* **🛡️ Integrated DNS AdBlock (dnsmasq):**
  * Network-wide ad, tracking, and malware blocking directly on the VPN server.
  * Support for remote blocklists (AdLists) and custom blacklist/whitelist domain rules.

* **🚫 BitTorrent Filtering:**
  * Kernel-level iptables packet inspection to drop P2P/BitTorrent traffic and prevent hosting abuse.

* **📦 Backup & Server Configuration:**
  * One-click full backup and restore (`.tar.gz`) containing OpenVPN PKI, WireGuard, DNS, and database state.
  * Live in-browser `server.conf` editor with service restart trigger.
  * Dark and Light theme support.

---

<a id="en-install"></a>
### 🚀 Quick Install

#### Prerequisites:
* **OS:** Ubuntu 22.04 / 24.04 LTS or Debian 11 / 12
* **Permissions:** root (sudo)
* Works on fresh systems as well as existing OpenVPN servers.

#### Single-command installation:

```bash
git clone https://github.com/fsystem88/openvpn-webui.git /opt/openvpn-webui
cd /opt/openvpn-webui
chmod +x install.sh
sudo ./install.sh
```

The script will:
1. Detect network configuration (public IP vs. NAT).
2. Set up OpenVPN (or connect to an existing server).
3. Initialize Python venv, generate secure secrets, and compute `scrypt` password hashes.
4. Enable and start the `openvpn-webui.service`.

---

<a id="en-management"></a>
### 🛠️ Management Menu

To reconfigure, reset credentials, or safely uninstall the software, re-run the installation script:

```bash
cd /opt/openvpn-webui
sudo ./install.sh
```

An interactive menu will appear:
```text
1) Install / Update Web UI
2) Reset Web UI Admin Password
3) Create Backup Archive
4) Uninstall Web UI only (keep OpenVPN running)
5) Complete Uninstall (remove OpenVPN and Web UI)
6) Exit
```

> **Safety Notice:** An automatic archive is always saved to `/root/openvpn_backup_*.tar.gz` prior to any uninstall action.

#### Systemd Service Management:

```bash
# Check status
systemctl status openvpn-webui

# Restart UI service
systemctl restart openvpn-webui

# View live logs
journalctl -u openvpn-webui -f
```

---

<a id="en-security"></a>
### 🔒 Security Recommendations

* **Password Hashing:** Passwords are saved strictly as salted `scrypt` hashes.
* **Session Integrity:** Cookie signatures utilize HMAC-SHA256 with cryptographically generated 256-bit secrets.
* **HTTPS Reverse Proxy:** For production deployments, running behind Nginx or Caddy with automated SSL (Let's Encrypt) is highly recommended:

```nginx
server {
    server_name vpn.example.com;
    listen 443 ssl http2;
    # SSL certificate configuration...

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

<a id="en-license"></a>
### 📄 License

Distributed under the [MIT](LICENSE) License.
