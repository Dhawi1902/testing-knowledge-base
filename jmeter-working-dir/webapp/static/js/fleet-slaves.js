/* Fleet Management — Slaves Tab */

// ===== Load slaves (config only, no status check) =====
async function loadSlaves() {
    try {
        const data = await api('/api/config/slaves');
        Fleet.slaveData = (data.slaves || []).map(s => ({
            ip: typeof s === 'string' ? s : s.ip,
            nickname: (typeof s === 'object' && s.nickname) ? s.nickname : '',
            enabled: typeof s === 'string' ? true : s.enabled !== false,
            overrides: (typeof s === 'object' && s.overrides) ? s.overrides : {},
            status: null,
        }));
    } catch (e) {
        Fleet.slaveData = [];
    }
    render();
    updateSummary();
    updateViewButtons();
}

// ===== Status check =====
async function refreshStatus() {
    if (Fleet.checking) return;
    Fleet.checking = true;
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;

    Fleet.slaveData.forEach(s => { if (s.enabled !== false) s.status = 'checking'; });
    render();

    try {
        const data = await api('/api/slaves/status');
        const statusMap = {};
        (data.slaves || []).forEach(s => { statusMap[s.ip] = s; });
        Fleet.slaveData.forEach(s => {
            const st = statusMap[s.ip];
            if (st) {
                s.status = st.status || 'down';
                s.jmeter = st.jmeter || 'unknown';
                s.error = st.error || null;
            }
        });
        Fleet.lastCheckedTs = data.checked_at ? new Date(data.checked_at * 1000) : new Date();
    } catch (e) {
        Fleet.slaveData.forEach(s => { s.status = 'down'; });
        showToast('Failed to check status', 'error');
    }
    render();
    updateSummary();
    btn.disabled = false;
    Fleet.checking = false;
    loadHealthHistory().then(() => render());
}

// ===== Render =====
function render() {
    const emptyEl = document.getElementById('slavesEmpty');
    const containerEl = document.getElementById('slaveContainer');
    if (!emptyEl || !containerEl) return;
    if (!Fleet.slaveData.length) {
        emptyEl.style.display = '';
        containerEl.style.display = 'none';
    } else {
        emptyEl.style.display = 'none';
        containerEl.style.display = '';
    }
    if (Fleet.currentView === 'grid') renderGrid();
    else renderList();
    renderMonitoringPanel();
}

