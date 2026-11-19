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
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
			background: var(--bg-main);
			color: var(--text-main);
			min-height: 100vh;
			padding: 20px 18px 60px;
			-webkit-font-smoothing: antialiased;
		}
		.container { max-width: 1440px; margin: 0 auto; }

		.header {
			display: flex; justify-content: space-between; align-items: center;
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-xl); padding: 16px 22px; margin-bottom: 16px;
			box-shadow: var(--shadow-md); flex-wrap: wrap; gap: 12px;
		}
		.brand-text h1 { font-size: 18px; font-weight: 700; }
		.brand-text p { font-size: 12px; color: var(--text-muted); margin-top: 2px; }
		.header-actions { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }

		.btn {
			padding: 8px 14px; border-radius: var(--radius-sm); font-size: 12.5px;
			font-weight: 600; cursor: pointer; transition: all 0.15s ease;
			border: 1px solid var(--border-subtle); background: #1e293b;
			color: var(--text-main); display: inline-flex; align-items: center;
			gap: 6px; text-decoration: none; white-space: nowrap;
		}
		[data-theme="light"] .btn:not(.btn-primary):not(.btn-danger):not(.btn-success):not(.btn-warning) {
			background: #f1f5f9; color: #0f172a; border-color: #cbd5e1;
		}
		.btn:hover { transform: translateY(-1px); filter: brightness(1.06); }
		.btn:disabled { opacity: 0.45; cursor: not-allowed; transform: none; }
		.btn-primary { background: linear-gradient(135deg, #3b82f6, #2563eb); border-color: transparent; color: #fff; }
		.btn-success { background: rgba(16, 185, 129, 0.15); border-color: rgba(16, 185, 129, 0.35); color: #34d399; }
		.btn-danger { background: rgba(239, 68, 68, 0.15); border-color: rgba(239, 68, 68, 0.35); color: #fca5a5; }
		.btn-warning { background: rgba(245, 158, 11, 0.15); border-color: rgba(245, 158, 11, 0.35); color: #fbbf24; }
		.btn-sm { padding: 5px 9px; font-size: 11.5px; border-radius: 6px; }

		.lang-select, .control-select, .search-input, .textarea-input {
			padding: 9px 12px; background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-sm); color: var(--text-main); font-size: 13px;
			outline: none; font-family: inherit;
		}
		.search-input:focus, .textarea-input:focus, .control-select:focus {
			border-color: var(--primary);
		}
		.textarea-input { font-family: 'JetBrains Mono', monospace; font-size: 12px; resize: vertical; }

		/* Индикатор прогресса фоновых задач */
		.task-progress-banner {
			display: none; background: var(--bg-card); border: 1px solid rgba(59, 130, 246, 0.45);
			border-radius: var(--radius-md); padding: 12px 16px; margin-bottom: 16px;
			box-shadow: var(--shadow-sm);
		}
		.task-progress-banner.active { display: block; }
		.task-progress-top { display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 8px; gap: 10px; }
		.progress-track { width: 100%; height: 7px; background: var(--bg-input); border-radius: 99px; overflow: hidden; }
		.progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #10b981); transition: width 0.25s ease; }

		.hardware-bar {
			display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 16px;
		}
		.hw-pill {
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md); padding: 12px 16px;
			display: flex; align-items: center; justify-content: space-between; gap: 10px;
		}
		.hw-label { font-size: 12px; color: var(--text-muted); }
		.hw-pill strong { font-family: 'JetBrains Mono', monospace; font-size: 12.5px; }

		.status-banner {
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg); padding: 14px 20px; margin-bottom: 18px;
			display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;
		}
		.banner-item { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--text-dim); }
		.banner-item code {
			background: var(--bg-input); padding: 4px 10px; border-radius: 6px;
			color: #60a5fa; border: 1px solid var(--border-subtle); font-family: 'JetBrains Mono', monospace; font-size: 12px;
		}
		.status-badge { font-weight: 600; font-size: 12.5px; padding: 4px 10px; border-radius: 20px; }
		.status-badge.active { color: #34d399; background: rgba(16, 185, 129, 0.12); }
		.status-badge.inactive { color: #f87171; background: rgba(239, 68, 68, 0.12); }

		.tabs-bar {
			display: flex; gap: 4px; background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md); padding: 5px; margin-bottom: 18px; overflow-x: auto;
		}
		.tab-btn {
			padding: 9px 16px; cursor: pointer; color: var(--text-muted); font-size: 13px;
			font-weight: 600; border-radius: var(--radius-sm); white-space: nowrap; user-select: none;
		}
		.tab-btn:hover { color: var(--text-main); background: rgba(59, 130, 246, 0.08); }
		.tab-btn.active { color: #fff; background: linear-gradient(135deg, #3b82f6, #2563eb); }
		.tab-view { display: none; }
		.tab-view.active { display: block; }

		.filter-bar { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; align-items: center; }
		.search-wrapper { position: relative; flex: 1; min-width: 180px; display: flex; align-items: center; }
		.search-wrapper .search-input { width: 100%; padding-right: 34px; }
		.search-clear-btn {
			position: absolute; right: 8px; background: rgba(148, 163, 184, 0.15); border: none;
			color: var(--text-dim); width: 22px; height: 22px; border-radius: 50%; cursor: pointer; display: none;
		}

		/* Минималистичная карточка клиента + раскрывашка */
		.clients-grid {
			display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; align-items: start;
		}
		@media (max-width: 1360px) { .clients-grid { grid-template-columns: repeat(3, 1fr); } }
		@media (max-width: 980px) { .clients-grid { grid-template-columns: repeat(2, 1fr); } }
		@media (max-width: 640px) { .clients-grid { grid-template-columns: 1fr; } }

		.client-card {
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md); padding: 14px 16px; transition: all 0.15s ease;
			position: relative; overflow: hidden;
		}
		.client-card.online-card { border-color: rgba(16, 185, 129, 0.4); }
		.client-card.paused-card { border-color: rgba(245, 158, 11, 0.4); }
		.client-card:hover { background: var(--bg-card-hover); }

		.card-summary {
			display: flex; justify-content: space-between; align-items: center;
			gap: 8px; cursor: pointer; user-select: none;
		}
		.card-main-info { min-width: 0; flex: 1; }
		.client-name-row { display: flex; align-items: center; gap: 7px; }
		.client-name { font-size: 14px; font-weight: 700; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.client-subline {
			display: flex; align-items: center; gap: 8px; margin-top: 4px;
			font-size: 11.5px; color: var(--text-muted); flex-wrap: wrap;
		}
		.client-badge {
			font-size: 10px; padding: 2px 8px; border-radius: 20px; font-weight: 700;
			text-transform: uppercase; white-space: nowrap;
		}
		.client-badge.valid { background: rgba(16, 185, 129, 0.15); color: #34d399; }
		.client-badge.paused { background: rgba(245, 158, 11, 0.15); color: #fbbf24; }
		.client-badge.revoked { background: rgba(239, 68, 68, 0.15); color: #f87171; }
		.expand-chevron { font-size: 11px; color: var(--text-muted); transition: transform 0.2s; }
		.client-card.expanded .expand-chevron { transform: rotate(180deg); color: var(--primary); }

		.card-details-drawer {
			display: none; margin-top: 12px; padding-top: 12px;
			border-top: 1px solid var(--border-subtle); font-size: 12px; color: var(--text-dim);
		}
		.client-card.expanded .card-details-drawer { display: block; }
		.detail-kv { display: flex; justify-content: space-between; gap: 8px; margin-bottom: 6px; font-size: 11.5px; }
		.detail-kv strong { font-family: 'JetBrains Mono', monospace; color: var(--text-main); font-weight: 600; text-align: right; }
		.live-speed-row {
			display: flex; justify-content: space-between; margin: 8px 0;
			font-family: 'JetBrains Mono', monospace; font-size: 11.5px; font-weight: 600;
		}
		.card-actions {
			display: flex; gap: 5px; flex-wrap: wrap; margin-top: 10px; padding-top: 10px;
			border-top: 1px solid var(--border-subtle);
		}
		.card-actions .btn { flex: 1; justify-content: center; min-width: 0; }

		.pagination-bar {
			display: flex; justify-content: space-between; align-items: center;
			margin-top: 18px; padding: 12px 18px; background: var(--bg-card);
			border: 1px solid var(--border-subtle); border-radius: var(--radius-md); flex-wrap: wrap; gap: 10px;
		}
		.pagination-pages { display: flex; gap: 6px; flex-wrap: wrap; }
		.page-btn {
			min-width: 34px; height: 34px; padding: 0 8px; border-radius: 6px;
			border: 1px solid var(--border-subtle); background: var(--bg-input);
			color: var(--text-main); font-size: 12.5px; font-weight: 600; cursor: pointer;
		}
		.page-btn.active { background: var(--primary); color: #fff; border-color: var(--primary); }

		.chart-wrapper, .settings-card {
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg); padding: 20px; box-shadow: var(--shadow-sm);
		}
		.chart-toolbar { display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px; margin-bottom: 16px; }
		.chart-controls { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
		.btn-group { display: inline-flex; border-radius: 8px; overflow: hidden; border: 1px solid var(--border-subtle); }
		.btn-group-btn {
			background: var(--bg-input); border: none; padding: 8px 14px; font-size: 12px;
			color: var(--text-muted); cursor: pointer; font-weight: 600;
		}
		.btn-group-btn.active { background: var(--primary); color: #fff; }
		.chart-canvas-box { position: relative; height: 380px; width: 100%; margin-bottom: 16px; }
		.chart-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 10px; }
		.stat-pill {
			background: var(--bg-input); border: 1px solid var(--border-subtle);
			padding: 12px 16px; border-radius: var(--radius-md); font-size: 12.5px;
			display: flex; justify-content: space-between; align-items: center;
		}

		.settings-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(340px, 1fr)); gap: 18px; }
		.routing-grid { display: grid; grid-template-columns: 1fr 1.6fr; gap: 18px; align-items: start; }
		.routing-grid-left { display: flex; flex-direction: column; gap: 18px; }
		@media (max-width: 960px) { .routing-grid { grid-template-columns: 1fr; } }

		.form-group { margin-bottom: 10px; }
		.form-label { font-size: 11.5px; color: var(--text-dim); display: block; margin-bottom: 5px; font-weight: 600; }
		.form-row-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
		.form-row-3 { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
		@media (max-width: 600px) { .form-row-2, .form-row-3 { grid-template-columns: 1fr; } }

		.switch-row {
			background: var(--bg-input); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md); padding: 12px 14px;
			display: flex; justify-content: space-between; align-items: center; gap: 12px; margin-bottom: 10px;
		}
		.switch-info strong { font-size: 13px; display: block; margin-bottom: 2px; }
		.switch-info span { font-size: 11.5px; color: var(--text-muted); }
		.toggle-switch { position: relative; display: inline-block; width: 42px; height: 22px; flex-shrink: 0; }
		.toggle-switch input { opacity: 0; width: 0; height: 0; }
		.toggle-slider { position: absolute; inset: 0; background: #334155; border-radius: 22px; cursor: pointer; transition: 0.2s; }
		.toggle-slider:before {
			position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px;
			background: #fff; border-radius: 50%; transition: 0.2s;
		}
		.toggle-switch input:checked + .toggle-slider { background: var(--primary); }
		.toggle-switch input:checked + .toggle-slider:before { transform: translateX(20px); }

		.domains-list-box { background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 6px; }
		.domain-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; gap: 8px; border-bottom: 1px solid rgba(148,163,184,0.08); }
		.domain-row:last-child { border-bottom: none; }
		.domain-name { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: #93c5fd; word-break: break-all; }

		.modal-overlay {
			display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75);
			backdrop-filter: blur(6px); z-index: 1000; justify-content: center; align-items: center; padding: 14px;
		}
		.modal-overlay.active { display: flex; }
		.modal-card {
			background: var(--bg-card); border: 1px solid var(--border-subtle);
			border-radius: var(--radius-xl); padding: 24px; max-width: 460px; width: 100%;
			box-shadow: var(--shadow-lg);
		}
		.modal-card h2 { font-size: 18px; margin-bottom: 6px; }
		.modal-card p { font-size: 12.5px; color: var(--text-muted); margin-bottom: 14px; }

		.toast {
			position: fixed; bottom: 24px; right: 24px; background: var(--bg-card);
			border: 1px solid var(--border-subtle); border-radius: var(--radius-md);
			padding: 12px 18px; font-size: 13px; font-weight: 500; box-shadow: var(--shadow-lg);
			transform: translateY(20px); opacity: 0; transition: all 0.25s ease; z-index: 2000; pointer-events: none;
		}
		.toast.show { transform: translateY(0); opacity: 1; }
		.toast.success { border-left: 4px solid var(--success); }
		.toast.error { border-left: 4px solid var(--danger); }

		@media (max-width: 768px) {
			.hardware-bar { grid-template-columns: repeat(2, 1fr); }
			.chart-canvas-box { height: 260px; }
		}
	</style>
</head>
<body>
<div class="container">
	<header class="header">
		<div class="brand-text">
			<h1>OpenVPN Dashboard</h1>
			<p>Control Center by <a href="https://github.com/FSystem88" style="color: var(--text-muted);">FSystem88</a></p>
		</div>
		<div class="header-actions">
			<button class="btn" id="themeToggleBtn" onclick="toggleTheme()"><span id="themeToggleIcon">☀️</span></button>
			<select class="lang-select" id="langSelect" onchange="changeLanguage(this.value)">
				<option value="ru">RU</option>
				<option value="en">EN</option>
			</select>
			<button class="btn btn-primary" onclick="openCreateModal()">+ <span data-i18n="btn_create_client">Создать</span></button>
			<button class="btn" onclick="openBackupModal()">📦 <span data-i18n="btn_backup">Бэкап</span></button>
			<a href="/logout" class="btn btn-danger">🚪 <span data-i18n="btn_logout">Выйти</span></a>
		</div>
	</header>

	<div class="task-progress-banner" id="taskProgressBanner">
		<div class="task-progress-top">
			<strong id="taskProgressTitle">Задача</strong>
			<span id="taskProgressMsg" style="color:var(--text-dim);">—</span>
			<strong id="taskProgressPct" style="font-family:'JetBrains Mono',monospace;">0%</strong>
		</div>
		<div class="progress-track"><div class="progress-fill" id="taskProgressFill"></div></div>
	</div>

	<div class="hardware-bar" id="hardwareBar">
		<div class="hw-pill"><span class="hw-label">💻 CPU</span><strong id="hwCpu">0%</strong></div>
		<div class="hw-pill"><span class="hw-label">📊 RAM</span><strong id="hwRam">0 / 0 MB</strong></div>
		<div class="hw-pill"><span class="hw-label">💾 Disk</span><strong id="hwDisk">0 / 0 GB</strong></div>
		<div class="hw-pill"><span class="hw-label">🌐 WG Ping</span><strong id="hwPing">—</strong></div>
	</div>

	<div class="status-banner">
		<div class="banner-item"><span data-i18n="banner_endpoint">Сервер:</span><code id="bannerEndpointCode">{{ domain }}:{{ port }} ({{ proto }})</code></div>
		<div class="banner-item"><span id="serverStatusText" class="status-badge active">● ...</span></div>
		<div class="banner-item"><span data-i18n="banner_online">Онлайн:</span><strong id="activeClientsCount" style="color:var(--primary);">0 / 0</strong></div>
		<div class="banner-item" style="color:var(--text-muted); font-size:12px;" id="lastSyncTime">—</div>
	</div>

	<div class="tabs-bar">
		<div class="tab-btn active" onclick="switchTab('tab-clients')" data-i18n="tab_clients">👥 Клиенты</div>
		<div class="tab-btn" id="tabBtnSpeed" onclick="switchTab('tab-speed')" data-i18n="tab_speed">📈 Скорость</div>
		<div class="tab-btn" onclick="switchTab('tab-limits')" data-i18n="tab_limits">⚡ Лимиты</div>
		<div class="tab-btn" onclick="switchTab('tab-routing')" data-i18n="tab_routing">🔀 Маршрутизация</div>
		<div class="tab-btn" onclick="switchTab('tab-config')" data-i18n="tab_config">⚙️ Конфигурация</div>
		<div class="tab-btn" onclick="switchTab('tab-settings')" data-i18n="tab_settings">🔐 Аккаунт</div>
	</div>

	<!-- ВКЛАДКА КЛИЕНТОВ -->
	<div id="tab-clients" class="tab-view active">
		<div class="filter-bar">
			<div class="search-wrapper">
				<input type="text" class="search-input" id="clientSearch" placeholder="🔍 Поиск по имени или IP..." oninput="onFilterInputChange()" autocomplete="off">
				<button type="button" class="search-clear-btn" id="clearSearchBtn" onclick="clearClientSearch()">✕</button>
			</div>
			<select class="control-select" id="statusFilter" onchange="onFilterInputChange()">
				<option value="all">Все активные</option>
				<option value="online">🟢 Только онлайн</option>
				<option value="offline">⚪ Только офлайн</option>
				<option value="paused">⏸️ На паузе</option>
				<option value="revoked">🚫 Отозванные</option>
			</select>
			<select class="control-select" id="sortFilter" onchange="onFilterInputChange()">
				<option value="online_first">🟢 Сначала онлайн</option>
				<option value="name_asc">🔤 По имени</option>
			</select>
			<select class="control-select" id="pageSizeSelect" onchange="onPageSizeChange()">
				<option value="20">По 20</option>
				<option value="50">По 50</option>
				<option value="100">По 100</option>
			</select>
		</div>

		<div class="clients-grid" id="clientsGrid">
			<div style="grid-column: 1/-1; text-align:center; padding: 50px 20px; color:var(--text-muted);">⏳ Загрузка...</div>
		</div>

		<div class="pagination-bar" id="paginationBar" style="display:none;">
			<div class="pagination-info" id="paginationInfo"></div>
			<div class="pagination-pages" id="paginationPages"></div>
		</div>
	</div>

	<!-- ВКЛАДКА СКОРОСТИ -->
	<div id="tab-speed" class="tab-view">
		<div class="chart-wrapper">
			<div class="chart-toolbar">
				<div>
					<h3>Мониторинг скорости в реальном времени</h3>
					<p style="font-size:12px; color:var(--text-muted);">Прямой опрос сокета OpenVPN</p>
				</div>
				<div class="chart-controls">
					<select class="control-select" id="chartClientFilter" onchange="renderChartData()">
						<option value="__ALL__">👥 Все клиенты</option>
					</select>
					<div class="btn-group">
						<button class="btn-group-btn active" id="btnWin30" onclick="setWindowTime(30)">30s</button>
						<button class="btn-group-btn" id="btnWin60" onclick="setWindowTime(60)">1m</button>
						<button class="btn-group-btn" id="btnWin300" onclick="setWindowTime(300)">5m</button>
					</div>
					<select class="control-select" id="chartMetricType" onchange="renderChartData()">
						<option value="total">Σ Суммарно</option>
						<option value="down">↓ Download</option>
						<option value="up">↑ Upload</option>
					</select>
					<select class="control-select" id="chartPollInterval" onchange="changePollInterval()">
						<option value="1000">1s</option>
						<option value="3000">3s</option>
						<option value="5000">5s</option>
						<option value="10000">10s</option>
					</select>
				</div>
			</div>
			<div class="chart-canvas-box"><canvas id="speedChartCanvas"></canvas></div>
			<div class="chart-stats">
				<div class="stat-pill"><span>Download:</span> <strong id="liveTotalDown" style="color:#60a5fa;">0 B/s</strong></div>
				<div class="stat-pill"><span>Upload:</span> <strong id="liveTotalUp" style="color:#34d399;">0 B/s</strong></div>
				<div class="stat-pill"><span>Онлайн:</span> <strong id="liveActiveCount">0</strong></div>
			</div>
		</div>
	</div>

	<!-- ВКЛАДКА ЛИМИТОВ СКОРОСТИ -->
	<div id="tab-limits" class="tab-view">
		<div class="settings-grid">
			<div class="settings-card">
				<h3>⚡ Двусторонний лимит скорости (tc + ifb0)</h3>
				<p style="font-size:12.5px; color:var(--text-muted);">Ограничивает скорость в обе стороны (приём и отдача). 0 = без ограничения.</p>

				<div class="form-group">
					<label class="form-label">Режим ограничения</label>
					<select class="control-select" id="speedLimitMode" style="width:100%;" onchange="renderSpeedLimitsEditor()">
						<option value="none">⚪ Без ограничения</option>
						<option value="global">🌐 Для всех клиентов (общий лимит)</option>
						<option value="selected">☑️ Для выбранных клиентов (общий лимит)</option>
						<option value="per_client">🎯 Индивидуально для каждого клиента</option>
					</select>
				</div>

				<div class="form-group" id="globalLimitBox">
					<label class="form-label">Общий лимит скорости (Кбит/с, напр. 5120 = 5 Мбит/с)</label>
					<input type="number" min="0" step="64" class="search-input" id="globalSpeedLimitKbps" value="0" style="width:100%;">
				</div>

				<button class="btn btn-primary" style="width:100%; justify-content:center; padding:11px;" onclick="saveSpeedLimits()">💾 Применить лимиты скорости</button>
			</div>

			<div class="settings-card">
				<h3>👥 Список клиентов для лимитов</h3>
				<div class="domains-list-box" id="speedLimitsClientsBox" style="max-height:420px; overflow-y:auto;"></div>
			</div>
		</div>
	</div>

	<!-- ВКЛАДКА МАРШРУТИЗАЦИИ -->
	<div id="tab-routing" class="tab-view">
		<div class="routing-grid">
			<div class="routing-grid-left">
				<div class="settings-card">
					<h3>Сплит-туннель (WireGuard + ipset)</h3>
					<div style="display:flex; justify-content:space-between; padding:8px 0; font-size:13px;">
						<span>Статус WG0:</span><strong id="wgText">...</strong>
					</div>
					<div style="display:flex; justify-content:space-between; padding:8px 0; font-size:13px;">
						<span>Подсетей в ipset:</span><strong id="ipsetSubnetsCount" style="color:#60a5fa;">...</strong>
					</div>

					<div class="form-group" style="margin-top:8px;">
						<input type="text" id="remoteServerIp" class="search-input" placeholder="IP удалённого сервера" style="width:100%; margin-bottom:8px;">
						<input type="password" id="remoteServerPass" class="search-input" placeholder="Пароль root" style="width:100%; margin-bottom:8px;">
						<button class="btn btn-success" style="width:100%; justify-content:center;" onclick="setupRemoteTunnel()">🚀 Настроить туннель</button>
					</div>

					<div class="switch-row">
						<div class="switch-info"><strong>🚫 Блокировка BitTorrent</strong><span>Защита от абузов</span></div>
						<label class="toggle-switch"><input type="checkbox" id="torrentBlockCheck"><span class="toggle-slider"></span></label>
					</div>

					<div class="form-group">
						<label class="form-label">URL списка подсетей:</label>
						<input type="text" id="cidrUrlInput" class="search-input" style="width:100%;">
					</div>
					<div class="form-group">
						<label class="form-label">Свои IP/подсети:</label>
						<textarea id="customCidrsInput" class="textarea-input" rows="3" style="width:100%;"></textarea>
					</div>
					<div class="form-group">
						<label class="form-label">Режим:</label>
						<select class="control-select" id="routingModeSelect" style="width:100%;">
							<option value="off">🔴 Отключено</option>
							<option value="split">🟡 CIDR напрямую, остальное в WG</option>
							<option value="cidr_wg">🟣 CIDR в WG, остальное напрямую</option>
							<option value="all">🟢 Весь трафик через WireGuard</option>
						</select>
					</div>

					<div style="display:flex; gap:8px; flex-wrap:wrap;">
						<button class="btn btn-primary" onclick="saveRoutingSettings()">💾 Сохранить</button>
						<button class="btn" onclick="updateCidrIps()">🔄 Обновить CIDR</button>
					</div>
				</div>
			</div>

			<div class="settings-card">
				<h3>🛡️ DNS AdBlock (dnsmasq)</h3>
				<div class="switch-row">
					<div class="switch-info"><strong>Блокировка рекламы для всех клиентов</strong><span id="adblockStatusLabel">...</span></div>
					<label class="toggle-switch"><input type="checkbox" id="adblockEnableToggle" onchange="toggleAdblock(this.checked)"><span class="toggle-slider"></span></label>
				</div>

				<div class="form-row-2">
					<div>
						<label class="form-label">📋 Добавить AdList URL</label>
						<div style="display:flex; gap:6px; margin-bottom:8px;">
							<input type="text" id="adblockListUrl" class="search-input" placeholder="https://..." style="flex:1;">
							<select class="control-select" id="adblockListType">
								<option value="black">⚫ Black</option>
								<option value="white">⚪ White</option>
							</select>
							<button class="btn btn-primary" onclick="addAdblockList()">+</button>
						</div>
						<div class="domains-list-box" id="adblockListsBox" style="max-height:320px; overflow-y:auto;"></div>
					</div>

					<div>
						<label class="form-label">🌐 Добавить домен</label>
						<div style="display:flex; gap:6px; margin-bottom:8px;">
							<input type="text" id="adblockDomainInput" class="search-input" placeholder="ads.example.com" style="flex:1;">
							<select class="control-select" id="adblockDomainType">
								<option value="black">⚫ Black</option>
								<option value="white">⚪ White</option>
							</select>
							<button class="btn btn-primary" onclick="addAdblockDomain()">+</button>
						</div>
						<div class="domains-list-box" id="adblockDomainsBox" style="max-height:320px; overflow-y:auto;"></div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- ВКЛАДКА КОНФИГУРАЦИИ -->
	<div id="tab-config" class="tab-view">
		<div class="chart-wrapper">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px; flex-wrap:wrap; gap:10px;">
				<h3>⚙️ server.conf</h3>
				<div style="display:flex; gap:8px;">
					<button class="btn" onclick="loadConfigView()">🔄 Перечитать</button>
					<button class="btn btn-primary" onclick="saveRawConfig(true)">💾 Сохранить и рестарт</button>
				</div>
			</div>
			<textarea id="serverConfigText" class="textarea-input" rows="22" style="width:100%;"></textarea>
		</div>
	</div>

	<!-- ВКЛАДКА АККАУНТА -->
	<div id="tab-settings" class="tab-view">
		<div class="settings-grid">
			<div class="settings-card">
				<h3>🔐 Учётная запись</h3>
				<div class="form-group"><label class="form-label">Логин</label><input type="text" id="setAdminLogin" class="search-input" style="width:100%;"></div>
				<div class="form-group"><label class="form-label">Новый пароль</label><input type="password" id="setAdminPass" class="search-input" placeholder="••••••••" style="width:100%;"></div>
				<div class="form-row-2">
					<div class="form-group"><label class="form-label">Порт панели</label><input type="number" id="setPanelPort" class="search-input" style="width:100%;"></div>
					<div class="form-group"><label class="form-label">Домен / IP</label><input type="text" id="setOvpnDomain" class="search-input" style="width:100%;"></div>
				</div>
			</div>

			<div class="settings-card">
				<h3>🎛️ Модули</h3>
				<div class="switch-row"><div class="switch-info"><strong>📈 Мониторинг скорости</strong></div><label class="toggle-switch"><input type="checkbox" id="setEnableSpeed"><span class="toggle-slider"></span></label></div>
				<div class="switch-row"><div class="switch-info"><strong>💻 Панель ресурсов</strong></div><label class="toggle-switch"><input type="checkbox" id="setEnableHwBar"><span class="toggle-slider"></span></label></div>
				<div class="switch-row"><div class="switch-info"><strong>🚫 Блок BitTorrent</strong></div><label class="toggle-switch"><input type="checkbox" id="setTorrentBlock"><span class="toggle-slider"></span></label></div>
			</div>

			<div class="settings-card">
				<h3>🛠️ Службы</h3>
				<button class="btn btn-primary" style="width:100%; justify-content:center; margin-bottom:8px;" onclick="saveAllAccountSettings(false)">💾 Сохранить настройки</button>
				<button class="btn btn-success" style="width:100%; justify-content:center; margin-bottom:12px;" onclick="saveAllAccountSettings(true)">🚀 Сохранить и перезапустить OVPN</button>
				<div class="form-row-3">
					<button class="btn" style="justify-content:center;" onclick="controlOvpnService('restart')">🔄 Рестарт</button>
					<button class="btn btn-success" style="justify-content:center;" onclick="controlOvpnService('start')">▶️ Старт</button>
					<button class="btn btn-danger" style="justify-content:center;" onclick="controlOvpnService('stop')">⏹️ Стоп</button>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- МОДАЛКИ -->
<div class="modal-overlay" id="createModal">
	<div class="modal-card">
		<h2>➕ Новый клиент</h2>
		<p>Латиница, цифры, дефис и подчёркивание.</p>
		<label class="form-label">Имя клиента</label>
		<input type="text" id="newClientName" class="search-input" placeholder="iphone-user" style="width:100%; margin-bottom:10px;">
		<label class="form-label">Заметка</label>
		<input type="text" id="newClientNote" class="search-input" placeholder="Например: Ноутбук" style="width:100%; margin-bottom:10px;">
		<label class="form-label">Срок в днях (0 = ∞)</label>
		<input type="number" id="newClientTtl" class="search-input" value="0" min="0" style="width:100%; margin-bottom:16px;">
		<div style="display:flex; gap:8px; justify-content:flex-end;">
			<button class="btn" onclick="closeModals()">Отмена</button>
			<button class="btn btn-primary" onclick="submitCreateClient()">Создать</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="qrModal">
	<div class="modal-card" style="text-align:center;">
		<h2 id="qrModalTitle">📱 QR</h2>
		<p>Отсканируйте камерой телефона</p>
		<div style="background:#fff; padding:14px; border-radius:14px; display:inline-block; margin-bottom:14px;">
			<canvas id="qrCanvas"></canvas>
		</div>
		<div style="display:flex; gap:8px;">
			<button class="btn btn-primary" style="flex:1; justify-content:center;" id="qrCopyBtn">🔗 Копировать</button>
			<button class="btn" style="flex:1; justify-content:center;" onclick="closeModals()">Закрыть</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="backupModal">
	<div class="modal-card">
		<h2>📦 Резервное копирование</h2>
		<p>Архив конфигурации OpenVPN, WireGuard, dnsmasq и БД.</p>
		<button class="btn" onclick="downloadBackupArchive()" style="width:100%; justify-content:center; padding:12px; margin-bottom:8px;">📥 Скачать архив</button>
		<button class="btn btn-primary" onclick="document.getElementById('backupFileInput').click()" style="width:100%; justify-content:center; padding:12px; margin-bottom:12px;">📤 Восстановить из файла</button>
		<input type="file" id="backupFileInput" accept=".tar.gz" style="display:none;" onchange="processRestoreFile(event)">
		<button class="btn" style="width:100%; justify-content:center;" onclick="closeModals()">Закрыть</button>
	</div>
</div>

<div class="toast" id="toastBox"></div>

<script>
let currentTheme = localStorage.getItem("ovpn_theme") || "dark";
let currentLang = localStorage.getItem("ovpn_lang") || "ru";
let panelConfig = { enable_speed_monitor: "1", enable_hardware_bar: "1", speed_limit_mode: "none", global_speed_limit_kbps: "0", selected_limit_clients: "[]" };
let expandedClientName = null;
let allClientsList = [];
let currentPage = 1;
let pageSize = parseInt(localStorage.getItem('ovpn_page_size')) || 20;
let speedChart = null;
let selectedWindowSeconds = 30;
let speedPollTimer = null;
let speedDataPoints = [];
let latestLiveSpeeds = {};
let clientColorRegistry = {};
let paletteIdx = 0;
const colorPalette = ['#3b82f6','#10b981','#f43f5e','#f59e0b','#8b5cf6','#06b6d4','#ec4899','#84cc16'];

function applyTheme(theme) {
	currentTheme = theme;
	localStorage.setItem("ovpn_theme", theme);
	document.documentElement.setAttribute("data-theme", theme);
	document.getElementById("themeToggleIcon").textContent = theme === "light" ? "🌙" : "☀️";
}
function toggleTheme() { applyTheme(currentTheme === "light" ? "dark" : "light"); }
applyTheme(currentTheme);

function changeLanguage(lang) {
	currentLang = lang;
	localStorage.setItem("ovpn_lang", lang);
}

function showToast(msg, type = 'success') {
	const box = document.getElementById('toastBox');
	box.textContent = msg;
	box.className = `toast ${type} show`;
	clearTimeout(box._t);
	box._t = setTimeout(() => box.classList.remove('show'), 3200);
}

function copyToClipboard(text) {
	if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
	const ta = document.createElement("textarea");
	ta.value = text;
	ta.style.position = "fixed";
	ta.style.left = "-9999px";
	document.body.appendChild(ta);
	ta.focus(); ta.select();
	return new Promise((res, rej) => { document.execCommand('copy') ? res() : rej(); ta.remove(); });
}

function formatTs(ts) {
	if (!ts || Number(ts) <= 0) return "—";
	const d = new Date(Number(ts) * 1000);
	return d.toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatSpeed(bps) {
	if (!bps || bps <= 0) return '0 B/s';
	const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
	let i = 0, v = bps;
	while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
	return v.toFixed(1) + ' ' + units[i];
}

// Отслеживание прогресса фоновых задач на слабом VPS
let watchedTaskId = null;
let taskPollTimer = null;
function watchBackgroundTask(taskId, onDone) {
	watchedTaskId = taskId;
	const banner = document.getElementById('taskProgressBanner');
	banner.classList.add('active');
	if (taskPollTimer) clearInterval(taskPollTimer);

	const tick = async () => {
		try {
			const r = await fetch(`/api/tasks/status?task_id=${encodeURIComponent(taskId)}`);
			const j = await r.json();
			const tsk = j.task;
			if (!tsk) return;
			document.getElementById('taskProgressTitle').textContent = tsk.title || taskId;
			document.getElementById('taskProgressMsg').textContent = tsk.message || '';
			document.getElementById('taskProgressPct').textContent = `${tsk.progress || 0}%`;
			document.getElementById('taskProgressFill').style.width = `${tsk.progress || 0}%`;

			if (tsk.status === 'done' || tsk.status === 'error') {
				clearInterval(taskPollTimer);
				taskPollTimer = null;
				setTimeout(() => banner.classList.remove('active'), 2500);
				if (onDone) onDone(tsk.status === 'done', tsk.message);
			}
		} catch (e) {}
	};
	tick();
	taskPollTimer = setInterval(tick, 700);
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
	if (tabId === 'tab-limits') renderSpeedLimitsEditor();
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
}
function openBackupModal() { document.getElementById('backupModal').classList.add('active'); }
function closeModals() { document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active')); }

function toggleClientExpand(name) {
	expandedClientName = (expandedClientName === name) ? null : name;
	applyClientFilter();
}

function onFilterInputChange() {
	const input = document.getElementById('clientSearch');
	const clearBtn = document.getElementById('clearSearchBtn');
	if (clearBtn && input) clearBtn.style.display = input.value.length > 0 ? 'inline-flex' : 'none';
	currentPage = 1;
	applyClientFilter();
}
function clearClientSearch() {
	const input = document.getElementById('clientSearch');
	if (input) input.value = '';
	onFilterInputChange();
}
function onPageSizeChange() {
	pageSize = parseInt(document.getElementById('pageSizeSelect').value) || 20;
	localStorage.setItem('ovpn_page_size', pageSize);
	currentPage = 1;
	applyClientFilter();
}
function goToPage(p) { currentPage = p; applyClientFilter(); }

async function loadClients() {
	if (document.hidden) return;
	try {
		const res = await fetch('/api/clients');
		if (res.status === 401) { location.href = '/login'; return; }
		const data = await res.json();
		allClientsList = data.clients || [];

		const isActive = data.server?.status === 'active';
		const stEl = document.getElementById('serverStatusText');
		stEl.textContent = isActive ? '● Сервер активен' : '● Остановлен';
		stEl.className = `status-badge ${isActive ? 'active' : 'inactive'}`;

		const validTotal = allClientsList.filter(c => c.status === 'valid').length;
		const online = allClientsList.filter(c => c.is_online).length;
		document.getElementById('activeClientsCount').textContent = `${online} / ${validTotal}`;
		document.getElementById('lastSyncTime').textContent = `Обновлено: ${new Date().toLocaleTimeString()}`;

		applyClientFilter();
		if (document.getElementById('tab-limits')?.classList.contains('active')) {
			renderSpeedLimitsEditor();
		}
	} catch (e) {}
}

function applyClientFilter() {
	const query = document.getElementById('clientSearch').value.toLowerCase().trim();
	const statusMode = document.getElementById('statusFilter').value;
	const sortMode = document.getElementById('sortFilter').value;

	let filtered = allClientsList.filter(c => {
		const match = c.name.toLowerCase().includes(query) ||
			(c.note && c.note.toLowerCase().includes(query)) ||
			(c.real_ip && c.real_ip.toLowerCase().includes(query)) ||
			(c.virt_ip && c.virt_ip.toLowerCase().includes(query));
		if (!match) return false;
		if (statusMode === 'revoked') return c.status === 'revoked';
		if (c.status === 'revoked') return false;
		if (statusMode === 'paused') return c.is_paused;
		if (statusMode === 'online') return c.is_online;
		if (statusMode === 'offline') return !c.is_online && !c.is_paused;
		return true;
	});

	filtered.sort((a, b) => {
		if (sortMode === 'online_first' && a.is_online !== b.is_online) return a.is_online ? -1 : 1;
		return a.name.localeCompare(b.name, undefined, { sensitivity: 'base' });
	});

	const totalItems = filtered.length;
	const totalPages = Math.max(1, Math.ceil(totalItems / pageSize));
	if (currentPage > totalPages) currentPage = totalPages;
	const startIdx = (currentPage - 1) * pageSize;
	const pageSlice = filtered.slice(startIdx, startIdx + pageSize);

	renderClientsGrid(pageSlice);
	renderPagination(totalItems, startIdx, pageSlice.length, totalPages);
}

function renderPagination(totalItems, startIdx, countOnPage, totalPages) {
	const bar = document.getElementById('paginationBar');
	if (totalItems === 0) { bar.style.display = 'none'; return; }
	bar.style.display = 'flex';
	document.getElementById('paginationInfo').textContent = `Показано ${startIdx + 1}–${startIdx + countOnPage} из ${totalItems}`;
	let html = `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>«</button>`;
	for (let p = 1; p <= totalPages; p++) {
		html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
	}
	html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>»</button>`;
	document.getElementById('paginationPages').innerHTML = html;
}

function renderClientsGrid(clients) {
	const grid = document.getElementById('clientsGrid');
	if (!clients || clients.length === 0) {
		grid.innerHTML = `<div style="grid-column: 1/-1; text-align:center; padding: 40px; color:var(--text-muted);">Список клиентов пуст</div>`;
		return;
	}

	grid.innerHTML = clients.map(c => {
		const isExpanded = expandedClientName === c.name;
		const statusText = c.status === 'revoked' ? 'ОТОЗВАН' : (c.is_paused ? 'ПАУЗА' : (c.is_online ? 'ОНЛАЙН' : 'ОФЛАЙН'));
		const badgeCls = c.status === 'revoked' ? 'revoked' : (c.is_paused ? 'paused' : 'valid');

		const actionsHtml = c.status === 'valid'
			? `
				<button class="btn btn-sm" onclick="event.stopPropagation(); showQrModal('${c.name}', '${c.share_token}')">📱</button>
				<button class="btn btn-sm" onclick="event.stopPropagation(); copyShareUrl('${c.share_token}')">🔗</button>
				<button class="btn btn-sm btn-primary" onclick="event.stopPropagation(); downloadClientConfig('${c.name}')">⬇️</button>
				<button class="btn btn-sm btn-warning" onclick="event.stopPropagation(); togglePauseClient('${c.name}')">${c.is_paused ? '▶' : '⏸'}</button>
				<button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); revokeClient('${c.name}', false)">🚫</button>
			`
			: `<button class="btn btn-sm btn-danger" onclick="event.stopPropagation(); revokeClient('${c.name}', true)">🗑️ Удалить</button>`;

		return `
			<div class="client-card ${c.is_online ? 'online-card' : ''} ${c.is_paused ? 'paused-card' : ''} ${isExpanded ? 'expanded' : ''}" id="client-card-${c.name}">
				<div class="card-summary" onclick="toggleClientExpand('${c.name}')">
					<div class="card-main-info">
						<div class="client-name-row">
							<span class="client-name">${c.name}</span>
							<span class="client-badge ${badgeCls}">${statusText}</span>
						</div>
						<div class="client-subline">
							${c.note ? `<span>💬 ${c.note}</span>` : ''}
							${c.is_online ? `<span style="color:#60a5fa;">↓ ${c.speed_down_fmt}</span><span style="color:#34d399;">↑ ${c.speed_up_fmt}</span>` : ''}
						</div>
					</div>
					<span class="expand-chevron">▼</span>
				</div>

				<div class="card-details-drawer">
					<div class="detail-kv"><span>Real IP / TUN:</span><strong>${c.real_ip} / ${c.virt_ip}</strong></div>
					<div class="detail-kv"><span>Подключён:</span><strong>${formatTs(c.last_connected_at)}</strong></div>
					<div class="detail-kv"><span>Отключён:</span><strong>${formatTs(c.last_disconnected_at)}</strong></div>
					<div class="detail-kv"><span>Срок:</span><strong>${c.created} → ${c.expires}</strong></div>
					<div class="detail-kv"><span>Лимит:</span><strong>${c.speed_limit_kbps > 0 ? c.speed_limit_kbps + ' kbps' : '—'}</strong></div>
					<div class="card-actions">${actionsHtml}</div>
				</div>
			</div>
		`;
	}).join('');
}

// Лимиты скорости
function renderSpeedLimitsEditor() {
	const mode = document.getElementById('speedLimitMode')?.value || panelConfig.speed_limit_mode || 'none';
	let selected = [];
	try { selected = JSON.parse(panelConfig.selected_limit_clients || '[]'); } catch (e) {}
	const selSet = new Set(selected);

	const box = document.getElementById('speedLimitsClientsBox');
	if (!box) return;
	const validClients = allClientsList.filter(c => c.status === 'valid');
	if (!validClients.length) {
		box.innerHTML = `<div style="padding:18px; text-align:center; color:var(--text-muted);">Нет активных клиентов</div>`;
		return;
	}

	box.innerHTML = validClients.map(c => {
		const checked = selSet.has(c.name) ? 'checked' : '';
		const perVal = c.speed_limit_kbps || 0;
		return `
			<div class="domain-row">
				<label style="display:flex; align-items:center; gap:8px; cursor:pointer; flex:1;">
					<input type="checkbox" class="limit-client-cb" data-client="${c.name}" ${checked} ${mode !== 'selected' ? 'disabled' : ''}>
					<span style="font-weight:600; font-size:12.5px;">${c.name}</span>
				</label>
				<input type="number" min="0" step="64" class="search-input limit-per-client-input" data-client="${c.name}" value="${perVal}" placeholder="kbps" style="width:110px; padding:5px 8px; font-size:12px;" ${mode !== 'per_client' ? 'disabled' : ''}>
			</div>
		`;
	}).join('');
}

async function saveSpeedLimits() {
	const mode = document.getElementById('speedLimitMode').value;
	const globalKbps = parseInt(document.getElementById('globalSpeedLimitKbps').value) || 0;
	const selectedClients = Array.from(document.querySelectorAll('.limit-client-cb:checked')).map(el => el.dataset.client);
	const perClientLimits = {};
	document.querySelectorAll('.limit-per-client-input').forEach(el => {
		perClientLimits[el.dataset.client] = parseInt(el.value) || 0;
	});

	try {
		const r = await fetch('/api/speed-limits', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			body: JSON.stringify({
				speed_limit_mode: mode,
				global_speed_limit_kbps: globalKbps,
				selected_limit_clients: selectedClients,
				per_client_limits: perClientLimits,
			})
		});
		const d = await r.json();
		if (d.success) {
			panelConfig.speed_limit_mode = mode;
			panelConfig.global_speed_limit_kbps = String(globalKbps);
			panelConfig.selected_limit_clients = JSON.stringify(selectedClients);
			showToast('✅ Лимиты скорости применены');
			loadClients();
		} else {
			showToast('❌ ' + (d.message || 'Ошибка'), 'error');
		}
	} catch (e) { showToast('❌ Ошибка сети', 'error'); }
}

// График скорости
function initSpeedChart() {
	const ctx = document.getElementById('speedChartCanvas').getContext('2d');
	speedChart = new Chart(ctx, {
		type: 'line',
		data: { labels: [], datasets: [] },
		options: {
			responsive: true, maintainAspectRatio: false, animation: false,
			scales: {
				x: { ticks: { color: '#64748b' } },
				y: { beginAtZero: true, ticks: { color: '#64748b', callback: v => formatSpeed(v) } }
			}
		}
	});
}
function setWindowTime(sec) { selectedWindowSeconds = sec; fetchHistoryAndSync(); }
async function fetchHistoryAndSync() {
	try {
		const r = await fetch(`/api/clients/speeds/history?seconds=${selectedWindowSeconds}`);
		const d = await r.json();
		if (d.history) { speedDataPoints = d.history; renderChartData(); }
	} catch (e) {}
}
function renderChartData() {
	if (!speedChart) return;
	const metric = document.getElementById('chartMetricType').value;
	const target = document.getElementById('chartClientFilter').value;
	const names = new Set();
	speedDataPoints.forEach(p => Object.keys(p.speeds || {}).forEach(c => { if (target === '__ALL__' || target === c) names.add(c); }));
	speedChart.data.labels = speedDataPoints.map(p => p.time);
	speedChart.data.datasets = Array.from(names).map((c, idx) => ({
		label: c,
		data: speedDataPoints.map(p => (p.speeds && p.speeds[c]) ? (p.speeds[c][metric] || 0) : 0),
		borderColor: colorPalette[idx % colorPalette.length],
		borderWidth: 2, pointRadius: 0
	}));
	speedChart.update('none');
}
async function pollSpeedTick() {
	if (document.hidden) return;
	try {
		const r = await fetch('/api/clients/speeds');
		const d = await r.json();
		if (!d.speeds) return;
		latestLiveSpeeds = d.speeds;
		const nowTs = Date.now() / 1000;
		speedDataPoints.push({ time: d.timestamp, ts: nowTs, speeds: d.speeds });
		speedDataPoints = speedDataPoints.filter(p => p.ts >= nowTs - selectedWindowSeconds);
		let td = 0, tu = 0;
		Object.values(d.speeds).forEach(s => { td += s.down || 0; tu += s.up || 0; });
		document.getElementById('liveTotalDown').textContent = formatSpeed(td);
		document.getElementById('liveTotalUp').textContent = formatSpeed(tu);
		document.getElementById('liveActiveCount').textContent = Object.keys(d.speeds).length;
		if (document.getElementById('tab-speed').classList.contains('active')) renderChartData();
	} catch (e) {}
}
function changePollInterval() {
	const ms = parseInt(document.getElementById('chartPollInterval').value) || 1000;
	if (speedPollTimer) clearInterval(speedPollTimer);
	speedPollTimer = setInterval(pollSpeedTick, ms);
}

async function pollSystemStats() {
	if (document.hidden || panelConfig.enable_hardware_bar !== "1") return;
	try {
		const r = await fetch('/api/system/stats');
		const d = await r.json();
		if (d.stats) {
			document.getElementById('hwCpu').textContent = `${d.stats.cpu}%`;
			document.getElementById('hwRam').textContent = `${d.stats.ram_used} / ${d.stats.ram_total} MB`;
			document.getElementById('hwDisk').textContent = `${d.stats.disk_used} / ${d.stats.disk_total} GB`;
			document.getElementById('hwPing').textContent = d.stats.wg_ping;
		}
	} catch (e) {}
}

// Действия с клиентами и настройками
async function submitCreateClient() {
	const name = document.getElementById('newClientName').value.trim();
	const note = document.getElementById('newClientNote').value.trim();
	const ttl_days = parseInt(document.getElementById('newClientTtl').value) || 0;
	if (!name) return;
	closeModals();
	const r = await fetch('/api/clients', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, note, ttl_days }) });
	const d = await r.json();
	if (d.success) { showToast('✅ Клиент создан'); await loadClients(); downloadClientConfig(name); }
	else showToast('❌ ' + (d.message || 'Ошибка'), 'error');
}
async function togglePauseClient(name) {
	const r = await fetch(`/api/clients/${encodeURIComponent(name)}/pause`, { method: 'POST' });
	const d = await r.json();
	if (d.success) { showToast(d.is_paused ? '⏸️ На паузе' : '▶️ Активен'); loadClients(); }
}
async function revokeClient(name, permanent) {
	if (!confirm(permanent ? `Удалить ${name} навсегда?` : `Отозвать сертификат ${name}?`)) return;
	const r = await fetch(`/api/clients/${encodeURIComponent(name)}?permanent=${permanent}`, { method: 'DELETE' });
	const d = await r.json();
	if (d.success) { showToast('✅ Готово'); loadClients(); }
	else showToast('❌ ' + (d.message || 'Ошибка'), 'error');
}
function downloadClientConfig(name) { location.href = `/api/clients/${encodeURIComponent(name)}/download`; }
function copyShareUrl(token) {
	const link = `${location.origin}/d/${encodeURIComponent(token)}`;
	copyToClipboard(link).then(() => showToast('✅ Ссылка скопирована'));
}
function showQrModal(name, token) {
	const link = `${location.origin}/d/${encodeURIComponent(token)}`;
	document.getElementById('qrModalTitle').textContent = `📱 ${name}`;
	new QRious({ element: document.getElementById('qrCanvas'), value: link, size: 200, level: 'M' });
	document.getElementById('qrCopyBtn').onclick = () => copyToClipboard(link).then(() => showToast('✅ Скопировано'));
	document.getElementById('qrModal').classList.add('active');
}

async function loadRoutingView() {
	const r = await fetch('/api/routing/status');
	const d = await r.json();
	document.getElementById('ipsetSubnetsCount').textContent = d.ipset_count;
	document.getElementById('cidrUrlInput').value = d.cidr_url || '';
	document.getElementById('customCidrsInput').value = d.custom_cidrs || '';
	document.getElementById('routingModeSelect').value = d.routing_mode || 'off';
	document.getElementById('wgText').textContent = d.wg_up ? 'АКТИВЕН' : 'ОТКЛЮЧЕН';
	document.getElementById('torrentBlockCheck').checked = Boolean(d.torrent_block);
	await loadAdblockStatus();
}
async function saveRoutingSettings() {
	const r = await fetch('/api/routing/settings', {
		method: 'POST', headers: {'Content-Type':'application/json'},
		body: JSON.stringify({
			cidr_url: document.getElementById('cidrUrlInput').value.trim(),
			custom_cidrs: document.getElementById('customCidrsInput').value.trim(),
			routing_mode: document.getElementById('routingModeSelect').value,
			torrent_block: document.getElementById('torrentBlockCheck').checked
		})
	});
	const d = await r.json();
	if (d.success) { showToast('✅ Сохранено'); loadRoutingView(); }
}
async function updateCidrIps() {
	const r = await fetch('/api/routing/update_ips', { method: 'POST' });
	const d = await r.json();
	if (d.async && d.task_id) watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ CIDR обновлены'); loadRoutingView(); } });
}
async function setupRemoteTunnel() {
	const remote_ip = document.getElementById('remoteServerIp').value.trim();
	const remote_pass = document.getElementById('remoteServerPass').value;
	if (!remote_ip || !remote_pass) return showToast('❌ Укажите IP и пароль', 'error');
	const r = await fetch('/api/routing/setup', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ remote_ip, remote_pass }) });
	const d = await r.json();
	if (d.async && d.task_id) watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ Туннель настроен'); loadRoutingView(); } });
}

async function loadAdblockStatus() {
	const r = await fetch('/api/adblock/status');
	const j = await r.json();
	if (!j.success) return;
	const d = j.data;
	document.getElementById('adblockEnableToggle').checked = Boolean(d.enabled);
	document.getElementById('adblockStatusLabel').textContent = `Статус: ${d.enabled ? '🟢 АКТИВЕН' : '⚪ ОТКЛЮЧЕН'} | Правил: ${d.blocked_total}`;
	document.getElementById('adblockListsBox').innerHTML = (d.lists || []).map(l => `
		<div class="domain-row"><span class="domain-name">${l.url} (${l.domains_count})</span><button class="btn btn-sm btn-danger" onclick="deleteAdblockList(${l.id})">✕</button></div>
	`).join('') || '<div style="padding:12px; color:var(--text-muted);">Списков нет</div>';
	document.getElementById('adblockDomainsBox').innerHTML = (d.domains || []).map(dom => `
		<div class="domain-row"><span class="domain-name">${dom.domain} [${dom.list_type}]</span><button class="btn btn-sm btn-danger" onclick="deleteAdblockDomain(${dom.id})">✕</button></div>
	`).join('') || '<div style="padding:12px; color:var(--text-muted);">Доменов нет</div>';
}
async function toggleAdblock(enable) {
	const r = await fetch('/api/adblock/toggle', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ enable }) });
	const d = await r.json();
	if (d.async && d.task_id) watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ AdBlock обновлён'); loadAdblockStatus(); } });
}
async function addAdblockList() {
	const url = document.getElementById('adblockListUrl').value.trim();
	const list_type = document.getElementById('adblockListType').value;
	if (!url) return;
	const r = await fetch('/api/adblock/lists', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ url, list_type }) });
	const d = await r.json();
	if (d.async && d.task_id) {
		document.getElementById('adblockListUrl').value = '';
		watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ Список загружен'); loadAdblockStatus(); } });
	}
}
async function deleteAdblockList(id) { await fetch(`/api/adblock/lists/${id}`, { method: 'DELETE' }); loadAdblockStatus(); }
async function addAdblockDomain() {
	const domain = document.getElementById('adblockDomainInput').value.trim();
	const list_type = document.getElementById('adblockDomainType').value;
	if (!domain) return;
	const r = await fetch('/api/adblock/domains', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ domain, list_type }) });
	const d = await r.json();
	if (d.success) { document.getElementById('adblockDomainInput').value = ''; loadAdblockStatus(); }
}
async function deleteAdblockDomain(id) { await fetch(`/api/adblock/domains/${id}`, { method: 'DELETE' }); loadAdblockStatus(); }

async function loadConfigView() {
	const r = await fetch('/api/config');
	const d = await r.json();
	if (d.success) document.getElementById('serverConfigText').value = d.config;
}
async function saveRawConfig(restart) {
	const r = await fetch('/api/config', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ config: document.getElementById('serverConfigText').value, restart }) });
	const d = await r.json();
	if (d.success) showToast('✅ server.conf сохранён');
}

async function loadSettingsView() {
	const r = await fetch('/api/settings');
	const d = await r.json();
	if (d.success && d.settings) {
		panelConfig = { ...panelConfig, ...d.settings };
		document.getElementById('setAdminLogin').value = d.settings.admin_login || '';
		document.getElementById('setPanelPort').value = d.settings.panel_port || 8080;
		document.getElementById('setOvpnDomain').value = d.settings.ovpn_domain || '';
		document.getElementById('setEnableSpeed').checked = d.settings.enable_speed_monitor !== "0";
		document.getElementById('setEnableHwBar').checked = d.settings.enable_hardware_bar !== "0";
		document.getElementById('setTorrentBlock').checked = d.settings.torrent_block === "1";
		document.getElementById('speedLimitMode').value = d.settings.speed_limit_mode || 'none';
		document.getElementById('globalSpeedLimitKbps').value = d.settings.global_speed_limit_kbps || 0;
		document.getElementById('hardwareBar').style.display = panelConfig.enable_hardware_bar === "1" ? 'grid' : 'none';
		document.getElementById('tabBtnSpeed').style.display = panelConfig.enable_speed_monitor === "1" ? 'block' : 'none';
	}
}
async function saveAllAccountSettings(apply_to_ovpn) {
	const r = await fetch('/api/settings', {
		method: 'POST', headers: {'Content-Type':'application/json'},
		body: JSON.stringify({
			admin_login: document.getElementById('setAdminLogin').value.trim(),
			admin_password: document.getElementById('setAdminPass').value,
			panel_port: parseInt(document.getElementById('setPanelPort').value) || 8080,
			ovpn_domain: document.getElementById('setOvpnDomain').value.trim(),
			enable_speed_monitor: document.getElementById('setEnableSpeed').checked ? "1" : "0",
			enable_hardware_bar: document.getElementById('setEnableHwBar').checked ? "1" : "0",
			torrent_block: document.getElementById('setTorrentBlock').checked ? "1" : "0",
			apply_to_ovpn
		})
	});
	const d = await r.json();
	if (d.success) { showToast('✅ Настройки сохранены'); loadSettingsView(); }
}
async function controlOvpnService(action) {
	const r = await fetch(`/api/service/${action}`, { method: 'POST' });
	const d = await r.json();
	if (d.success) { showToast(`✅ ${action} OK`); setTimeout(loadClients, 800); }
}

function downloadBackupArchive() { location.href = '/api/backup'; closeModals(); }
async function processRestoreFile(e) {
	const file = e.target.files[0];
	if (!file || !confirm('Перезаписать текущую конфигурацию?')) return;
	closeModals();
	const fd = new FormData();
	fd.append('file', file);
	const r = await fetch('/api/restore', { method: 'POST', body: fd });
	const d = await r.json();
	if (d.success) { showToast('✅ Восстановлено'); setTimeout(() => location.reload(), 1200); }
}

document.addEventListener('DOMContentLoaded', async () => {
	initSpeedChart();
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
	<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
	<script src="https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js"></script>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		body {
			font-family: 'Plus Jakarta Sans', sans-serif; background: #090d16; color: #f1f5f9;
			min-height: 100vh; display: flex; justify-content: center; align-items: center; padding: 20px;
		}
		.card {
			width: 100%; max-width: 420px; background: #0f172a; border: 1px solid #1e293b;
			border-radius: 20px; padding: 32px 26px; text-align: center;
		}
		h1 { font-size: 20px; margin-bottom: 8px; word-break: break-all; }
		p { font-size: 13px; color: #94a3b8; margin-bottom: 20px; }
		.qr-box { background: #fff; padding: 14px; border-radius: 16px; display: inline-block; margin-bottom: 20px; }
		.btn {
			width: 100%; padding: 13px; background: linear-gradient(135deg, #3b82f6, #2563eb);
			border-radius: 10px; color: #fff; font-size: 14px; font-weight: 600;
			text-decoration: none; display: inline-flex; justify-content: center; margin-bottom: 10px;
		}
	</style>
</head>
<body>
<div class="card">
	<h1>{client_name}</h1>
	<p>Скачайте профиль и откройте его в OpenVPN Connect</p>
	<div class="qr-box"><canvas id="qrCanvas"></canvas></div>
	<a href="/d/{token}/raw" class="btn">⬇️ Скачать .ovpn профиль</a>
</div>
<script>
	new QRious({ element: document.getElementById('qrCanvas'), value: window.location.href, size: 190, level: 'M' });
</script>
</body>
</html>
"""