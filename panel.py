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
import sqlite3
import subprocess
import tarfile
import tempfile
import time
import urllib.request
from collections import deque
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse, Response
import uvicorn

try:
    import paramiko
except ImportError:
    paramiko = None

DOMAIN = os.getenv("OVPN_DOMAIN", "127.0.0.1")
OVPN_PORT = int(os.getenv("OVPN_PORT", "1984"))
PROTOCOL = os.getenv("OVPN_PROTO", "udp")
PANEL_PORT = int(os.getenv("PANEL_PORT", "8080"))
TUN_IFACE = os.getenv("OVPN_TUN_IFACE", "tun0")

SECRET_KEY = os.getenv("SECRET_KEY") or secrets.token_hex(32)
SESSION_SECRET = os.getenv("SESSION_SECRET") or secrets.token_hex(32)
SESSION_COOKIE = "openvpn_session"
SESSION_MAX_AGE = 86400

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

LOGIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>OpenVPN Panel — Login</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
			background: #090d16; color: #f1f5f9; min-height: 100vh; display: flex;
			justify-content: center; align-items: center; padding: 20px;
		}
		.background { position: fixed; inset: 0; overflow: hidden; pointer-events: none; }
		.blob {
			position: absolute; width: 600px; height: 600px; border-radius: 50%;
			background: radial-gradient(circle, rgba(59, 130, 246, 0.15), transparent 70%);
			top: -150px; left: 50%; transform: translateX(-50%);
		}
		.login-card {
			position: relative; width: 100%; max-width: 400px;
			background: rgba(17, 24, 39, 0.85); backdrop-filter: blur(16px);
			border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 20px;
			padding: 40px; box-shadow: 0 25px 60px rgba(0, 0, 0, 0.6);
		}
		.icon-box {
			width: 56px; height: 56px; margin: 0 auto 16px; border-radius: 14px;
			background: linear-gradient(135deg, #3b82f6, #6366f1);
			display: flex; align-items: center; justify-content: center; font-size: 26px;
			box-shadow: 0 10px 25px rgba(59, 130, 246, 0.35);
		}
		.title { text-align: center; font-size: 24px; font-weight: 700; margin-bottom: 24px; letter-spacing: -0.5px; }
		.field { margin-bottom: 18px; }
		.field label { display: block; font-size: 13px; font-weight: 500; color: #94a3b8; margin-bottom: 6px; }
		.field input {
			width: 100%; padding: 12px 14px; background: #0b1120;
			border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px;
			color: #f8fafc; font-size: 14px; outline: none; transition: all .2s;
		}
		.field input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.2); }
		button {
			width: 100%; padding: 13px; background: linear-gradient(135deg, #3b82f6, #2563eb);
			border: none; border-radius: 10px; color: #fff; font-size: 14px; font-weight: 600;
			cursor: pointer; transition: all .2s; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.3);
			margin-top: 8px;
		}
		button:hover { opacity: .95; transform: translateY(-1px); }
		.error-box {
			background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3);
			color: #f87171; padding: 10px 14px; border-radius: 8px; font-size: 13px; margin-bottom: 16px;
		}
	</style>
</head>
<body>
<div class="background"><div class="blob"></div></div>
<div class="login-card">
	<div class="icon-box">🛡️</div>
	<h1 class="title">OpenVPN Panel</h1>
	{{ERROR}}
	<form method="POST" action="/login" autocomplete="off">
		<div class="field">
			<label>Логин / Username</label>
			<input type="text" name="username" placeholder="admin" required autofocus>
		</div>
		<div class="field">
			<label>Пароль / Password</label>
			<input type="password" name="password" placeholder="••••••••" required>
		</div>
		<button type="submit">Войти / Sign In</button>
	</form>
