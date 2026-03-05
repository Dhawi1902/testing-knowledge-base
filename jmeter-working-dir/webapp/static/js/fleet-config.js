/* Fleet Management — Configuration Tab */

// ===== VM Configuration =====
async function loadVmConfig() {
    const data = await api('/api/config/vm');
    Fleet.currentVmConfig = data.config || {};
    renderVmConfig();
}

function renderVmConfig() {
    const container = document.getElementById('vmForm');
    if (!container) return;
    const ssh = Fleet.currentVmConfig.ssh_config || {};
    const scripts = Fleet.currentVmConfig.jmeter_scripts || {};
    const heap = Fleet.currentVmConfig.jmeter_heap || {};
    const slaveDir = Fleet.currentVmConfig.slave_dir || '~/jmeter-slave';
    const ro = Fleet.isAdmin ? '' : ' readonly';
    const dis = Fleet.isAdmin ? '' : ' disabled';
    container.innerHTML = `
        <form onsubmit="return false">
        <h3 class="text-sm mb-16 section-title">Slave Directory</h3>
        <div class="form-row mb-16">
            <div class="form-group form-col" style="flex:2;min-width:250px;">
                <label class="form-label">Base Directory (on slaves)</label>
                <input class="form-input form-input-mono" id="vm_slave_dir" value="${escHtml(slaveDir)}" placeholder="~/jmeter-slave"${ro}>
                <span class="text-sm text-secondary">Base path on slaves. Uses ~ which resolves via $HOME. test_data/, start-slave.sh, stop-slave.sh are derived from this.</span>
            </div>
        </div>
        <h3 class="text-sm mb-16 section-title">SSH Defaults</h3>
        <div class="form-row mb-16">
            <div class="form-group form-col" style="min-width:150px;">
                <label class="form-label">User</label>
                <input class="form-input" id="vm_ssh_user" value="${escHtml(ssh.user || '')}"${ro}>
            </div>
            <div class="form-group form-col" style="min-width:150px;">
                <label class="form-label">Password</label>
                <input type="text" name="username" autocomplete="username" style="display:none" aria-hidden="true" tabindex="-1">
                <input class="form-input" id="vm_ssh_password" type="password" value="${escHtml(ssh.password || '')}"${ro} autocomplete="new-password">
            </div>
            <div class="form-group form-col" style="min-width:200px;">
                <label class="form-label">SSH Key File</label>
                <input class="form-input form-input-mono" id="vm_ssh_keyfile" value="${escHtml(ssh.key_file || '')}" placeholder="/path/to/key.pem"${ro}>
            </div>
            <div class="form-group form-col" style="flex:2;min-width:200px;">
                <label class="form-label">Dest Path (override)</label>
                <input class="form-input form-input-mono" id="vm_ssh_dest" value="${escHtml(ssh.dest_path || '')}" placeholder="(auto: slave_dir/test_data/)"${ro}>
            </div>
        </div>
        <h3 class="text-sm mb-16 section-title">JMeter on Slaves</h3>
        <div class="form-row mb-16">
            <div class="form-group form-col" style="flex:2;min-width:250px;">
                <label class="form-label">JMeter Path (on slaves)</label>
                <input class="form-input form-input-mono" id="vm_jmeter_path" value="${escHtml(ssh.jmeter_path || '')}" placeholder="/opt/jmeter"${ro}>
                <span class="text-sm text-secondary">If set, auto-generates start/stop commands when scripts are empty.</span>
            </div>
            <div class="form-group form-col" style="min-width:120px;">
                <label class="form-label">Default OS</label>
                <select class="form-select" id="vm_os"${dis}>
                    <option value="linux"${(Fleet.currentVmConfig.os || 'linux') === 'linux' ? ' selected' : ''}>Linux</option>
                    <option value="windows"${Fleet.currentVmConfig.os === 'windows' ? ' selected' : ''}>Windows</option>
                </select>
            </div>
        </div>
        <h3 class="text-sm mb-16 section-title">JMeter Heap</h3>
        <div class="form-row mb-16">
            <div class="form-group form-col" style="min-width:120px;">
                <label class="form-label">Xms (initial)</label>
                <input class="form-input form-input-mono" id="vm_heap_xms" value="${escHtml(heap.xms || '512m')}" placeholder="512m"${ro}>
            </div>
            <div class="form-group form-col" style="min-width:120px;">
                <label class="form-label">Xmx (max)</label>
                <input class="form-input form-input-mono" id="vm_heap_xmx" value="${escHtml(heap.xmx || '1g')}" placeholder="1g"${ro}>
            </div>
            <div class="form-group form-col" style="flex:2;min-width:250px;">
                <label class="form-label">GC Algorithm</label>
                <input class="form-input form-input-mono" id="vm_heap_gc" value="${escHtml(heap.gc_algo || '')}" placeholder="-XX:+UseG1GC -XX:MaxGCPauseMillis=100"${ro}>
            </div>
        </div>
        <h3 class="text-sm mb-16 section-title">JMeter Scripts (on slaves)</h3>
        <div class="form-row mb-16">
            <div class="form-group form-col">
                <label class="form-label">Start Script (override)</label>
                <input class="form-input form-input-mono" id="vm_script_start" value="${escHtml(scripts.start || '')}" placeholder="(auto: slave_dir/start-slave.sh)"${ro}>
            </div>
            <div class="form-group form-col">
                <label class="form-label">Stop Script (override)</label>
                <input class="form-input form-input-mono" id="vm_script_stop" value="${escHtml(scripts.stop || '')}" placeholder="(auto: slave_dir/stop-slave.sh)"${ro}>
            </div>
        </div>
        <div class="text-sm text-secondary" style="margin-top:-8px;">Per-slave overrides can be set via the &#9881; button on each slave.</div>
        </form>`;
}

