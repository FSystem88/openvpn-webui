<div align="center">

# 🛡️ OpenVPN Web UI Control Center
**Современная, модульная и легковесная веб-панель управления OpenVPN**

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

| 📌 [Возможности](#ru-features) | 🧩 [Архитектура](#ru-arch) | 🚀 [Установка](#ru-install) | 🛠️ [Управление](#ru-management) | 🔒 [Безопасность](#ru-security) | 📄 [Лицензия](#ru-license) |
| :---: | :---: | :---: | :---: | :---: | :---: |

</div>

**OpenVPN Web UI** — это готовое open-source решение для управления сервером OpenVPN с современным веб-интерфейсом. Панель работает на SQLite, не требует тяжёлых СУБД, оптимизирована под слабые VPS (включая фоновый прогресс-бар для тяжёлых операций) и разворачивается одной командой.

---

<a id="ru-features"></a>
### ✨ Возможности

* **👥 Управление клиентами (Easy-RSA PKI):**
  * Создание, отзыв, восстановление отозванных и полное удаление сертификатов.
  * Заморозка доступа (пауза) одним кликом через `ccd` без перевыпуска ключей.
  * Лимиты трафика (в ГБ) и срок действия профиля (TTL в днях) с автоматической паузой при достижении лимита.
  * Заметки к клиентам, даты последнего подключения и отключения.
  * Скачивание `.ovpn`, генерация QR-кода и защищённой ссылки (`/d/{token}`) для быстрого импорта на iOS, Android, Windows и macOS.

* **⚡ Двустороннее ограничение скорости (`tc` HTB + `ifb0`):**
  * Шейпинг в обе стороны (Download и Upload) с режимами: без ограничений, для всех клиентов, для выбранных или индивидуально для каждого клиента.
  * Быстрые пресеты скорости (`1`, `5`, `10`, `25`, `50 Мбит/с`) и автоматическое восстановление правил при пересоздании `tun0`.

* **📈 Мониторинг в реальном времени (1s):**
  * Ежесекундное обновление скорости (`↓ / ↑`), статуса и счётчика онлайна прямо в карточках клиентов и на живом графике через management-сокет OpenVPN.
  * Системные метрики сервера: CPU, RAM, Disk и пинг до шлюза WireGuard.

* **🌐 Аналитика, журнал сайтов и инфографика (отключаемые модули):**
  * BPF-сниффер доменов (SNI / DNS / HTTP) с общим журналом, историей по каждому клиенту, Топ-10 и списком исключений (`*.domain.com`).
  * История реальных IP-адресов подключений клиентов.
  * Инфографика: Топ-10 клиентов по трафику, распределение статусов и Топ-10 посещаемых доменов.
  * Любой модуль (сниффер, статистика трафика, история IP, инфографика, панель ресурсов) включается и отключается на лету в настройках.

* **🔀 Сплит-туннель (WireGuard + `ipset`):**
  * Избирательная маршрутизация трафика через удалённый сервер (Dual-VPN) с автонастройкой по SSH.
  * Режимы маршрутизации: CIDR напрямую / в WG, весь трафик через WG, свои подсети и точечные правила по URL с проверкой конфликтов.

* **🛡️ DNS AdBlock (`dnsmasq`) и фильтрация трафика:**
  * Серверная блокировка рекламы и трекеров: импорт внешних списков (AdLists) и собственные чёрный/белый списки доменов.
  * Блокировка QUIC (UDP/443) для точного SNI и безопасная фильтрация BitTorrent через `iptables`.

* **📦 Бэкап, конфигурация и UI:**
  * Полный бэкап и восстановление (`.tar.gz`): OpenVPN PKI, WireGuard, `dnsmasq`, БД SQLite и `.env`.
  * Прямой редактор `server.conf` с перезапуском службы, индикатор прогресса фоновых задач, светлая и тёмная темы, адаптация под мобильные устройства.

---

<a id="ru-arch"></a>
### 🧩 Структура проекта

```text
├── panel.py            # FastAPI приложение, роуты API, авторизация и сессии
├── database.py         # SQLite (WAL), миграции, кэш настроек и метаданные клиентов
├── openvpn_manager.py  # PKI/Easy-RSA, SpeedMonitor, BPF-сниффер, tc + ifb0 шейпинг
├── network_manager.py  # WireGuard + ipset, DNS AdBlock (dnsmasq), метрики и трекер задач
├── ui_templates.py     # Веб-интерфейс (HTML/CSS/JS), страница логина и публичный лендинг
├── install.sh          # Интерактивный установщик, обновление, сброс пароля и бэкап
└── requirements.txt    # Зависимости Python

```

---

### 🚀 Быстрая установка

#### Требования к системе:

* **ОС:** Ubuntu 22.04 / 24.04 LTS или Debian 11 / 12
* **Права:** root (`sudo`)
* Подходит как для чистого сервера, так и для сервера с уже установленным OpenVPN (существующие конфиги и сертификаты сохраняются).

#### Установка одной командой:

```bash
git clone https://github.com/fsystem88/openvpn-webui.git /opt/openvpn-webui
cd /opt/openvpn-webui
chmod +x install.sh
sudo ./install.sh

```

В процессе работы установщик:

1. Установит системные зависимости (`python3`, `iptables`, `ipset`, `iproute2`, `dnsmasq`).
2. Настроит OpenVPN сервер (или бережно подключит существующий).
3. Создаст виртуальное окружение Python, сгенерирует ключи сессий и хэш пароля `scrypt`.
4. Зарегистрирует и запустит службу `openvpn-webui.service`.

---

### 🛠️ Меню управления

Для обновления, сброса пароля, бэкапа или удаления запустите скрипт повторно:

```bash
cd /opt/openvpn-webui
sudo ./install.sh

```

```text
1) Установить / Обновить Web UI
2) Сбросить пароль администратора Web UI
3) Создать резервную копию (Backup)
4) Удалить только Web-панель (оставить OpenVPN)
5) Полное удаление (OpenVPN + Web-панель)
6) Выход

```

> **Безопасность:** перед обновлением или удалением скрипт автоматически создаёт резервный архив в `/root/openvpn_backup_*.tar.gz`.

#### Управление через systemd:

```bash
systemctl status openvpn-webui
systemctl restart openvpn-webui
journalctl -u openvpn-webui -f

```

---

### 🔒 Безопасность

* **Пароли:** хранятся в виде солёного `scrypt`-хэша.
* **Сессии:** подписываются HMAC-SHA256 с 256-битными ключами из `.env` (`chmod 600`).
* **HTTPS / Reverse Proxy:** в продакшене рекомендуется проксировать панель через Nginx или Caddy с SSL:

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

### 📄 Лицензия

Проект распространяется под лицензией [MIT](https://www.google.com/search?q=LICENSE).

---

---

# 🇬🇧 English

| 📌 [Features](https://www.google.com/search?q=%23en-features) | 🧩 [Architecture](https://www.google.com/search?q=%23en-arch) | 🚀 [Install](https://www.google.com/search?q=%23en-install) | 🛠️ [Management](https://www.google.com/search?q=%23en-management) | 🔒 [Security](https://www.google.com/search?q=%23en-security) | 📄 [License](https://www.google.com/search?q=%23en-license) |
| --- | --- | --- | --- | --- | --- |


**OpenVPN Web UI** is a modular, lightweight, and secure open-source web control dashboard for OpenVPN servers. Powered by SQLite and FastAPI, it is optimized for low-RAM VPS instances (including async background task progress tracking) and deploys with a single command.

---

### ✨ Features

* **👥 Client Management (Easy-RSA PKI):**
* Issue, revoke, restore (unrevoke), and permanently delete client certificates.
* Instant pause/resume via `ccd` without invalidating keys.
* Per-client traffic quotas (GB) and expiration TTL (days) with automatic pause on limit.
* Client notes, last connected and last disconnected timestamps.
* `.ovpn` download, QR code generation, and secure share links (`/d/{token}`) for iOS, Android, Windows, and macOS.


* **⚡ Bidirectional Speed Limiting (`tc` HTB + `ifb0`):**
* Download & Upload bandwidth shaping with modes: disabled, global, selected clients, or per-client.
* Quick speed presets (`1`, `5`, `10`, `25`, `50 Mbps`) and automatic `tc` rule recovery if `tun0` restarts.


* **📈 1-Second Real-Time Telemetry:**
* Per-second live speed (`↓ / ↑`), online status, and active session updates directly in client cards and live charts via the OpenVPN management socket.
* Server resource bar: CPU, RAM, Disk, and WireGuard gateway ping.


* **🌐 Domain Analytics & Infographics (Toggleable Modules):**
* Kernel BPF domain sniffer (SNI / DNS / HTTP) with global & per-client logs, Top-10 domains, and wildcard ignore list (`*.domain.com`).
* Real client IP connection history.
* Infographics: Top-10 clients by traffic, status breakdown, and Top-10 visited domains.
* Every module can be toggled on/off in real time from the settings tab.


* **🔀 Split Tunneling (WireGuard + `ipset`):**
* Dual-VPN selective routing via a remote exit node with automated SSH setup.
* Flexible modes: Geo-CIDR direct/WG, full tunnel, custom subnets, and per-URL IP resolution with conflict detection.


* **🛡️ DNS AdBlock (`dnsmasq`) & Traffic Filtering:**
* Network-wide ad/tracker blocking with remote AdLists and custom blacklist/whitelist rules.
* QUIC (UDP/443) blocking for accurate SNI and safe `iptables` BitTorrent filtering.


* **📦 Backup, Config & UI:**
* One-click full backup and restore (`.tar.gz`) covering OpenVPN PKI, WireGuard, `dnsmasq`, SQLite DB, and `.env`.
* In-browser `server.conf` editor, background task progress bar, Dark/Light themes, and responsive mobile layout.



---

### 🧩 Project Structure

```text
├── panel.py            # FastAPI app, API routes, authentication & sessions
├── database.py         # SQLite (WAL), migrations, settings cache & client metadata
├── openvpn_manager.py  # PKI/Easy-RSA, SpeedMonitor, BPF sniffer, tc + ifb0 shaping
├── network_manager.py  # WireGuard + ipset, DNS AdBlock (dnsmasq), stats & task tracker
├── ui_templates.py     # Web UI (HTML/CSS/JS), login page & public landing page
├── install.sh          # Interactive installer, updater, password reset & backup
└── requirements.txt    # Python dependencies

```

---

### 🚀 Quick Install

#### Prerequisites:

* **OS:** Ubuntu 22.04 / 24.04 LTS or Debian 11 / 12
* **Permissions:** root (`sudo`)
* Works on both fresh servers and existing OpenVPN installations (existing configs and certificates are preserved).

#### Single-command installation:

```bash
git clone https://github.com/fsystem88/openvpn-webui.git /opt/openvpn-webui
cd /opt/openvpn-webui
chmod +x install.sh
sudo ./install.sh

```

The installer will:

1. Install required system packages (`python3`, `iptables`, `ipset`, `iproute2`, `dnsmasq`).
2. Set up OpenVPN (or safely attach to an existing server).
3. Create a Python venv, generate session secrets, and store a salted `scrypt` admin password hash.
4. Enable and start `openvpn-webui.service`.

---

### 🛠️ Management Menu

Re-run the script anytime to update, reset credentials, create a backup, or uninstall:

```bash
cd /opt/openvpn-webui
sudo ./install.sh

```

```text
1) Install / Update Web UI
2) Reset Web UI Admin Password
3) Create Backup Archive
4) Uninstall Web UI only (keep OpenVPN running)
5) Complete Uninstall (remove OpenVPN and Web UI)
6) Exit

```

> **Safety Notice:** An automatic backup archive is always saved to `/root/openvpn_backup_*.tar.gz` before updates or uninstall actions.

#### Systemd Service Management:

```bash
systemctl status openvpn-webui
systemctl restart openvpn-webui
journalctl -u openvpn-webui -f

```

---

### 🔒 Security

* **Password Hashing:** Salted `scrypt` hashes.
* **Session Integrity:** HMAC-SHA256 signed cookies with 256-bit secrets stored in `.env` (`chmod 600`).
* **HTTPS Reverse Proxy:** Running behind Nginx or Caddy with Let's Encrypt SSL is recommended for production:

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

### 📄 License

Distributed under the [MIT](https://www.google.com/search?q=LICENSE) License.