function renderList() {
    const container = document.getElementById('slaveContainer');
    if (!Fleet.slaveData.length) { container.innerHTML = ''; return; }
    const allSelected = Fleet.slaveData.length > 0 && Fleet.slaveData.every(s => Fleet.selected.has(s.ip));
    let html = '<div class="slave-list">';
    if (Fleet.isAdmin) {
        html += `<div class="slave-list-header">
            <label class="check">
                <input type="checkbox" class="select-cb" ${allSelected ? 'checked' : ''} onchange="toggleSelectAll(this.checked)">
                <span class="check-box"></span>
            </label>
            <span>Select all</span>
        </div>`;
    }
    Fleet.slaveData.forEach((s, i) => {
        const enabled = s.enabled !== false;
        const sel = Fleet.selected.has(s.ip);
        const expanded = Fleet.expandedConfigs.has(s.ip);
        const hasOverrides = s.overrides && (s.overrides.user || s.overrides.password || s.overrides.dest_path);
        const aIp = escAttr(s.ip);
        const ipClick = Fleet.isAdmin ? `onclick="editSlaveIp('${aIp}', this)" title="Click to edit"` : '';
        const hasMetrics = Fleet.resourceData[s.ip] && Fleet.resourceData[s.ip].cpu_percent != null;

        html += `<div class="slave-entry${enabled ? '' : ' disabled'}${sel ? ' selected' : ''}">
            <div class="slave-row">
                ${Fleet.isAdmin ? `<label class="check"><input type="checkbox" class="select-cb" ${sel ? 'checked' : ''} onchange="toggleSelect('${aIp}', this.checked)"><span class="check-box"></span></label>` : ''}
                ${statusDot(s)}
                <span class="slave-ip" ${ipClick}>${escHtml(s.ip)}</span>
                <span class="slave-meta">VM #${i + 1}${s.nickname ? ` <em>${escHtml(s.nickname)}</em>` : ''}${hasOverrides ? ' <span class="badge badge-sm">custom</span>' : ''}${historySparkline(s)}</span>
                <div class="slave-actions">
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-outline btn-xs" onclick="startSingle('${aIp}')" data-tooltip="Start">&#9654;</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-danger-outline btn-xs" onclick="stopSingle('${aIp}')" data-tooltip="Stop">&#9632;</button>` : ''}
                    ${Fleet.isAdmin ? `<button class="gear-btn${expanded ? ' active' : ''}" onclick="toggleConfig('${aIp}')" data-tooltip="SSH overrides">${gearIcon()}</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<div class="dropdown">
                        <button class="btn btn-outline btn-xs" onclick="toggleDropdown(this)">${Fleet.ICON_MORE}</button>
                        <div class="dropdown-menu">
                            <button class="dropdown-item" onclick="testSsh('${aIp}')">SSH Test</button>
                            <button class="dropdown-item" onclick="testRmi('${aIp}')">RMI Test</button>
                            <button class="dropdown-item" onclick="provisionSingle('${aIp}')">Provision</button>
                            <button class="dropdown-item" onclick="restartSingle('${aIp}')">Restart</button>
                            <button class="dropdown-item" onclick="viewLog('${aIp}')">View Log</button>
                            <button class="dropdown-item" onclick="confirmCleanData('${aIp}')">Clean Data</button>
                            <button class="dropdown-item" onclick="confirmCleanLog('${aIp}')">Clean Log</button>
                            <div class="dropdown-sep"></div>
                            <button class="dropdown-item" style="color:var(--color-danger)" onclick="removeSlave('${aIp}')">Remove</button>
                        </div>
                    </div>` : ''}
                    ${Fleet.isAdmin ? `<label class="toggle" title="${enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleSlave('${aIp}', this.checked)">
                        <span class="toggle-track"></span>
                    </label>` : ''}
                </div>
            </div>
            <div class="slave-row-details">
                ${hasMetrics ? inlineMetrics(s.ip) : `<div class="slave-status-row">${statusBadge(s)}${provisionBadges(s)}${s.error ? ' <span class="text-sm text-danger">' + escHtml(s.error) + '</span>' : ''}</div>`}
                ${hasMetrics ? `<div class="slave-status-row">${statusBadge(s)}${provisionBadges(s)}</div>` : ''}
            </div>
            ${expanded ? renderConfigPanel(s) : ''}
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderGrid() {
    const container = document.getElementById('slaveContainer');
    if (!Fleet.slaveData.length) { container.innerHTML = ''; return; }
    let html = '<div class="slave-grid">';
    Fleet.slaveData.forEach((s, i) => {
        const enabled = s.enabled !== false;
        const sel = Fleet.selected.has(s.ip);
        const expanded = Fleet.expandedConfigs.has(s.ip);
        const hasOverrides = s.overrides && (s.overrides.user || s.overrides.password || s.overrides.dest_path);
        const aIp = escAttr(s.ip);
        const ipClick = Fleet.isAdmin ? `onclick="editSlaveIp('${aIp}', this)" title="Click to edit"` : '';
        const hasMetrics = Fleet.resourceData[s.ip] && Fleet.resourceData[s.ip].cpu_percent != null;

        html += `<div class="vm-card${enabled ? '' : ' disabled'}${sel ? ' selected' : ''}">
            <div class="flex-between gap-8">
                <div class="flex gap-8 items-center">
                    ${Fleet.isAdmin ? `<label class="check"><input type="checkbox" class="select-cb" ${sel ? 'checked' : ''} onchange="toggleSelect('${aIp}', this.checked)"><span class="check-box"></span></label>` : ''}
                    <span class="vm-ip" ${ipClick}>${escHtml(s.ip)}</span>
                    ${hasOverrides ? '<span class="badge badge-sm">custom</span>' : ''}
                </div>
                <div class="flex gap-4 items-center flex-wrap">
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-outline btn-xs" onclick="startSingle('${aIp}')" data-tooltip="Start">&#9654;</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<button class="btn btn-danger-outline btn-xs" onclick="stopSingle('${aIp}')" data-tooltip="Stop">&#9632;</button>` : ''}
                    ${Fleet.isAdmin ? `<button class="gear-btn${expanded ? ' active' : ''}" onclick="toggleConfig('${aIp}')" data-tooltip="SSH overrides">${gearIcon()}</button>` : ''}
                    ${Fleet.isAdmin && enabled ? `<div class="dropdown">
                        <button class="btn btn-outline btn-xs" onclick="toggleDropdown(this)">${Fleet.ICON_MORE}</button>
                        <div class="dropdown-menu">
                            <button class="dropdown-item" onclick="testSsh('${aIp}')">SSH Test</button>
                            <button class="dropdown-item" onclick="testRmi('${aIp}')">RMI Test</button>
                            <button class="dropdown-item" onclick="provisionSingle('${aIp}')">Provision</button>
                            <button class="dropdown-item" onclick="restartSingle('${aIp}')">Restart</button>
                            <button class="dropdown-item" onclick="viewLog('${aIp}')">View Log</button>
                            <button class="dropdown-item" onclick="confirmCleanData('${aIp}')">Clean Data</button>
                            <button class="dropdown-item" onclick="confirmCleanLog('${aIp}')">Clean Log</button>
                            <div class="dropdown-sep"></div>
                            <button class="dropdown-item" style="color:var(--color-danger)" onclick="removeSlave('${aIp}')">Remove</button>
                        </div>
                    </div>` : ''}
                    ${Fleet.isAdmin ? `<label class="toggle" title="${enabled ? 'Disable' : 'Enable'}">
                        <input type="checkbox" ${enabled ? 'checked' : ''} onchange="toggleSlave('${aIp}', this.checked)">
                        <span class="toggle-track"></span>
                    </label>` : ''}
                </div>
            </div>
            <div class="vm-card-meta">
                VM #${i + 1}${s.nickname ? ` &mdash; <em>${escHtml(s.nickname)}</em>` : ''}
                ${historySparkline(s)}
            </div>
            <div class="vm-card-status">
                ${statusBadge(s)}${provisionBadges(s)}${s.error ? ' <span class="text-sm text-danger">' + escHtml(s.error) + '</span>' : ''}
            </div>
            ${hasMetrics ? inlineMetrics(s.ip) : ''}
            ${expanded ? renderConfigPanel(s) : ''}
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

// ===== View toggle =====
function setView(view) {
    Fleet.currentView = view;
    localStorage.setItem('slave_view', view);
    updateViewButtons();
    render();
}

function updateViewButtons() {
    const listBtn = document.getElementById('viewListBtn');
    const gridBtn = document.getElementById('viewGridBtn');
    if (listBtn) listBtn.classList.toggle('active', Fleet.currentView === 'list');
    if (gridBtn) gridBtn.classList.toggle('active', Fleet.currentView === 'grid');
}

// ===== Selection =====
function toggleSelect(ip, checked) {
    if (checked) Fleet.selected.add(ip);
    else Fleet.selected.delete(ip);
    updateBulkBar();
    render();
}

function clearSelection() {
    Fleet.selected.clear();
    updateBulkBar();
    render();
}

function toggleSelectAll(checked) {
    if (checked) Fleet.slaveData.forEach(s => Fleet.selected.add(s.ip));
    else Fleet.selected.clear();
    updateBulkBar();
    render();
}

function updateBulkBar() {
    const def = document.getElementById('defaultActions');
    const bulk = document.getElementById('bulkActions');
    if (!bulk) return;
    if (Fleet.selected.size > 0) {
        def.style.display = 'none';
        bulk.style.display = 'flex';
        document.getElementById('bulkCount').textContent = Fleet.selected.size + ' selected';
    } else {
        def.style.display = 'flex';
        bulk.style.display = 'none';
    }
}

async function bulkEnable(enabled) {
    for (const ip of Fleet.selected) {
        const slave = Fleet.slaveData.find(s => s.ip === ip);
        if (slave) slave.enabled = enabled;
    }
    await saveSlaves();
    showToast(`${Fleet.selected.size} slaves ${enabled ? 'enabled' : 'disabled'}`, 'info');
    Fleet.selected.clear();
    updateBulkBar();
    render();
    updateSummary();
}

async function bulkRemove() {
    if (!await confirmAction(`Remove ${Fleet.selected.size} slave(s)?`, { danger: true })) return;
    Fleet.slaveData = Fleet.slaveData.filter(s => !Fleet.selected.has(s.ip));
    await saveSlaves();
    showToast(`Removed ${Fleet.selected.size} slave(s)`, 'info');
    Fleet.selected.clear();
    updateBulkBar();
    render();
    updateSummary();
}

// ===== Single actions =====
async function toggleSlave(ip, enabled) {
    const slave = Fleet.slaveData.find(s => s.ip === ip);
    if (slave) slave.enabled = enabled;
    await saveSlaves();
    showToast(`${ip} ${enabled ? 'enabled' : 'disabled'}`, 'info');
    render();
    updateSummary();
}

function editSlaveIp(oldIp, spanEl) {
    const input = document.createElement('input');
    input.className = 'ip-edit';
    input.value = oldIp;
    spanEl.replaceWith(input);
    input.focus();
    input.select();

    async function commit() {
        const newIp = input.value.trim();
        if (!newIp || newIp === oldIp) { render(); return; }
        if (Fleet.slaveData.find(s => s.ip === newIp)) {
            showToast('IP already exists', 'warning');
            render();
            return;
        }
        const slave = Fleet.slaveData.find(s => s.ip === oldIp);
        if (slave) {
            if (Fleet.selected.has(oldIp)) { Fleet.selected.delete(oldIp); Fleet.selected.add(newIp); }
            slave.ip = newIp;
            await saveSlaves();
            showToast(`Updated ${oldIp} → ${newIp}`, 'info');
        }
        render();
    }

    input.addEventListener('blur', commit);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') input.blur();
        if (e.key === 'Escape') { input.value = oldIp; input.blur(); }
    });
}

async function addSlave() {
    const ip = await promptAction('Add Slave', { placeholder: '10.0.0.1 or 100.64.1.2', description: 'Enter the slave VM IP address', validate: v => v && v.trim() ? null : 'Enter a valid IP address' });
    if (!ip) return;
    const trimmed = ip.trim();
    const ipRegex = /^(\d{1,3}\.){3}\d{1,3}$/;
    const hostnameRegex = /^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?)*$/;
    if (!ipRegex.test(trimmed) && !hostnameRegex.test(trimmed)) {
        showToast('Invalid IP address or hostname', 'warning');
        return;
    }
    if (Fleet.slaveData.find(s => s.ip === trimmed)) {
        showToast('Slave already exists', 'warning');
        return;
    }
    Fleet.slaveData.push({ ip: trimmed, nickname: '', enabled: true, overrides: {}, status: null });
    await saveSlaves();
    showToast(`Added ${trimmed}`, 'success');
    render();
    updateSummary();
}

async function removeSlave(ip) {
    if (!await confirmAction(`Remove slave ${ip}?`, { danger: true })) return;
    Fleet.slaveData = Fleet.slaveData.filter(s => s.ip !== ip);
    Fleet.selected.delete(ip);
    await saveSlaves();
    showToast(`Removed ${ip}`, 'info');
    updateBulkBar();
    render();
    updateSummary();
}

// ===== Per-slave config overrides =====
function toggleConfig(ip) {
    if (Fleet.expandedConfigs.has(ip)) Fleet.expandedConfigs.delete(ip);
    else Fleet.expandedConfigs.add(ip);
    render();
}

function renderConfigPanel(s) {
    const ov = s.overrides || {};
    const ssh = Fleet.currentVmConfig.ssh_config || {};
    const ip = escAttr(s.ip);
    return `<form onsubmit="return false" class="slave-config-panel">
        <div class="form-group">
            <label class="form-label">Nickname</label>
            <input class="form-input" value="${escAttr(s.nickname || '')}" placeholder="Optional display name"
                onchange="updateNickname('${ip}',this.value)">
        </div>
        <div class="form-group">
            <label class="form-label">SSH User</label>
            <input class="form-input" value="${escAttr(ov.user || '')}" placeholder="${escAttr(ssh.user || 'root')}"
                onchange="updateOverride('${ip}','user',this.value)">
        </div>
        <div class="form-group">
            <label class="form-label">SSH Password</label>
            <input type="text" name="username" autocomplete="username" style="display:none" aria-hidden="true" tabindex="-1">
            <input class="form-input" type="password" value="${escAttr(ov.password || '')}" placeholder="(global default)"
                onchange="updateOverride('${ip}','password',this.value)" autocomplete="new-password">
        </div>
        <div class="form-group">
            <label class="form-label">SSH Key File</label>
            <input class="form-input form-input-mono" value="${escAttr(ov.key_file || '')}" placeholder="${escAttr(ssh.key_file || '(password auth)')}"
                onchange="updateOverride('${ip}','key_file',this.value)">
        </div>
        <div class="form-group" style="flex:2;">
            <label class="form-label">Dest Path</label>
            <input class="form-input form-input-mono" value="${escAttr(ov.dest_path || '')}" placeholder="${escAttr(ssh.dest_path || '/tmp/')}"
                onchange="updateOverride('${ip}','dest_path',this.value)">
        </div>
        <div class="form-group">
            <label class="form-label">JMeter Path</label>
            <input class="form-input form-input-mono" value="${escAttr(ov.jmeter_path || '')}" placeholder="${escAttr(ssh.jmeter_path || '(global default)')}"
                onchange="updateOverride('${ip}','jmeter_path',this.value)">
        </div>
        <div class="override-hint">Leave blank to use global defaults from VM Configuration.</div>
    </form>`;
}

async function updateNickname(ip, value) {
    const slave = Fleet.slaveData.find(s => s.ip === ip);
    if (!slave) return;
    slave.nickname = value.trim();
    await saveSlaves();
    render();
}

async function updateOverride(ip, field, value) {
    const slave = Fleet.slaveData.find(s => s.ip === ip);
    if (!slave) return;
    if (!slave.overrides) slave.overrides = {};
    slave.overrides[field] = value.trim();
    await saveSlaves();
    showToast(`${ip} override updated`, 'info');
}

// ===== Start/Stop All =====
async function startAll() {
    if (!await confirmAction('Start JMeter servers on all enabled slave VMs?')) return;
    const btn = document.getElementById('startAllBtn');
    if (btn) btn.disabled = true;
    try {
        const data = await api('/api/slaves/start', { method: 'POST' });
        const results = data.results || [];
        const ok = results.filter(r => r.ok).length;
        const fail = results.length - ok;
        showToast(`Started ${ok}/${results.length} servers${fail ? ` (${fail} failed)` : ''}`, fail ? 'warning' : 'success');
    } catch (e) {
        showToast('Failed to start servers', 'error');
    }
    if (btn) btn.disabled = false;
    setTimeout(refreshStatus, 3000);
}

async function stopAll() {
    if (!await confirmAction('Stop JMeter servers on all slave VMs?', { danger: true })) return;
    const btn = document.getElementById('stopAllBtn');
    if (btn) btn.disabled = true;
    try {
        const data = await api('/api/slaves/stop', { method: 'POST' });
        const results = data.results || [];
        const ok = results.filter(r => r.ok).length;
        showToast(`Stopped ${ok}/${results.length} servers`, 'success');
    } catch (e) {
        showToast('Failed to stop servers', 'error');
    }
    if (btn) btn.disabled = false;
    setTimeout(refreshStatus, 2000);
}

// ===== Individual Start/Stop =====
async function startSingle(ip) {
    showToast(`Starting JMeter on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/start`, { method: 'POST' });
        const r = data.result;
        showToast(r.ok ? `Started on ${ip}` : `Failed on ${ip}: ${r.error || 'Unknown error'}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`Failed to start on ${ip}`, 'error');
    }
    setTimeout(() => refreshStatus(), 3000);
}

async function stopSingle(ip) {
    showToast(`Stopping JMeter on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/stop`, { method: 'POST' });
        const r = data.result;
        showToast(r.ok ? `Stopped on ${ip}` : `Failed on ${ip}: ${r.error || 'Unknown error'}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`Failed to stop on ${ip}`, 'error');
    }
    setTimeout(() => refreshStatus(), 2000);
}