async function saveVmConfig() {
    const config = {
        slave_dir: document.getElementById('vm_slave_dir').value || '~/jmeter-slave',
        ssh_config: {
            user: document.getElementById('vm_ssh_user').value,
            password: document.getElementById('vm_ssh_password').value,
            key_file: document.getElementById('vm_ssh_keyfile').value,
            dest_path: document.getElementById('vm_ssh_dest').value,
            jmeter_path: document.getElementById('vm_jmeter_path').value,
        },
        jmeter_scripts: {
            start: document.getElementById('vm_script_start').value,
            stop: document.getElementById('vm_script_stop').value,
        },
        jmeter_heap: {
            xms: document.getElementById('vm_heap_xms').value || '512m',
            xmx: document.getElementById('vm_heap_xmx').value || '1g',
            gc_algo: document.getElementById('vm_heap_gc').value,
        },
        os: document.getElementById('vm_os').value,
    };
    await api('/api/config/vm', { method: 'PUT', body: { config } });
    Fleet.currentVmConfig = config;
    showToast('VM config saved', 'success');
}

// ===== Slave JMeter Properties =====
async function loadJmeterProperties() {
    try {
        const [catalogResp, propsResp] = await Promise.all([
            api('/api/config/jmeter-properties/catalog'),
            api('/api/config/jmeter-properties/slave'),
        ]);
        Fleet.jpropsCatalog = catalogResp.catalog || [];
        Fleet.jpropsOverrides = propsResp.properties || {};
        Fleet.jpropsPath = propsResp.path || '';
        renderJmeterProperties();
    } catch (e) {
        const c = document.getElementById('jpropsContainer');
        if (c) c.innerHTML = '<div class="text-secondary" style="text-align:center;padding:16px;">Failed to load properties.</div>';
    }
}

