document.addEventListener('DOMContentLoaded', function () {
    fetchDataAndRender();
});

// --- Globals ---
let allKeysData = {}; // Store the raw data from API

// --- API Fetching ---
async function fetchAPI(url, options = {}) {
    try {
        const response = await fetch(url, options);
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ detail: response.statusText }));
            throw new Error(errorData.detail || `HTTP error! status: ${response.status}`);
        }
        if (response.status === 204) return null;
        return response.json();
    } catch (error) {
        console.error('API Call Failed:', url, error);
        showNotification(`API请求失败: ${error.message}`, 'error');
        throw error;
    }
}

async function fetchDataAndRender() {
    try {
        const data = await fetchAPI('/api/keys/status');
        allKeysData = data;
        renderDashboard(data);
        renderApiStats(data.api_stats);
        renderKeyBuckets(data);
    } catch (error) {
        // Error is already shown by fetchAPI
    }
}

// --- Rendering Functions ---
function renderDashboard(data) {
    const dashboard = document.getElementById('stats-dashboard');
    if (!dashboard) return;
    const stats = {
        full: data.full_token_keys?.length || 0,
        empty: Object.keys(data.empty_token_keys || {}).length,
        retired: data.retired_keys?.length || 0,
        quarantine: data.quarantine_keys?.length || 0,
    };
    dashboard.innerHTML = `
        <div class="stats-card"><div class="stat-item"><div class="stat-value text-green-500">${stats.full}</div><div class="stat-label">就绪</div></div></div>
        <div class="stats-card"><div class="stat-item"><div class="stat-value text-yellow-500">${stats.empty}</div><div class="stat-label">冷却中</div></div></div>
        <div class="stats-card"><div class="stat-item"><div class="stat-value text-blue-500">${stats.retired}</div><div class="stat-label">今日已用尽</div></div></div>
        <div class="stats-card"><div class="stat-item"><div class="stat-value text-red-500">${stats.quarantine}</div><div class="stat-label">隔离区</div></div></div>
    `;
}

function renderApiStats(stats) {
    const container = document.getElementById('api-stats');
    if (!container || !stats) return;

    const createStatItem = (period, data) => {
        const successRateColor = data.success_rate >= 95 ? 'text-green-500' : data.success_rate >= 80 ? 'text-yellow-500' : 'text-red-500';
        return `
            <div class="stat-item">
                <div class="stat-value">${data.total}</div>
                <div class="stat-label">${period}调用</div>
                <div class="stat-label font-semibold ${successRateColor}">${data.success_rate}%</div>
            </div>
        `;
    };

    container.innerHTML = `
        ${createStatItem('1分钟', stats.calls_1m)}
        ${createStatItem('1小时', stats.calls_1h)}
        ${createStatItem('24小时', stats.calls_24h)}
        ${createStatItem('本月', stats.calls_month)}
    `;
}

function renderKeyBuckets(data) {
    const container = document.getElementById('key-buckets');
    if (!container) return;
    container.innerHTML = `
        ${createBucketHtml('就绪', 'full_token_keys', data.full_token_keys || [], 'green')}
        ${createBucketHtml('冷却中', 'empty_token_keys', data.empty_token_keys || {}, 'yellow')}
        ${createBucketHtml('今日已用尽', 'retired_keys', data.retired_keys || [], 'blue')}
        ${createBucketHtml('隔离区', 'quarantine_keys', data.quarantine_keys || [], 'red')}
    `;
    addEventListeners();
}

function createBucketHtml(title, bucketKey, items, color) {
    const count = Array.isArray(items) ? items.length : Object.keys(items).length;
    let itemsHtml = `<p class="text-gray-500 p-4">暂无密钥</p>`;
    if (count > 0) {
        const keys = Array.isArray(items) ? items : Object.keys(items);
        itemsHtml = keys.map(key => createKeyItemHtml(key, bucketKey, color, items[key])).join('');
    }
    return `
        <div class="stats-card">
            <div class="stats-card-header cursor-pointer" onclick="toggleSection(this)">
                <h3 class="stats-card-title"><i class="fas fa-chevron-down toggle-icon mr-2"></i><span class="text-${color}-500">${title} (${count})</span></h3>
                <label class="text-sm font-medium flex items-center" onclick="event.stopPropagation();"><input type="checkbox" class="mr-1" onchange="toggleSelectAll(this, '${bucketKey}')">全选</label>
            </div>
            <div id="batch-actions-${bucketKey}" class="p-3 border-t border-gray-200 hidden flex items-center flex-wrap gap-2">
                <span class="text-sm font-semibold">已选择 <span id="selected-count-${bucketKey}">0</span> 项</span>
                <button class="action-btn-sm bg-green-500" onclick="verifySelectedKeys('${bucketKey}')">验证</button>
                <button class="action-btn-sm bg-blue-500" onclick="resetSelectedKeys('${bucketKey}')">重置</button>
                <button class="action-btn-sm bg-red-500" onclick="deleteSelectedKeys('${bucketKey}')">删除</button>
            </div>
            <div class="key-content p-4 collapsed"><div class="key-list" data-bucket="${bucketKey}">${itemsHtml}</div></div>
        </div>
    `;
}