async function restartSingle(ip) {
    showToast(`Restarting JMeter on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/restart`, { method: 'POST' });
        const r = data.start_result;
        showToast(r.ok ? `Restarted on ${ip}` : `Restart failed on ${ip}: ${r.error || 'Unknown error'}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`Failed to restart on ${ip}`, 'error');
    }
    setTimeout(() => refreshStatus(), 3000);
}

// ===== Test SSH/RMI =====
async function testSsh(ip) {
    showToast(`Testing SSH to ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/test-ssh`, { method: 'POST' });
        const r = data.result;
        showToast(r.ok ? `SSH OK: ${ip}` : `SSH failed: ${ip} — ${r.message}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`SSH test failed for ${ip}`, 'error');
    }
}

async function testRmi(ip) {
    showToast(`Testing RMI port on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/test-rmi`, { method: 'POST' });
        const r = data.result;
        showToast(r.ok ? `RMI port open: ${ip}` : `RMI port closed: ${ip} — ${r.message}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`RMI test failed for ${ip}`, 'error');
    }
}

// ===== Provision =====
async function provisionSingle(ip) {
    openProvisionModal([ip]);
}

async function bulkProvision() {
    const ips = [...Fleet.selected].filter(ip => {
        const s = Fleet.slaveData.find(sl => sl.ip === ip);
        return s && s.enabled !== false;
    });
    if (!ips.length) { showToast('No enabled slaves selected', 'warning'); return; }
    openProvisionModal(ips);
}

function openProvisionModal(ips) {
    const modal = document.getElementById('provisionModal');
    const log = document.getElementById('provisionLog');
    const title = document.getElementById('provisionModalTitle');
    title.textContent = ips.length === 1 ? `Provisioning ${ips[0]}` : `Provisioning ${ips.length} slaves`;
    log.innerHTML = '';
    modal.style.display = 'flex';
    runProvision(ips, log);
}

function closeProvisionModal() {
    document.getElementById('provisionModal').style.display = 'none';
}

async function runProvision(ips, logEl) {
    for (const ip of ips) {
        appendLog(logEl, `\n=== Provisioning ${ip} ===`, 'text-light');
        try {
            const data = await api(`/api/slaves/${encodeURIComponent(ip)}/provision`, { method: 'POST' });
            const r = data.result;
            if (r.steps) {
                r.steps.forEach(step => {
                    const icon = step.ok ? '\u2713' : '\u2717';
                    appendLog(logEl, `  ${icon} ${step.name}: ${step.detail || (step.ok ? 'OK' : 'FAILED')}`);
                });
            }
            if (r.status) {
                Fleet.provisionStatus[ip] = r.status;
            }
            appendLog(logEl, r.ok ? `  => ${ip} provisioned successfully` : `  => ${ip} provisioning had errors`, '');
        } catch (e) {
            appendLog(logEl, `  ERROR: Failed to provision ${ip} — ${e.message || 'network error'}`, '');
        }
    }
    appendLog(logEl, '\nDone.', 'text-light');
    document.getElementById('provisionModalTitle').textContent = 'Provisioning Complete';
    render();
}

async function checkProvisionStatus(ip) {
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/provision-status`, { method: 'POST' });
        if (data.result && data.result.status) {
            Fleet.provisionStatus[ip] = data.result.status;
            render();
        }
    } catch (e) { /* ignore */ }
}

