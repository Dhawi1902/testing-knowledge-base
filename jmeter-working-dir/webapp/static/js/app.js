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
    const BRAND_SVG = {
        grafana: '<svg class="icon" width="14" height="14" viewBox="0 0 128 128" fill="currentColor" stroke="none"><path d="M120.8 56.9c-.2-2.1-.6-4.5-1.2-7.2s-1.8-5.5-3.2-8.6c-1.5-3-3.4-6.2-5.9-9.1-1-1.2-2.1-2.3-3.2-3.5 1.8-6.9-2.1-13-2.1-13-6.7-.4-10.9 2.1-12.4 3.2-.2-.1-.6-.2-.8-.3-1.1-.4-2.3-.9-3.5-1.3-1.2-.3-2.4-.8-3.6-1-1.2-.3-2.5-.6-3.9-.8-.2 0-.4-.1-.7-.1C77.5 6 69.1 2 69.1 2c-9.6 6.2-11.4 14.4-11.4 14.4s0 .2-.1.4c-.6.1-1 .3-1.5.4-.7.2-1.4.4-2.1.8l-2.1.9c-1.4.7-2.8 1.3-4.2 2.1-1.3.8-2.6 1.5-3.9 2.4-.2-.1-.3-.2-.3-.2-12.9-5-24.3 1-24.3 1-1 13.8 5.2 22.3 6.4 23.9-.3.9-.6 1.7-.9 2.5-1 3.1-1.7 6.3-2.1 9.6-.1.4-.1 1-.2 1.4C10.5 67.5 7 79.6 7 79.6 16.9 91 28.5 91.7 28.5 91.7c1.4 2.6 3.2 5.2 5.1 7.5.8 1 1.7 1.9 2.5 2.9-3.6 10.3.6 19 .6 19 11.1.4 18.4-4.8 19.9-6.1 1.1.3 2.2.7 3.3 1 3.4.9 6.9 1.4 10.3 1.5h4.5c5.2 7.5 14.4 8.5 14.4 8.5 6.5-6.9 6.9-13.6 6.9-15.2v-.6c1.3-1 2.6-2 4-3.1 2.6-2.3 4.8-5.1 6.8-7.9.2-.2.3-.6.6-.8 7.4.4 12.5-4.6 12.5-4.6-1.2-7.7-5.6-11.4-6.5-12.1l-.1-.1-.1-.1-.1-.1c0-.4.1-.9.1-1.4.1-.9.1-1.7.1-2.5v-3.3c0-.2 0-.4-.1-.7l-.1-.7-.1-.7c-.1-.9-.3-1.7-.4-2.5-.8-3.3-2.1-6.5-3.7-9.2-1.8-2.9-3.9-5.3-6.3-7.5-2.4-2.1-5.1-3.9-7.9-5.1-2.9-1.3-5.7-2.1-8.7-2.4-1.4-.2-3-.2-4.4-.2h-2.3c-.8.1-1.5.2-2.2.3-3 .6-5.7 1.7-8.1 3.1-2.4 1.4-4.5 3.3-6.3 5.4-1.8 2.1-3.1 4.3-4 6.7-.9 2.3-1.4 4.8-1.5 7.2v2.6c0 .3 0 .6.1.9.1 1.2.3 2.3.7 3.4.7 2.2 1.7 4.2 3 5.9s2.8 3.1 4.4 4.2c1.7 1.1 3.3 1.9 5.1 2.4s3.4.8 5 .7h2.3c.2 0 .4-.1.6-.1.2 0 .3-.1.6-.1.3-.1.8-.2 1.1-.3.7-.2 1.3-.6 2-.8.7-.3 1.2-.7 1.7-1 .1-.1.3-.2.4-.3.6-.4.7-1.2.2-1.8-.4-.4-1.1-.6-1.7-.3-.1.1-.2.1-.4.2-.4.2-1 .4-1.4.6-.6.1-1.1.3-1.7.4-.3 0-.6.1-.9.1h-1.8s-.1 0 0 0h-.7c-.1 0-.3 0-.4-.1-1.2-.2-2.5-.6-3.7-1.1-1.2-.6-2.4-1.3-3.4-2.3-1.1-1-2-2.1-2.8-3.4-.8-1.3-1.2-2.8-1.4-4.2-.1-.8-.2-1.5-.1-2.3v-.7c0 .1 0 0 0 0V70c0-.4.1-.8.2-1.2.6-3.3 2.2-6.5 4.7-8.9.7-.7 1.3-1.2 2.1-1.7.8-.6 1.5-1 2.3-1.3.8-.3 1.7-.7 2.5-.9.9-.2 1.8-.4 2.6-.4.4 0 .9-.1 1.3-.1h.8c.1 0 0 0 0 0h.4c1 .1 2 .2 2.9.4 1.9.4 3.7 1.1 5.5 2.1 3.5 2 6.5 5 8.3 8.6.9 1.8 1.5 3.7 1.9 5.8.1.6.1 1 .2 1.5v2.7c0 .6-.1 1.1-.1 1.7-.1.6-.1 1.1-.2 1.7s-.2 1.1-.3 1.7c-.2 1.1-.7 2.1-1 3.2-.8 2.1-1.9 4.1-3.2 5.8-2.6 3.6-6.3 6.6-10.3 8.5-2.1.9-4.2 1.7-6.4 2-1.1.2-2.2.3-3.3.3h-1.6c.1 0 0 0 0 0h-.1c-.6 0-1.2 0-1.8-.1-2.4-.2-4.7-.7-7-1.3-2.3-.7-4.5-1.5-6.6-2.6-4.2-2.2-7.9-5.4-10.9-9-1.4-1.9-2.8-3.9-3.9-5.9s-1.9-4.3-2.5-6.5c-.7-2.2-1-4.5-1.1-6.8v-3.5c0-1.1.1-2.3.3-3.5.1-1.2.3-2.3.6-3.5.2-1.2.6-2.3.9-3.5.7-2.3 1.4-4.5 2.4-6.6 2-4.2 4.5-7.9 7.5-10.9.8-.8 1.5-1.4 2.4-2.1.3-.3 1.1-1 2-1.5s1.8-1.1 2.8-1.5c.4-.2.9-.4 1.4-.7.2-.1.4-.2.8-.3.2-.1.4-.2.8-.3 1-.4 2-.8 3-1.1.2-.1.6-.1.8-.2.2-.1.6-.1.8-.2.6-.1 1-.2 1.5-.4.2-.1.6-.1.8-.2.2 0 .6-.1.8-.1.2 0 .6-.1.8-.1l.4-.1.4-.1c.2 0 .6-.1.8-.1.3 0 .6-.1.9-.1.2 0 .7-.1.9-.1.2 0 .3 0 .6-.1h.7c.3 0 .6 0 .9-.1h.4s.1 0 0 0h4.1c2 .1 4 .3 5.8.7 3.7.7 7.4 1.9 10.6 3.5 3.2 1.5 6.2 3.5 8.6 5.6.1.1.3.2.4.4.1.1.3.2.4.4.3.2.6.6.9.8.3.2.6.6.9.8.2.3.6.6.8.9 1.1 1.1 2.1 2.3 3 3.4 1.8 2.3 3.2 4.6 4.3 6.8.1.1.1.2.2.4.1.1.1.2.2.4s.2.6.4.8c.1.2.2.6.3.8.1.2.2.6.3.8.4 1 .8 2 1.1 3 .6 1.5.9 2.9 1.2 4 .1.4.6.8 1 .8.6 0 .9-.4.9-1-.3-1.7-.3-3.1-.4-4.8z"/></svg>',
        influxdb: '<svg class="icon" width="14" height="14" viewBox="0 0 128 128" fill="currentColor" stroke="none"><path d="m94.543 87.625 29.379-6.75a3.35 3.35 0 0 0 1.258-.543 3.358 3.358 0 0 0 1.383-2.305c.058-.46.019-.925-.114-1.37L113.957 22.34a3.499 3.499 0 0 0-1.59-2.14 3.49 3.49 0 0 0-2.633-.391l-29.37 6.75c-.887.23-1.65.8-2.118 1.593a3.452 3.452 0 0 0-.383 2.625L90.32 85.094a3.499 3.499 0 0 0 1.59 2.14c.79.477 1.738.618 2.633.391Zm-10.125 33.566 35.621-33.054c1.344-1.36 1.004-2.196-.844-1.528l-24.484 5.575a6.222 6.222 0 0 0-2.715 1.46 6.221 6.221 0 0 0-1.676 2.586l-7.425 23.954c-.508 1.855.168 2.363 1.523 1.007Zm-64.992-10.789 53.344 16.52c.91.172 1.851.012 2.656-.45a3.947 3.947 0 0 0 1.734-2.07l8.938-28.68a3.48 3.48 0 0 0 .117-1.378 3.492 3.492 0 0 0-.418-1.317 3.473 3.473 0 0 0-.89-1.058 3.562 3.562 0 0 0-1.227-.633L30.336 74.973a3.545 3.545 0 0 0-2.695.304 3.57 3.57 0 0 0-1.696 2.118l-8.879 28.62a3.556 3.556 0 0 0 .278 2.68 3.547 3.547 0 0 0 2.082 1.707ZM2.2 51.7l10.816 47.452c.336 1.856 1.207 1.856 1.68 0l7.425-23.949a6.709 6.709 0 0 0 .031-3.113 6.783 6.783 0 0 0-1.37-2.793L3.721 50.852c-1.183-1.395-2.066-1.008-1.523.847ZM43.906.973 3.046 38.875a3.47 3.47 0 0 0-.168 4.848l20.43 22.144a3.483 3.483 0 0 0 2.415 1.098 3.48 3.48 0 0 0 2.484-.926l40.848-37.965a3.446 3.446 0 0 0 .172-4.847L48.832 1.094A3.48 3.48 0 0 0 47.722.3a3.467 3.467 0 0 0-1.326-.3 3.419 3.419 0 0 0-1.34.238 3.435 3.435 0 0 0-1.149.735Zm39.496 85.804c1.864.508 3.035-.496 2.54-2.422L74.124 33.082c-.508-1.855-2.035-2.363-3.375-1.02L32.258 67.895c-1.352 1.343-1.016 2.859.836 3.367Zm20.09-71.515L56.898.972c-1.851-.511-2.187.169-.675 1.684l17.054 18.387a6.549 6.549 0 0 0 2.7 1.527 6.58 6.58 0 0 0 3.093.11l24.485-5.563c1.8-.508 1.8-1.355-.063-1.855Zm0 0"/></svg>',
    };
    const links = [
        { key: 'monitoring_grafana', label: 'Grafana', svg: BRAND_SVG.grafana },
        { key: 'monitoring_influxdb', label: 'InfluxDB', svg: BRAND_SVG.influxdb },
    ];
    const menu = document.getElementById('monitoringMenu');
    const wrapper = document.getElementById('monitoringDropdown');
    if (!menu || !wrapper) return;
    let count = 0;
    links.forEach(({ key, label, svg }) => {
        const url = localStorage.getItem(key);
        if (!url) return;
        const a = document.createElement('a');
        a.className = 'dropdown-item';
        a.href = url;
        a.target = '_blank';
        a.rel = 'noopener';
        a.innerHTML = svg + ' ' + label;
        menu.appendChild(a);
        count++;
    });
    if (count > 0) wrapper.classList.remove('hidden');
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
