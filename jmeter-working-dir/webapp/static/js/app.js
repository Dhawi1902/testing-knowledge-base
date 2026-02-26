/* ===== Theme Init ===== */
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

function toggleTheme() {
    const current = document.documentElement.getAttribute('data-theme');
    const next = current === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('theme', next);
}

/* ===== Sidebar Toggle ===== */
const sidebar = document.getElementById('sidebar');
const sidebarBackdrop = document.getElementById('sidebarBackdrop');
const sidebarToggle = document.getElementById('sidebarToggle');
const menuBtn = document.getElementById('menuBtn');

function isMobile() { return window.innerWidth <= 768; }

function openSidebar() {
    sidebar.classList.add('open');
    sidebar.classList.remove('collapsed');
    document.body.classList.remove('sidebar-collapsed');
    if (sidebarBackdrop) sidebarBackdrop.classList.add('active');
}

function closeSidebar() {
    if (isMobile()) {
        sidebar.classList.remove('open');
        if (sidebarBackdrop) sidebarBackdrop.classList.remove('active');
    } else {
        sidebar.classList.add('collapsed');
        document.body.classList.add('sidebar-collapsed');
    }
}

function toggleSidebar() {
    if (isMobile()) {
        sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    } else {
        sidebar.classList.contains('collapsed') ? openSidebar() : closeSidebar();
    }
}

if (sidebarToggle) sidebarToggle.addEventListener('click', closeSidebar);
if (menuBtn) menuBtn.addEventListener('click', toggleSidebar);
if (sidebarBackdrop) sidebarBackdrop.addEventListener('click', closeSidebar);

// Close sidebar on mobile when a nav link is clicked
document.querySelectorAll('.sidebar .nav-item').forEach(link => {
    link.addEventListener('click', () => { if (isMobile()) closeSidebar(); });
});

// Mobile-specific page init
(function initMobilePage() {
    if (!isMobile()) return;
    const mobileBar = document.getElementById('mobileActionBar');
    if (mobileBar) {
        document.body.classList.add('has-mobile-bar');
        const startBtn = document.getElementById('startTestBtn');
        const stopBtn = document.getElementById('stopTestBtn');
        const mBtns = mobileBar.querySelectorAll('.btn');
        if (startBtn && mBtns[0]) {
            const observer = new MutationObserver(() => {
                mBtns[0].disabled = startBtn.disabled;
                if (mBtns[1] && stopBtn) mBtns[1].disabled = stopBtn.disabled;
            });
            observer.observe(startBtn, { attributes: true, attributeFilter: ['disabled'] });
            if (stopBtn) observer.observe(stopBtn, { attributes: true, attributeFilter: ['disabled'] });
        }
    }
})();

/* ===== Toast Notifications ===== */
function showToast(message, type = 'info', duration = 4000, id = '') {
    const container = document.getElementById('toastContainer');
    if (id) dismissToast(id);
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    if (id) toast.dataset.toastId = id;
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateY(16px)';
        toast.style.transition = 'opacity 0.3s, transform 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}
function dismissToast(id) {
    const el = document.querySelector(`[data-toast-id="${id}"]`);
    if (el) el.remove();
}

/* ===== Base Path (from <meta name="base-path">) ===== */
const BASE_PATH = document.querySelector('meta[name="base-path"]')?.content || '';

/* ===== Fetch Wrapper ===== */
async function api(url, options = {}) {
    const defaults = {
        headers: { 'Content-Type': 'application/json' },
    };
    const config = { ...defaults, ...options };
    if (options.body && typeof options.body === 'object' && !(options.body instanceof FormData)) {
        config.body = JSON.stringify(options.body);
    }
    if (options.body instanceof FormData) {
        delete config.headers['Content-Type'];
    }
    try {
        const resp = await fetch(BASE_PATH + url, config);
        if (!resp.ok) {
            const data = await resp.json().catch(() => ({}));
            throw new Error(data.error || data.detail || `HTTP ${resp.status}`);
        }
        return await resp.json();
    } catch (err) {
        showToast(err.message, 'error');
        throw err;
    }
}

/* ===== Tab Switching ===== */
function initTabs(container) {
    const el = typeof container === 'string' ? document.querySelector(container) : container;
    if (!el) return;
    // Panels live as siblings/in the parent card, not inside the tab bar
    const scope = el.closest('.card') || el.parentElement || el;
    const buttons = el.querySelectorAll('.tab-btn');
    function activateTab(target) {
        el.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); });
        scope.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
        const btn = el.querySelector(`.tab-btn[data-tab="${target}"]`);
        if (btn) { btn.classList.add('active'); btn.setAttribute('aria-selected', 'true'); }
        const panel = scope.querySelector(`#${target}`);
        if (panel) panel.classList.add('active');
    }
    buttons.forEach(btn => {
        btn.addEventListener('click', () => activateTab(btn.dataset.tab));
    });
    // Activate tab from URL hash (e.g. #tab-integrations)
    const hash = window.location.hash.replace('#', '');
    if (hash && scope.querySelector(`#${hash}`)) {
        activateTab(hash);
    }
}

/* ===== Modal ===== */
function openModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.add('active');
}

function closeModal(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.remove('active');
}

// Close modal on overlay click
document.addEventListener('click', (e) => {
    if (e.target.classList.contains('modal-overlay')) {
        e.target.classList.remove('active');
    }
});