// ===== Collapse =====
function toggleSlaveList() {
    const body = document.getElementById('slaveBody');
    const icon = document.getElementById('slaveCollapseIcon');
    if (!body || !icon) return;
    const hidden = body.style.display === 'none';
    body.style.display = hidden ? '' : 'none';
    icon.innerHTML = hidden ? '&#9660;' : '&#9654;';
}

// ===== Sync Data =====
async function syncData() {
    const modal = document.getElementById('syncModal');
    const preview = document.getElementById('syncPreview');
    const logEl = document.getElementById('syncLog');
    logEl.style.display = 'none';
    logEl.innerHTML = '';
    preview.innerHTML = 'Loading...';
    modal.style.display = 'flex';
    try {
        const data = await api('/api/slaves/sync-data/preview');
        if (!data.files || !data.files.length) {
            preview.innerHTML = '<div class="text-light">No CSV files in test data directory.</div>';
            document.getElementById('syncBtn').disabled = true;
            return;
        }
        if (!data.slaves || !data.slaves.length) {
            preview.innerHTML = '<div class="text-light">No active slaves configured.</div>';
            document.getElementById('syncBtn').disabled = true;
            return;
        }
        document.getElementById('syncBtn').disabled = false;
        let html = `<div class="text-sm mb-8"><strong>${data.files.length} file(s)</strong> will be copied to <strong>${data.slaves.length} slave(s)</strong>:</div>`;
        html += '<ul style="margin:0;padding-left:20px;">';
        data.files.forEach(f => { html += `<li class="text-sm">${escHtml(f.filename)} (${f.size || '?'})</li>`; });
        html += '</ul>';
        html += `<div class="text-sm text-light mt-8">Target slaves: ${data.slaves.map(escHtml).join(', ')}</div>`;
        preview.innerHTML = html;
    } catch (e) {
        preview.innerHTML = '<div class="text-light">Failed to load preview.</div>';
    }
}