</div>
</body>
</html>
"""

MAIN_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
	<title>OpenVPN Control Center</title>
	<link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220 0 100 100%22><text y=%22.9em%22 font-size=%2290%22>🛡️</text></svg>">
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
	<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
	<script src="https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js"></script>
	<style>
		:root {
			--bg-main: #080c14;
			--bg-card: #0f172a;
			--bg-card-hover: #141e33;
			--bg-input: #0a1120;
			--border-subtle: #1e293b;
			--border-active: #3b82f6;
			--text-main: #f1f5f9;
			--text-muted: #64748b;
			--text-dim: #94a3b8;
			--primary: #3b82f6;
			--primary-hover: #2563eb;
			--success: #10b981;
			--danger: #ef4444;
			--warning: #f59e0b;
			--radius-sm: 8px;
			--radius-md: 12px;
			--radius-lg: 16px;
			--radius-xl: 20px;
			--shadow-sm: 0 2px 8px rgba(0,0,0,0.3);
			--shadow-md: 0 4px 16px rgba(0,0,0,0.4);
			--shadow-lg: 0 12px 40px rgba(0,0,0,0.5);
		}

		[data-theme="light"] {
			--bg-main: #f8fafc;
			--bg-card: #ffffff;
			--bg-card-hover: #f1f5f9;
			--bg-input: #f1f5f9;
			--border-subtle: #e2e8f0;
			--border-active: #2563eb;
			--text-main: #0f172a;
			--text-muted: #64748b;
			--text-dim: #334155;
			--shadow-sm: 0 2px 8px rgba(0,0,0,0.05);
			--shadow-md: 0 4px 16px rgba(0,0,0,0.07);
			--shadow-lg: 0 12px 40px rgba(0,0,0,0.1);
		}
		[data-theme="light"] body {
			background-color: var(--bg-main);
			background-image:
				radial-gradient(circle at 20% 0%, rgba(37, 99, 235, 0.05) 0%, transparent 50%),
				radial-gradient(circle at 80% 100%, rgba(124, 58, 237, 0.04) 0%, transparent 50%);
		}
		[data-theme="light"] .btn:not(.btn-primary):not(.btn-danger):not(.btn-success):not(.btn-warning) {
			background: #f1f5f9;
			color: #0f172a;
			border-color: #cbd5e1;
		}
		[data-theme="light"] .btn:not(.btn-primary):not(.btn-danger):not(.btn-success):not(.btn-warning):hover {
			background: #e2e8f0;
			border-color: #94a3b8;
		}
		[data-theme="light"] .btn-primary {
			background: linear-gradient(135deg, #2563eb, #1d4ed8) !important;
			color: #ffffff !important;
		}
		[data-theme="light"] .btn-danger {
			background: rgba(239, 68, 68, 0.12) !important;
			color: #dc2626 !important;
			border-color: rgba(239, 68, 68, 0.3) !important;
		}
		[data-theme="light"] .btn-danger:hover {
			background: #dc2626 !important;
			color: #ffffff !important;
		}
		[data-theme="light"] .btn-success {
			background: rgba(16, 185, 129, 0.12) !important;
			color: #059669 !important;
			border-color: rgba(16, 185, 129, 0.3) !important;
		}
		[data-theme="light"] .btn-success:hover {
			background: #059669 !important;
			color: #ffffff !important;
		}
		[data-theme="light"] .tab-btn:hover,
		[data-theme="light"] .btn-group-btn:hover,
		[data-theme="light"] .route-via-btn:hover {
			background: #e2e8f0;
			color: #0f172a;
		}
		[data-theme="light"] .tab-btn.active,
		[data-theme="light"] .page-btn.active,
		[data-theme="light"] .btn-group-btn.active,
		[data-theme="light"] .route-via-btn.active {
			color: #ffffff !important;
		}
		[data-theme="light"] .client-name,
		[data-theme="light"] .chart-wrapper h3,
		[data-theme="light"] .settings-card h3,
		[data-theme="light"] .modal-card h2,
		[data-theme="light"] .switch-info strong,
		[data-theme="light"] .routing-spoiler summary {
			color: #0f172a !important;
		}
		[data-theme="light"] .modal-card {
			background: #ffffff;
			border-color: #cbd5e1;
		}
		[data-theme="light"] .session-meta {
			color: #334155;
			background: rgba(16, 185, 129, 0.08);
		}
		[data-theme="light"] .session-meta strong,
		[data-theme="light"] .hw-pill strong,
		[data-theme="light"] .stat-pill strong {
			color: #0f172a;
		}
		[data-theme="light"] .client-card:hover {
			border-color: #cbd5e1;
		}
		[data-theme="light"] .toast {
			background: #ffffff;
			color: #0f172a;
			border-color: #cbd5e1;
		}
		[data-theme="light"] .banner-item code {
			color: #1d4ed8;
		}

		* { margin: 0; padding: 0; box-sizing: border-box; }
		html, body { height: 100%; }
		body {
			font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
			background: var(--bg-main);
			background-image:
				radial-gradient(circle at 20% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 50%),
				radial-gradient(circle at 80% 100%, rgba(139, 92, 246, 0.06) 0%, transparent 50%);
			background-attachment: fixed;
			color: var(--text-main);
			min-height: 100vh;
			padding: 24px 20px 60px;
			-webkit-font-smoothing: antialiased;
		}
		* { scrollbar-width: thin; scrollbar-color: rgba(59, 130, 246, 0.35) transparent; }
		*::-webkit-scrollbar { width: 8px; height: 8px; background: transparent; }
		*::-webkit-scrollbar-track { background: transparent; }
		*::-webkit-scrollbar-thumb {
			background: rgba(59, 130, 246, 0.25);
			border-radius: 10px;
			border: 2px solid transparent;
			background-clip: padding-box;
		}
		*::-webkit-scrollbar-thumb:hover { background: rgba(59, 130, 246, 0.5); background-clip: padding-box; }

		.container { max-width: 1440px; margin: 0 auto; }

		.header {
			display: flex;
			justify-content: space-between;
			align-items: center;
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-xl);
			padding: 18px 24px;
			margin-bottom: 20px;
			box-shadow: var(--shadow-md);
			flex-wrap: wrap;
			gap: 16px;
		}
		.brand { display: flex; align-items: center; gap: 14px; }
		.brand-text h1 {
			font-size: 19px;
			font-weight: 700;
			letter-spacing: -0.4px;
			line-height: 1.2;
		}
		.brand-text p {
			font-size: 12px;
			color: var(--text-muted);
			margin-top: 2px;
		}
		.header-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }

		.btn {
			padding: 9px 16px;
			border-radius: var(--radius-sm);
			font-size: 13px;
			font-weight: 600;
			cursor: pointer;
			transition: all 0.15s ease;
			border: 1px solid var(--border-subtle);
			background: #1e293b;
			color: var(--text-main);
			display: inline-flex;
			align-items: center;
			gap: 6px;
			text-decoration: none;
			white-space: nowrap;
			line-height: 1.4;
		}
		.btn:hover {
			background: #293548;
			border-color: #334155;
			transform: translateY(-1px);
		}
		.btn:active { transform: translateY(0); }
		.btn:disabled { opacity: 0.4; cursor: not-allowed; transform: none; }
		.btn-primary {
			background: linear-gradient(135deg, #3b82f6, #2563eb);
			border-color: transparent;
			box-shadow: 0 4px 14px rgba(59, 130, 246, 0.35);
		}
		.btn-primary:hover {
			background: linear-gradient(135deg, #2563eb, #1d4ed8);
			box-shadow: 0 6px 18px rgba(59, 130, 246, 0.45);
		}
		.btn-success {
			background: rgba(16, 185, 129, 0.12);
			border-color: rgba(16, 185, 129, 0.35);
			color: #34d399;
		}
		.btn-success:hover { background: #10b981; color: #fff; border-color: #10b981; }
		.btn-danger {
			background: rgba(239, 68, 68, 0.12);
			border-color: rgba(239, 68, 68, 0.35);
			color: #fca5a5;
		}
		.btn-danger:hover { background: #ef4444; color: #fff; border-color: #ef4444; }
		.btn-warning {
			background: rgba(245, 158, 11, 0.12);
			border-color: rgba(245, 158, 11, 0.35);
			color: #fcd34d;
		}
		.btn-warning:hover { background: #f59e0b; color: #fff; border-color: #f59e0b; }
		.btn-sm { padding: 6px 11px; font-size: 12px; border-radius: 6px; }

		.lang-select, .control-select {
			padding: 9px 14px;
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-sm);
			color: var(--text-main);
			font-size: 13px;
			font-weight: 500;
			outline: none;
			cursor: pointer;
			transition: all 0.15s ease;
			font-family: inherit;
			appearance: none;
			background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%2364748b' stroke-width='3'%3E%3Cpath d='M6 9l6 6 6-6'/%3E%3C/svg%3E");
			background-repeat: no-repeat;
			background-position: right 10px center;
			padding-right: 30px;
		}
		.lang-select:focus, .control-select:focus {
			border-color: var(--primary);
			box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
		}

		.hardware-bar {
			display: grid;
			grid-template-columns: repeat(4, 1fr);
			gap: 12px;
			margin-bottom: 20px;
		}
		.hw-pill {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 14px 18px;
			display: flex;
			align-items: center;
			justify-content: space-between;
			gap: 12px;
			box-shadow: var(--shadow-sm);
			transition: all 0.2s;
			min-width: 0;
		}
		.hw-pill:hover { border-color: #334155; }
		.hw-pill .hw-label {
			font-size: 12px;
			color: var(--text-muted);
			font-weight: 500;
			display: flex;
			align-items: center;
			gap: 6px;
			white-space: nowrap;
		}
		.hw-pill strong {
			font-family: 'JetBrains Mono', 'SF Mono', monospace;
			font-size: 13px;
			font-weight: 600;
			color: var(--text-main);
			white-space: nowrap;
		}

		.status-banner {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			padding: 16px 22px;
			margin-bottom: 22px;
			display: flex;
			justify-content: space-between;
			align-items: center;
			flex-wrap: wrap;
			gap: 16px;
			box-shadow: var(--shadow-sm);
		}
		.banner-item {
			display: flex;
			align-items: center;
			gap: 8px;
			font-size: 13.5px;
			color: var(--text-dim);
		}
		.banner-item code {
			background: var(--bg-input);
			padding: 5px 12px;
			border-radius: 6px;
			color: #60a5fa;
			border: 1px solid var(--border-subtle);
			font-family: 'JetBrains Mono', 'SF Mono', monospace;
			font-size: 12.5px;
		}
		.status-badge {
			display: inline-flex;
			align-items: center;
			gap: 6px;
			font-weight: 600;
			font-size: 13px;
			padding: 5px 12px;
			border-radius: 20px;
		}
		.status-badge.active {
			color: #34d399;
			background: rgba(16, 185, 129, 0.1);
		}
		.status-badge.inactive {
			color: #f87171;
			background: rgba(239, 68, 68, 0.1);
		}

		.tabs-bar {
			display: flex;
			gap: 4px;
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 6px;
			margin-bottom: 22px;
			overflow-x: auto;
			-webkit-overflow-scrolling: touch;
			scrollbar-width: none;
		}
		.tabs-bar::-webkit-scrollbar { display: none; }
		.tab-btn {
			padding: 10px 18px;
			cursor: pointer;
			color: var(--text-muted);
			font-size: 13.5px;
			font-weight: 600;
			border-radius: var(--radius-sm);
			white-space: nowrap;
			transition: all 0.15s ease;
			user-select: none;
		}
		.tab-btn:hover { color: var(--text-main); background: #1e293b; }
		.tab-btn.active {
			color: #fff;
			background: linear-gradient(135deg, #3b82f6, #2563eb);
			box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
		}
		.tab-view { display: none; animation: fadeIn 0.2s ease; }
		.tab-view.active { display: block; }
		@keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }

		.filter-bar {
			display: flex;
			gap: 12px;
			margin-bottom: 20px;
			flex-wrap: wrap;
			align-items: center;
		}
		.search-input, .textarea-input {
			flex: 1;
			min-width: 180px;
			padding: 11px 14px;
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-sm);
			color: var(--text-main);
			font-size: 13.5px;
			outline: none;
			transition: all 0.15s ease;
			font-family: inherit;
		}
		.search-input::placeholder, .textarea-input::placeholder { color: var(--text-muted); }
		.search-input:focus, .textarea-input:focus {
			border-color: var(--primary);
			box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.15);
		}
		.search-wrapper {
			position: relative;
			flex: 1;
			min-width: 180px;
			display: flex;
			align-items: center;
		}
		.search-wrapper .search-input {
			width: 100%;
			padding-right: 36px;
		}
		.search-clear-btn {
			position: absolute;
			right: 10px;
			background: rgba(148, 163, 184, 0.15);
			border: none;
			color: var(--text-dim);
			width: 22px;
			height: 22px;
			border-radius: 50%;
			font-size: 12px;
			cursor: pointer;
			display: none;
			align-items: center;
			justify-content: center;
			transition: all 0.15s ease;
			line-height: 1;
		}
		.search-clear-btn:hover {
			background: rgba(239, 68, 68, 0.25);
			color: #f87171;
		}
		.textarea-input {
			font-family: 'JetBrains Mono', 'SF Mono', monospace;
			font-size: 12.5px;
			line-height: 1.6;
			resize: vertical;
		}

		.clients-grid {
			display: grid;
			grid-template-columns: repeat(4, 1fr);
			gap: 14px;
		}
		@media (max-width: 1400px) {
			.clients-grid { grid-template-columns: repeat(3, 1fr); }
		}
		@media (max-width: 1000px) {
			.clients-grid { grid-template-columns: repeat(2, 1fr); }
		}
		.client-card {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			padding: 18px;
			transition: all 0.2s ease;
			display: flex;
			flex-direction: column;
			justify-content: space-between;
			box-shadow: var(--shadow-sm);
			position: relative;
			overflow: hidden;
			min-width: 0;
		}
		.client-card::before {
			content: '';
			position: absolute;
			top: 0; left: 0; right: 0;
			height: 3px;
			background: transparent;
			transition: background 0.2s;
		}
		.client-card.online-card::before { background: linear-gradient(90deg, #10b981, #06b6d4); }
		.client-card.paused-card::before { background: linear-gradient(90deg, #f59e0b, #eab308); }
		.client-card:hover {
			border-color: #334155;
			transform: translateY(-2px);
			box-shadow: var(--shadow-md);
		}
		.card-top {
			display: flex;
			justify-content: space-between;
			align-items: flex-start;
			margin-bottom: 10px;
			gap: 8px;
		}
		.client-name {
			font-size: 15px;
			font-weight: 700;
			word-break: break-all;
			line-height: 1.3;
			color: #fff;
		}
		.client-badge {
			font-size: 10px;
			padding: 3px 9px;
			border-radius: 20px;
			font-weight: 700;
			text-transform: uppercase;
			letter-spacing: 0.4px;
			white-space: nowrap;
			flex-shrink: 0;
		}
		.client-badge.valid {
			background: rgba(16, 185, 129, 0.15);
			color: #34d399;
			border: 1px solid rgba(16, 185, 129, 0.3);
		}
		.client-badge.paused {
			background: rgba(245, 158, 11, 0.15);
			color: #fbbf24;
			border: 1px solid rgba(245, 158, 11, 0.3);
		}
		.client-badge.revoked {
			background: rgba(239, 68, 68, 0.15);
			color: #f87171;
			border: 1px solid rgba(239, 68, 68, 0.3);
		}

		.client-note {
			font-size: 11.5px;
			color: #fbbf24;
			margin-bottom: 8px;
			font-style: italic;
			padding: 5px 9px;
			background: rgba(245, 158, 11, 0.06);
			border-radius: 6px;
			border-left: 2px solid #f59e0b;
			overflow: hidden;
			text-overflow: ellipsis;
			white-space: nowrap;
		}
		.card-details {
			font-size: 12px;
			color: var(--text-dim);
			line-height: 1.55;
			margin-bottom: 10px;
		}
		.session-meta {
			background: rgba(16, 185, 129, 0.05);
			border: 1px solid rgba(16, 185, 129, 0.18);
			border-radius: var(--radius-sm);
			padding: 8px 10px;
			margin: 8px 0;
			font-size: 11.5px;
			color: #cbd5e1;
		}
		.session-meta.offline-meta {
			background: var(--bg-input);
			border-color: var(--border-subtle);
			color: var(--text-muted);
		}
		.session-row {
			display: flex;
			justify-content: space-between;
			gap: 8px;
			align-items: center;
			flex-wrap: wrap;
		}
		.session-row span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
		.session-row strong {
			font-family: 'JetBrains Mono', monospace;
			color: #e2e8f0;
			font-weight: 600;
		}
		.live-speed-row {
			display: flex;
			justify-content: space-between;
			margin-top: 6px;
			font-weight: 600;
			font-family: 'JetBrains Mono', monospace;
			font-size: 11.5px;
		}

		.card-actions {
			display: flex;
			gap: 5px;
			flex-wrap: wrap;
			margin-top: 12px;
			padding-top: 12px;
			border-top: 1px solid var(--border-subtle);
		}
		.card-actions .btn { flex: 1; justify-content: center; min-width: 0; padding: 6px 8px; font-size: 11.5px; }

		.pagination-bar {
			display: flex;
			justify-content: space-between;
			align-items: center;
			margin-top: 22px;
			padding: 14px 20px;
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			flex-wrap: wrap;
			gap: 12px;
		}
		.pagination-info { font-size: 13px; color: var(--text-muted); }
		.pagination-pages { display: flex; gap: 6px; flex-wrap: wrap; }
		.page-btn {
			min-width: 36px;
			height: 36px;
			padding: 0 10px;
			border-radius: var(--radius-sm);
			border: 1px solid var(--border-subtle);
			background: var(--bg-input);
			color: var(--text-main);
			font-size: 13px;
			font-weight: 600;
			cursor: pointer;
			display: inline-flex;
			align-items: center;
			justify-content: center;
			transition: all 0.15s;
			font-family: inherit;
		}
		.page-btn:hover:not(:disabled) {
			border-color: var(--primary);
			color: var(--primary);
			background: rgba(59, 130, 246, 0.08);
		}
		.page-btn.active {
			background: linear-gradient(135deg, #3b82f6, #2563eb);
			border-color: transparent;
			color: #fff;
			box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
		}
		.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

		.chart-wrapper {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			padding: 24px;
			box-shadow: var(--shadow-sm);
		}
		.chart-wrapper h3 {
			font-size: 16px;
			font-weight: 700;
			color: #fff;
			margin-bottom: 16px;
			display: flex;
			align-items: center;
			gap: 8px;
		}
		.chart-toolbar {
			display: flex;
			justify-content: space-between;
			align-items: flex-start;
			flex-wrap: wrap;
			gap: 16px;
			margin-bottom: 20px;
		}
		.chart-toolbar h3 { margin-bottom: 4px; }
		.chart-toolbar p { font-size: 12.5px; color: var(--text-muted); }
		.chart-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
		.btn-group {
			display: inline-flex;
			border-radius: var(--radius-sm);
			overflow: hidden;
			border: 1px solid var(--border-subtle);
			background: var(--bg-input);
		}
		.btn-group-btn {
			background: transparent;
			border: none;
			padding: 9px 16px;
			font-size: 12.5px;
			color: var(--text-muted);
			cursor: pointer;
			transition: all 0.15s;
			border-right: 1px solid var(--border-subtle);
			font-weight: 600;
			font-family: inherit;
		}
		.btn-group-btn:last-child { border-right: none; }
		.btn-group-btn:hover { color: var(--text-main); background: #1e293b; }
		.btn-group-btn.active {
			background: linear-gradient(135deg, #3b82f6, #2563eb);
			color: #fff;
		}

		.chart-canvas-box {
			position: relative;
			height: 420px;
			width: 100%;
			margin-bottom: 20px;
		}
		.chart-stats {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
			gap: 12px;
		}
		.stat-pill {
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			padding: 14px 18px;
			border-radius: var(--radius-md);
			font-size: 12.5px;
			color: var(--text-muted);
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 12px;
		}
		.stat-pill strong {
			color: var(--text-main);
			font-size: 15px;
			font-weight: 700;
			font-family: 'JetBrains Mono', monospace;
		}

		.settings-grid {
			display: grid;
			grid-template-columns: repeat(auto-fit, minmax(380px, 1fr));
			gap: 20px;
			align-items: stretch;
		}
		.settings-card {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			padding: 24px;
			box-shadow: var(--shadow-sm);
			display: flex;
			flex-direction: column;
			gap: 14px;
			min-width: 0;
			overflow: hidden;
		}
		.settings-card > * { min-width: 0; max-width: 100%; }
		.settings-card h3 {
			font-size: 16px;
			font-weight: 700;
			color: #fff;
			display: flex;
			align-items: center;
			gap: 8px;
			flex-wrap: wrap;
		}
		.settings-card .card-desc {
			font-size: 12.5px;
			color: var(--text-muted);
			line-height: 1.5;
		}
		.settings-card input, .settings-card select, .settings-card textarea { max-width: 100%; width: 100%; }

		.form-group { margin-bottom: 0; min-width: 0; }
		.form-label {
			font-size: 11.5px;
			color: var(--text-dim);
			display: block;
			margin-bottom: 6px;
			font-weight: 600;
			text-transform: uppercase;
			letter-spacing: 0.4px;
		}
		.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
		.form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; }

		.switch-row {
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 12px 16px;
			display: flex;
			justify-content: space-between;
			align-items: center;
			gap: 14px;
			transition: border-color 0.15s;
		}
		.switch-row:hover { border-color: #334155; }
		.switch-info { flex: 1; min-width: 0; }
		.switch-info strong {
			font-size: 13px;
			display: block;
			color: #f1f5f9;
			margin-bottom: 3px;
			font-weight: 600;
			line-height: 1.35;
		}
		.switch-info span {
			font-size: 11.5px;
			color: var(--text-muted);
			line-height: 1.4;
			display: block;
		}
		.toggle-switch {
			position: relative;
			display: inline-block;
			width: 44px;
			height: 24px;
			flex-shrink: 0;
			cursor: pointer;
		}
		.toggle-switch input { opacity: 0; width: 0; height: 0; }
		.toggle-slider {
			position: absolute;
			inset: 0;
			background: #334155;
			border-radius: 24px;
			transition: 0.2s;
		}
		.toggle-slider:before {
			position: absolute;
			content: "";
			height: 18px;
			width: 18px;
			left: 3px;
			bottom: 3px;
			background: white;
			border-radius: 50%;
			transition: 0.2s;
		}
		.toggle-switch input:checked + .toggle-slider {
			background: linear-gradient(135deg, #3b82f6, #2563eb);
		}
		.toggle-switch input:checked + .toggle-slider:before {
			transform: translateX(20px);
		}

		.modal-overlay {
			display: none;
			position: fixed;
			inset: 0;
			background: rgba(0, 0, 0, 0.75);
			backdrop-filter: blur(8px);
			z-index: 1000;
			justify-content: center;
			align-items: center;
			padding: 14px;
			animation: fadeIn 0.15s ease;
		}
		.modal-overlay.active { display: flex; }
		.modal-card {
			background: #0f172a;
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-xl);
			padding: 28px;
			max-width: 480px;
			width: 100%;
			box-shadow: var(--shadow-lg);
			max-height: 90vh;
			display: flex;
			flex-direction: column;
			overflow: hidden;
		}
		.modal-card h2 {
			font-size: 19px;
			margin-bottom: 6px;
			font-weight: 700;
			color: #fff;
		}
		.modal-card p {
			font-size: 13px;
			color: var(--text-muted);
			margin-bottom: 18px;
			line-height: 1.5;
		}

		.domains-list-box {
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 6px;
		}
		.domain-row {
			display: flex;
			justify-content: space-between;
			align-items: center;
			padding: 10px 14px;
			border-radius: 6px;
			font-size: 13px;
			gap: 10px;
			transition: background 0.15s;
		}
		.domain-row:hover { background: #1e293b; }
		.domain-name {
			font-family: 'JetBrains Mono', monospace;
			color: #93c5fd;
			word-break: break-all;
			font-weight: 500;
			font-size: 12.5px;
		}
		.domain-count-badge {
			font-size: 10.5px;
			padding: 2px 7px;
			background: rgba(59, 130, 246, 0.15);
			color: #60a5fa;
			border-radius: 10px;
			font-weight: 600;
			font-family: 'JetBrains Mono', monospace;
		}

		.toast {
			position: fixed;
			bottom: 30px;
			right: 30px;
			background: #1e293b;
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 14px 20px;
			font-size: 13.5px;
			font-weight: 500;
			box-shadow: var(--shadow-lg);
			transform: translateY(20px);
			opacity: 0;
			transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
			z-index: 2000;
			pointer-events: none;
			max-width: 380px;
		}
		.toast.show { transform: translateY(0); opacity: 1; }
		.toast.success { border-left: 4px solid var(--success); }
		.toast.error { border-left: 4px solid var(--danger); }

		.routing-grid {
			display: grid;
			grid-template-columns: 1fr 2fr;
			gap: 20px;
			align-items: start;
		}
		.routing-grid-left {
			display: flex;
			flex-direction: column;
			gap: 20px;
		}
		.routing-spoiler {
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md);
			padding: 12px 14px;
			margin-top: 6px;
			transition: all 0.2s;
		}
		.routing-spoiler[open] {
			border-color: rgba(59, 130, 246, 0.3);
		}
		.routing-spoiler summary {
			font-size: 13px;
			font-weight: 600;
			color: #f1f5f9;
			cursor: pointer;
			user-select: none;
			display: flex;
			align-items: center;
			justify-content: space-between;
			outline: none;
		}
		.routing-spoiler summary::-webkit-details-marker { display: none; }
		.routing-spoiler summary::after {
			content: '▼';
			font-size: 10px;
			color: var(--text-muted);
			transition: transform 0.2s;
		}
		.routing-spoiler[open] summary::after {
			transform: rotate(180deg);
			color: var(--primary);
		}
		.routing-spoiler-content {
			margin-top: 14px;
			display: flex;
			flex-direction: column;
			gap: 12px;
		}
		.wg-status-row {
			display: flex;
			justify-content: space-between;
			padding: 10px 0;
			font-size: 13px;
			border-bottom: 1px solid var(--border-subtle);
		}
		.wg-status-row:last-child { border-bottom: none; }
		.wg-status-row span { color: var(--text-muted); }
		.wg-status-row strong {
			font-family: 'JetBrains Mono', monospace;
			font-weight: 600;
		}

		.pending-link-row {
			background: rgba(59, 130, 246, 0.06);
			border: 1px solid rgba(59, 130, 246, 0.25);
			border-radius: var(--radius-md);
			padding: 12px 14px;
			display: flex;
			flex-direction: column;
			gap: 10px;
			margin-bottom: 10px;
		}
		.pending-link-row .pending-url {
			font-family: 'JetBrains Mono', monospace;
			font-size: 12.5px;
			color: #93c5fd;
			word-break: break-all;
			font-weight: 600;
		}
		.pending-link-row .pending-ips {
			font-family: 'JetBrains Mono', monospace;
			font-size: 11.5px;
			color: var(--text-dim);
			word-break: break-all;
		}
		.pending-link-row .pending-actions {
			display: flex;
			gap: 8px;
			align-items: center;
			flex-wrap: wrap;
		}
		.route-via-group {
			display: inline-flex;
			border-radius: 6px;
			overflow: hidden;
			border: 1px solid var(--border-subtle);
			background: var(--bg-input);
		}
		.route-via-btn {
			background: transparent;
			border: none;
			padding: 6px 12px;
			font-size: 11.5px;
			color: var(--text-muted);
			cursor: pointer;
			font-weight: 600;
			font-family: inherit;
			transition: all 0.15s;
			border-right: 1px solid var(--border-subtle);
		}
		.route-via-btn:last-child { border-right: none; }
		.route-via-btn:hover { color: var(--text-main); background: #1e293b; }
		.route-via-btn.active { background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; }

		@media (max-width: 1024px) {
			.hardware-bar { grid-template-columns: repeat(2, 1fr); }
		}
		@media (max-width: 768px) {
			body { padding: 12px 10px 40px; }
			.header { padding: 14px; border-radius: var(--radius-lg); }
			.brand-text h1 { font-size: 16px; }
			.brand-text p { font-size: 11px; }
			.header-actions { width: 100%; }
			.header-actions .btn, .header-actions .lang-select { flex: 1; justify-content: center; padding: 9px 10px; font-size: 12px; }
			.hardware-bar { grid-template-columns: repeat(2, 1fr); gap: 8px; }
			.hw-pill { padding: 10px 12px; flex-direction: column; align-items: flex-start; gap: 4px; min-width: 0; }
			.hw-pill .hw-label { font-size: 11px; }
			.hw-pill strong { font-size: 12px; }
			.status-banner { padding: 12px 14px; flex-direction: column; align-items: stretch; }
			.banner-item { justify-content: space-between; }
			.tabs-bar { padding: 4px; }
			.tab-btn { padding: 8px 12px; font-size: 12.5px; }
			.clients-grid { grid-template-columns: 1fr; }
			.settings-grid, .routing-grid { grid-template-columns: 1fr; }
			.form-row-2, .form-row-3 { grid-template-columns: 1fr; }
			.chart-wrapper, .settings-card { padding: 16px; border-radius: var(--radius-md); }
			.chart-toolbar { flex-direction: column; align-items: stretch; gap: 12px; }
			.chart-canvas-box { height: 280px; }
			.chart-controls { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; width: 100%; }
			#chartClientFilter, .btn-group { grid-column: 1 / -1; width: 100%; }
			.btn-group { display: flex; }
			.btn-group-btn { flex: 1; padding: 10px 4px; font-size: 12px; }
			.chart-stats { grid-template-columns: 1fr; }
			.stat-pill { padding: 10px 14px; font-size: 12px; }
			.stat-pill strong { font-size: 13px; }
			.toast { left: 14px; right: 14px; bottom: 14px; max-width: none; }
			.pagination-bar { flex-direction: column; align-items: center; padding: 12px; }
			.pagination-pages { width: 100%; justify-content: center; }
			.modal-card { padding: 20px; border-radius: var(--radius-lg); }
		}
	</style>
</head>
<body>
<div class="container">
	<header class="header">
		<div class="brand">
			<div class="brand-text">
				<h1>OpenVPN Dashboard</h1>
				<p>Control Center by <a href="https://github.com/FSystem88" style="color: var(--text-muted);">FSystem88</a></p>
			</div>
		</div>
		<div class="header-actions">
			<button class="btn" id="themeToggleBtn" onclick="toggleTheme()" title="Сменить тему" style="padding:9px 12px;">
				<span id="themeToggleIcon">☀️</span>
			</button>
			<select class="lang-select" id="langSelect" onchange="changeLanguage(this.value)">
				<option value="ru">RU</option>
				<option value="en">EN</option>
			</select>
			<button class="btn btn-primary" onclick="openCreateModal()">
				<span></span> <span data-i18n="btn_create_client">Создать</span>
			</button>
			<button class="btn" onclick="openBackupModal()">
				<span>📦</span> <span data-i18n="btn_backup">Бэкап</span>
			</button>
			<a href="/logout" class="btn btn-danger">
				<span>🚪</span> <span data-i18n="btn_logout">Выйти</span>
			</a>
		</div>
	</header>

	<div class="hardware-bar" id="hardwareBar">
		<div class="hw-pill">
			<span class="hw-label">💻 CPU</span>
			<strong id="hwCpu">0%</strong>
		</div>
		<div class="hw-pill">
			<span class="hw-label">📊 RAM</span>
			<strong id="hwRam">0 / 0 MB</strong>
		</div>
		<div class="hw-pill">
			<span class="hw-label">💾 Disk</span>
			<strong id="hwDisk">0 / 0 GB</strong>
		</div>
		<div class="hw-pill">
			<span class="hw-label">🌐 WG Ping</span>
			<strong id="hwPing">—</strong>
		</div>
	</div>

	<div class="status-banner">
		<div class="banner-item">
			<span data-i18n="banner_endpoint">Сервер:</span>
			<code id="bannerEndpointCode">{{ domain }}:{{ port }} ({{ proto }})</code>
		</div>
		<div class="banner-item">
			<span id="serverStatusText" class="status-badge active">● ...</span>
		</div>
		<div class="banner-item">
			<span data-i18n="banner_online">Онлайн:</span>
			<strong id="activeClientsCount" style="color:var(--primary);">0 / 0</strong>
		</div>
		<div class="banner-item" style="color:var(--text-muted); font-size:12.5px;" id="lastSyncTime">—</div>
	</div>

	<div class="tabs-bar">
		<div class="tab-btn active" id="tabBtnClients" onclick="switchTab('tab-clients')" data-i18n="tab_clients">👥 Клиенты</div>
		<div class="tab-btn" id="tabBtnSpeed" onclick="switchTab('tab-speed')" data-i18n="tab_speed">📈 Скорость</div>
		<div class="tab-btn" id="tabBtnRouting" onclick="switchTab('tab-routing')" data-i18n="tab_routing">🔀 Маршрутизация</div>
		<div class="tab-btn" id="tabBtnConfig" onclick="switchTab('tab-config')" data-i18n="tab_config">⚙️ Конфигурация</div>
		<div class="tab-btn" id="tabBtnSettings" onclick="switchTab('tab-settings')" data-i18n="tab_settings">🔐 Аккаунт</div>
	</div>

	<div id="tab-clients" class="tab-view active">
		<div class="filter-bar">
			<div class="search-wrapper">
				<input type="text" class="search-input" id="clientSearch" data-i18n-placeholder="search_placeholder" placeholder="🔍 Поиск по имени или IP..." oninput="onFilterInputChange()" autocomplete="off">
				<button type="button" class="search-clear-btn" id="clearSearchBtn" onclick="clearClientSearch()" title="Очистить">✕</button>
			</div>
			<select class="control-select" id="statusFilter" onchange="onFilterInputChange()">
				<option value="all" data-i18n="filter_all">Все активные</option>
				<option value="online" data-i18n="filter_online">🟢 Только онлайн</option>
				<option value="offline" data-i18n="filter_offline">⚪ Только офлайн</option>
				<option value="paused" data-i18n="filter_paused">⏸️ На паузе</option>
				<option value="revoked" data-i18n="filter_revoked">🚫 Отозванные</option>
			</select>
			<select class="control-select" id="sortFilter" onchange="onFilterInputChange()">
				<option value="online_first" data-i18n="sort_online">🟢 Сначала онлайн</option>
				<option value="name_asc" data-i18n="sort_name">🔤 По имени</option>
			</select>
			<select class="control-select" id="pageSizeSelect" onchange="onPageSizeChange()">
				<option value="20" data-i18n="per_page_20">По 20</option>
				<option value="50" data-i18n="per_page_50">По 50</option>
				<option value="100" data-i18n="per_page_100">По 100</option>
			</select>
		</div>

		<div class="clients-grid" id="clientsGrid">
			<div style="grid-column: 1/-1; text-align:center; padding: 60px 20px; color:var(--text-muted); font-size:14px;" data-i18n="loading">
				⏳ Загрузка...
			</div>
		</div>

		<div class="pagination-bar" id="paginationBar" style="display:none;">
			<div class="pagination-info" id="paginationInfo"></div>
			<div class="pagination-pages" id="paginationPages"></div>
		</div>
	</div>

	<div id="tab-speed" class="tab-view">
		<div class="chart-wrapper">
			<div class="chart-toolbar">
				<div>
					<h3 data-i18n="chart_title">Мониторинг скорости в реальном времени</h3>
					<p data-i18n="chart_subtitle">Прямой опрос сокета OpenVPN в памяти</p>
				</div>
				<div class="chart-controls">
					<select class="control-select" id="chartClientFilter" onchange="renderChartData()">
						<option value="__ALL__" data-i18n="chart_all_users">👥 Все клиенты</option>
					</select>
					<div class="btn-group">
						<button class="btn-group-btn active" id="btnWin30" onclick="setWindowTime(30)">30s</button>
						<button class="btn-group-btn" id="btnWin60" onclick="setWindowTime(60)">1m</button>
						<button class="btn-group-btn" id="btnWin300" onclick="setWindowTime(300)">5m</button>
					</div>
					<select class="control-select" id="chartMetricType" onchange="renderChartData()">
						<option value="total" data-i18n="metric_total">Σ Суммарно</option>
						<option value="down" data-i18n="metric_down">↓ Download</option>
						<option value="up" data-i18n="metric_up">↑ Upload</option>
					</select>
					<select class="control-select" id="chartPollInterval" onchange="changePollInterval()">
						<option value="1000">1s</option>
						<option value="3000">3s</option>
						<option value="5000">5s</option>
						<option value="10000">10s</option>
					</select>
				</div>
			</div>
			<div class="chart-canvas-box">
				<canvas id="speedChartCanvas"></canvas>
			</div>
			<div class="chart-stats">
				<div class="stat-pill"><span data-i18n="stat_down">Текущий Download:</span> <strong id="liveTotalDown" style="color:#60a5fa;">0 B/s</strong></div>
				<div class="stat-pill"><span data-i18n="stat_up">Текущий Upload:</span> <strong id="liveTotalUp" style="color:#34d399;">0 B/s</strong></div>
				<div class="stat-pill"><span data-i18n="stat_active">Активных подключений:</span> <strong id="liveActiveCount">0</strong></div>
			</div>
		</div>
	</div>

	<div id="tab-routing" class="tab-view">
		<div class="routing-grid">
			<div class="routing-grid-left">
				<div class="settings-card">
					<h3 data-i18n="routing_title">Сплит-туннель (WireGuard + ipset)</h3>
					<p class="card-desc" data-i18n="routing_desc">Маршрутизация через второй VPN-сервер</p>

					<div class="wg-status-row">
						<span data-i18n="wg_status_label">Статус WG0:</span>
						<strong id="wgText">...</strong>
					</div>
					<div class="wg-status-row">
						<span data-i18n="ipset_count_label">Подсетей в ipset:</span>
						<strong id="ipsetSubnetsCount" style="color:#60a5fa;">...</strong>
					</div>

					<div style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin: 6px 0;">
						<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
							<strong style="font-size:13px;" data-i18n="remote_title_inline">🔗 Удалённая точка выхода</strong>
							<span id="remoteEndpointStatus" style="font-size:12px; padding:3px 10px; border-radius:12px; font-weight:600;">...</span>
						</div>
						<div id="remoteEndpointConnected" style="display:none; font-size:13px;">
							<span data-i18n="remote_connected_to">Подключено к:</span>
							<strong id="remoteEndpointIp" style="font-family:'JetBrains Mono',monospace; color:#34d399;">—</strong>
							<button class="btn btn-sm" style="margin-left:10px;" onclick="showRemoteReconfigure()" data-i18n="btn_reconfigure">Перенастроить</button>
						</div>

						<div id="remoteEndpointForm">
							<div class="form-group" style="margin-bottom:8px;">
								<input type="text" id="remoteServerIp" class="search-input" data-i18n-placeholder="remote_ip_placeholder" placeholder="IP удаленного сервера">
							</div>
							<div class="form-group" style="margin-bottom:8px;">
								<input type="password" id="remoteServerPass" class="search-input" data-i18n-placeholder="remote_pass_placeholder" placeholder="Пароль root">
							</div>
							<div style="display:flex; gap:10px;">
								<button class="btn btn-danger" style="justify-content:center; width:50%;" onclick="hideRemoteReconfigure()" data-i18n="btn_cancel">❌ Отмена</button>
								<button class="btn btn-success" style="justify-content:center; width:50%;" onclick="setupRemoteTunnel()" data-i18n="btn_setup_tunnel">🚀 Настроить туннель</button>
							</div>
						</div>
					</div>

					<div class="switch-row">
						<div class="switch-info">
							<strong data-i18n="torrent_block_title">🚫 Блокировка BitTorrent</strong>
							<span data-i18n="torrent_block_desc">Защита от абузов и банов хостинга</span>
						</div>
						<label class="toggle-switch">
							<input type="checkbox" id="torrentBlockCheck">
							<span class="toggle-slider"></span>
						</label>
					</div>

					<div class="form-group">
						<label class="form-label" data-i18n="routing_url_label">URL списка подсетей:</label>
						<input type="text" id="cidrUrlInput" class="search-input">
					</div>
					<div class="form-group">
						<label class="form-label" data-i18n="custom_cidrs_label">Свои IP/подсети:</label>
						<textarea id="customCidrsInput" class="textarea-input" rows="3" placeholder="77.88.8.8/32&#10;192.168.10.0/24"></textarea>
					</div>
					<div class="form-group">
						<label class="form-label" data-i18n="routing_mode_label">Режим:</label>
						<select class="control-select" id="routingModeSelect">
							<option value="off" data-i18n="mode_off">🔴 Отключено</option>
							<option value="split" data-i18n="mode_split">🟡 CIDR напрямую, остальное в WG</option>
							<option value="cidr_wg" data-i18n="mode_cidr_wg">🟣 CIDR в WG, остальное напрямую</option>
							<option value="all" data-i18n="mode_all">🟢 Весь трафик через WireGuard</option>
						</select>
					</div>

					<details class="routing-spoiler">
						<summary><span data-i18n="split_details_summary">🔗 Управление ссылками сплит-туннеля</span></summary>
						<div class="routing-spoiler-content">
							<p style="font-size:12px; color:var(--text-muted); line-height:1.4;" data-i18n="split_details_desc">Разрешите URL в IP для выборочной маршрутизации через WireGuard или напрямую.</p>
							<div style="display:flex; gap:8px; flex-wrap:wrap;">
								<input type="text" id="splitLinkUrl" class="search-input" placeholder="https://example.com" style="flex:1; min-width:180px;">
								<button class="btn btn-primary btn-sm" onclick="resolveLink()" data-i18n="btn_resolve_link">🔍 Найти IP</button>
							</div>
							<div id="pendingLinksBox"></div>
							<div class="domains-list-box" id="splitLinksList" style="max-height:220px; overflow-y:auto;"></div>
						</div>
					</details>

					<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:8px;">
						<button class="btn btn-primary" onclick="saveRoutingSettings()" data-i18n="btn_save">💾 Сохранить</button>
						<button class="btn" onclick="updateCidrIps()" data-i18n="btn_refresh_cidr">🔄 Обновить CIDR</button>
					</div>
				</div>
			</div>

			<div class="settings-card">
				<h3 data-i18n="adblock_title">🛡️ Блокировка рекламы (DNS AdBlock / dnsmasq)</h3>
				<p class="card-desc" data-i18n="adblock_desc">Автоматическая фильтрация рекламы и трекеров на уровне VPN-сервера без потери скорости</p>

				<div class="switch-row">
					<div class="switch-info">
						<strong data-i18n="adblock_enable">Включить блокировку рекламы для всех клиентов</strong>
						<span id="adblockStatusLabel">...</span>
					</div>
					<label class="toggle-switch">
						<input type="checkbox" id="adblockEnableToggle" onchange="toggleAdblock(this.checked)">
						<span class="toggle-slider"></span>
					</label>
				</div>

				<div class="form-row-2" style="margin-top:4px;">
					<div style="background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px; min-width:0;">
						<label class="form-label" data-i18n="adblock_add_list">📋 Добавить AdList по ссылке</label>
						<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
							<input type="text" id="adblockListUrl" class="search-input" placeholder="https://..." style="flex:1; min-width:140px;">
							<select class="control-select" id="adblockListType">
								<option value="black" data-i18n="adblock_black">⚫ Черный список</option>
								<option value="white" data-i18n="adblock_white">⚪ Белый список</option>
							</select>
							<button class="btn btn-primary" onclick="addAdblockList()"><span data-i18n="btn_add">➕ Добавить</span></button>
						</div>
						<div class="domains-list-box" id="adblockListsBox" style="max-height:360px; overflow-y:auto;"></div>
					</div>

					<div style="background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px; min-width:0;">
						<label class="form-label" data-i18n="adblock_add_domain">🌐 Добавить отдельный домен</label>
						<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
							<input type="text" id="adblockDomainInput" class="search-input" placeholder="ads.example.com" style="flex:1; min-width:140px;">
							<select class="control-select" id="adblockDomainType">
								<option value="black" data-i18n="adblock_to_black">⚫ В черный</option>
								<option value="white" data-i18n="adblock_to_white">⚪ В белый</option>
							</select>
							<button class="btn btn-primary" onclick="addAdblockDomain()"><span data-i18n="btn_add">➕ Добавить</span></button>
						</div>
						<div class="domains-list-box" id="adblockDomainsBox" style="max-height:360px; overflow-y:auto;"></div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<div id="tab-config" class="tab-view">
		<div class="chart-wrapper">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
				<div>
					<h3 data-i18n="config_title">⚙️ Прямой редактор server.conf</h3>
					<p style="font-size:12.5px; color:var(--text-muted); margin-top:4px;">/etc/openvpn/server/server.conf</p>
				</div>
				<div style="display:flex; gap:8px; flex-wrap:wrap;">
					<button class="btn" onclick="loadConfigView()" data-i18n="btn_reread">🔄 Перечитать</button>
					<button class="btn btn-primary" onclick="saveRawConfig(true)" data-i18n="btn_save_restart">💾 Сохранить и перезапустить</button>
				</div>
			</div>
			<textarea id="serverConfigText" class="textarea-input" rows="24" style="width:100%;"></textarea>
		</div>
	</div>

	<div id="tab-settings" class="tab-view">
		<div class="settings-grid">
			<div class="settings-card">
				<h3 data-i18n="card_admin">🔐 Учетная запись и Панель</h3>
				<p class="card-desc" data-i18n="card_admin_desc">Безопасность входа и параметры панели</p>

				<div class="form-row-2">
					<div class="form-group">
						<label class="form-label" data-i18n="label_admin_login">Логин администратора</label>
						<input type="text" id="setAdminLogin" class="search-input">
					</div>
					<div class="form-group">
						<label class="form-label" data-i18n="label_admin_pass">Новый пароль</label>
						<input type="password" id="setAdminPass" class="search-input" placeholder="••••••••">
					</div>
				</div>

				<div class="form-row-2">
					<div class="form-group">
						<label class="form-label" data-i18n="label_panel_port">Порт панели</label>
						<input type="number" id="setPanelPort" class="search-input">
					</div>
					<div class="form-group">
						<label class="form-label">Домен / IP сервера</label>
						<input type="text" id="setOvpnDomain" class="search-input">
					</div>
				</div>
			</div>

			<div class="settings-card">
				<h3 data-i18n="card_modules">🎛️ Модули и функции</h3>
				<p class="card-desc" data-i18n="card_modules_desc">Включение и отключение элементов интерфейса</p>

				<div class="switch-row">
					<div class="switch-info">
						<strong data-i18n="label_speed_monitor">📈 Мониторинг скорости</strong>
						<span data-i18n="label_speed_monitor_desc">Живые графики скорости</span>
					</div>
					<label class="toggle-switch">
						<input type="checkbox" id="setEnableSpeed">
						<span class="toggle-slider"></span>
					</label>
				</div>
				<div class="switch-row">
					<div class="switch-info">
						<strong data-i18n="label_hw_bar">💻 Панель ресурсов</strong>
						<span data-i18n="label_hw_bar_desc">CPU / RAM / Disk / Ping</span>
					</div>
					<label class="toggle-switch">
						<input type="checkbox" id="setEnableHwBar">
						<span class="toggle-slider"></span>
					</label>
				</div>
				<div class="switch-row">
					<div class="switch-info">
						<strong data-i18n="label_torrent_block">🚫 Блок BitTorrent</strong>
						<span data-i18n="label_torrent_block_desc">iptables string match</span>
					</div>
					<label class="toggle-switch">
						<input type="checkbox" id="setTorrentBlock">
						<span class="toggle-slider"></span>
					</label>
				</div>
			</div>

			<div class="settings-card">
				<h3 data-i18n="card_service">🛠️ Управление службами</h3>
				<p class="card-desc" data-i18n="card_service_desc">Применение параметров и управление демоном</p>

				<div style="display:flex; flex-direction:column; gap:10px;">
					<button class="btn btn-primary" style="padding:13px; justify-content:center;" onclick="saveAllAccountSettings(false)" data-i18n="btn_save_all">
						💾 Сохранить настройки
					</button>
					<button class="btn btn-success" style="padding:13px; justify-content:center;" onclick="saveAllAccountSettings(true)" data-i18n="btn_save_apply">
						🚀 Сохранить и перезапустить
					</button>
				</div>

				<h4 style="font-size:12px; color:var(--text-dim); text-transform:uppercase; letter-spacing:0.5px;" data-i18n="label_ovpn_service">OpenVPN daemon</h4>
				<div class="form-row-3">
					<button class="btn" style="justify-content:center;" onclick="controlOvpnService('restart')" data-i18n="btn_restart">🔄 Рестарт</button>
					<button class="btn btn-success" style="justify-content:center;" onclick="controlOvpnService('start')" data-i18n="btn_start">▶️ Старт</button>
					<button class="btn btn-danger" style="justify-content:center;" onclick="controlOvpnService('stop')" data-i18n="btn_stop">⏹️ Стоп</button>
				</div>
			</div>
		</div>
	</div>
</div>

<div class="modal-overlay" id="createModal">
	<div class="modal-card">
		<h2 data-i18n="modal_create_title">➕ Новый клиент</h2>
		<p data-i18n="modal_create_desc">Латиница, цифры, дефис и подчеркивание.</p>
		<label class="form-label" data-i18n="label_client_name">Имя клиента</label>
		<input type="text" id="newClientName" class="search-input" placeholder="iphone-user" style="width:100%; margin-bottom:12px;" autofocus>
		<label class="form-label" data-i18n="label_client_note">Заметка</label>
		<input type="text" id="newClientNote" class="search-input" data-i18n-placeholder="note_placeholder" placeholder="Например: Ноутбук" style="width:100%; margin-bottom:12px;">
		<div style="margin-bottom: 20px;">
			<label class="form-label" data-i18n="label_ttl_days">Срок в днях (0 = ∞)</label>
			<input type="number" id="newClientTtl" class="search-input" value="0" min="0" style="width:100%;">
		</div>
		<div style="display:flex; gap:10px; justify-content:flex-end;">
			<button class="btn" onclick="closeModals()" data-i18n="btn_cancel">Отмена</button>
			<button class="btn btn-primary" onclick="submitCreateClient()" data-i18n="btn_create">Создать</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="qrModal">
	<div class="modal-card" style="text-align:center;">
		<h2 id="qrModalTitle">📱 QR</h2>
		<p data-i18n="modal_qr_desc">Отсканируйте камерой телефона для скачивания .ovpn профиля</p>
		<div style="background:#fff; padding:16px; border-radius:16px; display:inline-block; margin: 0 auto 16px;">
			<canvas id="qrCanvas"></canvas>
		</div>
		<div style="display:flex; gap:10px;">
			<button class="btn btn-primary" style="flex:1; justify-content:center;" id="qrCopyBtn" data-i18n="btn_copy_link">🔗 Копировать</button>
			<button class="btn" style="flex:1; justify-content:center;" onclick="closeModals()" data-i18n="btn_close">Закрыть</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="backupModal">
	<div class="modal-card">
		<h2 data-i18n="modal_backup_title">📦 Резервное копирование</h2>
		<p data-i18n="modal_backup_desc">Полный архив конфигурации.</p>
		<div style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
			<button class="btn" onclick="downloadBackupArchive()" style="padding:14px; justify-content:center;" data-i18n="btn_download_backup">📥 Скачать архив</button>
			<button class="btn btn-primary" onclick="document.getElementById('backupFileInput').click()" style="padding:14px; justify-content:center;" data-i18n="btn_restore_backup">📤 Восстановить из файла</button>
		</div>
		<input type="file" id="backupFileInput" accept=".tar.gz" style="display:none;" onchange="processRestoreFile(event)">
		<button class="btn" style="width:100%; justify-content:center;" onclick="closeModals()" data-i18n="btn_close">Закрыть</button>
	</div>
</div>

<div class="toast" id="toastBox"></div>

<script>
const i18n = {
	ru: {
		btn_create_client: "Создать",
		btn_backup: "Бэкап",
		btn_logout: "Выйти",
		banner_endpoint: "Сервер:",
		banner_online: "Онлайн:",
		server_active: "● Сервер активен",
		server_stopped: "● Остановлен",
		updated_at: "Обновлено:",
		tab_clients: "👥 Клиенты",
		tab_speed: "📈 Скорость",
		tab_routing: "🔀 Маршрутизация",
		tab_config: "⚙️ Конфигурация",
		tab_settings: "🔐 Аккаунт",
		search_placeholder: "🔍 Поиск по имени или IP...",
		filter_all: "Все активные",
		filter_online: "🟢 Только онлайн",
		filter_offline: "⚪ Только офлайн",
		filter_paused: "⏸️ На паузе",
		filter_revoked: "🚫 Отозванные",
		sort_online: "🟢 Сначала онлайн",
		sort_name: "🔤 По имени",
		per_page_20: "По 20",
		per_page_50: "По 50",
		per_page_100: "По 100",
		pagination_showing: "Показано {from}–{to} из {total}",
		empty_clients_list: "Список клиентов пуст",
		chart_title: "Мониторинг скорости в реальном времени",
		chart_subtitle: "Прямой опрос сокета OpenVPN в памяти",
		chart_all_users: "👥 Все клиенты",
		metric_total: "Σ Суммарно",
		metric_down: "↓ Download",
		metric_up: "↑ Upload",
		stat_down: "Текущий Download:",
		stat_up: "Текущий Upload:",
		stat_active: "Активных подключений:",
		routing_title: "Сплит-туннель (WireGuard + ipset)",
		routing_desc: "Маршрутизация через второй VPN-сервер",
		wg_status_label: "Статус WG0:",
		wg_active: "АКТИВЕН",
		wg_inactive: "ОТКЛЮЧЕН",
		ipset_count_label: "Подсетей в ipset:",
		torrent_block_title: "🚫 Блокировка BitTorrent",
		torrent_block_desc: "Защита от абузов и банов хостинга",
		routing_url_label: "URL списка подсетей:",
		custom_cidrs_label: "Свои IP/подсети:",
		routing_mode_label: "Режим:",
		mode_off: "🔴 Отключено",
		mode_split: "🟡 CIDR напрямую, остальное в WG",
		mode_cidr_wg: "🟣 CIDR в WG, остальное напрямую",
		mode_all: "🟢 Весь трафик через WireGuard",
		btn_save: "💾 Сохранить",
		btn_refresh_cidr: "🔄 Обновить CIDR",
		remote_ip_placeholder: "IP удаленного сервера",
		remote_pass_placeholder: "Пароль root",
		btn_setup_tunnel: "🚀 Настроить туннель",
		btn_resolve_link: "🔍 Найти IP и CIDR",
		btn_save_link: "💾 Сохранить",
		btn_cancel_link: "✕ Отмена",
		route_via_split: "🟡 Напрямую",
		route_via_wg: "🟣 Через WG",
		modal_create_title: "➕ Новый клиент",
		modal_create_desc: "Латиница, цифры, дефис и подчеркивание.",
		label_client_name: "Имя клиента",
		label_client_note: "Заметка",
		note_placeholder: "Например: Ноутбук",
		label_ttl_days: "Срок в днях (0 = ∞)",
		modal_qr_desc: "Отсканируйте камерой телефона",
		btn_copy_link: "🔗 Копировать",
		modal_backup_title: "📦 Резервное копирование",
		modal_backup_desc: "Полный архив конфигурации.",
		btn_download_backup: "📥 Скачать архив",
		btn_restore_backup: "📤 Восстановить из файла",
		btn_cancel: "✕ Отмена",
		btn_create: "Создать",
		btn_close: "Закрыть",
		badge_online: "🟢 Онлайн",
		badge_offline: "⚪ Офлайн",
		badge_paused: "⏸️ НА ПАУЗЕ",
		badge_valid: "АКТИВЕН",
		badge_revoked: "ОТОЗВАН",
		loading: "⏳ Загрузка...",
		btn_link: "🔗",
		btn_config: "⬇️",
		btn_pause: "⏸️",
		btn_resume: "▶️",
		btn_delete_forever: "🗑️ Удалить",
		title_qr: "QR-код",
		title_revoke: "Отозвать",
		toast_generating_keys: "⏳ Генерация ключей...",
		toast_client_created: "✅ Клиент создан",
		toast_network_error: "❌ Ошибка сети",
		toast_cert_revoked: "✅ Сертификат отозван",
		toast_client_deleted: "✅ Клиент удален",
		toast_link_copied: "✅ Ссылка скопирована!",
		toast_saving_routes: "⏳ Сохранение...",
		toast_routes_saved: "✅ Настройки сохранены",
		toast_updating_cidr: "⏳ Обновление ipset...",
		toast_cidr_updated: "✅ CIDR обновлены",
		toast_ip_pass_required: "❌ Укажите IP и пароль",
		toast_deploying_tunnel: "⏳ Развертывание туннеля...",
		toast_tunnel_deployed: "✅ Туннель настроен",
		toast_restoring: "⏳ Восстановление...",
		toast_restored: "✅ Восстановлено",
		toast_link_added: "✅ Ссылка добавлена",
		toast_link_removed: "✅ Ссылка удалена",
		toast_resolve_error: "❌ Не удалось разрешить домен",
		toast_resolving: "⏳ Разрешение домена...",
		toast_resolved: "✅ Домен разрешен",
		confirm_delete_forever: "Удалить клиента {name} навсегда?",
		confirm_revoke: "Отозвать сертификат {name}?",
		confirm_setup_tunnel: "Настроить туннель на удаленном сервере?",
		confirm_restore: "Перезаписать текущую конфигурацию?",
		config_load_error: "Ошибка загрузки конфигурации",
		card_admin: "🔐 Учетная запись и Панель",
		card_admin_desc: "Безопасность входа и параметры панели",
		label_admin_login: "Логин администратора",
		label_admin_pass: "Новый пароль",
		label_panel_port: "Порт панели",
		card_modules: "🎛️ Модули и функции",
		card_modules_desc: "Включение и отключение элементов интерфейса",
		label_speed_monitor: "📈 Мониторинг скорости",
		label_speed_monitor_desc: "Живые графики скорости",
		label_hw_bar: "💻 Панель ресурсов",
		label_hw_bar_desc: "CPU / RAM / Disk / Ping",
		label_torrent_block: "🚫 Блок BitTorrent",
		label_torrent_block_desc: "iptables string match",
		card_service: "🛠️ Управление службами",
		card_service_desc: "Применение параметров и управление демоном",
		btn_save_all: "💾 Сохранить настройки",
		btn_save_apply: "🚀 Сохранить и перезапустить",
		label_ovpn_service: "OpenVPN daemon",
		btn_restart: "🔄 Рестарт",
		btn_start: "▶️ Старт",
		btn_stop: "⏹️ Стоп",
		remote_title_inline: "🔗 Удалённая точка выхода",
		remote_connected_to: "Подключено к:",
		btn_reconfigure: "Перенастроить",
		adblock_title: "🛡️ Блокировка рекламы (DNS AdBlock)",
		adblock_desc: "Автоматическая фильтрация рекламы и трекеров без потери скорости",
		adblock_enable: "Включить блокировку рекламы для всех клиентов",
		adblock_add_list: "📋 Добавить AdList по ссылке",
		adblock_add_domain: "🌐 Добавить отдельный домен",
		adblock_black: "⚫ Черный список",
		adblock_white: "⚪ Белый список",
		adblock_to_black: "⚫ В черный",
		adblock_to_white: "⚪ В белый",
		btn_add: "➕ Добавить",
		config_title: "⚙️ Прямой редактор server.conf",
		btn_reread: "🔄 Перечитать",
		btn_save_restart: "💾 Сохранить и перезапустить",
		split_details_summary: "🔗 Управление ссылками сплит-туннеля",
		split_details_desc: "Разрешите URL в IP для выборочной маршрутизации через WireGuard или напрямую."
	},
	en: {
		btn_create_client: "Create",
		btn_backup: "Backup",
		btn_logout: "Logout",
		banner_endpoint: "Server:",
		banner_online: "Online:",
		server_active: "● Server Active",
		server_stopped: "● Stopped",
		updated_at: "Updated:",
		tab_clients: "👥 Clients",
		tab_speed: "📈 Speed",
		tab_routing: "🔀 Routing",
		tab_config: "⚙️ Config",
		tab_settings: "🔐 Account",
		search_placeholder: "🔍 Search by name or IP...",
		filter_all: "All Active",
		filter_online: "🟢 Online only",
		filter_offline: "⚪ Offline only",
		filter_paused: "⏸️ Paused",
		filter_revoked: "🚫 Revoked",
		sort_online: "🟢 Online first",
		sort_name: "🔤 By Name",
		per_page_20: "20 / page",
		per_page_50: "50 / page",
		per_page_100: "100 / page",
		pagination_showing: "Showing {from}–{to} of {total}",
		empty_clients_list: "No clients",
		chart_title: "Realtime Speed Monitoring",
		chart_subtitle: "In-memory OpenVPN socket telemetry",
		chart_all_users: "👥 All Clients",
		metric_total: "Σ Total",
		metric_down: "↓ Download",
		metric_up: "↑ Upload",
		stat_down: "Current Download:",
		stat_up: "Current Upload:",
		stat_active: "Active sessions:",
		routing_title: "Split Tunnel (WireGuard + ipset)",
		routing_desc: "Routing through second VPN server",
		wg_status_label: "WG0 Status:",
		wg_active: "ACTIVE",
		wg_inactive: "INACTIVE",
		ipset_count_label: "Subnets in ipset:",
		torrent_block_title: "🚫 BitTorrent Block",
		torrent_block_desc: "Protection against host abuse",
		routing_url_label: "CIDR list URL:",
		custom_cidrs_label: "Custom bypass IPs:",
		routing_mode_label: "Mode:",
		mode_off: "🔴 Disabled",
		mode_split: "🟡 CIDR direct, rest via WG",
		mode_cidr_wg: "🟣 CIDR via WG, rest direct",
		mode_all: "🟢 Full tunnel via WireGuard",
		btn_save: "💾 Save",
		btn_refresh_cidr: "🔄 Sync CIDR",
		remote_ip_placeholder: "Remote server IP",
		remote_pass_placeholder: "Root password",
		btn_setup_tunnel: "🚀 Setup Tunnel",
		btn_resolve_link: "🔍 Resolve IP and CIDR",
		btn_save_link: "💾 Save",
		btn_cancel_link: "✕ Cancel",
		route_via_split: "🟡 Direct",
		route_via_wg: "🟣 Via WG",
		modal_create_title: "➕ Create Client",
		modal_create_desc: "Latin letters, numbers, hyphens, underscores.",
		label_client_name: "Client name",
		label_client_note: "Note",
		note_placeholder: "e.g., Laptop",
		label_ttl_days: "TTL days (0 = ∞)",
		modal_qr_desc: "Scan with phone camera",
		btn_copy_link: "🔗 Copy",
		modal_backup_title: "📦 Backup",
		modal_backup_desc: "Full archive of configuration.",
		btn_download_backup: "📥 Download",
		btn_restore_backup: "📤 Restore",
		btn_cancel: "✕ Cancel",
		btn_create: "Create",
		btn_close: "Close",
		badge_online: "🟢 Online",
		badge_offline: "⚪ Offline",
		badge_paused: "⏸️ PAUSED",
		badge_valid: "VALID",
		badge_revoked: "REVOKED",
		loading: "⏳ Loading...",
		btn_link: "🔗",
		btn_config: "⬇️",
		btn_pause: "⏸️",
		btn_resume: "▶️",
		btn_delete_forever: "🗑️ Delete",
		title_qr: "QR code",
		title_revoke: "Revoke",
		toast_generating_keys: "⏳ Generating keys...",
		toast_client_created: "✅ Client created",
		toast_network_error: "❌ Network error",
		toast_cert_revoked: "✅ Certificate revoked",
		toast_client_deleted: "✅ Client deleted",
		toast_link_copied: "✅ Link copied!",
		toast_saving_routes: "⏳ Saving...",
		toast_routes_saved: "✅ Settings saved",
		toast_updating_cidr: "⏳ Updating ipset...",
		toast_cidr_updated: "✅ CIDR updated",
		toast_ip_pass_required: "❌ IP and password required",
		toast_deploying_tunnel: "⏳ Deploying tunnel...",
		toast_tunnel_deployed: "✅ Tunnel deployed",
		toast_restoring: "⏳ Restoring...",
		toast_restored: "✅ Restored",
		toast_link_added: "✅ Link added",
		toast_link_removed: "✅ Link removed",
		toast_resolve_error: "❌ Could not resolve domain",
		toast_resolving: "⏳ Resolving domain...",
		toast_resolved: "✅ Domain resolved",
		confirm_delete_forever: "Permanently delete {name}?",
		confirm_revoke: "Revoke certificate for {name}?",
		confirm_setup_tunnel: "Setup tunnel on remote server?",
		confirm_restore: "Overwrite current configuration?",
		config_load_error: "Failed to load config",
		card_admin: "🔐 Account & Panel",
		card_admin_desc: "Login security and panel network settings",
		label_admin_login: "Admin login",
		label_admin_pass: "New password",
		label_panel_port: "Panel port",
		card_modules: "🎛️ Modules & Features",
		card_modules_desc: "Interface element visibility",
		label_speed_monitor: "📈 Speed Monitor",
		label_speed_monitor_desc: "Live speed charts",
		label_hw_bar: "💻 Hardware Bar",
		label_hw_bar_desc: "CPU / RAM / Disk / Ping",
		label_torrent_block: "🚫 Block BitTorrent",
		label_torrent_block_desc: "iptables string match",
		card_service: "🛠️ Services & Management",
		card_service_desc: "Apply settings and manage daemon",
		btn_save_all: "💾 Save settings",
		btn_save_apply: "🚀 Save & Restart",
		label_ovpn_service: "OpenVPN daemon",
		btn_restart: "🔄 Restart",
		btn_start: "▶️ Start",
		btn_stop: "⏹️ Stop",
		remote_title_inline: "🔗 Remote Exit Node",
		remote_connected_to: "Connected to:",
		btn_reconfigure: "Reconfigure",
		adblock_title: "🛡️ Ad Blocking (DNS AdBlock)",
		adblock_desc: "Automatic ad and tracker filtering at server level with zero lag",
		adblock_enable: "Enable ad blocking for all clients",
		adblock_add_list: "📋 Add AdList URL",
		adblock_add_domain: "🌐 Add custom domain",
		adblock_black: "⚫ Blacklist",
		adblock_white: "⚪ Whitelist",
		adblock_to_black: "⚫ To blacklist",
		adblock_to_white: "⚪ To whitelist",
		btn_add: "➕ Add",
		config_title: "⚙️ Direct server.conf editor",
		btn_reread: "🔄 Reload",
		btn_save_restart: "💾 Save & Restart",
		split_details_summary: "🔗 Split Tunnel Link Management",
		split_details_desc: "Resolve URL to IP for selective routing via WireGuard or direct."
	}
};

let currentTheme = localStorage.getItem("ovpn_theme") || "dark";

function applyTheme(theme) {
	currentTheme = theme;
	localStorage.setItem("ovpn_theme", theme);
	document.documentElement.setAttribute("data-theme", theme);
	const icon = document.getElementById("themeToggleIcon");
	if (icon) icon.textContent = theme === "light" ? "🌙" : "☀️";
}

function toggleTheme() {
	applyTheme(currentTheme === "light" ? "dark" : "light");
}
applyTheme(currentTheme);

let currentLang = localStorage.getItem("ovpn_lang") || "ru";
let panelConfig = {
	enable_speed_monitor: "1",
	enable_hardware_bar: "1"
};

function t(key, params = {}) {
	let str = (i18n[currentLang] && i18n[currentLang][key]) || i18n.ru[key] || key;
	for (const k in params) {
		str = str.replace(`{${k}}`, params[k]);
	}
	return str;
}

function setLanguage(lang) {
	currentLang = lang;
	localStorage.setItem("ovpn_lang", lang);
	document.documentElement.lang = lang;
	const langSelect = document.getElementById("langSelect");
	if (langSelect) langSelect.value = lang;

	document.querySelectorAll("[data-i18n]").forEach(el => {
		const key = el.getAttribute("data-i18n");
		el.textContent = t(key);
	});
	document.querySelectorAll("[data-i18n-placeholder]").forEach(el => {
		const key = el.getAttribute("data-i18n-placeholder");
		el.placeholder = t(key);
	});

	updateServerBannerText();
	syncChartUserDropdown();
	applyClientFilter();
	if (document.getElementById('tab-routing')?.classList.contains('active')) {
		loadAdblockStatus();
	}
}
function changeLanguage(lang) { setLanguage(lang); }

function showToast(msg, type = 'success') {
	const box = document.getElementById('toastBox');
	box.textContent = msg;
	box.className = `toast ${type} show`;
	clearTimeout(box._t);
	box._t = setTimeout(() => box.classList.remove('show'), 3200);
}

// Универсальное копирование (работает на HTTP и IP без SSL)
function copyToClipboard(text) {
	if (navigator.clipboard && window.isSecureContext) {
		return navigator.clipboard.writeText(text);
	} else {
		const textArea = document.createElement("textarea");
		textArea.value = text;
		textArea.style.position = "fixed";
		textArea.style.left = "-999999px";
		textArea.style.top = "-999999px";
		document.body.appendChild(textArea);
		textArea.focus();
		textArea.select();
		return new Promise((resolve, reject) => {
			document.execCommand('copy') ? resolve() : reject();
			textArea.remove();
		});
	}
}

function applyDynamicFeatureVisibility() {
	const hwBar = document.getElementById('hardwareBar');
	if (hwBar) hwBar.style.display = panelConfig.enable_hardware_bar === "1" ? 'grid' : 'none';

	const tabSpeed = document.getElementById('tabBtnSpeed');
	if (tabSpeed) tabSpeed.style.display = panelConfig.enable_speed_monitor === "1" ? 'block' : 'none';

	if (panelConfig.ovpn_domain && panelConfig.ovpn_port) {
		const codeEl = document.getElementById('bannerEndpointCode');
		if (codeEl) codeEl.textContent = `${panelConfig.ovpn_domain}:${panelConfig.ovpn_port} (${panelConfig.ovpn_proto || 'udp'})`;
	}
	applyClientFilter();
}

function switchTab(tabId) {
	document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
	document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
	const btn = document.querySelector(`[onclick="switchTab('${tabId}')"]`);
	if (btn) btn.classList.add('active');
	document.getElementById(tabId).classList.add('active');

	if (tabId === 'tab-config') loadConfigView();
	if (tabId === 'tab-routing') loadRoutingView();
	if (tabId === 'tab-settings') loadSettingsView();
	if (tabId === 'tab-speed') {
		if (speedChart) speedChart.resize();
		fetchHistoryAndSync();
	}
}

function openCreateModal() {
	document.getElementById('createModal').classList.add('active');
	document.getElementById('newClientName').value = '';
	document.getElementById('newClientNote').value = '';
	document.getElementById('newClientTtl').value = '0';
	setTimeout(() => document.getElementById('newClientName').focus(), 100);
}
function openBackupModal() { document.getElementById('backupModal').classList.add('active'); }
function closeModals() {
	document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active'));
}

document.querySelectorAll('.modal-overlay').forEach(m => {
	m.addEventListener('click', e => { if (e.target === m) closeModals(); });
});
document.addEventListener('keydown', e => {
	if (e.key === 'Escape') closeModals();
	if (e.key === 'Enter' && document.getElementById('createModal').classList.contains('active')) submitCreateClient();
});

function formatSpeed(bytesPerSec) {
	if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
	const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
	let i = 0, val = bytesPerSec;
	while (val >= 1024 && i < units.length - 1) { val /= 1024; i++; }
	return val.toFixed(1) + ' ' + units[i];
}

async function pollSystemStats() {
	if (document.hidden || panelConfig.enable_hardware_bar !== "1") return;
	try {
		const res = await fetch('/api/system/stats');
		if (!res.ok) return;
		const data = await res.json();
		const s = data.stats;
		if (!s) return;

		document.getElementById('hwCpu').textContent = `${s.cpu}%`;
		document.getElementById('hwRam').textContent = `${s.ram_used} / ${s.ram_total} MB`;
		document.getElementById('hwDisk').textContent = `${s.disk_used} / ${s.disk_total} GB`;
		document.getElementById('hwPing').textContent = s.wg_ping;
	} catch (e) {}
}

let speedChart = null;
let selectedWindowSeconds = 30;
let speedPollTimer = null;
let clientColorRegistry = {};
const colorPalette = [
	'#3b82f6', '#10b981', '#f43f5e', '#f59e0b', '#8b5cf6',
	'#06b6d4', '#ec4899', '#84cc16', '#6366f1', '#14b8a6',
	'#fb7185', '#38bdf8', '#a855f7', '#4ade80', '#fbbf24'
];
let paletteIdx = 0;
let speedDataPoints = [];
let latestLiveSpeeds = {};
let chartFilterDirty = false;
let pendingLinks = [];

function getColorForClient(name) {
	if (!clientColorRegistry[name]) {
		clientColorRegistry[name] = colorPalette[paletteIdx % colorPalette.length];
		paletteIdx++;
	}
	return clientColorRegistry[name];
}

function setWindowTime(seconds) {
	selectedWindowSeconds = seconds;
	document.querySelectorAll('.btn-group-btn').forEach(b => b.classList.remove('active'));
	if (seconds === 30) document.getElementById('btnWin30').classList.add('active');
	if (seconds === 60) document.getElementById('btnWin60').classList.add('active');
	if (seconds === 300) document.getElementById('btnWin300').classList.add('active');
	fetchHistoryAndSync();
}

function initSpeedChart() {
	const ctx = document.getElementById('speedChartCanvas').getContext('2d');
	const isMobile = window.innerWidth <= 768;

	speedChart = new Chart(ctx, {
		type: 'line',
		data: { labels: [], datasets: [] },
		options: {
			responsive: true,
			maintainAspectRatio: false,
			animation: false,
			interaction: { mode: 'nearest', intersect: false },
			plugins: {
				legend: { display: false },
				tooltip: {
					backgroundColor: 'rgba(15, 23, 42, 0.95)',
					titleColor: '#f8fafc',
					bodyColor: '#cbd5e1',
					borderColor: '#334155',
					borderWidth: 1,
					padding: isMobile ? 8 : 12,
					boxPadding: 4,
					filter: item => item.parsed.y > 0 || !isMobile,
					callbacks: {
						label: ctx => ` ${ctx.dataset.label}: ${formatSpeed(ctx.parsed.y)}`
					}
				}
			},
			scales: {
				x: {
					grid: { color: 'rgba(148, 163, 184, 0.08)' },
					ticks: { color: '#64748b', font: { size: isMobile ? 10 : 11 }, maxTicksLimit: isMobile ? 5 : 10 }
				},
				y: {
					beginAtZero: true,
					grid: { color: 'rgba(148, 163, 184, 0.08)' },
					ticks: { color: '#64748b', font: { size: isMobile ? 10 : 11 }, callback: v => formatSpeed(v) }
				}
			}
		}
	});
}

async function fetchHistoryAndSync() {
	try {
		const res = await fetch(`/api/clients/speeds/history?seconds=${selectedWindowSeconds}`);
		if (!res.ok) return;
		const data = await res.json();
		if (data.history) {
			speedDataPoints = data.history;
			renderChartData();
		}
	} catch (e) {}
}

async function pollSpeedTick() {
	if (document.hidden) return;
	try {
		const res = await fetch('/api/clients/speeds');
		if (!res.ok) return;
		const data = await res.json();
		if (!data.speeds) return;

		latestLiveSpeeds = data.speeds;

		const nowTs = Date.now() / 1000;
		speedDataPoints.push({
			time: data.timestamp || new Date().toLocaleTimeString(),
			ts: nowTs,
			speeds: data.speeds
		});

		const minTs = nowTs - selectedWindowSeconds;
		speedDataPoints = speedDataPoints.filter(p => p.ts >= minTs);

		let totDown = 0, totUp = 0;
		for (const c in data.speeds) {
			totDown += (data.speeds[c].down || 0);
			totUp += (data.speeds[c].up || 0);
		}
		document.getElementById('liveTotalDown').textContent = formatSpeed(totDown);
		document.getElementById('liveTotalUp').textContent = formatSpeed(totUp);
		const onlineCount = Object.keys(data.speeds).length;
		document.getElementById('liveActiveCount').textContent = onlineCount;

		const validTotal = allClientsList.filter(c => c.status === 'valid').length;
		if (validTotal > 0) {
			document.getElementById('activeClientsCount').textContent = `${onlineCount} / ${validTotal}`;
		}

		if (!chartFilterDirty) {
			syncChartUserDropdown();
		}
		updateClientCardsRealtime(data.speeds);

		if (document.getElementById('tab-speed').classList.contains('active')) {
			renderChartData();
		}
	} catch (e) {}
}

function syncChartUserDropdown() {
	const sel = document.getElementById('chartClientFilter');
	const currentVal = sel.value || '__ALL__';

	const namesSet = new Set();
	allClientsList.forEach(c => {
		if (c.status === 'valid') namesSet.add(c.name);
	});
	Object.keys(latestLiveSpeeds).forEach(name => namesSet.add(name));

	const sortedNames = Array.from(namesSet).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));

	const existingOptions = Array.from(sel.options).map(o => o.value);
	const newOptions = ['__ALL__', ...sortedNames];

	if (existingOptions.length === newOptions.length && existingOptions.every((v, i) => v === newOptions[i])) {
		return;
	}

	let html = `<option value="__ALL__">${t('chart_all_users')}</option>`;
	sortedNames.forEach(name => {
		const isOnline = Boolean(latestLiveSpeeds[name]);
		const prefix = isOnline ? '🟢 ' : '';
		const selectedAttr = (name === currentVal) ? ' selected' : '';
		html += `<option value="${name}"${selectedAttr}>${prefix}${name}</option>`;
	});

	sel.innerHTML = html;
	if (currentVal !== '__ALL__' && !namesSet.has(currentVal)) {
		sel.value = '__ALL__';
	} else {
		sel.value = currentVal;
	}
}

function updateClientCardsRealtime(speedsMap) {
	allClientsList.forEach(c => {
		const live = speedsMap[c.name];
		c.is_online = Boolean(live && !c.is_paused);
		if (live && !c.is_paused) {
			c.speed_down = live.down || 0;
			c.speed_up = live.up || 0;
			c.speed_down_fmt = live.down_fmt || '0 B/s';
			c.speed_up_fmt = live.up_fmt || '0 B/s';
			if (live.real_ip) c.real_ip = live.real_ip;
			if (live.virt_ip) c.virt_ip = live.virt_ip;
		} else {
			c.speed_down = 0;
			c.speed_up = 0;
			c.speed_down_fmt = '0 B/s';
			c.speed_up_fmt = '0 B/s';
		}

		const cardEl = document.getElementById(`client-card-${c.name}`);
		if (!cardEl) return;

		cardEl.classList.toggle('online-card', c.is_online);
		cardEl.classList.toggle('paused-card', c.is_paused);

		const statusEl = document.getElementById(`card-online-${c.name}`);
		if (statusEl) {
			if (c.is_paused) {
				statusEl.innerHTML = `<span style="color:var(--warning); font-weight:600;">${t('badge_paused')}</span>`;
			} else {
				statusEl.innerHTML = c.is_online
					? `<span style="color:var(--success); font-weight:600;">${t('badge_online')}</span>`
					: `<span style="color:var(--text-muted);">${t('badge_offline')}</span>`;
			}
		}

		const metaEl = document.getElementById(`card-meta-${c.name}`);
		if (metaEl) {
			metaEl.className = `session-meta ${c.is_online ? '' : 'offline-meta'}`;
		}

		const ipEl = document.getElementById(`card-ip-${c.name}`);
		if (ipEl) ipEl.textContent = c.is_online ? c.real_ip : '—';

		const tunEl = document.getElementById(`card-tun-${c.name}`);
		if (tunEl) tunEl.textContent = c.is_online ? c.virt_ip : '—';

		const downEl = document.getElementById(`card-down-${c.name}`);
		if (downEl) {
			downEl.textContent = `↓ ${c.speed_down_fmt}`;
			downEl.style.color = c.is_online ? '#60a5fa' : 'var(--text-muted)';
		}

		const upEl = document.getElementById(`card-up-${c.name}`);
		if (upEl) {
			upEl.textContent = `↑ ${c.speed_up_fmt}`;
			upEl.style.color = c.is_online ? '#34d399' : 'var(--text-muted)';
		}
	});
}

function renderChartData() {
	if (!speedChart) return;
	const metric = document.getElementById('chartMetricType').value;
	const targetClient = document.getElementById('chartClientFilter').value;
	const isMobile = window.innerWidth <= 768;

	const labels = speedDataPoints.map(p => p.time);
	const clientNames = new Set();

	speedDataPoints.forEach(p => {
		Object.keys(p.speeds).forEach(c => {
			if (targetClient === '__ALL__' || targetClient === c) {
				clientNames.add(c);
			}
		});
	});

	const datasets = [];
	Array.from(clientNames).sort((a, b) => a.localeCompare(b)).forEach(client => {
		const color = getColorForClient(client);
		const points = speedDataPoints.map(p => {
			const item = p.speeds[client];
			if (!item) return 0;
			if (metric === 'down') return item.down || 0;
			if (metric === 'up') return item.up || 0;
			return item.total || 0;
		});

		datasets.push({
			label: client,
			data: points,
			borderColor: color,
			backgroundColor: color + '15',
			fill: targetClient !== '__ALL__',
			borderWidth: isMobile ? 1.5 : 2,
			tension: 0.25,
			pointRadius: 0
		});
	});

	speedChart.data.labels = labels;
	speedChart.data.datasets = datasets;
	speedChart.update('none');
}

function changePollInterval() {
	const ms = parseInt(document.getElementById('chartPollInterval').value) || 1000;
	if (speedPollTimer) clearInterval(speedPollTimer);
	speedPollTimer = setInterval(pollSpeedTick, ms);
	pollSpeedTick();
}

let allClientsList = [];
let lastServerState = 'active';
let currentPage = 1;
let pageSize = parseInt(localStorage.getItem('ovpn_page_size')) || 20;

function updateServerBannerText() {
	const statusEl = document.getElementById('serverStatusText');
	if (!statusEl) return;
	if (lastServerState === 'active') {
		statusEl.textContent = t('server_active');
		statusEl.className = 'status-badge active';
	} else {
		statusEl.textContent = t('server_stopped');
		statusEl.className = 'status-badge inactive';
	}
}

async function loadClients() {
	if (document.hidden) return;
	try {
		const res = await fetch('/api/clients');
		if (res.status === 401) { location.href = '/login'; return; }
		const data = await res.json();
		allClientsList = data.clients || [];

		lastServerState = data.server?.status === 'active' ? 'active' : 'inactive';
		if (data.server?.domain && data.server?.port) {
			document.getElementById('bannerEndpointCode').textContent = `${data.server.domain}:${data.server.port} (${data.server.proto || 'udp'})`;
		}
		updateServerBannerText();

		const validTotal = allClientsList.filter(c => c.status === 'valid').length;
		const online = allClientsList.filter(c => c.is_online).length;
		document.getElementById('activeClientsCount').textContent = `${online} / ${validTotal}`;
		document.getElementById('lastSyncTime').textContent = `${t('updated_at')} ${new Date().toLocaleTimeString()}`;

		if (!chartFilterDirty) {
			syncChartUserDropdown();
		}

		const isModalActive = document.querySelector('.modal-overlay.active') !== null;
		if (!isModalActive) {
			applyClientFilter();
		}
	} catch (e) {}
}

function onFilterInputChange() {
	const input = document.getElementById('clientSearch');
	const clearBtn = document.getElementById('clearSearchBtn');
	if (clearBtn && input) {
		clearBtn.style.display = input.value.length > 0 ? 'inline-flex' : 'none';
	}
	currentPage = 1;
	applyClientFilter();
}

function clearClientSearch() {
	const input = document.getElementById('clientSearch');
	const clearBtn = document.getElementById('clearSearchBtn');
	if (input) {
		input.value = '';
		input.focus();
	}
	if (clearBtn) {
		clearBtn.style.display = 'none';
	}
	currentPage = 1;
	applyClientFilter();
}

function onPageSizeChange() {
	pageSize = parseInt(document.getElementById('pageSizeSelect').value) || 20;
	localStorage.setItem('ovpn_page_size', pageSize);
	currentPage = 1;
	applyClientFilter();
}

function goToPage(page) {
	currentPage = page;
	applyClientFilter();
	window.scrollTo({ top: 0, behavior: 'smooth' });
}

function applyClientFilter() {
	const query = document.getElementById('clientSearch').value.toLowerCase().trim();
	const statusMode = document.getElementById('statusFilter').value;
	const sortMode = document.getElementById('sortFilter').value;

	let filtered = allClientsList.filter(c => {
		const matchName = c.name.toLowerCase().includes(query) ||
			(c.note && c.note.toLowerCase().includes(query)) ||
			(c.real_ip && c.real_ip.toLowerCase().includes(query)) ||
			(c.virt_ip && c.virt_ip.toLowerCase().includes(query));

		if (!matchName) return false;
		if (statusMode === 'revoked') return c.status === 'revoked';
		if (c.status === 'revoked') return false;
		if (statusMode === 'paused') return c.is_paused;
		if (statusMode === 'online') return c.is_online;
		if (statusMode === 'offline') return !c.is_online && !c.is_paused;
		return true;
	});

	filtered.sort((a, b) => {
		if (sortMode === 'online_first') {
			if (a.is_online !== b.is_online) return a.is_online ? -1 : 1;
			return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
		}
		if (sortMode === 'name_asc') return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
		return 0;
	});

	const totalItems = filtered.length;
	const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
	if (currentPage > totalPages) currentPage = totalPages;
	if (currentPage < 1) currentPage = 1;

	const startIdx = (currentPage - 1) * pageSize;
	const pageSlice = filtered.slice(startIdx, startIdx + pageSize);

	renderClientsGrid(pageSlice);
	renderPagination(totalItems, startIdx, pageSlice.length, totalPages);
}

function renderPagination(totalItems, startIdx, countOnPage, totalPages) {
	const bar = document.getElementById('paginationBar');
	const info = document.getElementById('paginationInfo');
	const pagesBox = document.getElementById('paginationPages');

	if (totalItems === 0) {
		bar.style.display = 'none';
		return;
	}
	bar.style.display = 'flex';
	info.textContent = t('pagination_showing', {
		from: startIdx + 1,
		to: startIdx + countOnPage,
		total: totalItems
	});

	let btnsHtml = `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>«</button>`;

	for (let p = 1; p <= totalPages; p++) {
		if (p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2) {
			btnsHtml += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
		} else if (Math.abs(p - currentPage) === 3) {
			btnsHtml += `<span style="padding: 8px 4px; color: var(--text-muted);">…</span>`;
		}
	}

	btnsHtml += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>»</button>`;
	pagesBox.innerHTML = btnsHtml;
}

function renderClientsGrid(clients) {
	const grid = document.getElementById('clientsGrid');
	if (!clients || clients.length === 0) {
		grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 60px 20px; color:var(--text-muted); font-size:14px;">${t('empty_clients_list')}</div>`;
		return;
	}

	const speedOn = panelConfig.enable_speed_monitor === "1";

	let html = '';
	clients.forEach(c => {
		const isOnline = c.is_online;
		const isPaused = c.is_paused;

		let onlineHtml = '';
		if (isPaused) {
			onlineHtml = `<span style="color:var(--warning); font-weight:600;">${t('badge_paused')}</span>`;
		} else {
			onlineHtml = isOnline
				? `<span style="color:var(--success); font-weight:600;">${t('badge_online')}</span>`
				: `<span style="color:var(--text-muted);">${t('badge_offline')}</span>`;
		}

		let statusLabel = t('badge_valid');
		let badgeClass = 'valid';
		if (c.status === 'revoked') {
			statusLabel = t('badge_revoked');
			badgeClass = 'revoked';
		} else if (isPaused) {
			statusLabel = t('badge_paused');
			badgeClass = 'paused';
		}

		const downColor = isOnline ? '#60a5fa' : 'var(--text-muted)';
		const upColor = isOnline ? '#34d399' : 'var(--text-muted)';
		const noteHtml = c.note ? `<div class="client-note" title="${c.note}">💬 ${c.note}</div>` : '';

		const speedRowHtml = speedOn ? `
			<div class="live-speed-row">
				<span id="card-down-${c.name}" style="color:${downColor};">↓ ${c.speed_down_fmt || '0 B/s'}</span>
				<span id="card-up-${c.name}" style="color:${upColor};">↑ ${c.speed_up_fmt || '0 B/s'}</span>
			</div>
		` : '';

		let actionsHtml = '';
		if (c.status === 'valid') {
			actionsHtml = `
				<button class="btn btn-sm" onclick='showQrModal("${c.name}", "${c.share_token}")' title="${t('title_qr')}">📱</button>
				<button class="btn btn-sm" onclick='copyShareUrl("${c.share_token}")'>${t('btn_link')}</button>
				<button class="btn btn-sm btn-primary" onclick='downloadClientConfig("${c.name}")' title="${t('btn_config')}">${t('btn_config')}</button>
				<button class="btn btn-sm ${isPaused ? 'btn-primary' : 'btn-warning'}" onclick='togglePauseClient("${c.name}")'>${isPaused ? t('btn_resume') : t('btn_pause')}</button>
				<button class="btn btn-sm btn-danger" onclick='revokeClient("${c.name}", false)' title="${t('title_revoke')}">🚫</button>
			`;
		} else {
			actionsHtml = `
				<button class="btn btn-sm btn-danger" onclick='revokeClient("${c.name}", true)'>${t('btn_delete_forever')}</button>
			`;
		}

		html += `
			<div class="client-card ${isOnline ? 'online-card' : ''} ${isPaused ? 'paused-card' : ''}" id="client-card-${c.name}">
				<div>
					<div class="card-top">
						<div class="client-name">${c.name}</div>
						<div class="client-badge ${badgeClass}">${statusLabel}</div>
					</div>
					${noteHtml}
					<div class="card-details">
						<div style="display:flex; justify-content:space-between; margin-bottom:6px; gap:8px;">
							<span id="card-online-${c.name}">${onlineHtml}</span>
							<span style="font-size:11px;">${c.created} → ${c.expires}</span>
						</div>
						<div class="session-meta ${isOnline ? '' : 'offline-meta'}" id="card-meta-${c.name}">
							<div class="session-row">
								<span>🌐 <strong id="card-ip-${c.name}">${isOnline ? c.real_ip : '—'}</strong></span>
								<span>TUN: <strong id="card-tun-${c.name}">${isOnline ? c.virt_ip : '—'}</strong></span>
							</div>
							${speedRowHtml}
						</div>
					</div>
				</div>
				<div class="card-actions">${actionsHtml}</div>
			</div>
		`;
	});
	grid.innerHTML = html;
}



function showQrModal(name, token) {
	if (!token) return;
	const link = `${location.origin}/d/${encodeURIComponent(token)}`;
	document.getElementById('qrModalTitle').textContent = `📱 ${name}`;
	new QRious({
		element: document.getElementById('qrCanvas'),
		value: link,
		size: 220,
		level: 'M'
	});
	document.getElementById('qrCopyBtn').onclick = () => {
		copyToClipboard(link).then(() => showToast(t('toast_link_copied'))).catch(() => showToast('Ошибка копирования', 'error'));
	};
	document.getElementById('qrModal').classList.add('active');
}

async function submitCreateClient() {
	const name = document.getElementById('newClientName').value.trim();
	const note = document.getElementById('newClientNote').value.trim();
	const ttl_days = parseInt(document.getElementById('newClientTtl').value) || 0;

	if (!name) return;
	closeModals();
	showToast(t('toast_generating_keys'));
	try {
		const res = await fetch('/api/clients', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ name, note, ttl_days })
		});
		const d = await res.json();
		if (d.success) {
			showToast(t('toast_client_created'));
			await loadClients();
			setTimeout(() => downloadClientConfig(name), 300);
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function togglePauseClient(name) {
	try {
		const res = await fetch(`/api/clients/${encodeURIComponent(name)}/pause`, { method: 'POST' });
		const d = await res.json();
		if (d.success) {
			showToast(d.is_paused ? '⏸️ Paused' : '▶️ Resumed');
			loadClients();
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function revokeClient(name, permanent = false) {
	const msg = permanent ? t('confirm_delete_forever', { name }) : t('confirm_revoke', { name });
	if (!confirm(msg)) return;
	try {
		const res = await fetch(`/api/clients/${encodeURIComponent(name)}?permanent=${permanent}`, { method: 'DELETE' });
		const d = await res.json();
		if (d.success) {
			showToast(permanent ? t('toast_client_deleted') : t('toast_cert_revoked'));
			loadClients();
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

function downloadClientConfig(name) {
	location.href = `/api/clients/${encodeURIComponent(name)}/download`;
}

function copyShareUrl(token) {
	if (!token) return;
	const link = `${location.origin}/d/${encodeURIComponent(token)}`;
	copyToClipboard(link).then(() => showToast(t('toast_link_copied'))).catch(() => showToast('Ошибка копирования', 'error'));
}

async function loadRoutingView() {
	try {
		const res = await fetch('/api/routing/status');
		const d = await res.json();
		document.getElementById('ipsetSubnetsCount').textContent = d.ipset_count;
		document.getElementById('cidrUrlInput').value = d.cidr_url || '';
		document.getElementById('customCidrsInput').value = d.custom_cidrs || '';
		document.getElementById('routingModeSelect').value = d.routing_mode;
		document.getElementById('wgText').textContent = d.wg_up ? t('wg_active') : t('wg_inactive');
		document.getElementById('wgText').style.color = d.wg_up ? 'var(--success)' : 'var(--danger)';
		document.getElementById('torrentBlockCheck').checked = Boolean(d.torrent_block);

		if (d.wg_endpoint) {
			document.getElementById('remoteEndpointConnected').style.display = 'block';
			document.getElementById('remoteEndpointForm').style.display = 'none';
			document.getElementById('remoteEndpointIp').textContent = d.wg_endpoint;
			document.getElementById('remoteEndpointStatus').textContent = '🟢 ' + (d.wg_up ? 'Подключено' : 'Не активно');
			document.getElementById('remoteEndpointStatus').style.background = d.wg_up ? 'rgba(16,185,129,0.15)' : 'rgba(245,158,11,0.15)';
			document.getElementById('remoteEndpointStatus').style.color = d.wg_up ? '#34d399' : '#fbbf24';
		} else {
			document.getElementById('remoteEndpointConnected').style.display = 'none';
			document.getElementById('remoteEndpointForm').style.display = 'block';
			document.getElementById('remoteEndpointStatus').textContent = '⚪ Не настроено';
			document.getElementById('remoteEndpointStatus').style.background = 'rgba(100,116,139,0.15)';
			document.getElementById('remoteEndpointStatus').style.color = '#94a3b8';
		}

		await loadSplitLinks();
		await loadAdblockStatus();
		renderPendingLinks(); 
	} catch (e) {}
}

function showRemoteReconfigure() {
    document.getElementById('remoteEndpointConnected').style.display = 'none';
    document.getElementById('remoteEndpointForm').style.display = 'block';
    document.getElementById('remoteServerPass').value = '';
}

function hideRemoteReconfigure() {
    document.getElementById('remoteEndpointForm').style.display = 'none';
    document.getElementById('remoteEndpointConnected').style.display = 'block';
    document.getElementById('remoteServerPass').value = '';
}

function renderPendingLinks() {
	const box = document.getElementById('pendingLinksBox');
	if (pendingLinks.length === 0) {
		box.innerHTML = '';
		return;
	}
	box.innerHTML = pendingLinks.map((p, idx) => `
		<div class="pending-link-row" style="${p.has_conflict ? 'border-color: #f59e0b; background: rgba(245,158,11,0.08);' : ''}">
			<div class="pending-url">🔗 ${p.url}</div>
			<div class="pending-ips">IP: ${p.ips.length ? p.ips.join(', ') : '—'}</div>
			${p.has_conflict ? `
				<div style="font-size:12px; color:#fbbf24; font-weight:600;">
					⚠️ Внимание: IP сайта найдены в текущем списке CIDR (${p.conflict_ips.join(', ')}). Куда направить трафик для этого сайта?
				</div>
			` : ''}
			<div class="pending-actions">
				<div class="route-via-group">
					<button class="route-via-btn ${p.route_via === 'split' ? 'active' : ''}" onclick="setPendingRoute(${idx}, 'split')">${t('route_via_split')}</button>
					<button class="route-via-btn ${p.route_via === 'wg' ? 'active' : ''}" onclick="setPendingRoute(${idx}, 'wg')">${t('route_via_wg')}</button>
				</div>
				<button class="btn btn-sm btn-primary" onclick="savePendingLink(${idx})">${t('btn_save_link')}</button>
				<button class="btn btn-sm btn-danger" onclick="cancelPendingLink(${idx})">${t('btn_cancel_link')}</button>
			</div>
		</div>
	`).join('');
}

function setPendingRoute(idx, route) {
	if (!pendingLinks[idx]) return;
	pendingLinks[idx].route_via = route;
	renderPendingLinks();
}

function cancelPendingLink(idx) {
	pendingLinks.splice(idx, 1);
	renderPendingLinks();
}

async function savePendingLink(idx) {
	const p = pendingLinks[idx];
	if (!p) return;
	try {
		const res = await fetch('/api/routing/save-link', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				url: p.url,
				resolved_ips: (p.ips || []).join(','),
				route_via: p.route_via
			})
		});
		const d = await res.json();
		if (d.success) {
			pendingLinks.splice(idx, 1);
			renderPendingLinks();
			showToast(t('toast_link_added'));
			loadSplitLinks();
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function loadSplitLinks() {
	try {
		const res = await fetch('/api/routing/links');
		const d = await res.json();
		const box = document.getElementById('splitLinksList');
		if (!d.links || d.links.length === 0) {
			box.innerHTML = `<div style="text-align:center; padding:30px; color:var(--text-muted); font-size:13px;">Записей нет</div>`;
			return;
		}
		box.innerHTML = d.links.map(link => `
			<div class="domain-row" style="flex-direction:column; align-items:stretch; gap:4px;">
				<div style="display:flex; justify-content:space-between; gap:10px; align-items:center;">
					<span class="domain-name" style="flex:1;">${link.url}</span>
					<span style="font-size:10.5px; padding:2px 8px; border-radius:10px; font-weight:600; font-family:'JetBrains Mono',monospace;
						${link.route_via === 'wg' ? 'background:rgba(139,92,246,0.15);color:#a78bfa;' : 'background:rgba(245,158,11,0.15);color:#fbbf24;'}">
						${link.route_via === 'wg' ? 'WG' : 'DIRECT'}
					</span>
					<button class="btn btn-sm btn-danger" style="padding:4px 8px;" onclick="removeSplitLink(${link.id})">✕</button>
				</div>
				<div style="font-size:11px; color:var(--text-muted); font-family:'JetBrains Mono',monospace; word-break:break-all;">
					${link.resolved_ip || '—'}
				</div>
			</div>
		`).join('');
	} catch (e) {}
}

async function removeSplitLink(id) {
	try {
		await fetch(`/api/routing/links/${id}`, { method: 'DELETE' });
		showToast(t('toast_link_removed'));
		loadSplitLinks();
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function resolveLink() {
	const url = document.getElementById('splitLinkUrl').value.trim();
	if (!url) return;
	showToast(t('toast_resolving'));
	try {
		const res = await fetch('/api/routing/resolve-link', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url })
		});
		const d = await res.json();
		if (!d.success) {
			showToast(t('toast_resolve_error'), 'error');
			return;
		}
		pendingLinks.push({
			url: d.url || url,
			hostname: d.hostname || '',
			ips: d.ips || [],
			has_conflict: Boolean(d.has_conflict),
			conflict_ips: d.conflict_ips || [],
			route_via: d.has_conflict ? 'wg' : 'split'
		});
		document.getElementById('splitLinkUrl').value = '';
		renderPendingLinks();
		showToast(t('toast_resolved'));
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function loadSettingsView() {
	try {
		const res = await fetch('/api/settings');
		const d = await res.json();
		if (d.success && d.settings) {
			const s = d.settings;
			panelConfig = { ...panelConfig, ...s };
			applyDynamicFeatureVisibility();

			document.getElementById('setAdminLogin').value = s.admin_login || '';
			document.getElementById('setAdminPass').value = '';
			document.getElementById('setPanelPort').value = s.panel_port || 8080;
			document.getElementById('setOvpnDomain').value = s.ovpn_domain || '';

			document.getElementById('setEnableSpeed').checked = s.enable_speed_monitor !== "0";
			document.getElementById('setEnableHwBar').checked = s.enable_hardware_bar !== "0";
			document.getElementById('setTorrentBlock').checked = s.torrent_block === "1";
		}
	} catch (e) {}
}

async function loadAdblockStatus() {
	try {
		const res = await fetch('/api/adblock/status');
		const json = await res.json();
		if (!json.success) return;
		const d = json.data;

		const toggle = document.getElementById('adblockEnableToggle');
		if (toggle) toggle.checked = Boolean(d.enabled);

		const lbl = document.getElementById('adblockStatusLabel');
		if (lbl) {
			const stateTxt = d.enabled
				? (d.dnsmasq_active ? '🟢 АКТИВЕН' : '🟡 Ошибка службы dnsmasq')
				: '⚪ ОТКЛЮЧЕН';
			lbl.textContent = `Статус: ${stateTxt} | Правил: ${(d.blocked_total || 0).toLocaleString()} (DNS: ${d.dns_ip})`;
		}

		const listsBox = document.getElementById('adblockListsBox');
		if (listsBox) {
			if (!d.lists || d.lists.length === 0) {
				listsBox.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-size:12.5px;">Списки еще не добавлены</div>`;
			} else {
				listsBox.innerHTML = d.lists.map(item => `
					<div class="domain-row">
						<div style="min-width:0; flex:1;">
							<div class="domain-name" style="font-size:12px;">${item.url}</div>
							<div style="font-size:11px; color:var(--text-muted); margin-top:2px;">
								${item.list_type === 'white' ? '⚪ Белый список' : '⚫ Черный список'} • Доменов: <b>${(item.domains_count || 0).toLocaleString()}</b>
							</div>
						</div>
						<button class="btn btn-sm btn-danger" onclick="deleteAdblockList(${item.id})">✕</button>
					</div>
				`).join('');
			}
		}

		const domBox = document.getElementById('adblockDomainsBox');
		if (domBox) {
			if (!d.domains || d.domains.length === 0) {
				domBox.innerHTML = `<div style="text-align:center; padding:20px; color:var(--text-muted); font-size:12.5px;">Кастомных доменов нет</div>`;
			} else {
				domBox.innerHTML = d.domains.map(item => `
					<div class="domain-row">
						<span class="domain-name">${item.domain}</span>
						<div style="display:flex; align-items:center; gap:8px;">
							<span class="domain-count-badge" style="${item.list_type === 'white' ? 'background:rgba(16,185,129,0.15);color:#34d399;' : 'background:rgba(239,68,68,0.15);color:#f87171;'}">
								${item.list_type === 'white' ? 'WHITE' : 'BLACK'}
							</span>
							<button class="btn btn-sm btn-danger" onclick="deleteAdblockDomain(${item.id})">✕</button>
						</div>
					</div>
				`).join('');
			}
		}
	} catch (e) {}
}

async function toggleAdblock(enable) {
	showToast(enable ? '⏳ Включение блокировки и настройка dnsmasq...' : '⏳ Отключение блокировки...');
	try {
		const res = await fetch('/api/adblock/toggle', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ enable })
		});
		const d = await res.json();
		if (d.success) {
			showToast(enable ? '🛡️ Блокировка рекламы включена!' : '⏸️ Блокировка отключена');
			loadAdblockStatus();
		} else {
			document.getElementById('adblockEnableToggle').checked = !enable;
			showToast('❌ ' + (d.message || 'Ошибка'), 'error');
		}
	} catch (e) {
		document.getElementById('adblockEnableToggle').checked = !enable;
		showToast('❌ Ошибка сети', 'error');
	}
}

async function addAdblockList() {
	const url = document.getElementById('adblockListUrl').value.trim();
	const list_type = document.getElementById('adblockListType').value;
	if (!url) return;

	showToast('⏳ Загрузка списка...');
	try {
		const res = await fetch('/api/adblock/lists', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ url, list_type })
		});
		const d = await res.json();
		if (d.success) {
			document.getElementById('adblockListUrl').value = '';
			showToast('✅ ' + d.message);
			loadAdblockStatus();
		} else {
			showToast('❌ ' + (d.message || 'Ошибка'), 'error');
		}
	} catch (e) {
		showToast('❌ Ошибка сети', 'error');
	}
}

async function deleteAdblockList(id) {
	try {
		await fetch(`/api/adblock/lists/${id}`, { method: 'DELETE' });
		showToast('🗑️ Список удален');
		loadAdblockStatus();
	} catch (e) {
		showToast('❌ Ошибка сети', 'error');
	}
}

async function addAdblockDomain() {
	const domain = document.getElementById('adblockDomainInput').value.trim();
	const list_type = document.getElementById('adblockDomainType').value;
	if (!domain) return;

	try {
		const res = await fetch('/api/adblock/domains', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ domain, list_type })
		});
		const d = await res.json();
		if (d.success) {
			document.getElementById('adblockDomainInput').value = '';
			showToast('✅ ' + d.message);
			loadAdblockStatus();
		} else {
			showToast('❌ ' + (d.message || 'Ошибка'), 'error');
		}
	} catch (e) {
		showToast('❌ Ошибка сети', 'error');
	}
}

async function deleteAdblockDomain(id) {
	try {
		await fetch(`/api/adblock/domains/${id}`, { method: 'DELETE' });
		showToast('🗑️ Домен удален');
		loadAdblockStatus();
	} catch (e) {
		showToast('❌ Ошибка сети', 'error');
	}
}

async function saveAllAccountSettings(applyToOvpn = false) {
	const payload = {
		admin_login: document.getElementById('setAdminLogin').value.trim(),
		admin_password: document.getElementById('setAdminPass').value,
		panel_port: parseInt(document.getElementById('setPanelPort').value) || 8080,
		ovpn_domain: document.getElementById('setOvpnDomain').value.trim(),
		enable_speed_monitor: document.getElementById('setEnableSpeed').checked ? "1" : "0",
		enable_hardware_bar: document.getElementById('setEnableHwBar').checked ? "1" : "0",
		torrent_block: document.getElementById('setTorrentBlock').checked ? "1" : "0",
		apply_to_ovpn: Boolean(applyToOvpn)
	};
	
	showToast(t('toast_saving_routes'));
	try {
		const res = await fetch('/api/settings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify(payload)
		});
		const d = await res.json();
		if (d.success) {
			if (d.settings) {
				panelConfig = { ...panelConfig, ...d.settings };
				applyDynamicFeatureVisibility();
			}
			showToast('✅ Saved!');
			loadClients();
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) {
		showToast(t('toast_network_error'), 'error');
	}
}

async function controlOvpnService(action) {
	showToast(`⏳ ${action}...`);
	try {
		const res = await fetch(`/api/service/${action}`, { method: 'POST' });
		const d = await res.json();
		if (d.success) {
			showToast(`✅ ${action} OK`);
			setTimeout(loadClients, 1000);
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function saveRoutingSettings() {
	const url = document.getElementById('cidrUrlInput').value.trim();
	const custom_cidrs = document.getElementById('customCidrsInput').value.trim();
	const mode = document.getElementById('routingModeSelect').value;
	const torrent_block = document.getElementById('torrentBlockCheck').checked;

	showToast(t('toast_saving_routes'));
	try {
		const r = await fetch('/api/routing/settings', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				cidr_url: url,
				custom_cidrs: custom_cidrs,
				routing_mode: mode,
				torrent_block: torrent_block
			})
		});
		const d = await r.json();
		if (d.success) { showToast(t('toast_routes_saved')); loadRoutingView(); }
		else showToast('❌ ' + (d.message || 'Error'), 'error');
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function updateCidrIps() {
	showToast(t('toast_updating_cidr'));
	try {
		const r = await fetch('/api/routing/update_ips', { method: 'POST' });
		const d = await r.json();
		if (d.success) { showToast(t('toast_cidr_updated')); loadRoutingView(); }
		else showToast('❌ ' + (d.message || 'Error'), 'error');
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function setupRemoteTunnel() {
	const ip = document.getElementById('remoteServerIp').value.trim();
	const pass = document.getElementById('remoteServerPass').value;
	if (!ip || !pass) { showToast(t('toast_ip_pass_required'), 'error'); return; }
	if (!confirm(t('confirm_setup_tunnel'))) return;
	showToast(t('toast_deploying_tunnel'));
	try {
		const r = await fetch('/api/routing/setup', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ remote_ip: ip, remote_pass: pass })
		});
		const d = await r.json();
		if (d.success) { showToast(t('toast_tunnel_deployed')); pendingLinks = []; renderPendingLinks(); loadRoutingView(); }
		else showToast('❌ ' + (d.message || 'Error'), 'error');
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

async function loadConfigView() {
	try {
		const r = await fetch('/api/config');
		const d = await r.json();
		document.getElementById('serverConfigText').value = d.success ? d.config : t('config_load_error');
	} catch (e) {
		document.getElementById('serverConfigText').value = t('config_load_error');
	}
}

async function saveRawConfig(restart) {
	const config = document.getElementById('serverConfigText').value;
	showToast(t('toast_saving_routes'));
	try {
		const r = await fetch('/api/config', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({ config, restart })
		});
		const d = await r.json();
		if (d.success) {
			showToast('✅ server.conf saved & restarted!');
			loadClients();
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (e) { showToast(t('toast_network_error'), 'error'); }
}

function downloadBackupArchive() {
	location.href = '/api/backup';
	closeModals();
}

async function processRestoreFile(e) {
	const file = e.target.files[0];
	if (!file || !confirm(t('confirm_restore'))) return;
	closeModals();
	showToast(t('toast_restoring'));

	const formData = new FormData();
	formData.append('file', file);

	try {
		const res = await fetch('/api/restore', {
			method: 'POST',
			body: formData
		});
		const d = await res.json();
		if (d.success) {
			showToast(t('toast_restored'));
			setTimeout(() => location.reload(), 1500);
		} else {
			showToast('❌ ' + (d.message || 'Error'), 'error');
		}
	} catch (err) {
		showToast(t('toast_network_error'), 'error');
	}
}

document.addEventListener('DOMContentLoaded', async () => {
	document.getElementById('pageSizeSelect').value = String(pageSize);
	setLanguage(currentLang);
	initSpeedChart();

	const chartFilterEl = document.getElementById('chartClientFilter');
	chartFilterEl.addEventListener('mousedown', () => { chartFilterDirty = true; });
	chartFilterEl.addEventListener('touchstart', () => { chartFilterDirty = true; });
	chartFilterEl.addEventListener('focus', () => { chartFilterDirty = true; });
	chartFilterEl.addEventListener('blur', () => { setTimeout(() => { chartFilterDirty = false; }, 500); });

	await loadSettingsView();
	await loadClients();
	changePollInterval();
	pollSystemStats();
	setInterval(loadClients, 10000);
	setInterval(pollSystemStats, 5000);
});
</script>
</body>
</html>
"""