/* ===== Confirm Dialog ===== */
let _confirmResolve = null;
function confirmAction(message, { title = 'Confirm', detail = '', danger = false } = {}) {
    return new Promise(resolve => {
        _confirmResolve = resolve;
        document.getElementById('confirmTitle').textContent = title;
        document.getElementById('confirmMessage').textContent = message;
        const detailEl = document.getElementById('confirmDetail');
        detailEl.textContent = detail;
        detailEl.style.display = detail ? 'block' : 'none';
        const btn = document.getElementById('confirmBtn');
        btn.className = danger ? 'btn btn-danger' : 'btn btn-primary';
        btn.textContent = danger ? 'Delete' : 'Confirm';
        openModal('confirmModal');
        btn.focus();
    });
}
function closeConfirmModal(result) {
    closeModal('confirmModal');
    if (_confirmResolve) { _confirmResolve(result); _confirmResolve = null; }
}
document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && document.getElementById('confirmModal').classList.contains('active')) {
        closeConfirmModal(false);
    }
    if (e.key === 'Enter' && document.getElementById('confirmModal').classList.contains('active')) {
        closeConfirmModal(true);
    }
});

/* ===== Prompt Dialog ===== */
let _promptResolve = null;
let _promptValidate = null;
function promptAction(title, { placeholder = '', defaultValue = '', description = '', validate = null } = {}) {
    return new Promise(resolve => {
        _promptResolve = resolve;
        _promptValidate = validate;
        document.getElementById('promptTitle').textContent = title;
        document.getElementById('promptDesc').textContent = description;
        document.getElementById('promptDesc').style.display = description ? 'block' : 'none';
        const input = document.getElementById('promptInput');
        input.placeholder = placeholder;
        input.value = defaultValue;
        document.getElementById('promptError').classList.remove('active');
        openModal('promptModal');
        input.focus();
        input.select();
    });
}
function submitPromptModal() {
    const value = document.getElementById('promptInput').value.trim();
    if (_promptValidate) {
        const err = _promptValidate(value);
        if (err) {
            const errEl = document.getElementById('promptError');
            errEl.textContent = err;
            errEl.classList.add('active');
            return;
        }
    }
    closeModal('promptModal');
    if (_promptResolve) { _promptResolve(value); _promptResolve = null; }
}
function closePromptModal(value) {
    closeModal('promptModal');
    if (_promptResolve) { _promptResolve(value); _promptResolve = null; }
}
document.getElementById('promptInput').addEventListener('keydown', e => {
    if (e.key === 'Enter') submitPromptModal();
    if (e.key === 'Escape') closePromptModal(null);
});

/* ===== Dropdown Menu ===== */
function toggleDropdown(btn) {
    const menu = btn.nextElementSibling;
    const wasOpen = menu.classList.contains('open');
    document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    if (!wasOpen) menu.classList.add('open');
}
document.addEventListener('click', e => {
    if (!e.target.closest('.dropdown')) {
        document.querySelectorAll('.dropdown-menu.open').forEach(m => m.classList.remove('open'));
    }
});

/* ===== WebSocket Manager ===== */
class WSManager {
    constructor(url, options = {}) {
        this.url = url;
        this.ws = null;
        this.onMessage = null;
        this.onClose = null;
        this.onError = null;
        this._intentionalClose = false;
        this._retryCount = 0;
        this._maxRetries = options.maxRetries || 10;
        this._autoReconnect = options.autoReconnect !== false;
    }

    connect() {
        this._intentionalClose = false;
        const protocol = location.protocol === 'https:' ? 'wss:' : 'ws:';
        this.ws = new WebSocket(`${protocol}//${location.host}${BASE_PATH}${this.url}`);
        this.ws.onopen = () => {
            this._retryCount = 0;
        };
        this.ws.onmessage = (e) => {
            if (this.onMessage) this.onMessage(e.data);
        };
        this.ws.onclose = (e) => {
            if (!this._intentionalClose && this._autoReconnect && this._retryCount < this._maxRetries && e.code !== 4001) {
                const delay = Math.min(1000 * Math.pow(2, this._retryCount), 30000);
                this._retryCount++;
                setTimeout(() => this.connect(), delay);
            } else {
                if (this.onClose) this.onClose(e.code);
            }
        };
        this.ws.onerror = (e) => {
            if (this.onError) this.onError(e);
        };
        return this;
    }

    send(data) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(typeof data === 'string' ? data : JSON.stringify(data));
        }
    }

    close() {
        this._intentionalClose = true;
        if (this.ws) this.ws.close();
    }
}

/* ===== Monitoring Links (global, cached via localStorage) ===== */
(function initMonitoringLinks() {
    const grafana = localStorage.getItem('monitoring_grafana');
    const influxdb = localStorage.getItem('monitoring_influxdb');
    const grafanaEl = document.getElementById('grafanaLink');
    const influxdbEl = document.getElementById('influxdbLink');
    if (grafana && grafanaEl) { grafanaEl.href = grafana; grafanaEl.classList.remove('hidden'); }
    if (influxdb && influxdbEl) { influxdbEl.href = influxdb; influxdbEl.classList.remove('hidden'); }
})();

/* ===== Shared Utilities ===== */
function formatSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024*1024) return (bytes/1024).toFixed(1) + ' KB';
    return (bytes/(1024*1024)).toFixed(1) + ' MB';
}
function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function escAttr(s) { return escHtml(s).replace(/'/g, '&#39;'); }

/* ===== Auto-scroll Log Output ===== */
function appendLog(containerId, text, className = '') {
    const el = document.getElementById(containerId);
    if (!el) return;
    const span = document.createElement('span');
    if (className) span.className = className;
    span.textContent = text + '\n';
    el.appendChild(span);
    const autoScroll = document.getElementById('autoScrollToggle');
    if (!autoScroll || autoScroll.checked) {
        el.scrollTop = el.scrollHeight;
    }
}
