/* Fleet Management — Shared State & Helpers */
window.Fleet = {
    slaveData: [],
    selected: new Set(),
    expandedConfigs: new Set(),
    currentView: localStorage.getItem('slave_view') || 'list',
    checking: false,
    lastCheckedTs: null,
    currentVmConfig: {},
    healthHistory: {},
    resourceData: {},
    _lastPollTs: null,
    _countdownTimer: null,
    chartData: {},         // { ip: [{ts, cpu, ram, disk, net_rx, net_tx, jvm_rss, load, threads}] }
    _prevNetBytes: {},     // { ip: {rx, tx, ts} } for throughput delta
    drillDownIp: null,     // IP of expanded drill-down, or null
    provisionStatus: {},
    _metricsTimer: null,
    _metricsInterval: parseInt(localStorage.getItem('fleet_interval') || '30000'),
    jpropsCatalog: [],
    jpropsOverrides: {},
    jpropsPath: '',
    extData: [],
    extSelected: new Set(),
    currentLogIp: '',
    ACCESS_LEVEL: '',
    isAdmin: false,
    ICON_MORE: '',
    ICON_DOWNLOAD: '',
    ICON_TRASH: '',
    CURATED_SLAVE: {
        'RMI': ['server.rmi.localport','server_port','java.rmi.server.hostname','server.rmi.ssl.disable'],
        'Runtime': ['server.exitaftertest'],
        'HTTP': ['httpclient4.retrycount','httpsampler.ignore_failed_embedded_resources'],
        'Results / Save': ['jmeter.save.saveservice.output_format','jmeter.save.saveservice.timestamp_format'],
    },
};

/* ===== Helper functions (used across fleet JS files) ===== */

function gearIcon() {
    return '<svg class="icon" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z"/><circle cx="12" cy="12" r="3"/></svg>';
}

function statusBadge(s) {
    if (s.status === null) return '';
    if (s.enabled === false) return '<span class="badge badge-info" style="font-size:11px;">Disabled</span>';
    if (s.status === 'checking') return '<span class="badge badge-warning" style="font-size:11px;">Checking</span>';
    if (s.status !== 'up') return '<span class="badge badge-danger" style="font-size:11px;">Offline</span>';
    const jm = s.jmeter === 'running';
    return '<span class="badge badge-success" style="font-size:11px;">Online</span>'
        + (s.jmeter ? ` <span class="badge ${jm ? 'badge-success' : 'badge-warning'}" style="font-size:11px;">${jm ? 'JMeter Up' : 'JMeter Down'}</span>` : '');
}

function statusDot(s) {
    if (s.status === null) return '<span class="status-dot unknown"></span>';
    const cls = s.enabled === false ? 'unknown' : (s.status || 'down');
    const label = s.enabled === false ? 'Disabled' : s.status === 'up' ? 'Online' : s.status === 'checking' ? 'Checking' : 'Offline';
    return `<span class="status-dot ${cls}"></span><span class="text-xs text-secondary">${label}</span>`;
}

function historySparkline(s) {
    const entries = Fleet.healthHistory[s.ip];
    if (!entries || entries.length < 2) return '';
    const recent = entries.slice(-20);
    let dots = '';
    recent.forEach(e => {
        let color;
        if (e.status === 'up') color = 'var(--color-success, #22c55e)';
        else if (e.status === 'down') color = 'var(--color-danger, #ef4444)';
        else color = 'var(--color-border)';
        const title = new Date(e.timestamp * 1000).toLocaleString();
        dots += `<span style="display:inline-block;width:6px;height:12px;border-radius:1px;background:${color};margin-right:1px;" title="${title} — ${e.status}${e.cpu_percent != null ? ' CPU:' + e.cpu_percent + '%' : ''}${e.ram_percent != null ? ' RAM:' + e.ram_percent + '%' : ''}"></span>`;
    });
    return `<span style="display:inline-flex;align-items:center;gap:0;margin-left:4px;" title="Last ${recent.length} status checks">${dots}</span>`;
}

function provisionBadges(s) {
    const ps = Fleet.provisionStatus[s.ip];
    if (!ps) return '';
    const items = [
        { key: 'java', label: 'Java' },
        { key: 'jmeter', label: 'JMeter' },
        { key: 'scripts', label: 'Scripts' },
        { key: 'agent', label: 'Agent' },
        { key: 'firewall', label: 'FW' },
    ];
    return items.map(it => {
        const val = ps[it.key];
        if (val === undefined) return '';
        const cls = val ? 'badge-success' : 'badge-danger';
        return `<span class="badge ${cls}" style="font-size:9px;">${it.label}</span>`;
    }).join('');
}

function formatLastChecked() {
    if (!Fleet.lastCheckedTs) return '';
    const now = new Date();
    const diffMs = now - Fleet.lastCheckedTs;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return 'just now';
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffH = Math.floor(diffMin / 60);
    return `${diffH}h ago`;
}

async function saveSlaves() {
    const slaves = Fleet.slaveData.map(s => {
        const obj = { ip: s.ip, enabled: s.enabled !== false };
        if (s.nickname) obj.nickname = s.nickname;
        const ov = s.overrides || {};
        if (ov.user || ov.password || ov.dest_path || ov.jmeter_path || ov.key_file) obj.overrides = ov;
        return obj;
    });
    await api('/api/config/slaves', { method: 'PUT', body: { slaves } });
}

function updateSummary() {
    const total = Fleet.slaveData.length;
    const enabled = Fleet.slaveData.filter(s => s.enabled !== false).length;
    const disabled = total - enabled;
    const checked = Fleet.slaveData.filter(s => s.status !== null && s.enabled !== false).length;
    const up = Fleet.slaveData.filter(s => s.enabled !== false && s.status === 'up').length;
    const down = checked - up;

    const statsEl = document.getElementById('fleetStats');
    if (statsEl) {
        if (total > 0) {
            statsEl.style.display = '';
            document.getElementById('statVMs').textContent = total;
            document.getElementById('statOnline').textContent = up;
            document.getElementById('statOffline').textContent = down;
            document.getElementById('statDisabled').textContent = disabled;
        } else {
            statsEl.style.display = 'none';
        }
    }

    const lc = formatLastChecked();
    const lcEl = document.getElementById('lastCheckedLabel');
    if (lcEl) lcEl.textContent = lc ? 'checked ' + lc : '';
}

function progressBar(value, thresholds) {
    const t = thresholds || { warn: 60, danger: 80 };
    const cls = value > t.danger ? 'monitor-bar-danger' : value > t.warn ? 'monitor-bar-warn' : 'monitor-bar-ok';
    return `<div class="monitor-bar"><div class="monitor-bar-fill ${cls}" style="width:${Math.min(value, 100)}%"></div><span class="monitor-bar-label">${value}%</span></div>`;
}

function recordMetrics(ip, metrics) {
    if (!Fleet.chartData[ip]) Fleet.chartData[ip] = [];
    const arr = Fleet.chartData[ip];
    arr.push({ ts: Date.now(), ...metrics });
    const cutoff = Date.now() - 5 * 60 * 1000;
    while (arr.length > 0 && arr[0].ts < cutoff) arr.shift();
    if (typeof FleetDashboard !== 'undefined' && FleetDashboard.charts.cpu) {
        FleetDashboard.pushMetrics(ip, metrics);
    }
}

/* miniSparkline() and inlineMetrics() removed — replaced by FleetDashboard canvas charts */
