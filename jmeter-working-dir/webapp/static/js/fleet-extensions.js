/* Fleet Management — Extensions Tab */

async function loadExtensions() {
    try {
        const resp = await fetch(BASE_PATH + '/api/extensions');
        const data = await resp.json();
        Fleet.extData = data.files || [];
        renderExtensions();
    } catch (e) {
        const c = document.getElementById('extContainer');
        if (c) c.innerHTML = '<div class="text-light" style="text-align:center;padding:16px;">Failed to load extensions</div>';
    }
}

function renderExtensions() {
    const container = document.getElementById('extContainer');
    const empty = document.getElementById('extEmpty');
    const countEl = document.getElementById('extCount');
    if (!container) return;
    if (countEl) countEl.textContent = Fleet.extData.length > 0 ? `(${Fleet.extData.length} file${Fleet.extData.length !== 1 ? 's' : ''})` : '';

    if (Fleet.extData.length === 0) {
        container.innerHTML = '';
        if (empty) empty.style.display = '';
        return;
    }
    if (empty) empty.style.display = 'none';

    const allChecked = Fleet.extData.length > 0 && Fleet.extSelected.size === Fleet.extData.length;
    let html = '<table class="properties-table" style="width:100%;"><thead><tr>';
    if (Fleet.isAdmin) html += `<th style="width:32px;"><label class="check"><input type="checkbox" onchange="extToggleAll(this.checked)" ${allChecked ? 'checked' : ''}><span class="check-box"></span></label></th>`;
    html += '<th>Filename</th><th style="width:90px;">Size</th><th style="width:120px;">Modified</th>';
    if (Fleet.isAdmin) html += '<th style="width:40px;"></th>';
    html += '</tr></thead><tbody>';

    Fleet.extData.forEach(f => {
        const checked = Fleet.extSelected.has(f.filename) ? 'checked' : '';
        const date = new Date(f.modified * 1000).toLocaleDateString();
        html += '<tr>';
        if (Fleet.isAdmin) html += `<td><label class="check"><input type="checkbox" value="${f.filename}" onchange="extToggleOne(this)" ${checked}><span class="check-box"></span></label></td>`;
        html += `<td class="text-mono">${f.filename}</td>`;
        html += `<td>${formatSize(f.size)}</td>`;
        html += `<td>${date}</td>`;
        if (Fleet.isAdmin) html += `<td><button class="btn btn-ghost btn-sm" onclick="deleteExtension('${f.filename}')" data-tooltip="Delete">${Fleet.ICON_TRASH}</button></td>`;
        html += '</tr>';
    });
    html += '</tbody></table>';
    container.innerHTML = html;
}

function extToggleAll(checked) {
    Fleet.extSelected.clear();
    if (checked) Fleet.extData.forEach(f => Fleet.extSelected.add(f.filename));
    renderExtensions();
}

function extToggleOne(cb) {
    if (cb.checked) Fleet.extSelected.add(cb.value);
    else Fleet.extSelected.delete(cb.value);
    renderExtensions();
}

function getSelectedExtFiles() {
    return Fleet.extSelected.size > 0 ? Array.from(Fleet.extSelected) : [];
}

async function uploadExtension(overwrite) {
    const input = document.getElementById('uploadJarFile');
    if (!input.files.length) return;
    const file = input.files[0];
    const formData = new FormData();
    formData.append('file', file);
    const url = BASE_PATH + '/api/extensions/upload' + (overwrite ? '?overwrite=true' : '');
    try {
        const resp = await fetch(url, { method: 'POST', body: formData });
        const data = await resp.json();
        if (resp.status === 409) {
            if (await confirmAction(`"${file.name}" already exists. Overwrite it?`)) {
                await uploadExtension(true);
            } else {
                input.value = '';
            }
            return;
        }
        if (!resp.ok) { showToast(data.error || 'Upload failed', 'error'); input.value = ''; return; }
        showToast(`Uploaded ${data.filename}`, 'success');
        input.value = '';
        loadExtensions();
    } catch (e) {
        showToast('Upload failed', 'error');
        input.value = '';
    }
}

async function deleteExtension(filename) {
    if (!await confirmAction(`Delete "${filename}"?`)) return;
    try {
        const resp = await fetch(BASE_PATH + '/api/extensions/' + encodeURIComponent(filename), { method: 'DELETE' });
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Delete failed', 'error'); return; }
        showToast(`Deleted ${filename}`, 'success');
        Fleet.extSelected.delete(filename);
        loadExtensions();
    } catch (e) {
        showToast('Delete failed', 'error');
    }
}

async function installToMaster() {
    const files = getSelectedExtFiles();
    const label = files.length > 0 ? `${files.length} selected JAR(s)` : 'all JARs';
    if (!await confirmAction(`Install ${label} to local JMeter lib/ext?`)) return;
    try {
        const resp = await fetch(BASE_PATH + '/api/extensions/install-master', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files }),
        });
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Install failed', 'error'); return; }
        showToast(`Installed to master: ${data.summary}`, data.ok ? 'success' : 'warning');
    } catch (e) {
        showToast('Install failed', 'error');
    }
}

async function deployToSlaves() {
    const files = getSelectedExtFiles();
    const label = files.length > 0 ? `${files.length} selected JAR(s)` : 'all JARs';
    if (!await confirmAction(`Deploy ${label} to all active slaves?`)) return;
    showToast('Deploying extensions to slaves...', 'info');
    try {
        const resp = await fetch(BASE_PATH + '/api/extensions/deploy-slaves', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ files }),
        });
        const data = await resp.json();
        if (!resp.ok) { showToast(data.error || 'Deploy failed', 'error'); return; }
        showToast(`Deploy: ${data.summary}. Restart JMeter servers to load.`, data.ok ? 'success' : 'warning');
    } catch (e) {
        showToast('Deploy failed', 'error');
    }
}