function closeSyncModal() {
    document.getElementById('syncModal').style.display = 'none';
}

async function runSyncData() {
    const logEl = document.getElementById('syncLog');
    const btn = document.getElementById('syncBtn');
    btn.disabled = true;
    btn.textContent = 'Syncing...';
    logEl.style.display = '';
    appendLog(logEl, 'Distributing files to slaves...', 'text-light');
    try {
        const data = await api('/api/slaves/sync-data', { method: 'POST' });
        if (data.results) {
            data.results.forEach(r => {
                const icon = r.ok ? '\u2713' : '\u2717';
                appendLog(logEl, `  ${icon} ${r.ip}: ${r.file} — ${r.detail || (r.ok ? 'OK' : 'FAILED')}`);
            });
        }
        appendLog(logEl, `\n${data.summary || 'Done.'}`, 'text-light');
        showToast(data.ok ? 'Data synced successfully' : 'Some transfers failed', data.ok ? 'success' : 'warning');
    } catch (e) {
        appendLog(logEl, `ERROR: ${e.message || 'Sync failed'}`, '');
        showToast('Sync failed', 'error');
    }
    btn.textContent = 'Sync All';
    btn.disabled = false;
}

// ===== View Slave Log =====
async function viewLog(ip) {
    Fleet.currentLogIp = ip;
    const modal = document.getElementById('logModal');
    const content = document.getElementById('logContent');
    const title = document.getElementById('logModalTitle');
    const pathEl = document.getElementById('logPath');
    title.textContent = `Log: ${ip}`;
    content.textContent = 'Loading...';
    pathEl.textContent = '';
    modal.style.display = 'flex';
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/log`);
        const r = data.result;
        if (r.ok) {
            content.textContent = r.log || '(empty log)';
            content.scrollTop = content.scrollHeight;
        } else {
            content.textContent = `Error: ${r.error || 'Failed to fetch log'}`;
        }
        pathEl.textContent = r.path || '';
    } catch (e) {
        content.textContent = `Failed to fetch log: ${e.message || 'network error'}`;
    }
}

function closeLogModal() {
    document.getElementById('logModal').style.display = 'none';
    Fleet.currentLogIp = '';
}

async function refreshLog() {
    if (Fleet.currentLogIp) await viewLog(Fleet.currentLogIp);
}

async function saveCurrentLog() {
    if (!Fleet.currentLogIp) return;
    showToast(`Saving log from ${Fleet.currentLogIp}...`, 'info');
    try {
        const data = await api('/api/slaves/collect-logs', { method: 'POST', body: { ips: [Fleet.currentLogIp] } });
        const r = data.results?.[0];
        showToast(r?.ok ? `Saved to ${data.dest}/${r.file}` : `Save failed: ${r?.error || 'Unknown'}`, r?.ok ? 'success' : 'error');
    } catch (e) {
        showToast('Save failed', 'error');
    }
}

// ===== Clean Data =====
function confirmCleanData(ip) {
    if (!confirm(`Delete all CSV files in test_data/ on ${ip}?`)) return;
    cleanData(ip);
}

async function cleanData(ip) {
    showToast(`Cleaning data on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/clean-data`, { method: 'POST' });
        const r = data.result;
        showToast(r.ok ? `Cleaned ${r.files_removed} file(s) on ${ip}` : `Clean failed on ${ip}: ${r.error || 'Unknown'}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`Clean failed for ${ip}`, 'error');
    }
}