LANDING_HTML = """
<!DOCTYPE html>
<html lang="ru">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0">
	<title>OpenVPN Profile — {client_name}</title>
	<link rel="preconnect" href="https://fonts.googleapis.com">
	<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
	<script src="https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js"></script>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Plus Jakarta Sans', -apple-system, sans-serif;
			background: #090d16; color: #f1f5f9; min-height: 100vh; display: flex;
			justify-content: center; align-items: center; padding: 20px;
		}
		.background { position: fixed; inset: 0; overflow: hidden; pointer-events: none; }
		.blob {
			position: absolute; width: 600px; height: 600px; border-radius: 50%;
			background: radial-gradient(circle, rgba(59, 130, 246, 0.15), transparent 70%);
			top: -150px; left: 50%; transform: translateX(-50%);
		}
		.card {
			position: relative; width: 100%; max-width: 440px;
			background: rgba(17, 24, 39, 0.9); backdrop-filter: blur(16px);
			border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 24px;
			padding: 36px 30px; box-shadow: 0 25px 60px rgba(0, 0, 0, 0.7);
			text-align: center;
		}
		.logo {
			width: 64px; height: 64px; margin: 0 auto 18px; border-radius: 16px;
			background: linear-gradient(135deg, #3b82f6, #6366f1);
			display: flex; align-items: center; justify-content: center; font-size: 32px;
			box-shadow: 0 10px 25px rgba(59, 130, 246, 0.4);
		}
		h1 { font-size: 22px; font-weight: 700; margin-bottom: 6px; word-break: break-all; }
		p { font-size: 13.5px; color: #94a3b8; margin-bottom: 24px; }
		.qr-box {
			background: #fff; padding: 16px; border-radius: 20px; display: inline-block;
			margin-bottom: 24px; box-shadow: 0 10px 30px rgba(0,0,0,0.3);
		}
		.btn {
			width: 100%; padding: 14px; background: linear-gradient(135deg, #3b82f6, #2563eb);
			border: none; border-radius: 12px; color: #fff; font-size: 14px; font-weight: 600;
			cursor: pointer; transition: all .2s; box-shadow: 0 4px 15px rgba(37, 99, 235, 0.35);
			text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 8px;
			margin-bottom: 10px;
		}
		.btn:hover { opacity: .95; transform: translateY(-1px); }
		.btn-outline {
			background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1);
			box-shadow: none; color: #f8fafc;
		}
		.btn-outline:hover { background: rgba(51, 65, 85, 0.8); }
		.notice {
			font-size: 12px; color: #94a3b8; margin-top: 14px; line-height: 1.4;
		}
	</style>
</head>
<body>
<div class="background"><div class="blob"></div></div>
<div class="card">
	<div class="logo">🛡️</div>
	<h1>{client_name}</h1>
	<p>Скачайте файл профиля и откройте его в приложении OpenVPN Connect</p>
	<div class="qr-box">
		<canvas id="qrCanvas"></canvas>
	</div>
	<a href="/d/{token}/raw" class="btn">⬇️ Скачать .ovpn профиль</a>
	<div id="importBtnBox"></div>
	<div class="notice">
		Подсказка: на телефоне нажмите <b>«Скачать .ovpn»</b> и выберите <i>«Открыть с помощью OpenVPN»</i>.
	</div>
</div>
<script>
	new QRious({
		element: document.getElementById('qrCanvas'),
		value: window.location.href,
		size: 200,
		level: 'M'
	});

	// Кнопка прямого импорта работает только при наличии HTTPS
	if (window.location.protocol === 'https:') {
		const importBox = document.getElementById('importBtnBox');
		importBox.innerHTML = '<a href="openvpn://import-profile/{raw_url}" class="btn btn-outline">⚡ Авто-импорт в OpenVPN</a>';
	}
</script>
</body>
</html>
"""

