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

MAIN_HTML = r"""
<!DOCTYPE html>
<html lang="ru">
<head>
	<meta charset="UTF-8">
	<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
	<title>OpenVPN Control Center Ultimate</title>
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
			--purple: #8b5cf6;
			--cyan: #06b6d4;
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
		[data-theme="light"] .d-tab-btn.active,
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
		[data-theme="light"] .domain-row:hover {
			background: #f1f5f9;
		}
		[data-theme="light"] .domain-name {
			color: #1d4ed8;
		}
		[data-theme="light"] .domain-count-badge {
			color: #1d4ed8;
			background: rgba(37, 99, 235, 0.12);
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
		*::-webkit-scrollbar-corner { background: transparent; }

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
			color: #fff;
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

		.task-progress-banner {
			display: none;
			background: var(--bg-card);
			border: 1px solid rgba(59, 130, 246, 0.45);
			border-radius: var(--radius-md);
			padding: 12px 18px;
			margin-bottom: 20px;
			box-shadow: var(--shadow-sm);
		}
		.task-progress-banner.active { display: block; }
		.task-progress-top { display: flex; justify-content: space-between; font-size: 12.5px; margin-bottom: 8px; gap: 10px; }
		.progress-track { width: 100%; height: 7px; background: var(--bg-input); border-radius: 99px; overflow: hidden; }
		.progress-fill { height: 100%; width: 0%; background: linear-gradient(90deg, #3b82f6, #10b981); transition: width 0.25s ease; }

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
		.status-badge.active { color: #34d399; background: rgba(16, 185, 129, 0.1); }
		.status-badge.inactive { color: #f87171; background: rgba(239, 68, 68, 0.1); }

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
		.search-wrapper .search-input { width: 100%; padding-right: 36px; }
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
		.search-clear-btn:hover { background: rgba(239, 68, 68, 0.25); color: #f87171; }
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
		@media (max-width: 1400px) { .clients-grid { grid-template-columns: repeat(3, 1fr); } }
		@media (max-width: 1000px) { .clients-grid { grid-template-columns: repeat(2, 1fr); } }
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
		.client-name { font-size: 15px; font-weight: 700; word-break: break-all; line-height: 1.3; color: #fff; }
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
		.client-badge.valid { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
		.client-badge.paused { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
		.client-badge.revoked { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }

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
		.card-details { font-size: 12px; color: var(--text-dim); line-height: 1.55; margin-bottom: 10px; }
		.session-meta {
			background: rgba(16, 185, 129, 0.05);
			border: 1px solid rgba(16, 185, 129, 0.18);
			border-radius: var(--radius-sm);
			padding: 8px 10px;
			margin: 8px 0;
			font-size: 11.5px;
			color: #cbd5e1;
		}
		.session-meta.offline-meta { background: var(--bg-input); border-color: var(--border-subtle); color: var(--text-muted); }
		.session-row { display: flex; justify-content: space-between; gap: 8px; align-items: center; flex-wrap: wrap; }
		.session-row span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
		.session-row strong { font-family: 'JetBrains Mono', monospace; color: #e2e8f0; font-weight: 600; }
		.live-speed-row { display: flex; justify-content: space-between; margin-top: 6px; font-weight: 600; font-family: 'JetBrains Mono', monospace; font-size: 11.5px; }
		.card-traffic {
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			padding: 9px 11px;
			border-radius: var(--radius-sm);
			display: flex;
			justify-content: space-between;
			align-items: center;
			margin-top: 8px;
			font-size: 12px;
			gap: 8px;
		}
		.traffic-main { font-weight: 600; color: var(--text-main); }
		.traffic-sub { font-size: 10.5px; color: var(--text-muted); margin-top: 3px; }
		.card-extra-meta {
			margin-top: 8px;
			padding: 7px 10px;
			background: var(--bg-input);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-sm);
			font-size: 11px;
			color: var(--text-dim);
		}
		.card-extra-line { display: flex; justify-content: space-between; gap: 6px; margin-bottom: 3px; }
		.card-extra-line:last-child { margin-bottom: 0; }
		.card-extra-line strong { font-family: 'JetBrains Mono', monospace; color: var(--text-main); }

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
			min-width: 36px; height: 36px; padding: 0 10px; border-radius: var(--radius-sm);
			border: 1px solid var(--border-subtle); background: var(--bg-input); color: var(--text-main);
			font-size: 13px; font-weight: 600; cursor: pointer; display: inline-flex;
			align-items: center; justify-content: center; transition: all 0.15s; font-family: inherit;
		}
		.page-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); background: rgba(59, 130, 246, 0.08); }
		.page-btn.active { background: linear-gradient(135deg, #3b82f6, #2563eb); border-color: transparent; color: #fff; box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3); }
		.page-btn:disabled { opacity: 0.4; cursor: not-allowed; }

		.chart-wrapper {
			background: var(--bg-card);
			border: 1px solid var(--border-subtle);
			border-radius: var(--radius-lg);
			padding: 24px;
			box-shadow: var(--shadow-sm);
		}
		.chart-wrapper h3 { font-size: 16px; font-weight: 700; color: #fff; margin-bottom: 16px; display: flex; align-items: center; gap: 8px; }
		.chart-toolbar { display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; margin-bottom: 20px; }
		.chart-toolbar h3 { margin-bottom: 4px; }
		.chart-toolbar p { font-size: 12.5px; color: var(--text-muted); }
		.chart-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
		.btn-group { display: inline-flex; border-radius: var(--radius-sm); overflow: hidden; border: 1px solid var(--border-subtle); background: var(--bg-input); }
		.btn-group-btn {
			background: transparent; border: none; padding: 9px 16px; font-size: 12.5px; color: var(--text-muted);
			cursor: pointer; transition: all 0.15s; border-right: 1px solid var(--border-subtle); font-weight: 600; font-family: inherit;
		}
		.btn-group-btn:last-child { border-right: none; }
		.btn-group-btn:hover { color: var(--text-main); background: #1e293b; }
		.btn-group-btn.active { background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; }
		.chart-canvas-box { position: relative; height: 420px; width: 100%; margin-bottom: 20px; }
		.chart-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; }
		.stat-pill {
			background: var(--bg-input); border: 1px solid var(--border-subtle); padding: 14px 18px;
			border-radius: var(--radius-md); font-size: 12.5px; color: var(--text-muted);
			display: flex; justify-content: space-between; align-items: center; gap: 12px;
		}
		.stat-pill strong { color: var(--text-main); font-size: 15px; font-weight: 700; font-family: 'JetBrains Mono', monospace; }

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
		.settings-card h3 { font-size: 16px; font-weight: 700; color: #fff; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
		.settings-card .card-desc { font-size: 12.5px; color: var(--text-muted); line-height: 1.5; }
		.settings-card input:not([type="checkbox"]), .settings-card select, .settings-card textarea { max-width: 100%; width: 100%; }
		.limit-client-cb { width: 18px !important; height: 18px !important; accent-color: var(--primary); cursor: pointer; flex-shrink: 0; }
		.speed-presets { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
		.preset-btn {
			padding: 5px 10px; border-radius: 6px; font-size: 11.5px; font-weight: 600;
			background: var(--bg-input); border: 1px solid var(--border-subtle); color: var(--text-dim);
			cursor: pointer; transition: all 0.15s;
		}
		.preset-btn:hover { border-color: var(--primary); color: var(--text-main); background: rgba(59, 130, 246, 0.12); }
		.limit-row {
			display: flex; justify-content: space-between; align-items: center; gap: 12px;
			padding: 10px 12px; border-bottom: 1px solid rgba(148, 163, 184, 0.08);
		}
		.limit-row:last-child { border-bottom: none; }
		.limit-row-left { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
		.limit-row-name { font-weight: 600; font-size: 13px; color: var(--text-main); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
		.limit-row-right { display: flex; align-items: center; gap: 6px; flex-shrink: 0; }

		.form-group { margin-bottom: 0; min-width: 0; }
		.form-label { font-size: 11.5px; color: var(--text-dim); display: block; margin-bottom: 6px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.4px; }
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
		.switch-info strong { font-size: 13px; display: block; color: #f1f5f9; margin-bottom: 3px; font-weight: 600; line-height: 1.35; }
		.switch-info span { font-size: 11.5px; color: var(--text-muted); line-height: 1.4; display: block; }
		.toggle-switch { position: relative; display: inline-block; width: 44px; height: 24px; flex-shrink: 0; cursor: pointer; }
		.toggle-switch input { opacity: 0; width: 0; height: 0; }
		.toggle-slider { position: absolute; inset: 0; background: #334155; border-radius: 24px; transition: 0.2s; }
		.toggle-slider:before { position: absolute; content: ""; height: 18px; width: 18px; left: 3px; bottom: 3px; background: white; border-radius: 50%; transition: 0.2s; }
		.toggle-switch input:checked + .toggle-slider { background: linear-gradient(135deg, #3b82f6, #2563eb); }
		.toggle-switch input:checked + .toggle-slider:before { transform: translateX(20px); }

		.modal-overlay {
			display: none; position: fixed; inset: 0; background: rgba(0, 0, 0, 0.75);
			backdrop-filter: blur(8px); z-index: 1000; justify-content: center; align-items: center; padding: 14px; animation: fadeIn 0.15s ease;
		}
		.modal-overlay.active { display: flex; }
		.modal-card {
			background: #0f172a; border: 1px solid var(--border-subtle); border-radius: var(--radius-xl);
			padding: 28px; max-width: 480px; width: 100%; box-shadow: var(--shadow-lg); max-height: 90vh;
			display: flex; flex-direction: column; overflow: hidden;
		}
		.modal-card.modal-lg { max-width: 760px; }
		.modal-card h2 { font-size: 19px; margin-bottom: 6px; font-weight: 700; color: #fff; }
		.modal-card p { font-size: 13px; color: var(--text-muted); margin-bottom: 18px; line-height: 1.5; }

		.domains-tabs { display: flex; gap: 6px; margin-bottom: 14px; background: var(--bg-input); padding: 5px; border-radius: var(--radius-sm); border: 1px solid var(--border-subtle); }
		.d-tab-btn { background: transparent; border: none; border-radius: 6px; padding: 8px 16px; font-size: 12.5px; color: var(--text-muted); cursor: pointer; font-weight: 600; font-family: inherit; transition: all 0.15s; flex: 1; }
		.d-tab-btn:hover { color: var(--text-main); }
		.d-tab-btn.active { background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; box-shadow: 0 2px 8px rgba(59, 130, 246, 0.3); }
		.d-tab-view { display: none; flex: 1; overflow-y: auto; max-height: 380px; padding-right: 4px; }
		.d-tab-view.active { display: block; }

		.domains-list-box { background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 6px; }
		.domain-row { display: flex; justify-content: space-between; align-items: center; padding: 10px 14px; border-radius: 6px; font-size: 13px; gap: 10px; transition: background 0.15s; }
		.domain-row-main { display: flex; align-items: center; gap: 10px; min-width: 0; flex: 1; }
		.domain-row-meta { display: flex; align-items: center; gap: 12px; }
		.domain-row:hover { background: #1e293b; }
		.domain-name { font-family: 'JetBrains Mono', monospace; color: #93c5fd; word-break: break-all; font-weight: 500; font-size: 12.5px; }
		.domain-time { font-size: 11px; color: var(--text-muted); white-space: nowrap; font-family: 'JetBrains Mono', monospace; }
		.domain-count-badge { font-size: 10.5px; padding: 2px 7px; background: rgba(59, 130, 246, 0.15); color: #60a5fa; border-radius: 10px; font-weight: 600; font-family: 'JetBrains Mono', monospace; }

		.toast {
			position: fixed; bottom: 30px; right: 30px; background: #1e293b; border: 1px solid var(--border-subtle);
			border-radius: var(--radius-md); padding: 14px 20px; font-size: 13.5px; font-weight: 500;
			box-shadow: var(--shadow-lg); transform: translateY(20px); opacity: 0;
			transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1); z-index: 2000; pointer-events: none; max-width: 380px;
		}
		.toast.show { transform: translateY(0); opacity: 1; }
		.toast.success { border-left: 4px solid var(--success); }
		.toast.error { border-left: 4px solid var(--danger); }

		.routing-grid { display: grid; grid-template-columns: 1fr 2fr; gap: 20px; align-items: start; }
		.routing-grid-left { display: flex; flex-direction: column; gap: 20px; }
		.routing-spoiler { background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 12px 14px; margin-top: 6px; transition: all 0.2s; }
		.routing-spoiler[open] { border-color: rgba(59, 130, 246, 0.3); }
		.routing-spoiler summary { font-size: 13px; font-weight: 600; color: #f1f5f9; cursor: pointer; user-select: none; display: flex; align-items: center; justify-content: space-between; outline: none; }
		.routing-spoiler summary::-webkit-details-marker { display: none; }
		.routing-spoiler summary::after { content: '▼'; font-size: 10px; color: var(--text-muted); transition: transform 0.2s; }
		.routing-spoiler[open] summary::after { transform: rotate(180deg); color: var(--primary); }
		.routing-spoiler-content { margin-top: 14px; display: flex; flex-direction: column; gap: 12px; }
		.wg-status-row { display: flex; justify-content: space-between; padding: 10px 0; font-size: 13px; border-bottom: 1px solid var(--border-subtle); }
		.wg-status-row:last-child { border-bottom: none; }
		.wg-status-row span { color: var(--text-muted); }
		.wg-status-row strong { font-family: 'JetBrains Mono', monospace; font-weight: 600; }

		.hint-box {
			padding: 14px;
			background: rgba(59, 130, 246, 0.05);
			border: 1px solid rgba(59, 130, 246, 0.15);
			border-radius: var(--radius-md);
			font-size: 12.5px;
			color: var(--text-dim);
			line-height: 1.55;
		}
		.hint-box strong { color: #60a5fa; }

		.pending-link-row { background: rgba(59, 130, 246, 0.06); border: 1px solid rgba(59, 130, 246, 0.25); border-radius: var(--radius-md); padding: 12px 14px; display: flex; flex-direction: column; gap: 10px; margin-bottom: 10px; }
		.pending-link-row .pending-actions { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
		.route-via-group { display: inline-flex; border-radius: 6px; overflow: hidden; border: 1px solid var(--border-subtle); background: var(--bg-input); }
		.route-via-btn { background: transparent; border: none; padding: 6px 12px; font-size: 11.5px; color: var(--text-muted); cursor: pointer; font-weight: 600; font-family: inherit; transition: all 0.15s; border-right: 1px solid var(--border-subtle); }
		.route-via-btn:last-child { border-right: none; }
		.route-via-btn:hover { color: var(--text-main); background: #1e293b; }
		.route-via-btn.active { background: linear-gradient(135deg, #3b82f6, #2563eb); color: #fff; }

		@media (max-width: 1024px) { .hardware-bar { grid-template-columns: repeat(2, 1fr); } }
		@media (max-width: 768px) {
			body { padding: 12px 10px 40px; }
			.domain-row { flex-direction: column; align-items: stretch !important; gap: 8px !important; padding: 12px 10px !important; }
			.domain-row-main { display: flex; align-items: flex-start; gap: 8px; width: 100%; }
			.domain-row-meta { display: flex; justify-content: space-between; align-items: center; width: 100%; padding-top: 4px; border-top: 1px dashed var(--border-subtle); }
			.domain-name { word-break: break-all !important; white-space: normal !important; line-height: 1.4 !important; font-size: 13px !important; }
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
			.d-tab-btn { padding: 7px 10px; font-size: 12px; }
		}
	</style>
</head>
<body>
<div class="container" style="padding-bottom: 20px;">
	<header class="header">
		<div class="brand">
			<div class="brand-text">
				<h1>OpenVPN Dashboard</h1>
				<p>Ultimate Control Center & Analytics</p>
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
				<span>+</span> <span>Создать</span>
			</button>
			<button class="btn" onclick="openBackupModal()">
				<span>📦</span> <span>Бэкап</span>
			</button>
			<a href="/logout" class="btn btn-danger">
				<span>🚪</span> <span>Выйти</span>
			</a>
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
		<div class="banner-item"><span>Сервер:</span><code id="bannerEndpointCode">{{ domain }}:{{ port }} ({{ proto }})</code></div>
		<div class="banner-item"><span id="serverStatusText" class="status-badge active">● ...</span></div>
		<div class="banner-item"><span>Онлайн:</span><strong id="activeClientsCount" style="color:var(--primary);">0 / 0</strong></div>
		<div class="banner-item" style="color:var(--text-muted); font-size:12.5px;" id="lastSyncTime">—</div>
	</div>

	<div class="tabs-bar">
		<div class="tab-btn active" id="tabBtnClients" onclick="switchTab('tab-clients')">👥 Клиенты</div>
		<div class="tab-btn" id="tabBtnSpeed" onclick="switchTab('tab-speed')">📈 Скорость</div>
		<div class="tab-btn" id="tabBtnDomains" onclick="switchTab('tab-domains')">🌐 Сайты</div>
		<div class="tab-btn" id="tabBtnInfographics" onclick="switchTab('tab-infographics')">📊 Инфографика</div>
		<div class="tab-btn" id="tabBtnLimits" onclick="switchTab('tab-limits')">⚡ Лимиты</div>
		<div class="tab-btn" id="tabBtnRouting" onclick="switchTab('tab-routing')">🔀 Маршрутизация</div>
		<div class="tab-btn" id="tabBtnConfig" onclick="switchTab('tab-config')">⚙️ Конфигурация</div>
		<div class="tab-btn" id="tabBtnSettings" onclick="switchTab('tab-settings')">🔐 Аккаунт</div>
	</div>

	<!-- VIEW: CLIENTS -->
	<div id="tab-clients" class="tab-view active">
		<div class="filter-bar">
			<div class="search-wrapper">
				<input type="text" class="search-input" id="clientSearch" placeholder="🔍 Поиск по имени или IP..." oninput="onFilterInputChange()" autocomplete="off">
				<button type="button" class="search-clear-btn" id="clearSearchBtn" onclick="clearClientSearch()" title="Очистить">✕</button>
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
				<option value="traffic_desc">⬇️ По трафику</option>
				<option value="name_asc">🔤 По имени</option>
			</select>
			<select class="control-select" id="pageSizeSelect" onchange="onPageSizeChange()">
				<option value="20">По 20</option>
				<option value="50">По 50</option>
				<option value="100">По 100</option>
			</select>
		</div>
		<div class="clients-grid" id="clientsGrid">
			<div style="grid-column: 1/-1; text-align:center; padding: 60px 20px; color:var(--text-muted); font-size:14px;">⏳ Загрузка...</div>
		</div>
		<div class="pagination-bar" id="paginationBar" style="display:none;">
			<div class="pagination-info" id="paginationInfo"></div>
			<div class="pagination-pages" id="paginationPages"></div>
		</div>
	</div>

	<!-- VIEW: SPEED -->
	<div id="tab-speed" class="tab-view">
		<div class="chart-wrapper">
			<div class="chart-toolbar">
				<div>
					<h3>Мониторинг скорости в реальном времени</h3>
					<p>Прямой опрос сокета OpenVPN в памяти</p>
				</div>
				<div class="chart-controls">
					<select class="control-select" id="chartClientFilter" onchange="renderChartData()"><option value="__ALL__">👥 Все клиенты</option></select>
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
						<option value="1000">1s</option><option value="3000">3s</option><option value="5000">5s</option><option value="10000">10s</option>
					</select>
				</div>
			</div>
			<div class="chart-canvas-box"><canvas id="speedChartCanvas"></canvas></div>
			<div class="chart-stats">
				<div class="stat-pill"><span>Текущий Download:</span> <strong id="liveTotalDown" style="color:#60a5fa;">0 B/s</strong></div>
				<div class="stat-pill"><span>Текущий Upload:</span> <strong id="liveTotalUp" style="color:#34d399;">0 B/s</strong></div>
				<div class="stat-pill"><span>Активных подключений:</span> <strong id="liveActiveCount">0</strong></div>
			</div>
		</div>
	</div>

	<!-- VIEW: GLOBAL DOMAINS -->
	<div id="tab-domains" class="tab-view">
		<div class="chart-wrapper">
			<div class="chart-toolbar">
				<div>
					<h3>🌐 Журнал посещаемых сайтов</h3>
					<p>История переходов по всем клиентам сервера в реальном времени</p>
				</div>
				<div style="display:flex; gap:8px; align-items:center; width:100%; max-width:680px; flex-wrap:wrap;">
					<div class="search-wrapper" style="flex:1; min-width:180px;">
						<input type="text" id="tabGlobalDomainSearch" class="search-input" placeholder="🔍 Поиск по домену или клиенту..." oninput="onTabGlobalDomainInput()" autocomplete="off">
						<button type="button" class="search-clear-btn" id="clearTabGlobalDomainBtn" onclick="clearTabGlobalDomainSearch()" title="Очистить">✕</button>
					</div>
					<button class="btn btn-primary btn-sm" onclick="fetchTabGlobalDomains()">🔄 Обновить</button>
					<button class="btn btn-sm" onclick="openIgnoredDomainsModal()" title="Управление исключениями">🚫 Исключения</button>
					<button class="btn btn-warning btn-sm" onclick="runDbAction('clear_domains', 'Очистить всю историю сайтов?')">🗑️ Очистить</button>
				</div>
			</div>
			<div class="domains-list-box" id="tabGlobalDomainsListBox" style="max-height:640px; overflow-y:auto; margin-top:10px;">
				<div style="text-align:center; padding:40px; color:var(--text-muted); font-size:13px;">⏳ Загрузка...</div>
			</div>
		</div>
	</div>

	<!-- VIEW: INFOGRAPHICS -->
	<div id="tab-infographics" class="tab-view">
		<div class="chart-stats" style="margin-bottom:20px;">
			<div class="stat-pill"><span>∑ Весь трафик сервера</span> <strong id="infoTotalAll" style="color:#f59e0b;">0 B</strong></div>
			<div class="stat-pill"><span>📥 Суммарный Download</span> <strong id="infoTotalSent" style="color:#60a5fa;">0 B</strong></div>
			<div class="stat-pill"><span>📤 Суммарный Upload</span> <strong id="infoTotalRecv" style="color:#34d399;">0 B</strong></div>
		</div>
		<div class="settings-grid">
			<div class="chart-wrapper"><h3>📊 Топ-10 клиентов по трафику</h3><div style="height:300px; position:relative;"><canvas id="infoTopClientsChart"></canvas></div></div>
			<div class="chart-wrapper"><h3>👥 Распределение статусов</h3><div style="height:300px; position:relative;"><canvas id="infoStatusPieChart"></canvas></div></div>
			<div class="chart-wrapper"><h3>🌐 Топ-10 посещаемых доменов</h3><div style="height:300px; position:relative;"><canvas id="infoTopDomainsChart"></canvas></div></div>
		</div>
	</div>

	<!-- VIEW: SPEED LIMITS -->
	<div id="tab-limits" class="tab-view">
		<div class="settings-grid">
			<div class="settings-card">
				<h3>⚡ Двусторонний лимит скорости (tc + ifb0)</h3>
				<p class="card-desc">Ограничивает скорость в обе стороны (Download + Upload) для активных сессий. 0 = без ограничения.</p>
				<div class="form-group">
					<label class="form-label">Режим ограничения</label>
					<select class="control-select" id="speedLimitMode" onchange="renderSpeedLimitsEditor()">
						<option value="none">⚪ Без ограничения</option>
						<option value="global">🌐 Для всех клиентов (общий лимит)</option>
						<option value="selected">☑️ Для выбранных клиентов (общий лимит)</option>
						<option value="per_client">🎯 Индивидуально для каждого клиента</option>
					</select>
				</div>
				<div class="form-group" id="globalLimitGroup">
					<label class="form-label">Общий лимит скорости (МБ/с)</label>
					<input type="number" min="0" step="0.5" class="search-input" id="globalSpeedLimitMB" value="0" placeholder="Например: 2">
					<div class="speed-presets">
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(0.5)">0.5 МБ/с</button>
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(1)">1 МБ/с</button>
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(2)">2 МБ/с</button>
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(5)">5 МБ/с</button>
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(10)">10 МБ/с</button>
						<button type="button" class="preset-btn" onclick="setGlobalSpeedPreset(0)">∞ Без лимита</button>
					</div>
				</div>
				<button class="btn btn-primary" style="padding:13px; justify-content:center; margin-top:4px;" onclick="saveSpeedLimits()">💾 Применить лимиты скорости</button>
			</div>

			<div class="settings-card" id="speedLimitsClientsCard">
				<h3>👥 Список клиентов для лимитов</h3>
				<p class="card-desc" id="speedLimitsClientsHint">Выберите режим «Для выбранных» или «Индивидуально» для настройки по клиентам.</p>
				<div class="domains-list-box" id="speedLimitsClientsBox" style="max-height:420px; overflow-y:auto;"></div>
			</div>
		</div>
	</div>

	<!-- VIEW: ROUTING -->
	<div id="tab-routing" class="tab-view">
		<div class="routing-grid">
			<div class="routing-grid-left">
				<div class="settings-card">
					<h3>Сплит-туннель (WireGuard + ipset)</h3>
					<p class="card-desc">Маршрутизация через второй VPN-сервер</p>
					<div class="wg-status-row"><span>Статус WG0:</span><strong id="wgText">...</strong></div>
					<div class="wg-status-row"><span>Подсетей в ipset:</span><strong id="ipsetSubnetsCount" style="color:#60a5fa;">...</strong></div>

					<div style="background: var(--bg-input); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 14px; margin: 6px 0;">
						<div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px; margin-bottom:10px;">
							<strong style="font-size:13px;">🔗 Удалённая точка выхода</strong>
							<span id="remoteEndpointStatus" style="font-size:12px; padding:3px 10px; border-radius:12px; font-weight:600;">...</span>
						</div>
						<div id="remoteEndpointConnected" style="display:none; font-size:13px;">
							<span>Подключено к:</span>
							<strong id="remoteEndpointIp" style="font-family:'JetBrains Mono',monospace; color:#34d399;">—</strong>
							<button class="btn btn-sm" style="margin-left:10px;" onclick="showRemoteReconfigure()">Перенастроить</button>
						</div>
						<div id="remoteEndpointForm">
							<div class="form-group" style="margin-bottom:8px;"><input type="text" id="remoteServerIp" class="search-input" placeholder="IP удаленного сервера"></div>
							<div class="form-group" style="margin-bottom:8px;"><input type="text" id="remoteServerPass" class="search-input" placeholder="Пароль root"></div>
							<div style="display:flex; gap:10px;">
								<button class="btn btn-danger" style="justify-content:center; width:50%;" onclick="hideRemoteReconfigure()">❌ Отмена</button>
								<button class="btn btn-success" style="justify-content:center; width:50%;" onclick="setupRemoteTunnel()">🚀 Настроить туннель</button>
							</div>
						</div>
					</div>

					<div class="form-group"><label class="form-label">URL списка подсетей:</label><input type="text" id="cidrUrlInput" class="search-input"></div>
					<div class="form-group"><label class="form-label">Свои IP/подсети:</label><textarea id="customCidrsInput" class="textarea-input" rows="3" placeholder="77.88.8.8/32&#10;192.168.10.0/24"></textarea></div>
					<div class="form-group">
						<label class="form-label">Режим:</label>
						<select class="control-select" id="routingModeSelect">
							<option value="off">🔴 Отключено</option>
							<option value="split">🟡 CIDR напрямую, остальное в WG</option>
							<option value="cidr_wg">🟣 CIDR в WG, остальное напрямую</option>
							<option value="all">🟢 Весь трафик через WireGuard</option>
						</select>
					</div>

					<details class="routing-spoiler">
						<summary><span>🔗 Управление ссылками сплит-туннеля</span></summary>
						<div class="routing-spoiler-content">
							<p style="font-size:12px; color:var(--text-muted); line-height:1.4;">Разрешите URL в IP для выборочной маршрутизации через WireGuard или напрямую.</p>
							<div style="display:flex; gap:8px; flex-wrap:wrap;">
								<input type="text" id="splitLinkUrl" class="search-input" placeholder="https://example.com" style="flex:1; min-width:180px;">
								<button class="btn btn-primary btn-sm" onclick="resolveLink()">🔍 Найти IP</button>
							</div>
							<div id="pendingLinksBox"></div>
							<div class="domains-list-box" id="splitLinksList" style="max-height:220px; overflow-y:auto;"></div>
						</div>
					</details>

					<div style="display:flex; gap:10px; flex-wrap:wrap; margin-top:8px;">
						<button class="btn btn-primary" onclick="saveRoutingSettings()">💾 Сохранить</button>
						<button class="btn" onclick="updateCidrIps()">🔄 Обновить CIDR</button>
					</div>
				</div>
			</div>

			<div class="settings-card">
				<h3>🛡️ Блокировка рекламы (DNS AdBlock / dnsmasq)</h3>
				<p class="card-desc">Автоматическая фильтрация рекламы и трекеров на уровне VPN-сервера без потери скорости</p>
				<div class="switch-row">
					<div class="switch-info">
						<strong>Включить блокировку рекламы для всех клиентов</strong>
						<span id="adblockStatusLabel">...</span>
					</div>
					<label class="toggle-switch"><input type="checkbox" id="adblockEnableToggle" onchange="toggleAdblock(this.checked)"><span class="toggle-slider"></span></label>
				</div>
				<div class="form-row-2" style="margin-top:4px;">
					<div style="background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px; min-width:0;">
						<label class="form-label">📋 Добавить AdList по ссылке</label>
						<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
							<input type="text" id="adblockListUrl" class="search-input" placeholder="https://..." style="flex:1; min-width:140px;">
							<select class="control-select" id="adblockListType"><option value="black">⚫ Черный список</option><option value="white">⚪ Белый список</option></select>
							<button class="btn btn-primary" onclick="addAdblockList()">➕ Добавить</button>
						</div>
						<div class="domains-list-box" id="adblockListsBox" style="max-height:360px; overflow-y:auto;"></div>
					</div>
					<div style="background:var(--bg-input); border:1px solid var(--border-subtle); border-radius:var(--radius-md); padding:14px; min-width:0;">
						<label class="form-label">🌐 Добавить отдельный домен</label>
						<div style="display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px;">
							<input type="text" id="adblockDomainInput" class="search-input" placeholder="ads.example.com" style="flex:1; min-width:140px;">
							<select class="control-select" id="adblockDomainType"><option value="black">⚫ В черный</option><option value="white">⚪ В белый</option></select>
							<button class="btn btn-primary" onclick="addAdblockDomain()">➕ Добавить</button>
						</div>
						<div class="domains-list-box" id="adblockDomainsBox" style="max-height:360px; overflow-y:auto;"></div>
					</div>
				</div>
			</div>
		</div>
	</div>

	<!-- VIEW: CONFIG -->
	<div id="tab-config" class="tab-view">
		<div class="chart-wrapper">
			<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; flex-wrap:wrap; gap:12px;">
				<div>
					<h3>⚙️ Прямой редактор server.conf</h3>
					<p style="font-size:12.5px; color:var(--text-muted); margin-top:4px;">/etc/openvpn/server/server.conf</p>
				</div>
				<div style="display:flex; gap:8px; flex-wrap:wrap;">
					<button class="btn" onclick="loadConfigView()">🔄 Перечитать</button>
					<button class="btn btn-primary" onclick="saveRawConfig(true)">💾 Сохранить и перезапустить</button>
				</div>
			</div>
			<textarea id="serverConfigText" class="textarea-input" rows="24" style="width:100%;"></textarea>
		</div>
	</div>

	<!-- VIEW: SETTINGS -->
	<div id="tab-settings" class="tab-view">
		<div class="settings-grid">
			<div class="settings-card">
				<h3>🔐 Учетная запись и Панель</h3>
				<p class="card-desc">Безопасность входа и сетевые параметры панели</p>
				<div class="form-row-2">
					<div class="form-group"><label class="form-label">Логин администратора</label><input type="text" id="setAdminLogin" class="search-input"></div>
					<div class="form-group"><label class="form-label">Новый пароль</label><input type="text" id="setAdminPass" class="search-input" placeholder="••••••••"></div>
				</div>
				<div class="form-row-2">
					<div class="form-group"><label class="form-label">Время сессии (сек)</label><input type="number" id="setSessionAge" class="search-input"></div>
					<div class="form-group"><label class="form-label">Порт панели</label><input type="number" id="setPanelPort" class="search-input"></div>
				</div>
				<div class="form-row-2">
					<div class="form-group"><label class="form-label">Mgmt Host</label><input type="text" id="setMgmtHost" class="search-input" placeholder="127.0.0.1"></div>
					<div class="form-group"><label class="form-label">Mgmt Port</label><input type="number" id="setMgmtPort" class="search-input" placeholder="7505"></div>
				</div>
				<div class="form-row-2">
					<div class="form-group"><label class="form-label">TUN iface</label><input type="text" id="setTunIface" class="search-input" placeholder="tun0"></div>
					<div class="form-group"><label class="form-label">Хранение доменов (сек)</label><input type="number" id="setDomainRetention" class="search-input"></div>
				</div>
			</div>

			<div class="settings-card">
				<h3>🎛️ Модули и функции</h3>
				<p class="card-desc">Включение и отключение в реальном времени</p>
				<div class="switch-row">
					<div class="switch-info"><strong>🕵️ Сниффер трафика</strong><span>SNI / DNS / HTTP домены</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableSniffer"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>📈 Мониторинг скорости</strong><span>Живые графики скорости</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableSpeed"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>📊 Статистика трафика</strong><span>SQLite учет и лимиты</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableStats"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>🌐 История IP подключений</strong><span>Сохранять реальные IP пользователей</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableIpHistory"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>🎨 Инфографика</strong><span>Диаграммы и аналитика</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableInfographics"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>💻 Панель ресурсов</strong><span>CPU / RAM / Disk / Ping</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setEnableHwBar"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>⚡ Блок QUIC (UDP/443)</strong><span>Точный SNI сниффинг</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setQuicBlock"><span class="toggle-slider"></span></label>
				</div>
				<div class="switch-row">
					<div class="switch-info"><strong>🚫 Блок BitTorrent</strong><span>iptables string match</span></div>
					<label class="toggle-switch"><input type="checkbox" id="setTorrentBlock"><span class="toggle-slider"></span></label>
				</div>
			</div>

			<div class="settings-card">

				<h3>🛠️ Управление службами и БД</h3>
				<p class="card-desc">Применение параметров и очистка данных</p>
				<div style="display:flex; flex-direction:column; gap:10px;">
					<button class="btn btn-primary" style="padding:13px; justify-content:center;" onclick="saveAllAccountSettings(false)">💾 Сохранить настройки</button>
					<button class="btn btn-success" style="padding:13px; justify-content:center;" onclick="saveAllAccountSettings(true)">🚀 Сохранить и перезапустить</button>
				</div>

				<h4 style="font-size:12px; color:var(--text-dim); text-transform:uppercase; letter-spacing:0.5px;">OpenVPN daemon</h4>
				<div class="form-row-3">
					<button class="btn" style="justify-content:center;" onclick="controlOvpnService('restart')">🔄 Рестарт</button>
					<button class="btn btn-success" style="justify-content:center;" onclick="controlOvpnService('start')">▶️ Старт</button>
					<button class="btn btn-danger" style="justify-content:center;" onclick="controlOvpnService('stop')">⏹️ Стоп</button>
				</div>

				<h4 style="font-size:12px; color:var(--text-dim); text-transform:uppercase; letter-spacing:0.5px;">SQLite</h4>
				<div class="form-row-2">
					<button class="btn btn-warning" style="justify-content:center;" onclick="runDbAction('clear_domains', 'Очистить всю историю сайтов?')">🗑️ Сайты</button>
					<button class="btn btn-danger" style="justify-content:center;" onclick="runDbAction('clear_traffic', 'Сбросить трафик всех клиентов?')">↺ Трафик</button>
				</div>
				<div class="form-row-2">
					<button class="btn btn-warning" style="justify-content:center;" onclick="runDbAction('clear_ip_history', 'Очистить всю историю IP-адресов?')">🌐 Очистить IP</button>
					<button class="btn" style="justify-content:center;" onclick="runDbAction('vacuum', null)">🧹 VACUUM</button>
				</div>

				<div class="hint-box">
					<strong>💡 Подсказка:</strong>
					<span> После смены порта или протокола не забудьте сохранить server.conf и перевыпустить .ovpn профили.</span>
				</div>
			</div>
		</div>
	</div>
</div>

<!-- MODALS -->
<div class="modal-overlay" id="createModal">
	<div class="modal-card">
		<h2>➕ Новый клиент</h2>
		<p>Латиница, цифры, дефис и подчеркивание.</p>
		<label class="form-label">Имя клиента</label>
		<input type="text" id="newClientName" class="search-input" placeholder="iphone-user" style="width:100%; margin-bottom:12px;" autofocus>
		<label class="form-label">Заметка</label>
		<input type="text" id="newClientNote" class="search-input" placeholder="Например: Ноутбук шефа" style="width:100%; margin-bottom:12px;">
		<div style="display:grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 20px;">
			<div><label class="form-label">Лимит ГБ (0 = ∞)</label><input type="number" id="newClientLimit" class="search-input" value="0" min="0" style="width:100%;"></div>
			<div><label class="form-label">Срок в днях (0 = ∞)</label><input type="number" id="newClientTtl" class="search-input" value="0" min="0" style="width:100%;"></div>
		</div>
		<div style="display:flex; gap:10px; justify-content:flex-end;">
			<button class="btn" onclick="closeModals()">Отмена</button>
			<button class="btn btn-primary" onclick="submitCreateClient()">Создать</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="qrModal">
	<div class="modal-card" style="text-align:center;">
		<h2 id="qrModalTitle">📱 QR</h2>
		<p>Отсканируйте камерой телефона для скачивания .ovpn профиля</p>
		<div style="background:#fff; padding:16px; border-radius:16px; display:inline-block; margin: 0 auto 16px;"><canvas id="qrCanvas"></canvas></div>
		<div style="display:flex; gap:10px;">
			<button class="btn btn-primary" style="flex:1; justify-content:center;" id="qrCopyBtn">🔗 Копировать</button>
			<button class="btn" style="flex:1; justify-content:center;" onclick="closeModals()">Закрыть</button>
		</div>
	</div>
</div>

<div class="modal-overlay" id="domainsModal">
	<div class="modal-card modal-lg">
		<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
			<h2 id="domainsModalTitle">🌐 Сайты</h2>
			<span id="domainsCountBadge" style="font-size:12px; color:var(--primary); font-weight:600;">0</span>
		</div>
		<p>История посещенных доменов и подключений</p>
		<div class="domains-tabs">
			<button class="d-tab-btn active" id="d-tab-history" onclick="switchDomainTab('history')">📋 История</button>
			<button class="d-tab-btn" id="d-tab-top" onclick="switchDomainTab('top')">📊 Топ-10</button>
			<button class="d-tab-btn" id="d-tab-ips" onclick="switchDomainTab('ips')">🌐 IP-адреса</button>
		</div>
		<div id="d-view-history" class="d-tab-view active">
			<div style="display:flex; gap:8px; margin-bottom:10px;">
				<div class="search-wrapper" style="flex:1;"><input type="text" id="domainSearchInput" class="search-input" placeholder="🔍 Фильтр..." oninput="fetchClientDomains()" style="padding:8px 12px; font-size:13px;"></div>
				<button class="btn btn-sm" onclick="fetchClientDomains()">🔄</button>
				<button class="btn btn-sm btn-danger" onclick="clearClientDomains()">🗑️</button>
			</div>
			<div class="domains-list-box" id="domainsListBox"></div>
		</div>
		<div id="d-view-top" class="d-tab-view"><div class="domains-list-box" id="domainsTopBox"></div></div>
		<div id="d-view-ips" class="d-tab-view"><div class="domains-list-box" id="ipsListBox"></div></div>
		<div style="margin-top:16px;"><button class="btn" style="width:100%; justify-content:center;" onclick="closeModals()">Закрыть</button></div>
	</div>
</div>

<div class="modal-overlay" id="ignoredDomainsModal">
	<div class="modal-card modal-lg">
		<div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:6px;">
			<h2>🚫 Исключения из сниффинга</h2>
			<span id="ignoredDomainsCountBadge" style="font-size:12px; color:var(--danger); font-weight:600;">0</span>
		</div>
		<p>Домены и все их поддомены (*.domain.com) будут игнорироваться сниффером и не сохраняться в БД.</p>
		<div style="display:flex; gap:8px; margin-bottom:14px; flex-wrap:wrap;">
			<input type="text" id="newIgnoredDomainInput" class="search-input" placeholder="Например: yandex.ru или google.com" style="flex:1; min-width:180px;">
			<button class="btn btn-danger" onclick="addManualIgnoredDomain()">➕ Скрыть домен</button>
		</div>
		<div class="domains-list-box" id="ignoredDomainsListBox" style="max-height:380px; overflow-y:auto;"></div>
		<div style="margin-top:16px;"><button class="btn" style="width:100%; justify-content:center;" onclick="closeModals()">Закрыть</button></div>
	</div>
</div>

<div class="modal-overlay" id="backupModal">
	<div class="modal-card">
		<h2>📦 Резервное копирование</h2>
		<p>Полный архив ключей, сертификатов и конфигурации.</p>
		<div style="display:flex; flex-direction:column; gap:10px; margin-bottom:16px;">
			<button class="btn" onclick="downloadBackupArchive()" style="padding:14px; justify-content:center;">📥 Скачать архив</button>
			<button class="btn btn-primary" onclick="document.getElementById('backupFileInput').click()" style="padding:14px; justify-content:center;">📤 Восстановить из файла</button>
		</div>
		<input type="file" id="backupFileInput" accept=".tar.gz" style="display:none;" onchange="processRestoreFile(event)">
		<button class="btn" style="width:100%; justify-content:center;" onclick="closeModals()">Закрыть</button>
	</div>
</div>

<div class="toast" id="toastBox"></div>

<script>
let currentTheme = localStorage.getItem("ovpn_theme") || "dark";
let currentLang = localStorage.getItem("ovpn_lang") || "ru";
let panelConfig = {
	enable_sniffer: "1", enable_speed_monitor: "1", enable_traffic_stats: "1",
	enable_ip_history: "1", enable_infographics: "1", enable_hardware_bar: "1",
	speed_limit_mode: "none", global_speed_limit_kbps: "0", selected_limit_clients: "[]"
};
let allClientsList = [];
let currentPage = 1;
let pageSize = parseInt(localStorage.getItem('ovpn_page_size')) || 20;
let speedChart = null, infoClientsChart = null, infoStatusChart = null, infoDomainsChart = null;
let selectedWindowSeconds = 30, speedPollTimer = null, speedDataPoints = [], latestLiveSpeeds = {};
let chartFilterDirty = false, clientColorRegistry = {}, paletteIdx = 0, pendingLinks = [], currentDomainsClient = null;
const colorPalette = ['#3b82f6','#10b981','#f43f5e','#f59e0b','#8b5cf6','#06b6d4','#ec4899','#84cc16','#6366f1','#14b8a6'];

function escapeHtml(str) {
	if (!str) return '';
	return String(str)
		.replace(/&/g, '&amp;')
		.replace(/</g, '&lt;')
		.replace(/>/g, '&gt;')
		.replace(/"/g, '&quot;')
		.replace(/'/g, '&#039;');
}

function applyTheme(theme) {
	currentTheme = theme;
	localStorage.setItem("ovpn_theme", theme);
	document.documentElement.setAttribute("data-theme", theme);
	const icon = document.getElementById("themeToggleIcon");
	if (icon) icon.textContent = theme === "light" ? "🌙" : "☀️";
}
function toggleTheme() { applyTheme(currentTheme === "light" ? "dark" : "light"); }
applyTheme(currentTheme);

const RU_TO_EN = {
	"Создать": "Create", "Бэкап": "Backup", "Выйти": "Logout", "Сервер:": "Server:", "Онлайн:": "Online:",
	"👥 Клиенты": "👥 Clients", "📈 Скорость": "📈 Speed", "🌐 Сайты": "🌐 Sites", "📊 Инфографика": "📊 Infographics",
	"⚡ Лимиты": "⚡ Limits", "🔀 Маршрутизация": "🔀 Routing", "⚙️ Конфигурация": "⚙️ Config", "🔐 Аккаунт": "🔐 Account",
	"Все активные": "All Active", "🟢 Только онлайн": "🟢 Online only", "⚪ Только офлайн": "⚪ Offline only",
	"⏸️ На паузе": "⏸️ Paused", "🚫 Отозванные": "🚫 Revoked", "🟢 Сначала онлайн": "🟢 Online first",
	"⬇️ По трафику": "⬇️ By Traffic", "🔤 По имени": "🔤 By Name", "По 20": "20 / page", "По 50": "50 / page", "По 100": "100 / page",
	"Мониторинг скорости в реальном времени": "Realtime Speed Monitoring",
	"Прямой опрос сокета OpenVPN в памяти": "In-memory OpenVPN socket telemetry",
	"👥 Все клиенты": "👥 All Clients", "Σ Суммарно": "Σ Total", "Текущий Download:": "Current Download:",
	"Текущий Upload:": "Current Upload:", "Активных подключений:": "Active sessions:",
	"🌐 Журнал посещаемых сайтов": "🌐 Visited Sites Log",
	"История переходов по всем клиентам сервера в реальном времени": "Real-time domain history across all clients",
	"🔄 Обновить": "🔄 Refresh", "🚫 Исключения": "🚫 Ignored", "🗑️ Очистить": "🗑️ Clear",
	"∑ Весь трафик сервера": "∑ Total Server Traffic", "📥 Суммарный Download": "📥 Total Download", "📤 Суммарный Upload": "📤 Total Upload",
	"📊 Топ-10 клиентов по трафику": "📊 Top 10 Clients by Traffic", "👥 Распределение статусов": "👥 Status Distribution",
	"🌐 Топ-10 посещаемых доменов": "🌐 Top 10 Visited Domains",
	"⚡ Двусторонний лимит скорости (tc + ifb0)": "⚡ Bidirectional Speed Limit (tc + ifb0)",
	"Ограничивает скорость в обе стороны (Download + Upload) для активных сессий. 0 = без ограничения.": "Limits Download & Upload speed for active sessions. 0 = unlimited.",
	"Режим ограничения": "Limit mode", "⚪ Без ограничения": "⚪ Disabled",
	"🌐 Для всех клиентов (общий лимит)": "🌐 All clients (global limit)",
	"☑️ Для выбранных клиентов (общий лимит)": "☑️ Selected clients (global limit)",
	"🎯 Индивидуально для каждого клиента": "🎯 Per-client individual limits",
	"Общий лимит скорости (Кбит/с)": "Global speed limit (kbps)",
	"1 Мбит/с": "1 Mbps", "5 Мбит/с": "5 Mbps", "10 Мбит/с": "10 Mbps", "25 Мбит/с": "25 Mbps", "50 Мбит/с": "50 Mbps", "∞ Без лимита": "∞ Unlimited",
	"💾 Применить лимиты скорости": "💾 Apply speed limits", "👥 Список клиентов для лимитов": "👥 Clients for speed limits",
	"Сплит-туннель (WireGuard + ipset)": "Split Tunnel (WireGuard + ipset)",
	"Маршрутизация через второй VPN-сервер": "Routing via secondary VPN server",
	"Статус WG0:": "WG0 Status:", "Подсетей в ipset:": "Subnets in ipset:",
	"🔗 Удалённая точка выхода": "🔗 Remote Exit Node", "Подключено к:": "Connected to:", "Перенастроить": "Reconfigure",
	"❌ Отмена": "❌ Cancel", "🚀 Настроить туннель": "🚀 Setup Tunnel",
	"🚫 Блокировка BitTorrent": "🚫 BitTorrent Block", "Защита от абузов и банов хостинга": "Protection against host abuse",
	"URL списка подсетей:": "CIDR list URL:", "Свои IP/подсети:": "Custom IPs / subnets:", "Режим:": "Mode:",
	"🔴 Отключено": "🔴 Disabled", "🟡 CIDR напрямую, остальное в WG": "🟡 CIDR direct, rest via WG",
	"🟣 CIDR в WG, остальное напрямую": "🟣 CIDR via WG, rest direct", "🟢 Весь трафик через WireGuard": "🟢 Full tunnel via WireGuard",
	"🔗 Управление ссылками сплит-туннеля": "🔗 Split Tunnel Link Management",
	"Разрешите URL в IP для выборочной маршрутизации через WireGuard или напрямую.": "Resolve URLs to IPs for selective routing via WireGuard or direct.",
	"🔍 Найти IP": "🔍 Resolve IP", "💾 Сохранить": "💾 Save", "🔄 Обновить CIDR": "🔄 Sync CIDR",
	"🛡️ Блокировка рекламы (DNS AdBlock / dnsmasq)": "🛡️ Ad Blocking (DNS AdBlock / dnsmasq)",
	"Автоматическая фильтрация рекламы и трекеров на уровне VPN-сервера без потери скорости": "Server-side ad and tracker filtering with zero speed loss",
	"Включить блокировку рекламы для всех клиентов": "Enable ad blocking for all clients",
	"📋 Добавить AdList по ссылке": "📋 Add AdList URL", "⚫ Черный список": "⚫ Blacklist", "⚪ Белый список": "⚪ Whitelist",
	"➕ Добавить": "➕ Add", "🌐 Добавить отдельный домен": "🌐 Add custom domain", "⚫ В черный": "⚫ To blacklist", "⚪ В белый": "⚪ To whitelist",
	"⚙️ Прямой редактор server.conf": "⚙️ Direct server.conf Editor", "🔄 Перечитать": "🔄 Reload", "💾 Сохранить и перезапустить": "💾 Save & Restart",
	"🔐 Учетная запись и Панель": "🔐 Account & Panel", "Безопасность входа и сетевые параметры панели": "Login security and panel network settings",
	"Логин администратора": "Admin login", "Новый пароль": "New password", "Время сессии (сек)": "Session max age (sec)",
	"Порт панели": "Panel port", "Хранение доменов (сек)": "Domain retention (sec)",
	"🎛️ Модули и функции": "🎛️ Modules & Features", "Включение и отключение в реальном времени": "Toggle features in real time",
	"🕵️ Сниффер трафика": "🕵️ Traffic Sniffer", "SNI / DNS / HTTP домены": "SNI / DNS / HTTP domains",
	"📈 Мониторинг скорости": "📈 Speed Monitor", "Живые графики скорости": "Live speed charts",
	"📊 Статистика трафика": "📊 Traffic Stats", "SQLite учет и лимиты": "SQLite tracking and quotas",
	"🌐 История IP подключений": "🌐 IP Connection History", "Сохранять реальные IP пользователей": "Store real client IPs",
	"🎨 Инфографика": "🎨 Infographics", "Диаграммы и аналитика": "Charts and analytics",
	"💻 Панель ресурсов": "💻 Hardware Bar", "⚡ Блок QUIC (UDP/443)": "⚡ Block QUIC (UDP/443)", "Точный SNI сниффинг": "Accurate SNI sniffing",
	"🚫 Блок BitTorrent": "🚫 Block BitTorrent", "🛠️ Управление службами и БД": "🛠️ Services & Database",
	"Применение параметров и очистка данных": "Apply settings and clean data",
	"💾 Сохранить настройки": "💾 Save settings", "🚀 Сохранить и перезапустить": "🚀 Save & Restart",
	"🔄 Рестарт": "🔄 Restart", "▶️ Старт": "▶️ Start", "⏹️ Стоп": "⏹️ Stop",
	"🗑️ Сайты": "🗑️ Sites", "↺ Трафик": "↺ Traffic", "🌐 Очистить IP": "🌐 Clear IPs",
	"💡 Подсказка:": "💡 Hint:",
	"После смены порта или протокола не забудьте сохранить server.conf и перевыпустить .ovpn профили.": "After changing port or protocol, save server.conf and reissue .ovpn profiles.",
	"➕ Новый клиент": "➕ New Client", "Латиница, цифры, дефис и подчеркивание.": "Latin letters, numbers, hyphens, underscores.",
	"Имя клиента": "Client name", "Заметка": "Note", "Лимит ГБ (0 = ∞)": "Limit GB (0 = ∞)", "Срок в днях (0 = ∞)": "TTL days (0 = ∞)",
	"Отмена": "Cancel", "Закрыть": "Close", "🔗 Копировать": "🔗 Copy",
	"Отсканируйте камерой телефона для скачивания .ovpn профиля": "Scan with phone camera to download .ovpn profile",
	"История посещенных доменов и подключений": "Visited domains and connection history",
	"📋 История": "📋 History", "📊 Топ-10": "📊 Top-10", "🌐 IP-адреса": "🌐 IP Addresses",
	"🚫 Исключения из сниффинга": "🚫 Sniffer Ignore List", "➕ Скрыть домен": "➕ Ignore domain",
	"📦 Резервное копирование": "📦 Backup & Restore", "Полный архив ключей, сертификатов и конфигурации.": "Full archive of keys, certs and configs.",
	"📥 Скачать архив": "📥 Download archive", "📤 Восстановить из файла": "📤 Restore from file", 
	"Общий лимит скорости (МБ/с)": "Global speed limit (MB/s)",
	"0.5 МБ/с": "0.5 MB/s", "1 МБ/с": "1 MB/s", "2 МБ/с": "2 MB/s", "5 МБ/с": "5 MB/s", "10 МБ/с": "10 MB/s", "∞ Без лимита": "∞ Unlimited",
};

const PLACEHOLDER_EN = {
	"🔍 Поиск по имени или IP...": "🔍 Search by name or IP...",
	"🔍 Поиск по домену или клиенту...": "🔍 Search by domain or client...",
	"Например: 2": "e.g. 2",
	"IP удаленного сервера": "Remote server IP",
	"Пароль root": "Root password",
	"Например: Ноутбук шефа": "e.g. Boss laptop",
	"🔍 Фильтр...": "🔍 Filter...",
	"Например: yandex.ru или google.com": "e.g. example.com"
};

const I18N_DYN = {
	ru: {
		online: "🟢 Онлайн", offline: "⚪ Офлайн", paused: "⏸️ НА ПАУЗЕ", valid: "АКТИВЕН", revoked: "ОТОЗВАН",
		traffic: "Трафик:", connected: "Подключён:", disconnected: "Отключён:", speed_limit: "Лимит скорости:",
		restore: "♻️ Восстановить", del: "🗑️ Удалить", updated: "Обновлено:", server_on: "● Сервер активен", server_off: "● Остановлен",
		showing: "Показано {from}–{to} из {total}", empty: "Список клиентов пуст",
		hint_sel: "Отметьте клиентов, к которым применится общий лимит.",
		hint_per: "Укажите лимит в МБ/с для каждого клиента (0 = без лимита).",
		hint_none: "Выберите режим «Для выбранных» или «Индивидуально» для настройки по клиентам.",
		wg_on: "АКТИВЕН", wg_off: "ОТКЛЮЧЕН",
		remote_conn: "🟢 Подключено", remote_inact: "🟢 Не активно", remote_none: "⚪ Не настроено",
		direct: "🟡 Напрямую", via_wg: "🟣 Через WG",
		no_records: "Записей нет", no_lists: "Списков нет", no_domains: "Доменов нет",
		adb_status: "Статус:", adb_on: "🟢 АКТИВЕН", adb_off: "⚪ ОТКЛЮЧЕН", adb_rules: "Правил:",
		all_clients: "👥 Все клиенты", hide: "🚫 Скрыть", no_ignored: "Исключений нет",
		records_cnt: "Записей:", sites_prefix: "🌐 Сайты:", login_in: "Вход:", login_out: "Выход:"
	},
	en: {
		online: "🟢 Online", offline: "⚪ Offline", paused: "⏸️ PAUSED", valid: "VALID", revoked: "REVOKED",
		traffic: "Traffic:", connected: "Connected:", disconnected: "Disconnected:", speed_limit: "Speed limit:",
		restore: "♻️ Restore", del: "🗑️ Delete", updated: "Updated:", server_on: "● Server Active", server_off: "● Stopped",
		showing: "Showing {from}–{to} of {total}", empty: "No clients found",
		hint_sel: "Check clients to apply the global speed limit.",
		hint_per: "Set speed limit in MB/s per client (0 = unlimited).",
		hint_none: "Choose 'Selected clients' or 'Per-client' mode to configure clients.",
		wg_on: "ACTIVE", wg_off: "INACTIVE",
		remote_conn: "🟢 Connected", remote_inact: "🟢 Inactive", remote_none: "⚪ Not configured",
		direct: "🟡 Direct", via_wg: "🟣 Via WG",
		no_records: "No records", no_lists: "No lists", no_domains: "No domains",
		adb_status: "Status:", adb_on: "🟢 ACTIVE", adb_off: "⚪ DISABLED", adb_rules: "Rules:",
		all_clients: "👥 All Clients", hide: "🚫 Hide", no_ignored: "No ignored domains",
		records_cnt: "Records:", sites_prefix: "🌐 Sites:", login_in: "In:", login_out: "Out:"
	}
};

function t(key, params = {}) {
	let s = (I18N_DYN[currentLang] && I18N_DYN[currentLang][key]) || I18N_DYN.ru[key] || key;
	for (const k in params) s = s.replace(`{${k}}`, params[k]);
	return s;
}

function applyLanguage(lang) {
	currentLang = lang === 'en' ? 'en' : 'ru';
	localStorage.setItem("ovpn_lang", currentLang);
	document.documentElement.lang = currentLang;
	const sel = document.getElementById("langSelect");
	if (sel) sel.value = currentLang;

	document.querySelectorAll("h1,h2,h3,h4,p,span,strong,label,button,a,option,.tab-btn").forEach(el => {
		if (el.children.length > 0 && el.tagName !== "OPTION") return;
		const txt = el.textContent.trim();
		if (!el.dataset.origRu && RU_TO_EN[txt]) el.dataset.origRu = txt;
		if (el.dataset.origRu) {
			el.textContent = currentLang === 'en' ? (RU_TO_EN[el.dataset.origRu] || el.dataset.origRu) : el.dataset.origRu;
		}
	});
	document.querySelectorAll("input[placeholder],textarea[placeholder]").forEach(el => {
		if (!el.dataset.origPh && PLACEHOLDER_EN[el.placeholder]) el.dataset.origPh = el.placeholder;
		if (el.dataset.origPh) {
			el.placeholder = currentLang === 'en' ? PLACEHOLDER_EN[el.dataset.origPh] : el.dataset.origPh;
		}
	});

	const stEl = document.getElementById('serverStatusText');
	if (stEl) stEl.textContent = stEl.classList.contains('active') ? t('server_on') : t('server_off');
	applyClientFilter();
	renderSpeedLimitsEditor();
	syncChartUserDropdown();
	if (document.getElementById('tab-routing')?.classList.contains('active')) {
		loadRoutingView();
	}
}

function changeLanguage(lang) { applyLanguage(lang); }

function showToast(msg, type = 'success') {
	let text = String(msg || '');
	if (currentLang === 'en') {
		const toastMap = {
			"✅ Лимиты скорости применены": "✅ Speed limits applied",
			"✅ Клиент создан": "✅ Client created",
			"⏸️ На паузе": "⏸️ Paused",
			"▶️ Активен": "▶️ Active",
			"✅ Готово": "✅ Done",
			"✅ Восстановлен": "✅ Restored",
			"✅ Ссылка скопирована": "✅ Link copied",
			"✅ Скопировано": "✅ Copied",
			"✅ Настройки сохранены": "✅ Settings saved",
			"✅ CIDR обновлены": "✅ CIDR updated",
			"❌ Укажите IP и пароль": "❌ IP and password required",
			"✅ Туннель настроен": "✅ Tunnel deployed",
			"✅ AdBlock обновлён": "✅ AdBlock updated",
			"✅ Список загружен": "✅ List loaded",
			"✅ server.conf сохранён": "✅ server.conf saved",
			"✅ Восстановлено": "✅ Restored",
			"❌ Ошибка": "❌ Error"
		};
		if (toastMap[text]) text = toastMap[text];
		else text = text
			.replace(/^Домен (.+) скрыт$/, "Domain $1 ignored")
			.replace(/^❌ Ошибка/, "❌ Error");
	}
	const box = document.getElementById('toastBox');
	box.textContent = text;
	box.className = `toast ${type} show`;
	clearTimeout(box._t);
	box._t = setTimeout(() => box.classList.remove('show'), 3200);
}

function copyToClipboard(text) {
	if (navigator.clipboard && window.isSecureContext) return navigator.clipboard.writeText(text);
	const ta = document.createElement("textarea");
	ta.value = text; ta.style.position = "fixed"; ta.style.left = "-999999px";
	document.body.appendChild(ta); ta.focus(); ta.select();
	return new Promise((res, rej) => { document.execCommand('copy') ? res() : rej(); ta.remove(); });
}

function formatBytes(bytes) {
	if (!bytes || bytes <= 0) return '0 B';
	const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
	const i = Math.floor(Math.log(bytes) / Math.log(1024));
	return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + ' ' + sizes[i];
}
function formatSpeed(bps) {
	if (!bps || bps <= 0) return '0 B/s';
	const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
	let i = 0, v = bps;
	while (v >= 1024 && i < units.length - 1) { v /= 1024; i++; }
	return v.toFixed(1) + ' ' + units[i];
}
function formatTs(ts) {
	if (!ts || Number(ts) <= 0) return "—";
	return new Date(Number(ts) * 1000).toLocaleString('ru-RU', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
}

let taskPollTimer = null;
function watchBackgroundTask(taskId, onDone) {
	const banner = document.getElementById('taskProgressBanner');
	banner.classList.add('active');
	if (taskPollTimer) clearInterval(taskPollTimer);
	const tick = async () => {
		try {
			const r = await fetch(`/api/tasks/status?task_id=${encodeURIComponent(taskId)}`);
			const j = await r.json();
			const tsk = j.task;
			if (!tsk) return;
			const trTask = (str) => {
				if (currentLang !== 'en' || !str) return str || '';
				const map = {
					"Выполняется...": "Running...", "Готово": "Done",
					"Обновление CIDR": "Updating CIDR", "CIDR обновлены": "CIDR updated",
					"Загрузка AdList": "Loading AdList", "Настройка WireGuard туннеля": "WireGuard Tunnel Setup",
					"Проверка DNS-служб...": "Checking DNS services...", "Установка dnsmasq...": "Installing dnsmasq...",
					"Настройка конфигурации dnsmasq...": "Configuring dnsmasq...", "Сборка списков доменов...": "Building domain lists...",
					"Применение правил iptables и OpenVPN...": "Applying iptables & OpenVPN rules...",
					"Скачивание списка доменов...": "Downloading domain list...", "Сохранение в кэш и БД...": "Saving to cache & DB...",
					"Подготовка SSH-ключа...": "Preparing SSH key...", "Установка WireGuard на удалённом сервере...": "Installing WireGuard on remote server...",
					"Запуск локального wg0...": "Starting local wg0...", "Туннель развёрнут": "Tunnel deployed"
				};
				if (map[str]) return map[str];
				return str
					.replace(/^Запись (\d+) правил в dnsmasq\.\.\.$/, "Writing $1 rules to dnsmasq...")
					.replace(/^Подключение к (.+)\.\.\.$/, "Connecting to $1...")
					.replace(/^Список загружен \((\d+) правил\)$/, "List loaded ($1 rules)");
			};
			document.getElementById('taskProgressTitle').textContent = trTask(tsk.title || taskId);
			document.getElementById('taskProgressMsg').textContent = trTask(tsk.message || '');
			document.getElementById('taskProgressPct').textContent = `${tsk.progress || 0}%`;
			document.getElementById('taskProgressFill').style.width = `${tsk.progress || 0}%`;
			if (tsk.status === 'done' || tsk.status === 'error') {
				clearInterval(taskPollTimer); taskPollTimer = null;
				setTimeout(() => banner.classList.remove('active'), 2500);
				if (onDone) onDone(tsk.status === 'done', tsk.message);
			}
		} catch (e) {}
	};
	tick();
	taskPollTimer = setInterval(tick, 700);
}

function applyDynamicFeatureVisibility() {
	document.getElementById('hardwareBar').style.display = panelConfig.enable_hardware_bar === "1" ? 'grid' : 'none';
	document.getElementById('tabBtnDomains').style.display = panelConfig.enable_sniffer === "1" ? 'block' : 'none';
	document.getElementById('tabBtnSpeed').style.display = panelConfig.enable_speed_monitor === "1" ? 'block' : 'none';
	document.getElementById('tabBtnInfographics').style.display = panelConfig.enable_infographics === "1" ? 'block' : 'none';
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
	if (tabId === 'tab-infographics') loadInfographicsView();
	if (tabId === 'tab-domains') fetchTabGlobalDomains();
	if (tabId === 'tab-limits') renderSpeedLimitsEditor();
	if (tabId === 'tab-speed') { if (speedChart) speedChart.resize(); fetchHistoryAndSync(); }
}

function openCreateModal() {
	document.getElementById('createModal').classList.add('active');
	document.getElementById('newClientName').value = '';
	document.getElementById('newClientNote').value = '';
	document.getElementById('newClientLimit').value = '0';
	document.getElementById('newClientTtl').value = '0';
}
function openBackupModal() { document.getElementById('backupModal').classList.add('active'); }
function closeModals() { document.querySelectorAll('.modal-overlay').forEach(m => m.classList.remove('active')); currentDomainsClient = null; }
document.querySelectorAll('.modal-overlay').forEach(m => m.addEventListener('click', e => { if (e.target === m) closeModals(); }));

function onFilterInputChange() {
	const input = document.getElementById('clientSearch');
	const clearBtn = document.getElementById('clearSearchBtn');
	if (clearBtn && input) clearBtn.style.display = input.value.length > 0 ? 'inline-flex' : 'none';
	currentPage = 1; applyClientFilter();
}
function clearClientSearch() { const i = document.getElementById('clientSearch'); if (i) { i.value = ''; i.focus(); } onFilterInputChange(); }
function onPageSizeChange() { pageSize = parseInt(document.getElementById('pageSizeSelect').value) || 20; localStorage.setItem('ovpn_page_size', pageSize); currentPage = 1; applyClientFilter(); }
function goToPage(p) { currentPage = p; applyClientFilter(); window.scrollTo({ top: 0, behavior: 'smooth' }); }

async function loadClients() {
	if (document.hidden) return;
	try {
		const res = await fetch('/api/clients');
		if (res.status === 401) { location.href = '/login'; return; }
		const data = await res.json();
		allClientsList = data.clients || [];

		const isActive = data.server?.status === 'active';
		const stEl = document.getElementById('serverStatusText');
		stEl.textContent = isActive ? t('server_on') : t('server_off');
		stEl.className = `status-badge ${isActive ? 'active' : 'inactive'}`;
		if (data.server?.domain && data.server?.port) {
			document.getElementById('bannerEndpointCode').textContent = `${data.server.domain}:${data.server.port} (${data.server.proto || 'udp'})`;
		}

		const validTotal = allClientsList.filter(c => c.status === 'valid').length;
		const online = allClientsList.filter(c => c.is_online).length;
		document.getElementById('activeClientsCount').textContent = `${online} / ${validTotal}`;
		document.getElementById('lastSyncTime').textContent = `${t('updated')} ${new Date().toLocaleTimeString()}`;

		if (!chartFilterDirty) syncChartUserDropdown();
		const isDomainsTabActive = document.getElementById('tab-domains')?.classList.contains('active');
		const isModalActive = document.querySelector('.modal-overlay.active') !== null;
		if (!isDomainsTabActive && !isModalActive) applyClientFilter();
		if (document.getElementById('tab-limits')?.classList.contains('active')) renderSpeedLimitsEditor();
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
		if (sortMode === 'traffic_desc') return ((b.traffic_recv || 0) + (b.traffic_sent || 0)) - ((a.traffic_recv || 0) + (a.traffic_sent || 0));
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
	document.getElementById('paginationInfo').textContent = t('showing', { from: startIdx + 1, to: startIdx + countOnPage, total: totalItems });
	let html = `<button class="page-btn" onclick="goToPage(${currentPage - 1})" ${currentPage <= 1 ? 'disabled' : ''}>«</button>`;
	for (let p = 1; p <= totalPages; p++) {
		if (p === 1 || p === totalPages || Math.abs(p - currentPage) <= 2) {
			html += `<button class="page-btn ${p === currentPage ? 'active' : ''}" onclick="goToPage(${p})">${p}</button>`;
		} else if (Math.abs(p - currentPage) === 3) {
			html += `<span style="padding:8px 4px; color:var(--text-muted);">…</span>`;
		}
	}
	html += `<button class="page-btn" onclick="goToPage(${currentPage + 1})" ${currentPage >= totalPages ? 'disabled' : ''}>»</button>`;
	document.getElementById('paginationPages').innerHTML = html;
}

function renderClientsGrid(clients) {
	const grid = document.getElementById('clientsGrid');
	if (!clients || clients.length === 0) {
		grid.innerHTML = `<div style="grid-column:1/-1; text-align:center; padding:60px 20px; color:var(--text-muted);">${t('empty')}</div>`;
		return;
	}
	const snifferOn = panelConfig.enable_sniffer === "1";
	const speedOn = panelConfig.enable_speed_monitor === "1";
	const statsOn = panelConfig.enable_traffic_stats === "1";

	grid.innerHTML = clients.map(c => {
		const isOnline = c.is_online;
		const isPaused = c.is_paused;
		const onlineHtml = isPaused
			? `<span style="color:var(--warning); font-weight:600;">${t('paused')}</span>`
			: (isOnline ? `<span style="color:var(--success); font-weight:600;">${t('online')}</span>` : `<span style="color:var(--text-muted);">${t('offline')}</span>`);
		const statusLabel = c.status === 'revoked' ? t('revoked') : (isPaused ? t('paused') : t('valid'));
		const badgeCls = c.status === 'revoked' ? 'revoked' : (isPaused ? 'paused' : 'valid');

		const totalBytes = formatBytes((c.traffic_recv || 0) + (c.traffic_sent || 0));
		const downBytes = formatBytes(c.traffic_sent || 0);
		const upBytes = formatBytes(c.traffic_recv || 0);
		const safeName = escapeHtml(c.name);
		const safeNote = escapeHtml(c.note || '');
		const downColor = isOnline ? '#60a5fa' : 'var(--text-muted)';
		const upColor = isOnline ? '#34d399' : 'var(--text-muted)';
		const noteHtml = safeNote ? `<div class="client-note" title="${safeNote}">💬 ${safeNote}</div>` : '';
		const limitMbStr = c.speed_limit_kbps > 0 ? `${+(c.speed_limit_kbps / 8192).toFixed(2)} MB/s` : '—';

		const speedRowHtml = speedOn ? `<div class="live-speed-row"><span id="card-down-${safeName}" style="color:${downColor};">↓ ${c.speed_down_fmt || '0 B/s'}</span><span id="card-up-${safeName}" style="color:${upColor};">↑ ${c.speed_up_fmt || '0 B/s'}</span></div>` : '';
		const trafficBoxHtml = statsOn ? `<div class="card-traffic"><div><div class="traffic-main">${t('traffic')} ${totalBytes}</div><div class="traffic-sub">↓ ${downBytes} / ↑ ${upBytes}</div></div><button class="btn btn-sm" style="padding:4px 8px;" onclick="resetClientTraffic('${safeName}')">↺</button></div>` : '';
		const sitesBtnHtml = snifferOn ? `<button class="btn btn-sm" onclick="openDomainsModal('${safeName}')">🌐</button>` : '';

		const actionsHtml = c.status === 'valid'
			? `${sitesBtnHtml}<button class="btn btn-sm" onclick="showQrModal('${safeName}', '${c.share_token}')">📱</button><button class="btn btn-sm" onclick="copyShareUrl('${c.share_token}')">🔗</button><button class="btn btn-sm btn-primary" onclick="downloadClientConfig('${safeName}')">⬇️</button><button class="btn btn-sm ${isPaused ? 'btn-primary' : 'btn-warning'}" onclick="togglePauseClient('${safeName}')">${isPaused ? '▶️' : '⏸️'}</button><button class="btn btn-sm btn-danger" onclick="revokeClient('${safeName}', false)">🚫</button>`
			: `${sitesBtnHtml}<button class="btn btn-sm btn-success" onclick="restoreRevokedClient('${safeName}')">${t('restore')}</button><button class="btn btn-sm btn-danger" onclick="revokeClient('${safeName}', true)">${t('del')}</button>`;

		return `
			<div class="client-card ${isOnline ? 'online-card' : ''} ${isPaused ? 'paused-card' : ''}" id="client-card-${safeName}">
				<div>
					<div class="card-top"><div class="client-name">${safeName}</div><div class="client-badge ${badgeCls}">${statusLabel}</div></div>
					${noteHtml}
					<div class="card-details">
						<div style="display:flex; justify-content:space-between; margin-bottom:6px; gap:8px;">
							<span id="card-online-${safeName}">${onlineHtml}</span>
							<span style="font-size:11px;">${c.created} → ${c.expires}</span>
						</div>
						<div class="session-meta ${isOnline ? '' : 'offline-meta'}">
							<div class="session-row"><span>🌐 <strong>${c.real_ip}</strong></span><span>TUN: <strong>${c.virt_ip}</strong></span></div>
							${speedRowHtml}
						</div>
						${trafficBoxHtml}
						<div class="card-extra-meta">
							<div class="card-extra-line"><span>${t('connected')}</span><strong>${formatTs(c.last_connected_at)}</strong></div>
							<div class="card-extra-line"><span>${t('disconnected')}</span><strong>${formatTs(c.last_disconnected_at)}</strong></div>
							<div class="card-extra-line"><span>${t('speed_limit')}</span><strong>${limitMbStr}</strong></div>
						</div>
					</div>
				</div>
				<div class="card-actions">${actionsHtml}</div>
			</div>
		`;
	}).join('');
}

function setGlobalSpeedPreset(mb) {
	const el = document.getElementById('globalSpeedLimitMB');
	if (el) el.value = mb;
}

function renderSpeedLimitsEditor() {
	const mode = document.getElementById('speedLimitMode')?.value || panelConfig.speed_limit_mode || 'none';
	const globalGroup = document.getElementById('globalLimitGroup');
	const clientsCard = document.getElementById('speedLimitsClientsCard');
	const hintEl = document.getElementById('speedLimitsClientsHint');

	if (globalGroup) globalGroup.style.display = (mode === 'global' || mode === 'selected') ? 'block' : 'none';
	if (clientsCard) clientsCard.style.opacity = (mode === 'selected' || mode === 'per_client') ? '1' : '0.45';
	if (hintEl) {
		if (mode === 'selected') hintEl.textContent = t('hint_sel');
		else if (mode === 'per_client') hintEl.textContent = t('hint_per');
		else hintEl.textContent = t('hint_none');
	}

	let selected = [];
	try { selected = JSON.parse(panelConfig.selected_limit_clients || '[]'); } catch (e) {}
	const selSet = new Set(selected);

	const box = document.getElementById('speedLimitsClientsBox');
	if (!box) return;
	const validClients = allClientsList.filter(c => c.status === 'valid');
	if (!validClients.length) {
		box.innerHTML = `<div style="padding:20px; text-align:center; color:var(--text-muted);">${t('empty')}</div>`;
		return;
	}

	box.innerHTML = validClients.map(c => {
		const safeName = escapeHtml(c.name);
		const dot = c.is_online ? '🟢' : '⚪';
		const mbVal = c.speed_limit_kbps > 0 ? +(c.speed_limit_kbps / 8192).toFixed(2) : 0;
		const cbHtml = mode === 'selected'
			? `<input type="checkbox" class="limit-client-cb" data-client="${safeName}" ${selSet.has(c.name) ? 'checked' : ''}>`
			: '';
		const inputHtml = mode === 'per_client'
			? `<input type="number" min="0" step="0.5" class="search-input limit-per-client-input" data-client="${safeName}" value="${mbVal}" placeholder="0" style="width:95px; padding:6px 10px; font-size:12.5px;"><span style="font-size:11px; color:var(--text-muted);">MB/s</span>`
			: `<span style="font-size:11.5px; color:var(--text-muted); font-family:'JetBrains Mono',monospace;">${mbVal > 0 ? mbVal + ' MB/s' : '—'}</span>`;

		return `
			<div class="limit-row">
				<label class="limit-row-left" style="${mode === 'selected' ? 'cursor:pointer;' : ''}">
					${cbHtml}
					<span>${dot}</span>
					<span class="limit-row-name">${safeName}</span>
				</label>
				<div class="limit-row-right">${inputHtml}</div>
			</div>
		`;
	}).join('');
}

async function saveSpeedLimits() {
	const mode = document.getElementById('speedLimitMode').value;
	const globalMb = parseFloat(document.getElementById('globalSpeedLimitMB').value) || 0;
	const globalKbps = Math.round(globalMb * 8192);
	const selectedClients = Array.from(document.querySelectorAll('.limit-client-cb:checked')).map(el => el.dataset.client);
	const perClientLimits = {};
	document.querySelectorAll('.limit-per-client-input').forEach(el => {
		perClientLimits[el.dataset.client] = Math.round((parseFloat(el.value) || 0) * 8192);
	});

	const r = await fetch('/api/speed-limits', {
		method: 'POST', headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({ speed_limit_mode: mode, global_speed_limit_kbps: globalKbps, selected_limit_clients: selectedClients, per_client_limits: perClientLimits })
	});
	const d = await r.json();
	if (d.success) {
		panelConfig.speed_limit_mode = mode;
		panelConfig.global_speed_limit_kbps = String(globalKbps);
		panelConfig.selected_limit_clients = JSON.stringify(selectedClients);
		showToast('✅ Лимиты скорости применены');
		loadClients();
	} else showToast('❌ ' + (d.message || 'Ошибка'), 'error');
}

function getColorForClient(name) {
	if (!clientColorRegistry[name]) { clientColorRegistry[name] = colorPalette[paletteIdx % colorPalette.length]; paletteIdx++; }
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
	try { const r = await fetch(`/api/clients/speeds/history?seconds=${selectedWindowSeconds}`); const d = await r.json(); if (d.history) { speedDataPoints = d.history; renderChartData(); } } catch (e) {}
}
function syncChartUserDropdown() {
	const sel = document.getElementById('chartClientFilter');
	if (!sel) return;
	const currentVal = sel.value || '__ALL__';
	const namesSet = new Set();
	allClientsList.forEach(c => { if (c.status === 'valid') namesSet.add(c.name); });
	Object.keys(latestLiveSpeeds).forEach(name => namesSet.add(name));
	const sortedNames = Array.from(namesSet).sort((a, b) => a.localeCompare(b));
	let html = `<option value="__ALL__">${t('all_clients')}</option>`;
	sortedNames.forEach(name => { html += `<option value="${name}"${name === currentVal ? ' selected' : ''}>${latestLiveSpeeds[name] ? '🟢 ' : ''}${name}</option>`; });
	sel.innerHTML = html;
	sel.value = namesSet.has(currentVal) ? currentVal : '__ALL__';
}
function renderChartData() {
	if (!speedChart) return;
	const metric = document.getElementById('chartMetricType').value;
	const targetClient = document.getElementById('chartClientFilter').value;
	const labels = speedDataPoints.map(p => p.time);
	const names = new Set();
	speedDataPoints.forEach(p => Object.keys(p.speeds || {}).forEach(c => { if (targetClient === '__ALL__' || targetClient === c) names.add(c); }));
	speedChart.data.labels = labels;
	speedChart.data.datasets = Array.from(names).sort().map(client => {
		const color = getColorForClient(client);
		return { label: client, data: speedDataPoints.map(p => (p.speeds && p.speeds[client]) ? (p.speeds[client][metric] || 0) : 0), borderColor: color, backgroundColor: color + '15', fill: targetClient !== '__ALL__', borderWidth: 2, tension: 0.25, pointRadius: 0 };
	});
	speedChart.update('none');
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
				statusEl.innerHTML = `<span style="color:var(--warning); font-weight:600;">${t('paused')}</span>`;
			} else {
				statusEl.innerHTML = c.is_online
					? `<span style="color:var(--success); font-weight:600;">${t('online')}</span>`
					: `<span style="color:var(--text-muted);">${t('offline')}</span>`;
			}
		}

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

async function pollSpeedTick() {
	if (document.hidden) return;
	try {
		const res = await fetch('/api/clients/speeds');
		const data = await res.json();
		if (!data.speeds) return;
		latestLiveSpeeds = data.speeds;
		const nowTs = Date.now() / 1000;
		const timeStr = data.timestamp || new Date().toLocaleTimeString();

		speedDataPoints.push({ time: timeStr, ts: nowTs, speeds: data.speeds });
		speedDataPoints = speedDataPoints.filter(p => p.ts >= nowTs - selectedWindowSeconds);

		let td = 0, tu = 0;
		Object.values(data.speeds).forEach(s => { td += s.down || 0; tu += s.up || 0; });
		document.getElementById('liveTotalDown').textContent = formatSpeed(td);
		document.getElementById('liveTotalUp').textContent = formatSpeed(tu);

		const onlineCount = Object.keys(data.speeds).length;
		document.getElementById('liveActiveCount').textContent = onlineCount;
		document.getElementById('lastSyncTime').textContent = `${t('updated')} ${timeStr}`;

		const validTotal = allClientsList.filter(c => c.status === 'valid').length;
		if (validTotal > 0) {
			document.getElementById('activeClientsCount').textContent = `${onlineCount} / ${validTotal}`;
		}

		updateClientCardsRealtime(data.speeds);
		if (!chartFilterDirty) syncChartUserDropdown();
		if (document.getElementById('tab-speed').classList.contains('active')) renderChartData();
	} catch (e) {}
}
function changePollInterval() {
	const ms = parseInt(document.getElementById('chartPollInterval').value) || 1000;
	if (speedPollTimer) clearInterval(speedPollTimer);
	speedPollTimer = setInterval(pollSpeedTick, ms);
	pollSpeedTick();
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

async function loadInfographicsView() {
	const res = await fetch('/api/infographics');
	const json = await res.json();
	if (!json.success) return;
	const d = json.data;
	document.getElementById('infoTotalSent').textContent = formatBytes(d.total_sent);
	document.getElementById('infoTotalRecv').textContent = formatBytes(d.total_recv);
	document.getElementById('infoTotalAll').textContent = formatBytes(d.total_sent + d.total_recv);

	if (infoClientsChart) infoClientsChart.destroy();
	infoClientsChart = new Chart(document.getElementById('infoTopClientsChart').getContext('2d'), {
		type: 'bar', data: {
			labels: d.top_clients.map(x => x.name),
			datasets: [
				{ label: 'Download (GB)', data: d.top_clients.map(x => +(x.sent / (1024**3)).toFixed(2)), backgroundColor: '#3b82f6', borderRadius: 6 },
				{ label: 'Upload (GB)', data: d.top_clients.map(x => +(x.recv / (1024**3)).toFixed(2)), backgroundColor: '#10b981', borderRadius: 6 }
			]
		}, options: { responsive: true, maintainAspectRatio: false }
	});
	if (infoStatusChart) infoStatusChart.destroy();
	const sc = d.status_counts;
	infoStatusChart = new Chart(document.getElementById('infoStatusPieChart').getContext('2d'), {
		type: 'doughnut', data: { labels: ['Online', 'Offline', 'Paused', 'Revoked'], datasets: [{ data: [sc.online, sc.offline, sc.paused, sc.revoked], backgroundColor: ['#10b981', '#475569', '#f59e0b', '#ef4444'], borderWidth: 0 }] },
		options: { responsive: true, maintainAspectRatio: false }
	});
	if (infoDomainsChart) infoDomainsChart.destroy();
	infoDomainsChart = new Chart(document.getElementById('infoTopDomainsChart').getContext('2d'), {
		type: 'bar', data: { labels: d.top_domains.map(x => x.domain), datasets: [{ label: 'Requests', data: d.top_domains.map(x => x.count), backgroundColor: '#8b5cf6', borderRadius: 6 }] },
		options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false }
	});
}

function onTabGlobalDomainInput() {
	const input = document.getElementById('tabGlobalDomainSearch');
	const clearBtn = document.getElementById('clearTabGlobalDomainBtn');
	if (clearBtn && input) clearBtn.style.display = input.value.length > 0 ? 'inline-flex' : 'none';
	fetchTabGlobalDomains();
}
function clearTabGlobalDomainSearch() { const i = document.getElementById('tabGlobalDomainSearch'); if (i) i.value = ''; onTabGlobalDomainInput(); }
async function fetchTabGlobalDomains() {
	const q = (document.getElementById('tabGlobalDomainSearch')?.value || '').trim();
	const box = document.getElementById('tabGlobalDomainsListBox');
	if (!box) return;
	const r = await fetch(`/api/domains/global?q=${encodeURIComponent(q)}&limit=500`);
	const d = await r.json();
	const list = d.domains || [];
	box.innerHTML = list.map(item => `
		<div class="domain-row">
			<div class="domain-row-main">
				<span style="font-size:11px; padding:3px 8px; border-radius:6px; background:rgba(59,130,246,0.15); color:#60a5fa; font-weight:600; font-family:'JetBrains Mono',monospace;">👤 ${item.client_name}</span>
				<span class="domain-name">${item.domain}</span>
				${item.count > 1 ? `<span class="domain-count-badge">×${item.count}</span>` : ''}
			</div>
			<div class="domain-row-meta">
				<span class="domain-time">${item.time_fmt}</span>
				<button class="btn btn-sm btn-danger" style="padding:3px 8px; font-size:11px;" onclick="hideDomainFromSniffer('${item.domain}')">${t('hide')}</button>
			</div>
		</div>
	`).join('') || `<div style="text-align:center; padding:40px; color:var(--text-muted);">${t('no_records')}</div>`;
}
async function hideDomainFromSniffer(domain) {
	if (!confirm(`Исключить домен "${domain}" и поддомены?`)) return;
	const r = await fetch('/api/sniffer/ignored', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ domain }) });
	const d = await r.json();
	if (d.success) { showToast(`Домен ${domain} скрыт`); fetchTabGlobalDomains(); }
}
function openIgnoredDomainsModal() { document.getElementById('ignoredDomainsModal').classList.add('active'); loadIgnoredDomainsList(); }
async function loadIgnoredDomainsList() {
	const r = await fetch('/api/sniffer/ignored'); const d = await r.json(); const list = d.ignored || [];
	document.getElementById('ignoredDomainsCountBadge').textContent = list.length;
	document.getElementById('ignoredDomainsListBox').innerHTML = list.map(item => `<div class="domain-row"><span class="domain-name" style="color:var(--danger);">${item.domain}</span><button class="btn btn-sm btn-danger" onclick="deleteIgnoredDomain(${item.id})">${t('restore')}</button></div>`).join('') || `<div style="padding:20px; text-align:center; color:var(--text-muted);">${t('no_ignored')}</div>`;
}
async function addManualIgnoredDomain() {
	const input = document.getElementById('newIgnoredDomainInput'); const domain = input.value.trim(); if (!domain) return;
	const r = await fetch('/api/sniffer/ignored', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ domain }) });
	const d = await r.json(); if (d.success) { input.value = ''; loadIgnoredDomainsList(); fetchTabGlobalDomains(); }
}
async function deleteIgnoredDomain(id) { await fetch(`/api/sniffer/ignored/${id}`, { method: 'DELETE' }); loadIgnoredDomainsList(); }

function openDomainsModal(name) {
	currentDomainsClient = name;
	document.getElementById('domainsModalTitle').textContent = `${t('sites_prefix')} ${name}`;
	document.getElementById('domainSearchInput').value = '';
	switchDomainTab('history');
	document.getElementById('domainsModal').classList.add('active');
}
function switchDomainTab(tabName) {
	document.querySelectorAll('#domainsModal .d-tab-btn').forEach(b => b.classList.remove('active'));
	document.querySelectorAll('#domainsModal .d-tab-view').forEach(v => v.classList.remove('active'));
	document.getElementById(`d-tab-${tabName}`)?.classList.add('active');
	document.getElementById(`d-view-${tabName}`)?.classList.add('active');
	if (tabName === 'history') fetchClientDomains();
	else if (tabName === 'top') fetchClientTopDomains();
	else if (tabName === 'ips') fetchClientIps();
}
async function fetchClientDomains() {
	if (!currentDomainsClient) return;
	const q = document.getElementById('domainSearchInput').value.trim();
	const r = await fetch(`/api/clients/${encodeURIComponent(currentDomainsClient)}/domains?q=${encodeURIComponent(q)}`);
	const d = await r.json(); const list = d.domains || [];
	document.getElementById('domainsCountBadge').textContent = `${t('records_cnt')} ${list.length}`;
	document.getElementById('domainsListBox').innerHTML = list.map(i => `<div class="domain-row"><span class="domain-name">${i.domain} ${i.count > 1 ? '(×' + i.count + ')' : ''}</span><span class="domain-time">${i.time_fmt}</span></div>`).join('') || `<div style="padding:30px; text-align:center; color:var(--text-muted);">${t('no_records')}</div>`;
}
async function fetchClientTopDomains() {
	if (!currentDomainsClient) return;
	const r = await fetch(`/api/clients/${encodeURIComponent(currentDomainsClient)}/domains`);
	const d = await r.json(); const list = d.top_domains || [];
	document.getElementById('domainsTopBox').innerHTML = list.map((i, idx) => `<div class="domain-row"><span class="domain-name">#${idx+1} ${i.domain}</span><strong>${i.count} req</strong></div>`).join('') || `<div style="padding:30px; text-align:center; color:var(--text-muted);">${t('no_records')}</div>`;
}
async function fetchClientIps() {
	if (!currentDomainsClient) return;
	const r = await fetch(`/api/clients/${encodeURIComponent(currentDomainsClient)}/ips`);
	const d = await r.json(); const list = d.ips || [];
	document.getElementById('ipsListBox').innerHTML = list.map(i => `<div class="domain-row" style="flex-direction:column; align-items:stretch;"><div><strong style="color:#34d399;">${i.real_ip}</strong> (TUN: ${i.virt_ip})</div><div style="font-size:11px; color:var(--text-muted);">${t('login_in')} ${i.connected_fmt} | ${t('login_out')} ${i.disconnected_fmt}</div></div>`).join('') || `<div style="padding:30px; text-align:center; color:var(--text-muted);">${t('no_records')}</div>`;
}
async function clearClientDomains() {
	if (!currentDomainsClient || !confirm(`Очистить историю для ${currentDomainsClient}?`)) return;
	await fetch(`/api/clients/${encodeURIComponent(currentDomainsClient)}/domains`, { method: 'DELETE' });
	fetchClientDomains();
}

async function submitCreateClient() {
	const name = document.getElementById('newClientName').value.trim();
	const note = document.getElementById('newClientNote').value.trim();
	const limit_gb = parseFloat(document.getElementById('newClientLimit').value) || 0;
	const ttl_days = parseInt(document.getElementById('newClientTtl').value) || 0;
	if (!name) return;
	closeModals();
	const r = await fetch('/api/clients', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ name, note, limit_gb, ttl_days }) });
	const d = await r.json();
	if (d.success) { showToast('✅ Клиент создан'); await loadClients(); downloadClientConfig(name); }
	else showToast('❌ ' + (d.message || 'Ошибка'), 'error');
}
async function togglePauseClient(name) {
	const r = await fetch(`/api/clients/${encodeURIComponent(name)}/pause`, { method: 'POST' });
	const d = await r.json();
	if (d.success) { showToast(d.is_paused ? '⏸️ На паузе' : '▶️ Активен'); loadClients(); }
}
async function resetClientTraffic(name) {
	if (!confirm(`Обнулить трафик ${name}?`)) return;
	await fetch(`/api/clients/${encodeURIComponent(name)}/traffic`, { method: 'DELETE' });
	loadClients();
}
async function revokeClient(name, permanent) {
	if (!confirm(permanent ? `Удалить ${name} навсегда?` : `Отозвать ${name}?`)) return;
	const r = await fetch(`/api/clients/${encodeURIComponent(name)}?permanent=${permanent}`, { method: 'DELETE' });
	const d = await r.json();
	if (d.success) { showToast('✅ Готово'); loadClients(); }
}
async function restoreRevokedClient(name) {
	if (!confirm(`Восстановить ${name}?`)) return;
	const r = await fetch(`/api/clients/${encodeURIComponent(name)}/restore`, { method: 'POST' });
	const d = await r.json();
	if (d.success) { showToast('✅ Восстановлен'); loadClients(); }
}
function downloadClientConfig(name) { location.href = `/api/clients/${encodeURIComponent(name)}/download`; }
function copyShareUrl(token) { copyToClipboard(`${location.origin}/d/${encodeURIComponent(token)}`).then(() => showToast('✅ Ссылка скопирована')); }
function showQrModal(name, token) {
	const link = `${location.origin}/d/${encodeURIComponent(token)}`;
	document.getElementById('qrModalTitle').textContent = `📱 ${name}`;
	new QRious({ element: document.getElementById('qrCanvas'), value: link, size: 220, level: 'M' });
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
	document.getElementById('wgText').textContent = d.wg_up ? t('wg_on') : t('wg_off');
	document.getElementById('wgText').style.color = d.wg_up ? 'var(--success)' : 'var(--danger)';

	if (d.wg_endpoint) {
		document.getElementById('remoteEndpointConnected').style.display = 'block';
		document.getElementById('remoteEndpointForm').style.display = 'none';
		document.getElementById('remoteEndpointIp').textContent = d.wg_endpoint;
		document.getElementById('remoteEndpointStatus').textContent = d.wg_up ? t('remote_conn') : t('remote_inact');
	} else {
		document.getElementById('remoteEndpointConnected').style.display = 'none';
		document.getElementById('remoteEndpointForm').style.display = 'block';
		document.getElementById('remoteEndpointStatus').textContent = t('remote_none');
	}
	await loadSplitLinks();
	await loadAdblockStatus();
	renderPendingLinks();
}
function showRemoteReconfigure() { document.getElementById('remoteEndpointConnected').style.display = 'none'; document.getElementById('remoteEndpointForm').style.display = 'block'; }
function hideRemoteReconfigure() { document.getElementById('remoteEndpointForm').style.display = 'none'; document.getElementById('remoteEndpointConnected').style.display = 'block'; }

function renderPendingLinks() {
	const box = document.getElementById('pendingLinksBox');
	if (!box) return;
	box.innerHTML = pendingLinks.map((p, idx) => `
		<div class="pending-link-row">
			<div style="font-family:'JetBrains Mono',monospace; font-size:12px; color:#93c5fd;">🔗 ${p.url} (${(p.ips || []).join(', ')})</div>
			<div class="pending-actions">
				<div class="route-via-group">
					<button class="route-via-btn ${p.route_via === 'split' ? 'active' : ''}" onclick="setPendingRoute(${idx}, 'split')">${t('direct')}</button>
					<button class="route-via-btn ${p.route_via === 'wg' ? 'active' : ''}" onclick="setPendingRoute(${idx}, 'wg')">${t('via_wg')}</button>
				</div>
				<button class="btn btn-sm btn-primary" onclick="savePendingLink(${idx})">💾</button>
				<button class="btn btn-sm btn-danger" onclick="cancelPendingLink(${idx})">✕</button>
			</div>
		</div>
	`).join('');
}
function setPendingRoute(idx, route) { if (pendingLinks[idx]) { pendingLinks[idx].route_via = route; renderPendingLinks(); } }
function cancelPendingLink(idx) { pendingLinks.splice(idx, 1); renderPendingLinks(); }
async function savePendingLink(idx) {
	const p = pendingLinks[idx]; if (!p) return;
	const r = await fetch('/api/routing/save-link', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ url: p.url, resolved_ips: (p.ips || []).join(','), route_via: p.route_via }) });
	const d = await r.json(); if (d.success) { pendingLinks.splice(idx, 1); renderPendingLinks(); loadSplitLinks(); }
}
async function loadSplitLinks() {
	const r = await fetch('/api/routing/links'); const d = await r.json(); const box = document.getElementById('splitLinksList');
	if (!box) return;
	box.innerHTML = (d.links || []).map(l => `<div class="domain-row"><span class="domain-name">${l.url} [${l.route_via.toUpperCase()}]</span><button class="btn btn-sm btn-danger" onclick="removeSplitLink(${l.id})">✕</button></div>`).join('') || `<div style="padding:14px; text-align:center; color:var(--text-muted);">${t('no_records')}</div>`;
}
async function removeSplitLink(id) { await fetch(`/api/routing/links/${id}`, { method: 'DELETE' }); loadSplitLinks(); }
async function resolveLink() {
	const url = document.getElementById('splitLinkUrl').value.trim(); if (!url) return;
	const r = await fetch('/api/routing/resolve-link', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ url }) });
	const d = await r.json();
	if (d.success) { pendingLinks.push({ url: d.url || url, ips: d.ips || [], route_via: d.has_conflict ? 'wg' : 'split' }); document.getElementById('splitLinkUrl').value = ''; renderPendingLinks(); }
}
async function saveRoutingSettings() {
	const r = await fetch('/api/routing/settings', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ cidr_url: document.getElementById('cidrUrlInput').value.trim(), custom_cidrs: document.getElementById('customCidrsInput').value.trim(), routing_mode: document.getElementById('routingModeSelect').value }) });
	const d = await r.json();
	if (d.success) { showToast('✅ Настройки сохранены'); loadRoutingView(); }
	else { showToast('❌ ' + (d.message || 'Ошибка запуска WG0'), 'error'); loadRoutingView(); }
}
async function updateCidrIps() {
	const r = await fetch('/api/routing/update_ips', { method: 'POST' }); const d = await r.json();
	if (d.async && d.task_id) watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ CIDR обновлены'); loadRoutingView(); } });
}
async function setupRemoteTunnel() {
	const remote_ip = document.getElementById('remoteServerIp').value.trim(); const remote_pass = document.getElementById('remoteServerPass').value;
	if (!remote_ip || !remote_pass) return showToast('❌ Укажите IP и пароль', 'error');
	const r = await fetch('/api/routing/setup', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ remote_ip, remote_pass }) });
	const d = await r.json(); if (d.async && d.task_id) watchBackgroundTask(d.task_id, (ok, msg) => { if (ok) { showToast('✅ Туннель настроен'); loadRoutingView(); } else { showToast('❌ ' + (msg || 'Ошибка настройки туннеля'), 'error'); loadRoutingView(); } });
}

async function loadAdblockStatus() {
	const r = await fetch('/api/adblock/status'); const j = await r.json(); if (!j.success) return; const d = j.data;
	document.getElementById('adblockEnableToggle').checked = Boolean(d.enabled);
	document.getElementById('adblockStatusLabel').textContent = `${t('adb_status')} ${d.enabled ? t('adb_on') : t('adb_off')} | ${t('adb_rules')} ${(d.blocked_total || 0).toLocaleString()} (DNS: ${d.dns_ip})`;
	document.getElementById('adblockListsBox').innerHTML = (d.lists || []).map(l => `<div class="domain-row"><span class="domain-name">${l.url} (${l.domains_count})</span><button class="btn btn-sm btn-danger" onclick="deleteAdblockList(${l.id})">✕</button></div>`).join('') || `<div style="padding:14px; text-align:center; color:var(--text-muted);">${t('no_lists')}</div>`;
	document.getElementById('adblockDomainsBox').innerHTML = (d.domains || []).map(dom => `<div class="domain-row"><span class="domain-name">${dom.domain} [${dom.list_type}]</span><button class="btn btn-sm btn-danger" onclick="deleteAdblockDomain(${dom.id})">✕</button></div>`).join('') || `<div style="padding:14px; text-align:center; color:var(--text-muted);">${t('no_domains')}</div>`;
}
async function toggleAdblock(enable) {
	const r = await fetch('/api/adblock/toggle', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ enable }) });
	const d = await r.json(); if (d.async && d.task_id) watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ AdBlock обновлён'); loadAdblockStatus(); } });
}
async function addAdblockList() {
	const url = document.getElementById('adblockListUrl').value.trim(); const list_type = document.getElementById('adblockListType').value; if (!url) return;
	const r = await fetch('/api/adblock/lists', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ url, list_type }) });
	const d = await r.json(); if (d.async && d.task_id) { document.getElementById('adblockListUrl').value = ''; watchBackgroundTask(d.task_id, ok => { if (ok) { showToast('✅ Список загружен'); loadAdblockStatus(); } }); }
}
async function deleteAdblockList(id) { await fetch(`/api/adblock/lists/${id}`, { method: 'DELETE' }); loadAdblockStatus(); }
async function addAdblockDomain() {
	const domain = document.getElementById('adblockDomainInput').value.trim(); const list_type = document.getElementById('adblockDomainType').value; if (!domain) return;
	const r = await fetch('/api/adblock/domains', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ domain, list_type }) });
	const d = await r.json(); if (d.success) { document.getElementById('adblockDomainInput').value = ''; loadAdblockStatus(); }
}
async function deleteAdblockDomain(id) { await fetch(`/api/adblock/domains/${id}`, { method: 'DELETE' }); loadAdblockStatus(); }

async function loadConfigView() { const r = await fetch('/api/config'); const d = await r.json(); if (d.success) document.getElementById('serverConfigText').value = d.config; }
async function saveRawConfig(restart) { const r = await fetch('/api/config', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ config: document.getElementById('serverConfigText').value, restart }) }); const d = await r.json(); if (d.success) showToast('✅ server.conf сохранён'); }

async function loadSettingsView() {
	const r = await fetch('/api/settings'); const d = await r.json();
	if (d.success && d.settings) {
		const s = d.settings;
		panelConfig = { ...panelConfig, ...s };
		applyDynamicFeatureVisibility();
		document.getElementById('setAdminLogin').value = s.admin_login || '';
		document.getElementById('setAdminPass').value = '';
		document.getElementById('setSessionAge').value = s.session_max_age || 86400;
		document.getElementById('setPanelPort').value = s.panel_port || 8080;
		document.getElementById('setTunIface').value = s.tun_iface || 'tun0';
		document.getElementById('setMgmtHost').value = s.mgmt_host || '127.0.0.1';
		document.getElementById('setMgmtPort').value = s.mgmt_port || 7505;
		document.getElementById('setDomainRetention').value = s.domain_retention || 86400;
		document.getElementById('setEnableSniffer').checked = s.enable_sniffer !== "0";
		document.getElementById('setEnableSpeed').checked = s.enable_speed_monitor !== "0";
		document.getElementById('setEnableStats').checked = s.enable_traffic_stats !== "0";
		document.getElementById('setEnableIpHistory').checked = s.enable_ip_history !== "0";
		document.getElementById('setEnableInfographics').checked = s.enable_infographics !== "0";
		document.getElementById('setEnableHwBar').checked = s.enable_hardware_bar !== "0";
		document.getElementById('setQuicBlock').checked = s.quic_block !== "0";
		document.getElementById('setTorrentBlock').checked = s.torrent_block === "1";
		document.getElementById('speedLimitMode').value = s.speed_limit_mode || 'none';
		document.getElementById('globalSpeedLimitMB').value = s.global_speed_limit_kbps > 0 ? +(Number(s.global_speed_limit_kbps) / 8192).toFixed(2) : 0;
	}
}
async function saveAllAccountSettings(applyToOvpn) {
	const r = await fetch('/api/settings', {
		method: 'POST', headers: {'Content-Type':'application/json'},
		body: JSON.stringify({
			admin_login: document.getElementById('setAdminLogin').value.trim(),
			admin_password: document.getElementById('setAdminPass').value,
			session_max_age: parseInt(document.getElementById('setSessionAge').value) || 86400,
			panel_port: parseInt(document.getElementById('setPanelPort').value) || 8080,
			tun_iface: document.getElementById('setTunIface').value.trim() || 'tun0',
			mgmt_host: document.getElementById('setMgmtHost').value.trim() || '127.0.0.1',
			mgmt_port: parseInt(document.getElementById('setMgmtPort').value) || 7505,
			domain_retention: parseInt(document.getElementById('setDomainRetention').value) || 86400,
			enable_sniffer: document.getElementById('setEnableSniffer').checked ? "1" : "0",
			enable_speed_monitor: document.getElementById('setEnableSpeed').checked ? "1" : "0",
			enable_traffic_stats: document.getElementById('setEnableStats').checked ? "1" : "0",
			enable_ip_history: document.getElementById('setEnableIpHistory').checked ? "1" : "0",
			enable_infographics: document.getElementById('setEnableInfographics').checked ? "1" : "0",
			enable_hardware_bar: document.getElementById('setEnableHwBar').checked ? "1" : "0",
			quic_block: document.getElementById('setQuicBlock').checked ? "1" : "0",
			torrent_block: document.getElementById('setTorrentBlock').checked ? "1" : "0",
			apply_to_ovpn: Boolean(applyToOvpn)
		})
	});
	const d = await r.json(); if (d.success) { showToast('✅ Настройки сохранены'); loadSettingsView(); }
}
async function controlOvpnService(action) { const r = await fetch(`/api/service/${action}`, { method: 'POST' }); const d = await r.json(); if (d.success) { showToast(`✅ ${action} OK`); setTimeout(loadClients, 800); } }
async function runDbAction(action, confirmMsg) { if (confirmMsg && !confirm(confirmMsg)) return; const r = await fetch('/api/database/action', { method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify({ action }) }); const d = await r.json(); if (d.success) { showToast('✅ OK'); loadClients(); } }

function downloadBackupArchive() { location.href = '/api/backup'; closeModals(); }
async function processRestoreFile(e) {
	const file = e.target.files[0]; if (!file || !confirm('Перезаписать текущую конфигурацию?')) return; closeModals();
	const fd = new FormData(); fd.append('file', file);
	const r = await fetch('/api/restore', { method: 'POST', body: fd }); const d = await r.json();
	if (d.success) { showToast('✅ Восстановлено'); setTimeout(() => location.reload(), 1200); }
}

document.addEventListener('DOMContentLoaded', async () => {
	document.getElementById('pageSizeSelect').value = String(pageSize);
	initSpeedChart();
	await loadSettingsView();
	await loadClients();
	applyLanguage(currentLang);
	changePollInterval();
	pollSystemStats();
	setInterval(loadClients, 10000);
	setInterval(pollSystemStats, 5000);
});
</script>
</body>
</html>
"""

LANDING_HTML = r"""
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
		h1 { font-size: 22px; font-weight: 700; margin-bottom: 18px; }
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
		.btn-outline {
			background: rgba(30, 41, 59, 0.7); border: 1px solid rgba(255, 255, 255, 0.1);
			box-shadow: none; color: #f8fafc;
		}
	</style>
</head>
<body>
<div class="background"><div class="blob"></div></div>
<div class="card">
	<div class="logo">🛡️</div>
	<h1>{client_name}</h1>
	<div class="qr-box"><canvas id="qrCanvas"></canvas></div>
	<a href="/d/{token}/raw" class="btn">⬇️ Скачать .ovpn профиль</a>
	<a href="openvpn://import-profile/{raw_url}" class="btn btn-outline">⚡ Connect OpenVPN</a>
</div>
<script>
	new QRious({ element: document.getElementById('qrCanvas'), value: "{raw_url}", size: 200, level: 'M' });
</script>
</body>
</html>
"""