async function bulkCleanData() {
    const ips = [...Fleet.selected].filter(ip => {
        const s = Fleet.slaveData.find(sl => sl.ip === ip);
        return s && s.enabled !== false;
    });
    if (!ips.length) { showToast('No enabled slaves selected', 'warning'); return; }
    if (!confirm(`Delete all CSV files in test_data/ on ${ips.length} slave(s)?`)) return;
    showToast(`Cleaning data on ${ips.length} slaves...`, 'info');
    try {
        const data = await api('/api/slaves/bulk-clean-data', { method: 'POST', body: { ips } });
        const ok = data.results.filter(r => r.ok).length;
        showToast(`Cleaned data: ${ok}/${data.results.length} succeeded`, ok === data.results.length ? 'success' : 'warning');
    } catch (e) {
        showToast('Bulk clean failed', 'error');
    }
}

// ===== Clean Logs =====
function confirmCleanLog(ip) {
    if (!confirm(`Truncate jmeter-slave.log on ${ip}?`)) return;
    cleanLog(ip);
}

async function cleanLog(ip) {
    showToast(`Cleaning log on ${ip}...`, 'info');
    try {
        const data = await api(`/api/slaves/${encodeURIComponent(ip)}/clean-log`, { method: 'POST' });
        const r = data.result;
        const size = r.bytes_cleared > 1024 ? `${(r.bytes_cleared / 1024).toFixed(1)} KB` : `${r.bytes_cleared} bytes`;
        showToast(r.ok ? `Log cleared on ${ip} (${size})` : `Clean log failed on ${ip}: ${r.error || 'Unknown'}`, r.ok ? 'success' : 'error');
    } catch (e) {
        showToast(`Clean log failed for ${ip}`, 'error');
    }
}

async function bulkCleanLogs() {
    const ips = [...Fleet.selected].filter(ip => {
        const s = Fleet.slaveData.find(sl => sl.ip === ip);
        return s && s.enabled !== false;
    });
    if (!ips.length) { showToast('No enabled slaves selected', 'warning'); return; }
    if (!confirm(`Truncate jmeter-slave.log on ${ips.length} slave(s)?`)) return;
    showToast(`Cleaning logs on ${ips.length} slaves...`, 'info');
    try {
        const data = await api('/api/slaves/bulk-clean-logs', { method: 'POST', body: { ips } });
        const ok = data.results.filter(r => r.ok).length;
        showToast(`Cleaned logs: ${ok}/${data.results.length} succeeded`, ok === data.results.length ? 'success' : 'warning');
    } catch (e) {
        showToast('Bulk clean logs failed', 'error');
    }
}

// ===== Collect Logs =====
async function collectLogs() {
    const ips = [...Fleet.selected].filter(ip => {
        const s = Fleet.slaveData.find(sl => sl.ip === ip);
        return s && s.enabled !== false;
    });
    if (!ips.length) { showToast('No enabled slaves selected', 'warning'); return; }
    showToast(`Collecting logs from ${ips.length} slave(s)...`, 'info');
    try {
        const data = await api('/api/slaves/collect-logs', { method: 'POST', body: { ips } });
        showToast(data.ok ? `Logs saved: ${data.summary}` : `Partial: ${data.summary}`, data.ok ? 'success' : 'warning');
    } catch (e) {
        showToast('Collect logs failed', 'error');
    }
}