def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    conn.execute("PRAGMA temp_store=MEMORY;")
    conn.execute("PRAGMA cache_size=-4000;")
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS client_meta (
                client_name TEXT PRIMARY KEY,
                note TEXT DEFAULT '',
                expires_at INTEGER DEFAULT 0,
                is_paused INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS split_links (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                resolved_ip TEXT DEFAULT '',
                route_via TEXT DEFAULT 'split',
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS adblock_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL DEFAULT 'black',
                domains_count INTEGER DEFAULT 0,
                created_at INTEGER NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS adblock_domains (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                domain TEXT NOT NULL UNIQUE,
                list_type TEXT NOT NULL DEFAULT 'black',
                created_at INTEGER NOT NULL
            )
        """)

        default_settings = {
            "admin_login": os.getenv("ADMIN_LOGIN", "admin"),
            "admin_password_hash": os.getenv(
                "ADMIN_PASSWORD_HASH",
                hashlib.sha256("admin".encode("utf-8")).hexdigest(),
            ),
            "ovpn_domain": os.getenv("OVPN_DOMAIN", DOMAIN),
            "ovpn_port": str(OVPN_PORT),
            "ovpn_proto": PROTOCOL,
            "panel_port": str(PANEL_PORT),
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
            "enable_speed_monitor": "1",
            "enable_hardware_bar": "1",
            "cidr_url": "https://plitw.github.io/ros-country-ips/cidr_lists/ru_ipv4",
            "routing_mode": "split",
            "custom_cidrs": "",
            "torrent_block": "0",
            "split_link_ips": "",
            "adblock_enabled": "0",
            "adblock_dns_ip": ADBLOCK_DNS_IP,
        }
        for k, v in default_settings.items():
            conn.execute(
                "INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v)
            )

_settings_cache: Dict[str, str] = {}

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

def set_setting(key: str, value: str):
    val_str = str(value)
    with get_db() as conn:
        conn.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, val_str),
        )
    _settings_cache[key] = val_str

def set_settings_bulk(data: Dict[str, Any]):
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
            derived = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=16384, r=8, p=1)
            return hmac.compare_digest(derived.hex(), hash_hex)
        except Exception:
            return False
    # Обратная совместимость с sha256
    legacy = hashlib.sha256(password.encode("utf-8")).hexdigest()
    return hmac.compare_digest(legacy, stored_hash)

def get_admin_login() -> str:
    return get_setting("admin_login", "admin")

def get_admin_password_hash() -> str:
    return get_setting("admin_password_hash", hash_password("admin"))

def get_ovpn_subnet_cidr() -> str:
    raw = get_setting("ovpn_subnet", "10.8.0.0 255.255.255.0").strip().split()
    if len(raw) == 2:
        try:
            return str(ipaddress.IPv4Network(f"{raw[0]}/{raw[1]}", strict=False))
        except Exception:
            pass
    return "10.8.0.0/24"

def get_current_domain() -> str:
    return get_setting("ovpn_domain", DOMAIN)

def get_current_port() -> int:
    try:
        return int(get_setting("ovpn_port", str(OVPN_PORT)))
    except Exception:
        return OVPN_PORT

def get_current_proto() -> str:
    return get_setting("ovpn_proto", PROTOCOL)

def ensure_dnsmasq_installed_sync() -> Tuple[bool, str]:
    try:
        if Path("/opt/AdGuardHome").exists() or Path("/etc/systemd/system/AdGuardHome.service").exists():
            subprocess.run(["/opt/AdGuardHome/AdGuardHome", "-s", "uninstall"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "stop", "AdGuardHome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "disable", "AdGuardHome"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree("/opt/AdGuardHome", ignore_errors=True)
            Path("/etc/systemd/system/AdGuardHome.service").unlink(missing_ok=True)

        try:
            socket.gethostbyname("archive.ubuntu.com")
        except Exception:
            resolv_p = Path("/etc/resolv.conf")
            if resolv_p.is_symlink() or resolv_p.exists():
                resolv_p.unlink(missing_ok=True)
            resolv_p.write_text("nameserver 1.1.1.1\nnameserver 8.8.8.8\n", encoding="utf-8")

        if shutil.which("dnsmasq") is None:
            subprocess.run(["apt-get", "update"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
            env = os.environ.copy()
            env["DEBIAN_FRONTEND"] = "noninteractive"
            r = subprocess.run(
                ["apt-get", "install", "-y", "dnsmasq"],
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=120,
            )
            if r.returncode != 0 and shutil.which("dnsmasq") is None:
                return False, "Failed to install dnsmasq"

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
    ignore = {"localhost", "localhost.localdomain", "local", "broadcasthost", "ip6-localhost", "ip6-loopback", "0.0.0.0", "127.0.0.1"}
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
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (OpenVPN-Panel-AdBlock)"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read(100 * 1024 * 1024).decode("utf-8", errors="ignore")
        if "<html" in raw[:500].lower():
            return False, [], "Invalid list content"
        domains = parse_adlist_content(raw)
        if not domains:
            return False, [], "No valid domains"
        return True, domains, "OK"
    except Exception as e:
        return False, [], str(e)

def rebuild_dnsmasq_adblock_conf_sync() -> Tuple[bool, int, str]:
    ok, msg = ensure_dnsmasq_installed_sync()
    if not ok:
        return False, 0, msg

    adblock_on = get_setting("adblock_enabled", "0") == "1"
    if not adblock_on:
        DNSMASQ_ADBLOCK_CONF.write_text("", encoding="utf-8")
        subprocess.run(["systemctl", "kill", "-s", "SIGHUP", "dnsmasq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True, 0, "OK"

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
                doms = [line.strip() for line in cache_file.read_text(encoding="utf-8", errors="ignore").splitlines() if line.strip()]
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
    lines = []
    for dom in final_black:
        lines.append(f"address=/{dom}/0.0.0.0")

    DNSMASQ_ADBLOCK_CONF.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subprocess.run(["systemctl", "restart", "dnsmasq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True, len(final_black), "OK"

def apply_dns_redirect_iptables_sync(enable: bool, dns_ip: str):
    for proto in ("udp", "tcp"):
        rule = ["PREROUTING", "-i", TUN_IFACE, "-p", proto, "--dport", "53", "-j", "REDIRECT", "--to-ports", "53"]
        while subprocess.run(["iptables", "-t", "nat", "-D"] + rule, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0:
            pass
        if enable:
            subprocess.run(["iptables", "-t", "nat", "-I", "PREROUTING", "1"] + rule[1:], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def apply_adblock_state_sync(enable: bool) -> Tuple[bool, str]:
    dns_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
    set_setting("adblock_enabled", "1" if enable else "0")

    ok, _, msg = rebuild_dnsmasq_adblock_conf_sync()
    if not ok:
        set_setting("adblock_enabled", "0")
        return False, msg

    apply_dns_redirect_iptables_sync(enable, dns_ip)
    ok_conf, msg_conf = sync_openvpn_server_conf_from_settings(restart_service=True)
    if not ok_conf:
        return False, msg_conf

    _server_status_cache["ts"] = 0.0
    return True, "OK"

class SpeedMonitor:
    def __init__(self, history_len: int = 300):
        self.prev_traffic: Dict[str, Dict[str, Any]] = {}
        self.current_speeds: Dict[str, Dict[str, Any]] = {}
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.virt_ip_to_client: Dict[str, str] = {}
        self.online_clients: set = set()
        self.history: deque = deque(maxlen=history_len)

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

    async def update_tick(self):
        speed_enabled = get_setting("enable_speed_monitor", "1") == "1"
        current_data = await self.query_management_status()
        now = time.time()
        time_str = datetime.now().strftime("%H:%M:%S")
        new_speeds = {}
        ip_map = {}

        self.online_clients = set(current_data.keys())
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

    def get_history_window(self, seconds: int = 300) -> List[Dict[str, Any]]:
        min_ts = time.time() - seconds
        return [pt for pt in self.history if pt["ts"] >= min_ts]

speed_monitor = SpeedMonitor(history_len=300)

def check_expired_clients_sync():
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

def apply_torrent_block_sync(enable: bool):
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
        adblock_ip = s.get("adblock_dns_ip", ADBLOCK_DNS_IP).strip()

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

def parse_existing_server_conf_into_db():
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
        adblock_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
        dns_list = [d for d in re.findall(r'push\s+"dhcp-option\s+DNS\s+([^"]+)"', content) if d != adblock_ip]
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

def ensure_system_configs():
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
                f.write(f"\nmanagement {MGMT_HOST} {MGMT_PORT}\n")
            subprocess.run(
                ["systemctl", "reload-or-restart", "openvpn-server@server"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass

async def live_speed_worker():
    tick_counter = 0
    while True:
        try:
            await speed_monitor.update_tick()
            tick_counter += 1
            if tick_counter >= 30:
                await asyncio.to_thread(check_expired_clients_sync)
                tick_counter = 0
        except Exception:
            pass
        await asyncio.sleep(1.0)

@asynccontextmanager
async def lifespan(application: FastAPI):
    init_db()
    CCD_DIR.mkdir(parents=True, exist_ok=True)
    await asyncio.to_thread(ensure_system_configs)
    task_speed = asyncio.create_task(live_speed_worker())
    yield
    task_speed.cancel()

app = FastAPI(
    title="OpenVPN Panel",
    version="1.0.0",
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
    return verify_password(password, get_admin_password_hash())

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
        if time.time() - int(ts_str) > SESSION_MAX_AGE:
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

_pki_cache: Dict[str, Any] = {"mtime": 0.0, "clients": {}}
_server_status_cache: Dict[str, Any] = {
    "ts": 0.0,
    "data": {"status": "inactive", "domain": DOMAIN, "port": OVPN_PORT},
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

def invalidate_pki_cache():
    _pki_cache["mtime"] = 0.0

def client_exists(client_name: str) -> bool:
    if not re.match(r"^[a-zA-Z0-9_-]+$", client_name):
        return False
    return client_name in get_pki_clients_fast()

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

def get_server_status() -> Dict:
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
        with open("/proc/stat", "r") as f:
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
        meminfo = {}
        with open("/proc/meminfo", "r") as f:
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

@app.get("/api/adblock/status")
async def api_adblock_status():
    def _get():
        enabled = get_setting("adblock_enabled", "0") == "1"
        dns_ip = get_setting("adblock_dns_ip", ADBLOCK_DNS_IP)
        res = subprocess.run(["systemctl", "is-active", "dnsmasq"], capture_output=True, text=True)
        dnsmasq_active = res.stdout.strip() == "active"

        blocked_total = 0
        if DNSMASQ_ADBLOCK_CONF.exists():
            try:
                blocked_total = sum(
                    1 for line in DNSMASQ_ADBLOCK_CONF.read_text(encoding="utf-8", errors="ignore").splitlines()
                    if line.startswith("address=/")
                )
            except Exception:
                pass

        with get_db() as conn:
            lists = [dict(r) for r in conn.execute("SELECT id, url, list_type, domains_count, created_at FROM adblock_lists ORDER BY id DESC").fetchall()]
            domains = [dict(r) for r in conn.execute("SELECT id, domain, list_type, created_at FROM adblock_domains ORDER BY id DESC").fetchall()]

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

    ok, msg = await asyncio.to_thread(apply_adblock_state_sync, enable)
    return {"success": ok, "enabled": enable, "message": msg}

@app.post("/api/adblock/lists")
async def api_adblock_add_list(request: Request):
    try:
        data = await request.json()
        url = str(data.get("url", "")).strip()
        list_type = "white" if data.get("list_type") == "white" else "black"
    except Exception:
        return {"success": False, "message": "Invalid JSON"}

    if not url.startswith(("http://", "https://")):
        return {"success": False, "message": "Invalid URL"}

    def _download_and_store():
        ok_inst, msg_inst = ensure_dnsmasq_installed_sync()
        if not ok_inst:
            return False, msg_inst

        ok_fetch, domains, msg_fetch = fetch_and_parse_adlist(url)
        if not ok_fetch:
            return False, msg_fetch

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
                list_id = conn.execute("SELECT id FROM adblock_lists WHERE url=?", (url,)).fetchone()["id"]

        cache_dir = Path("/var/cache/ovpn_adblock")
        cache_dir.mkdir(parents=True, exist_ok=True)
        (cache_dir / f"list_{list_id}.txt").write_text("\n".join(domains), encoding="utf-8")

        rebuild_dnsmasq_adblock_conf_sync()
        return True, "OK"

    ok, msg = await asyncio.to_thread(_download_and_store)
    return {"success": ok, "message": msg}

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
        return {"success": False, "message": "Invalid domain"}
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
        return True, "OK"

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

@app.get("/api/system/stats")
async def api_system_stats():
    stats = await asyncio.to_thread(get_system_stats)
    return {"success": True, "stats": stats}

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

        if "panel_port" in data and str(data["panel_port"]).strip() != "":
            val = int(data["panel_port"])
            if 1 <= val <= 65535:
                updates["panel_port"] = str(val)

        if "ovpn_domain" in data:
            updates["ovpn_domain"] = str(data["ovpn_domain"]).strip()

        bool_fields = [
            "enable_speed_monitor",
            "enable_hardware_bar",
            "torrent_block",
        ]
        for k in bool_fields:
            if k in data:
                updates[k] = "1" if str(data[k]) in ("1", "true", "True") else "0"

        await asyncio.to_thread(set_settings_bulk, updates)

        if "torrent_block" in updates:
            await asyncio.to_thread(
                apply_torrent_block_sync, updates["torrent_block"] == "1"
            )

        if data.get("apply_to_ovpn"):
            await asyncio.to_thread(sync_openvpn_server_conf_from_settings, True)
            _server_status_cache["ts"] = 0.0

        s_out = await asyncio.to_thread(get_all_settings)
        s_out.pop("admin_password_hash", None)
        
        return {"success": True, "message": "OK", "settings": s_out}
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
        _server_status_cache["ts"] = 0.0
        return r.returncode == 0, r.stderr.strip() or "OK"

    ok, msg = await asyncio.to_thread(_do)
    return {"success": ok, "message": msg}

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

@app.get("/api/clients")
async def api_clients():
    pki_clients = await asyncio.to_thread(get_pki_clients_fast)
    meta_data = {}

    try:
        with get_db() as conn:
            for row in conn.execute(
                "SELECT client_name, note, expires_at, is_paused FROM client_meta"
            ):
                meta_data[row["client_name"]] = {
                    "note": row["note"],
                    "expires": row["expires_at"],
                    "is_paused": row["is_paused"],
                }
    except Exception:
        pass

    active_sessions = speed_monitor.active_sessions
    current_speeds = speed_monitor.current_speeds
    clients = []

    for name in sorted(pki_clients.keys()):
        meta = pki_clients[name]
        m_info = meta_data.get(
            name, {"note": "", "expires": 0, "is_paused": 0}
        )
        is_paused = bool(m_info["is_paused"])
        is_online = name in active_sessions and not is_paused
        sess = active_sessions.get(name, {})
        spd = current_speeds.get(name, {})

        clients.append(
            {
                "name": name,
                "status": meta["status"],
                "is_online": is_online,
                "is_paused": is_paused,
                "note": m_info["note"],
                "expires_at": m_info["expires"],
                "real_ip": sess.get("real_ip", "—") if is_online else "—",
                "virt_ip": sess.get("virt_ip", "—") if is_online else "—",
                "connected_since": sess.get("connected_since", "—") if is_online else "—",
                "speed_down": spd.get("down", 0) if is_online else 0,
                "speed_up": spd.get("up", 0) if is_online else 0,
                "speed_down_fmt": (
                    spd.get("down_fmt", "0 B/s") if is_online else "0 B/s"
                ),
                "speed_up_fmt": spd.get("up_fmt", "0 B/s") if is_online else "0 B/s",
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
    ttl_days = int(data.get("ttl_days", 0) or 0)

    if not name or not re.match(r"^[a-zA-Z0-9_-]+$", name):
        return {"success": False, "message": "Invalid name"}
    if len(name) > 64:
        return {"success": False, "message": "Name too long"}
    if client_exists(name):
        return {"success": False, "message": "Client already exists"}

    def _create():
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

        with get_db() as conn:
            conn.execute(
                "INSERT INTO client_meta (client_name, note, expires_at, is_paused) VALUES (?, ?, ?, 0) "
                "ON CONFLICT(client_name) DO UPDATE SET note=excluded.note, expires_at=excluded.expires_at",
                (name, note, expires_at),
            )

        invalidate_pki_cache()
        return True, "OK"

    ok, msg = await asyncio.to_thread(_create)
    return {"success": ok, "message": msg}

@app.post("/api/clients/{name}/pause")
async def api_toggle_pause_client(name: str):
    if not client_exists(name):
        return {"success": False, "message": "Not found"}

    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT is_paused FROM client_meta WHERE client_name=?", (name,)
            ).fetchone()
            cur_paused = row["is_paused"] if row else 0
            new_paused = 0 if cur_paused == 1 else 1
            conn.execute(
                "INSERT INTO client_meta (client_name, is_paused) VALUES (?, ?) "
                "ON CONFLICT(client_name) DO UPDATE SET is_paused=excluded.is_paused",
                (name, new_paused),
            )

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
            _server_status_cache["ts"] = 0.0
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
                shutil.copytree("/etc/openvpn", base_dir / "openvpn", ignore=shutil.ignore_patterns("*.log", "*.socket", "*.pid", "status*"))
            if Path("/etc/wireguard").exists():
                shutil.copytree("/etc/wireguard", base_dir / "wireguard", dirs_exist_ok=True)
            if Path("/etc/dnsmasq.d").exists():
                shutil.copytree("/etc/dnsmasq.d", base_dir / "dnsmasq.d", dirs_exist_ok=True)
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
                    # Безопасный вызов extractall без filter для обратной совместимости с Python 3.10/3.11
                    tar.extractall(path=base_dest)

                src_root = base_dest / "backup_data"
                if not src_root.exists():
                    src_root = base_dest

                if (src_root / "openvpn").exists():
                    shutil.copytree(src_root / "openvpn", Path("/etc/openvpn"), dirs_exist_ok=True)
                if (src_root / "wireguard").exists():
                    shutil.copytree(src_root / "wireguard", Path("/etc/wireguard"), dirs_exist_ok=True)
                if (src_root / "dnsmasq.d").exists():
                    shutil.copytree(src_root / "dnsmasq.d", Path("/etc/dnsmasq.d"), dirs_exist_ok=True)
                if (src_root / "panel.db").exists():
                    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src_root / "panel.db", DB_PATH)
                if (src_root / ".env").exists():
                    shutil.copy2(src_root / ".env", env_target)
                    os.chmod(env_target, 0o600)

            tmp_path.unlink(missing_ok=True)
            invalidate_pki_cache()
            parse_existing_server_conf_into_db()
            ensure_system_configs()
            subprocess.run(["systemctl", "restart", "openvpn-server@server"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run(["systemctl", "restart", "dnsmasq"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            return True, "OK"

        ok, msg = await asyncio.to_thread(_do_restore)
        return {"success": ok, "message": msg}
    except Exception as e:
        return {"success": False, "message": str(e)}

def reload_ipset_sync():
    subprocess.run(
        ["ipset", "create", "ru_ips", "hash:net", "maxelem", "262144", "-exist"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ipset", "create", "force_wg_ips", "hash:net", "maxelem", "65536", "-exist"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(
        ["ipset", "create", "force_direct_ips", "hash:net", "maxelem", "65536", "-exist"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    ru_file = Path("/etc/wireguard/ru.txt")
    custom_raw = get_setting("custom_cidrs")

    nets = []
    if ru_file.exists():
        for line in ru_file.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = line.strip()
            if line and re.match(
                r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:/[0-9]{1,2})?$",
                line,
            ):
                nets.append(line)

    if custom_raw:
        for line in custom_raw.splitlines():
            line = line.strip()
            if line and re.match(
                r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:/[0-9]{1,2})?$",
                line,
            ):
                nets.append(line)

    force_wg_nets = []
    force_direct_nets = []

    try:
        with get_db() as conn:
            rows = conn.execute("SELECT resolved_ip, route_via FROM split_links").fetchall()
            for r in rows:
                target_list = force_wg_nets if r["route_via"] == "wg" else force_direct_nets
                for ip in re.split(r"[,\s]+", r["resolved_ip"] or ""):
                    ip = ip.strip()
                    if ip and re.match(
                        r"^[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}(?:/[0-9]{1,2})?$",
                        ip,
                    ):
                        target_list.append(ip)
    except Exception:
        pass

    wg_override_set = set(force_wg_nets)
    nets = [n for n in nets if n not in wg_override_set]

    def _apply_set(name: str, items: list, max_elem: int = 262144):
        tmp = f"{name}_tmp"
        payload = f"create {tmp} hash:net maxelem {max_elem} -exist\nflush {tmp}\n"
        if items:
            payload += "\n".join(f"add {tmp} {n} -exist" for n in set(items)) + "\n"
        payload += f"swap {tmp} {name}\ndestroy {tmp}\n"
        subprocess.run(["ipset", "restore"], input=payload.encode("utf-8"), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    _apply_set("ru_ips", nets, 262144)
    _apply_set("force_wg_ips", force_wg_nets, 65536)
    _apply_set("force_direct_ips", force_direct_nets, 65536)

def apply_routing_mode_sync(mode: str):
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
        f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set force_wg_ips dst -j ACCEPT"
    ]
    priority_rules_del = [r.replace("-A PREROUTING", "-D PREROUTING") for r in priority_rules]

    if mode == "all":
        base_rules = [f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -j MARK --set-mark 0x1"]
        base_rules_del = [f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -j MARK --set-mark 0x1"]
    elif mode == "cidr_wg":
        base_rules = [f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set --match-set ru_ips dst -j MARK --set-mark 0x1"]
        base_rules_del = [f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -m set --match-set ru_ips dst -j MARK --set-mark 0x1"]
    else:
        base_rules = [f"iptables -t mangle -A PREROUTING -s {subnet_cidr} -m set ! --match-set ru_ips dst -j MARK --set-mark 0x1"]
        base_rules_del = [f"iptables -t mangle -D PREROUTING -s {subnet_cidr} -m set ! --match-set ru_ips dst -j MARK --set-mark 0x1"]

    all_mangle_up = "\n".join(f"PostUp = {r}" for r in (priority_rules + base_rules))
    all_mangle_down = "\n".join(f"PostDown = {r}" for r in (priority_rules_del + base_rules_del))

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
            await asyncio.to_thread(apply_routing_mode_sync, new_mode)

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

    try:
        await asyncio.to_thread(_download)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

@app.post("/api/routing/setup")
async def api_routing_setup(request: Request):
    if not paramiko:
        return {"success": False, "message": "paramiko not installed"}

    data = await request.json()
    remote_ip = data.get("remote_ip", "").strip()
    remote_pass = data.get("remote_pass", "")

    if not remote_ip or not remote_pass:
        return {"success": False, "message": "IP and password required"}
    try:
        ipaddress.ip_address(remote_ip)
    except ValueError:
        return {"success": False, "message": "Invalid remote IP address"}

    def _run_ssh(ssh_client, cmd: str) -> str:
        _, stdout, _ = ssh_client.exec_command(cmd)
        stdout.channel.recv_exit_status()
        return stdout.read().decode("utf-8", errors="ignore").strip()

    def _setup():
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

        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(remote_ip, username="root", password=remote_pass, timeout=15)

        try:
            _run_ssh(
                client,
                f'mkdir -p ~/.ssh && chmod 700 ~/.ssh && echo "{pub_key}" >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys',
            )
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

        subprocess.run(["systemctl", "stop", "wg-quick@wg0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["ip", "link", "del", "dev", "wg0"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mode = get_setting("routing_mode") or "split"
        set_setting("routing_mode", mode)
        apply_routing_mode_sync(mode)

    try:
        await asyncio.to_thread(_setup)
        return {"success": True}
    except Exception as e:
        return {"success": False, "message": str(e)}

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
                res = subprocess.run(["ipset", "test", "ru_ips", ip], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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
            "conflict_ips": conflict_ips
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
                "{{ERROR}}", '<div class="error-box">Form error</div>'
            ),
            status_code=400,
        )

    if not verify_login(username, password):
        return HTMLResponse(
            LOGIN_HTML.replace(
                "{{ERROR}}",
                '<div class="error-box">Invalid credentials</div>',
            ),
            status_code=401,
        )

    session = create_session()
    is_secure = request.url.scheme == "https"
    response = RedirectResponse("/", status_code=303)
    response.set_cookie(
        key=SESSION_COOKIE,
        value=session,
        max_age=SESSION_MAX_AGE,
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
