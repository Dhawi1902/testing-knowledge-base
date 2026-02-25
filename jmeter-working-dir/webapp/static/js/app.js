/* ===== Theme Init ===== */
(function() {
    const saved = localStorage.getItem('theme');
    if (saved) document.documentElement.setAttribute('data-theme', saved);
})();

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
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            const target = btn.dataset.tab;
            // Deactivate all
            el.querySelectorAll('.tab-btn').forEach(b => { b.classList.remove('active'); b.setAttribute('aria-selected', 'false'); });
            scope.querySelectorAll('.tab-panel').forEach(p => p.classList.remove('active'));
            // Activate target
            btn.classList.add('active');
            btn.setAttribute('aria-selected', 'true');
            const panel = scope.querySelector(`#${target}`);
            if (panel) panel.classList.add('active');
        });
    });
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
function confirmAction(message) {
    return window.confirm(message);
}

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