function renderJmeterProperties() {
    const container = document.getElementById('jpropsContainer');
    if (!container) return;
    const curated = Fleet.CURATED_SLAVE;
    const catalogMap = {};
    Fleet.jpropsCatalog.forEach(e => { catalogMap[e.key] = e; });

    let html = '';
    const renderedKeys = new Set();

    // Render curated sections
    for (const [section, keys] of Object.entries(curated)) {
        html += `<div class="mb-16">`;
        html += `<div class="text-sm text-bold mb-4" style="color:var(--color-text-secondary);">${escHtml(section)}</div>`;
        html += `<div class="props-grid">`;
        keys.forEach(key => {
            renderedKeys.add(key);
            const override = Fleet.jpropsOverrides[key];
            const catalogEntry = catalogMap[key];
            const defaultVal = catalogEntry ? catalogEntry.default : '';
            const desc = catalogEntry ? catalogEntry.description : '';
            const hasOverride = override !== undefined && override !== '';
            const displayVal = hasOverride ? override : defaultVal;
            const inputClass = hasOverride ? 'form-input form-input-mono' : 'form-input form-input-mono text-secondary';

            html += `<div class="prop-row flex gap-8 mb-4" style="align-items:center;">`;
            html += `<label class="form-label" style="min-width:280px;font-family:var(--font-mono);font-size:12px;" title="${escAttr(desc)}">${escHtml(key)}</label>`;
            html += `<input class="${inputClass} jprop-input" data-key="${escAttr(key)}" value="${escAttr(displayVal)}" `;
            html += `placeholder="${escAttr(defaultVal)}" ${Fleet.isAdmin ? '' : 'readonly'} `;
            html += `style="flex:1;${hasOverride ? '' : 'opacity:0.5;'}" `;
            html += `onfocus="this.style.opacity='1'" onblur="if(!this.value||this.value==='${escAttr(defaultVal)}')this.style.opacity='0.5'">`;
            if (Fleet.isAdmin && hasOverride) {
                html += `<button class="del-btn" onclick="resetJprop('${escAttr(key)}')" title="Reset to default">&circlearrowright;</button>`;
            } else {
                html += `<span style="width:24px;display:inline-block;"></span>`;
            }
            html += `</div>`;
        });
        html += `</div></div>`;
    }

    // Render custom overrides
    const customKeys = Object.keys(Fleet.jpropsOverrides).filter(k => !renderedKeys.has(k));
    if (customKeys.length) {
        html += `<div class="mb-16">`;
        html += `<div class="text-sm text-bold mb-4" style="color:var(--color-text-secondary);">Custom Overrides</div>`;
        customKeys.forEach(key => {
            renderedKeys.add(key);
            html += `<div class="prop-row flex gap-8 mb-4" style="align-items:center;">`;
            html += `<input class="form-input form-input-mono jprop-key" value="${escAttr(key)}" style="min-width:280px;" ${Fleet.isAdmin ? '' : 'readonly'}>`;
            html += `<input class="form-input form-input-mono jprop-input" data-key="${escAttr(key)}" value="${escAttr(Fleet.jpropsOverrides[key])}" style="flex:1;" ${Fleet.isAdmin ? '' : 'readonly'}>`;
            if (Fleet.isAdmin) {
                html += `<button class="del-btn" onclick="resetJprop('${escAttr(key)}')" title="Remove">&times;</button>`;
            }
            html += `</div>`;
        });
        html += `</div>`;
    }

    if (!html) {
        html = '<div class="text-secondary" style="text-align:center;padding:16px;">No properties. Click "+ Add Property" to configure.</div>';
    }

    container.innerHTML = html;
    const pathEl = document.getElementById('jpropsPath');
    if (pathEl) pathEl.textContent = Fleet.jpropsPath ? `File: ${Fleet.jpropsPath}` : '';

    const count = Object.keys(Fleet.jpropsOverrides).length;
    const countEl = document.getElementById('jpropsCount');
    if (countEl) countEl.textContent = count ? `(${count} override${count > 1 ? 's' : ''})` : '';
}

function resetJprop(key) {
    delete Fleet.jpropsOverrides[key];
    renderJmeterProperties();
}