function createKeyItemHtml(key, bucket, color, cooldown = null) {
    const maskedKey = key.substring(0, 4) + '...' + key.substring(key.length - 4);
    const cooldownInfo = cooldown ? `<span class="text-xs text-gray-500">冷却: ${cooldown.toFixed(1)}s</span>` : '';
    return `
        <div class="key-item border-l-4 border-${color}-500 flex justify-between items-center" data-key="${key}" data-bucket="${bucket}">
            <div class="flex items-center">
                <input type="checkbox" class="key-checkbox mr-2" value="${key}">
                <div>
                    <span class="font-mono text-sm">${maskedKey}</span>
                    ${cooldownInfo}
                </div>
            </div>
            <div class="key-actions flex gap-2">
                <button title="验证" class="action-btn-sm bg-green-500" onclick="verifySingleKey('${key}', this)"><i class="fas fa-check"></i></button>
                <button title="重置" class="action-btn-sm bg-blue-500" onclick="resetSingleKey('${key}', this)"><i class="fas fa-redo"></i></button>
                <button title="详情" class="action-btn-sm bg-purple-500" onclick="showKeyDetails('${key}')"><i class="fas fa-chart-pie"></i></button>
                <button title="删除" class="action-btn-sm bg-red-500" onclick="deleteSingleKey('${key}', this)"><i class="fas fa-trash"></i></button>
            </div>
        </div>
    `;
}

// --- Event Listeners & Actions ---
function addEventListeners() {
    document.querySelectorAll('.key-checkbox').forEach(cb => {
        cb.addEventListener('change', () => updateBatchActions(cb.closest('.key-list').dataset.bucket));
    });
}

function updateBatchActions(bucketKey) {
    const container = document.querySelector(`.key-list[data-bucket="${bucketKey}"]`);
    if (!container) return;
    const selectedCount = container.querySelectorAll('.key-checkbox:checked').length;
    const actionsBar = document.getElementById(`batch-actions-${bucketKey}`);
    const countSpan = document.getElementById(`selected-count-${bucketKey}`);

    if (selectedCount > 0) {
        actionsBar.classList.remove('hidden');
        countSpan.textContent = selectedCount;
    } else {
        actionsBar.classList.add('hidden');
    }
}

window.toggleSection = function(header) {
    const content = header.closest('.stats-card').querySelector('.key-content');
    const icon = header.querySelector('.toggle-icon');
    content.classList.toggle('collapsed');
    icon.classList.toggle('collapsed');
};

window.toggleSelectAll = function(checkbox, bucketKey) {
    document.querySelectorAll(`.key-list[data-bucket="${bucketKey}"] .key-checkbox`).forEach(cb => {
        cb.checked = checkbox.checked;
    });
    updateBatchActions(bucketKey);
};

window.refreshPage = function(button) {
    const icon = button.querySelector("i");
    icon.classList.add("fa-spin");
    fetchDataAndRender().finally(() => icon.classList.remove("fa-spin"));
};

// --- Single & Batch Actions ---
async function handleApiAction(button, actionFn) {
    const originalHtml = button.innerHTML;
    button.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
    button.disabled = true;
    try {
        await actionFn();
    } catch (e) {
        // Error notification is handled in fetchAPI
    } finally {
        button.innerHTML = originalHtml;
        button.disabled = false;
    }
}

async function verifySingleKey(key, btn) {
    handleApiAction(btn, async () => {
        const result = await fetchAPI(`/api/verify-key/${key}`, { method: 'POST' });
        showNotification(result.success ? `密钥验证成功` : `密钥验证失败: ${result.error}`, result.success ? 'success' : 'error');
    });
}