// ===== Saved Logs =====
async function openSavedLogs() {
    const modal = document.getElementById('savedLogsModal');
    const content = document.getElementById('savedLogsContent');
    const pathEl = document.getElementById('savedLogsPath');
    content.innerHTML = 'Loading...';
    pathEl.textContent = '';
    modal.style.display = 'flex';
    try {
        const data = await api('/api/slaves/saved-logs');
        pathEl.textContent = data.dest || '';
        if (!data.files || !data.files.length) {
            content.innerHTML = '<div class="text-center text-light py-16">No saved logs yet. Use "Collect Logs" to fetch from slaves.</div>';
            return;
        }
        let html = '<table class="table"><thead><tr><th>Slave IP</th><th>Filename</th><th>Size</th><th>Saved</th><th></th></tr></thead><tbody>';
        data.files.forEach(f => {
            const size = f.size > 1024 * 1024 ? (f.size / 1024 / 1024).toFixed(1) + ' MB' : f.size > 1024 ? (f.size / 1024).toFixed(1) + ' KB' : f.size + ' B';
            const date = new Date(f.modified * 1000).toLocaleString();
            html += `<tr>
                <td><code>${f.ip}</code></td>
                <td>${f.filename}</td>
                <td>${size}</td>
                <td>${date}</td>
                <td class="flex gap-4">
                    <button class="btn btn-outline btn-sm" onclick="viewSavedLog('${f.filename}')">View</button>
                    <a class="btn btn-outline btn-sm" href="${BASE_PATH}/api/slaves/saved-logs/${f.filename}" download>${Fleet.ICON_DOWNLOAD}</a>
                </td>
            </tr>`;
        });
        html += '</tbody></table>';
        content.innerHTML = html;
    } catch (e) {
        content.innerHTML = `<div class="text-center text-danger">Failed to load: ${e.message}</div>`;
    }
}

function closeSavedLogsModal() {
    document.getElementById('savedLogsModal').style.display = 'none';
}

async function viewSavedLog(filename) {
    closeSavedLogsModal();
    const modal = document.getElementById('logModal');
    const content = document.getElementById('logContent');
    const title = document.getElementById('logModalTitle');
    const pathEl = document.getElementById('logPath');
    const ip = filename.replace('_jmeter-slave.log', '').replace(/_/g, ':');
    title.textContent = `Saved Log: ${ip}`;
    content.textContent = 'Loading...';
    pathEl.textContent = filename;
    modal.style.display = 'flex';
    Fleet.currentLogIp = '';
    try {
        const resp = await fetch(`${BASE_PATH}/api/slaves/saved-logs/${filename}`);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        content.textContent = await resp.text() || '(empty)';
        content.scrollTop = content.scrollHeight;
    } catch (e) {
        content.textContent = `Failed to load: ${e.message}`;
    }
}

// ===== Health History =====
async function loadHealthHistory() {
    try {
        const data = await api('/api/slaves/health-history');
        Fleet.healthHistory = data.history || {};
    } catch (e) {
        Fleet.healthHistory = {};
    }
}

// ===== Resource Monitoring =====
function _applyMetricsResults(results) {
    (results || []).forEach(r => {
        if (r.ok) {
            Fleet.resourceData[r.ip] = {
                cpu_percent: r.cpu_percent,
                ram_percent: r.ram_percent,
                ram_used_mb: r.ram_used_mb,
                ram_total_mb: r.ram_total_mb,
                jmeter_running: r.jmeter_running,
                jvm_rss_mb: r.jvm_rss_mb || null,
                jvm_threads: r.jvm_threads || null,
                disk_percent: r.disk_percent || null,
                disk_used_gb: r.disk_used_gb || null,
                disk_total_gb: r.disk_total_gb || null,
                load_1m: r.load_1m || null,
                net_rx_bytes: r.net_rx_bytes || null,
                net_tx_bytes: r.net_tx_bytes || null,
            };
            // Record for sparklines
            if (r.cpu_percent != null && r.ram_percent != null) {
                recordMetrics(r.ip, r.cpu_percent, r.ram_percent);
            }
            const slave = Fleet.slaveData.find(s => s.ip === r.ip);
            if (slave) slave.jmeter = r.jmeter_running ? 'running' : 'stopped';
        }
    });
    render();
}

async function refreshResources() {
    const btn = document.getElementById('resourcesBtn');
    if (btn) btn.disabled = true;
    try {
        const data = await api('/api/slaves/metrics');
        const results = data.results || [];
        const anyAgent = results.some(r => r.ok && r.agent);
        if (anyAgent) {
            _applyMetricsResults(results);
        } else {
            const sshData = await api('/api/slaves/resources');
            _applyMetricsResults(sshData.results);
        }
        showToast('Resource check complete', 'success');
    } catch (e) {
        showToast('Failed to check resources', 'error');
    }
    if (btn) btn.disabled = false;
}

function startMetricsPolling() {
    if (Fleet._metricsTimer) return;
    _pollMetrics();
    Fleet._metricsTimer = setInterval(_pollMetrics, Fleet._metricsInterval);
}