async function saveJmeterProperties() {
    const inputs = document.querySelectorAll('.jprop-input');
    const props = {};
    inputs.forEach(input => {
        if (input.parentElement.querySelector('.jprop-key')) return;
        const key = input.dataset.key;
        const val = input.value.trim();
        if (key && val) props[key] = val;
    });
    const keyInputs = document.querySelectorAll('.jprop-key');
    keyInputs.forEach(keyInput => {
        const newKey = keyInput.value.trim();
        const valInput = keyInput.parentElement.querySelector('.jprop-input');
        if (newKey && valInput && valInput.value.trim()) {
            const origKey = valInput.dataset.key;
            if (origKey !== newKey) delete props[origKey];
            props[newKey] = valInput.value.trim();
        }
    });
    try {
        await api('/api/config/jmeter-properties/slave', { method: 'PUT', body: { properties: props } });
        Fleet.jpropsOverrides = props;
        showToast('Slave properties saved', 'success');
        renderJmeterProperties();
    } catch (e) {
        showToast('Failed to save properties', 'error');
    }
}

// ===== Add Property Modal =====
function openAddPropertyModal() {
    document.getElementById('addPropModal').classList.add('active');
    document.getElementById('propSearchInput').value = '';
    document.getElementById('propSearchInput').focus();
    filterPropertyList('');
}

function closeAddPropertyModal() {
    document.getElementById('addPropModal').classList.remove('active');
}

function filterPropertyList(query) {
    const container = document.getElementById('propSearchResults');
    const q = query.toLowerCase();
    let filtered = Fleet.jpropsCatalog;
    if (q) {
        filtered = Fleet.jpropsCatalog.filter(e =>
            e.key.toLowerCase().includes(q) ||
            e.description.toLowerCase().includes(q) ||
            e.category.toLowerCase().includes(q)
        );
    }
    const groups = {};
    filtered.slice(0, 50).forEach(e => {
        if (!groups[e.category]) groups[e.category] = [];
        groups[e.category].push(e);
    });
    let html = '';
    for (const [cat, entries] of Object.entries(groups)) {
        html += `<div class="text-sm text-bold mb-4 mt-8" style="color:var(--color-text-secondary);">${escHtml(cat)}</div>`;
        entries.forEach(e => {
            const already = e.key in Fleet.jpropsOverrides;
            html += `<div class="prop-search-item flex gap-8 mb-2" style="align-items:center;padding:4px 8px;border-radius:4px;cursor:pointer;${already ? 'opacity:0.4;' : ''}" `;
            html += `data-pkey="${escAttr(e.key)}" data-pdefault="${escAttr(e.default)}" `;
            html += `onclick="${already ? '' : 'addCatalogPropertyFromEl(this)'}">`;
            html += `<code style="font-size:12px;white-space:nowrap;">${escHtml(e.key)}</code>`;
            html += `<span class="text-secondary text-sm" style="flex:1;">${escHtml(e.description).substring(0, 80)}</span>`;
            if (e.default) html += `<code class="text-secondary" style="font-size:11px;white-space:nowrap;">${escHtml(e.default)}</code>`;
            html += `</div>`;
        });
    }
    if (!html) html = '<div class="text-secondary" style="text-align:center;padding:16px;">No matching properties.</div>';
    if (filtered.length > 50) html += `<div class="text-secondary text-sm" style="text-align:center;padding:8px;">Showing 50 of ${filtered.length} — type to narrow results</div>`;
    container.innerHTML = html;
}

function addCatalogProperty(key, defaultVal) {
    Fleet.jpropsOverrides[key] = defaultVal;
    renderJmeterProperties();
    closeAddPropertyModal();
    showToast(`Added ${key}`, 'success');
}

function addCatalogPropertyFromEl(el) {
    addCatalogProperty(el.dataset.pkey, el.dataset.pdefault);
}

function addCustomProperty() {
    const key = document.getElementById('customPropKey').value.trim();
    const val = document.getElementById('customPropVal').value.trim();
    if (!key) { showToast('Key cannot be empty', 'warning'); return; }
    Fleet.jpropsOverrides[key] = val;
    renderJmeterProperties();
    closeAddPropertyModal();
    showToast(`Added ${key}`, 'success');
}