async function resetSingleKey(key, btn) {
    handleApiAction(btn, async () => {
        await fetchAPI(`/api/keys/reset/${key}`, { method: 'POST' });
        showNotification(`密钥 ${key.substring(0,4)}... 已重置`, 'success');
        fetchDataAndRender();
    });
}

async function deleteSingleKey(key, btn) {
    if (!confirm(`确定要删除密钥 ${key.substring(0,4)}...?`)) return;
    handleApiAction(btn, async () => {
        await fetchAPI(`/api/config/keys/${key}`, { method: 'DELETE' });
        showNotification(`密钥 ${key.substring(0,4)}... 已删除`, 'success');
        fetchDataAndRender();
    });
}

function getSelectedKeys(bucketKey) {
    return Array.from(document.querySelectorAll(`.key-list[data-bucket="${bucketKey}"] .key-checkbox:checked`)).map(cb => cb.value);
}

window.verifySelectedKeys = async function(bucketKey) {
    const keys = getSelectedKeys(bucketKey);
    if (keys.length === 0) return showNotification('请先选择密钥', 'warning');
    showNotification(`开始验证 ${keys.length} 个密钥...`, 'info');
    const result = await fetchAPI('/api/verify-selected-keys', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({keys})
    });
    showNotification(`验证完成: ${result.valid_count} 成功, ${result.invalid_count} 失败.`, 'info');
    fetchDataAndRender();
}

window.resetSelectedKeys = async function(bucketKey) {
    const keys = getSelectedKeys(bucketKey);
    if (keys.length === 0) return showNotification('请先选择密钥', 'warning');
    if (!confirm(`确定要重置选中的 ${keys.length} 个密钥吗?`)) return;
    await fetchAPI('/api/reset-selected-fail-counts', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({keys})
    });
    showNotification(`成功重置 ${keys.length} 个密钥`, 'success');
    fetchDataAndRender();
}

window.deleteSelectedKeys = async function(bucketKey) {
    const keys = getSelectedKeys(bucketKey);
    if (keys.length === 0) return showNotification('请先选择密钥', 'warning');
    if (!confirm(`确定要删除选中的 ${keys.length} 个密钥吗?`)) return;
    await fetchAPI('/api/config/keys/delete-selected', {
        method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify({keys})
    });
    showNotification(`成功删除 ${keys.length} 个密钥`, 'success');
    fetchDataAndRender();
}

// --- Modals ---
window.closeKeyUsageDetailsModal = function() {
    const modal = document.getElementById('keyUsageDetailsModal');
    if (modal) modal.classList.add('hidden');
}

window.showKeyDetails = async function(key) {
    const modal = document.getElementById('keyUsageDetailsModal');
    const title = document.getElementById('keyUsageDetailsModalTitle');
    const content = document.getElementById('keyUsageDetailsContent');
    if (!modal || !title || !content) return;

    title.textContent = `密钥 ${key.substring(0, 4)}... 使用详情 (24小时)`;
    content.innerHTML = '<div class="text-center p-4"><i class="fas fa-spinner fa-spin"></i> 加载中...</div>';
    modal.classList.remove('hidden');

    try {
        const data = await fetchAPI(`/api/key-usage-details/${key}`);
        if (Object.keys(data).length === 0) {
            content.innerHTML = '<p class="text-center p-4 text-gray-500">该密钥在过去24小时内没有使用记录。</p>';
            return;
        }
        let tableHtml = '<table class="min-w-full divide-y divide-gray-200"><thead><tr><th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">模型</th><th class="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">调用次数</th></tr></thead><tbody class="bg-white divide-y divide-gray-200">';
        for (const [model, count] of Object.entries(data)) {
            tableHtml += `<tr><td class="px-4 py-2 whitespace-nowrap text-sm">${model}</td><td class="px-4 py-2 whitespace-nowrap text-sm">${count}</td></tr>`;
        }
        tableHtml += '</tbody></table>';
        content.innerHTML = tableHtml;
    } catch (error) {
        content.innerHTML = `<p class="text-center p-4 text-red-500">加载详情失败: ${error.message}</p>`;
    }
}

// --- Utility ---
function showNotification(message, type = 'success', duration = 3000) {
    const notification = document.getElementById('notification') || document.createElement('div');
    if (!notification.id) {
        notification.id = 'notification';
        document.body.appendChild(notification);
    }
    notification.textContent = message;
    notification.className = `notification show ${type}`;
    setTimeout(() => {
        notification.classList.remove('show');
    }, duration);
}