function stopMetricsPolling() {
    if (Fleet._metricsTimer) { clearInterval(Fleet._metricsTimer); Fleet._metricsTimer = null; }
}

async function _pollMetrics() {
    try {
        const data = await api('/api/slaves/metrics');
        const results = data.results || [];
        if (results.some(r => r.ok && r.agent)) {
            _applyMetricsResults(results);
        }
    } catch (e) { /* silent fail for auto-poll */ }
}

// ===== Monitoring toggle =====
function toggleMonitoring(btn) {
    if (Fleet._metricsTimer) {
        stopMetricsPolling();
        btn.classList.remove('btn-primary');
        btn.classList.add('btn-outline');
        localStorage.setItem('fleet_monitoring', 'off');
        showToast('Monitoring stopped', 'info');
    } else {
        startMetricsPolling();
        btn.classList.remove('btn-outline');
        btn.classList.add('btn-primary');
        localStorage.setItem('fleet_monitoring', 'on');
        const secs = Fleet._metricsInterval < 60000 ? `${Fleet._metricsInterval/1000}s` : `${Fleet._metricsInterval/60000}m`;
        showToast(`Monitoring started (${secs} interval)`, 'success');
    }
    renderMonitoringPanel();
}

function onIntervalChange() {
    const sel = document.getElementById('monitorInterval');
    Fleet._metricsInterval = parseInt(sel.value);
    localStorage.setItem('fleet_interval', Fleet._metricsInterval);
    if (Fleet._metricsTimer) {
        stopMetricsPolling();
        startMetricsPolling();
    }
    renderMonitoringPanel();
}

// ===== Monitoring Panel =====
function renderMonitoringPanel() {
    const panel = document.getElementById('monitoringPanel');
    if (!panel) return;

    const hasData = Object.keys(Fleet.resourceData).length > 0;
    if (!Fleet._metricsTimer || !hasData) {
        panel.style.display = 'none';
        return;
    }
    panel.style.display = '';

    // Update interval label
    const intervalLabel = document.getElementById('monitorIntervalLabel');
    if (intervalLabel) {
        const secs = Fleet._metricsInterval / 1000;
        intervalLabel.textContent = secs >= 60 ? `every ${secs/60}m` : `every ${secs}s`;
    }

    // Update live indicator
    const liveEl = document.getElementById('liveIndicator');
    if (liveEl) liveEl.style.display = Fleet._metricsTimer ? '' : 'none';

    const body = document.getElementById('monitoringBody');
    let html = '<table class="table"><thead><tr><th>Slave</th><th style="min-width:160px;">CPU</th><th style="min-width:160px;">RAM</th><th style="width:100px;">JVM RSS</th></tr></thead><tbody>';

    Fleet.slaveData.forEach(s => {
        if (s.enabled === false) return;
        const r = Fleet.resourceData[s.ip];
        if (!r) return;

        html += '<tr>';
        html += `<td><code>${escHtml(s.ip)}</code>${s.nickname ? ' <span class="text-light text-sm">(' + escHtml(s.nickname) + ')</span>' : ''}</td>`;

        if (r.cpu_percent != null) {
            html += `<td>${progressBar(r.cpu_percent, { warn: 60, danger: 80 })}</td>`;
        } else {
            html += '<td class="text-light">&mdash;</td>';
        }

        if (r.ram_percent != null) {
            const ramDetail = r.ram_total_mb ? `${r.ram_used_mb}/${r.ram_total_mb} MB` : '';
            html += `<td>${progressBar(r.ram_percent, { warn: 75, danger: 90 })}${ramDetail ? `<span class="text-xs text-light">${ramDetail}</span>` : ''}</td>`;
        } else {
            html += '<td class="text-light">&mdash;</td>';
        }

        if (r.jvm_rss_mb != null) {
            const cls = r.jvm_rss_mb > 900 ? 'text-danger' : r.jvm_rss_mb > 600 ? 'text-warning' : '';
            html += `<td class="${cls}" style="font-weight:600;">${r.jvm_rss_mb} MB</td>`;
        } else {
            html += '<td class="text-light">&mdash;</td>';
        }

        html += '</tr>';
    });

    html += '</tbody></table>';
    body.innerHTML = html;
}

// ===== Keyboard shortcuts =====
document.addEventListener('keydown', function(e) {
    // Don't intercept when typing in inputs
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA' || e.target.tagName === 'SELECT') return;
    // Don't intercept with modifier keys (except Escape)
    if (e.key !== 'Escape' && (e.ctrlKey || e.metaKey || e.altKey)) return;

    switch (e.key) {
        case 'r':
            e.preventDefault();
            refreshStatus();
            break;
        case 'm':
            e.preventDefault();
            const mb = document.getElementById('monitorBtn');
            if (mb) toggleMonitoring(mb);
            break;
        case 'a':
            if (Fleet.isAdmin) { e.preventDefault(); addSlave(); }
            break;
        case '1':
            e.preventDefault();
            document.querySelector('.fleet-tabs .tab-btn[data-tab="tab-slaves"]')?.click();
            break;
        case '2':
            e.preventDefault();
            document.querySelector('.fleet-tabs .tab-btn[data-tab="tab-config"]')?.click();
            break;
        case '3':
            e.preventDefault();
            document.querySelector('.fleet-tabs .tab-btn[data-tab="tab-extensions"]')?.click();
            break;
        case 'Escape':
            if (Fleet.selected.size > 0) {
                e.preventDefault();
                clearSelection();
            }
            break;
    }
});
