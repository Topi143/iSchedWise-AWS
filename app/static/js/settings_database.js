// Database Management Functions for Settings Page
let isCreatingDbBackup = false;
let isSavingDbAutoBackup = false;
let isExecutingDbAction = false;
let isRefreshingDbStats = false;
let hasLoadedDatabaseTab = false;
let dbTypedConfirmResolver = null;
let dbTypedConfirmExpectedPhrase = '';

const DB_ACTION_COUNTS = {
    cleanup_old_logs: 0,
    reset_class_schedules: 0,
    reset_exam_schedules: 0,
    reset_all_schedules: 0,
    truncate_archives: 0,
    truncate_login_history: 0,
    truncate_activity_logs: 0,
};

let dbLatestBackupMeta = {
    latest_backup_at: null,
    has_recent_backup: false,
};

const SETTINGS_TAB_CHANGED_EVENT = 'settings:tab-changed';
const SETTINGS_DB_TAB_ID = 'database';

const DB_DESTRUCTIVE_ACTIONS = {
    cleanup_old_logs: {
        endpoint: '/admin/api/database/cleanup/old_logs',
        buttonId: 'dbCleanupLogsBtn',
        countId: 'dbOldLogsCount',
        label: 'old activity logs',
        confirmColor: 'amber',
        buildPayload: () => ({
            action: 'cleanup_old_logs',
            days: getDbRetentionDays(),
        }),
        toPreviewCount: data => Number(data?.would_delete || 0),
        toSuccessMessage: data => `Cleaned up ${Number(data?.deleted || 0).toLocaleString()} old activity log records.`,
        zeroMessage: 'No old activity logs match the selected retention period.',
    },
    reset_class_schedules: {
        endpoint: '/admin/api/database/reset-schedules',
        buttonId: 'dbResetClassSchedulesBtn',
        countId: 'dbResetClassSchedulesCount',
        label: 'class schedules for the active term',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'reset_class_schedules',
            type: 'class',
        }),
        toPreviewCount: data => Number(data?.total_would_delete || data?.would_delete_class || 0),
        toSuccessMessage: data => `Reset ${Number(data?.deleted_class || 0).toLocaleString()} class schedules for the active term.`,
        zeroMessage: 'No class schedules found for the active term.',
    },
    reset_exam_schedules: {
        endpoint: '/admin/api/database/reset-schedules',
        buttonId: 'dbResetExamSchedulesBtn',
        countId: 'dbResetExamSchedulesCount',
        label: 'exam schedules for the active term',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'reset_exam_schedules',
            type: 'exam',
        }),
        toPreviewCount: data => Number(data?.total_would_delete || data?.would_delete_exam || 0),
        toSuccessMessage: data => `Reset ${Number(data?.deleted_exam || 0).toLocaleString()} exam schedules for the active term.`,
        zeroMessage: 'No exam schedules found for the active term.',
    },
    reset_all_schedules: {
        endpoint: '/admin/api/database/reset-schedules',
        buttonId: 'dbResetAllSchedulesBtn',
        countId: 'dbResetAllSchedulesCount',
        label: 'class and exam schedules for the active term',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'reset_all_schedules',
            type: 'all',
        }),
        toPreviewCount: data => Number(data?.total_would_delete || 0),
        toSuccessMessage: data => {
            const classDeleted = Number(data?.deleted_class || 0).toLocaleString();
            const examDeleted = Number(data?.deleted_exam || 0).toLocaleString();
            return `Reset ${classDeleted} class schedules and ${examDeleted} exam schedules for the active term.`;
        },
        zeroMessage: 'No class or exam schedules found for the active term.',
    },
    truncate_archives: {
        endpoint: '/admin/api/database/truncate/archives',
        buttonId: 'dbTruncateArchivesBtn',
        countId: 'dbTruncateArchivesCount',
        label: 'archive records',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'truncate_archives',
        }),
        toPreviewCount: data => Number(data?.would_delete || 0),
        toSuccessMessage: data => `Truncated archives table (${Number(data?.deleted || 0).toLocaleString()} records removed).`,
        zeroMessage: 'Archives table is already empty.',
    },
    truncate_login_history: {
        endpoint: '/admin/api/database/truncate/login_history',
        buttonId: 'dbTruncateLoginHistoryBtn',
        countId: 'dbTruncateLoginHistoryCount',
        label: 'login history records',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'truncate_login_history',
        }),
        toPreviewCount: data => Number(data?.would_delete || 0),
        toSuccessMessage: data => `Truncated login history table (${Number(data?.deleted || 0).toLocaleString()} records removed).`,
        zeroMessage: 'Login history table is already empty.',
    },
    truncate_activity_logs: {
        endpoint: '/admin/api/database/truncate/activity_logs',
        buttonId: 'dbTruncateActivityLogsBtn',
        countId: 'dbTruncateActivityLogsCount',
        label: 'all activity log records',
        confirmColor: 'red',
        buildPayload: () => ({
            action: 'truncate_activity_logs',
        }),
        toPreviewCount: data => Number(data?.would_delete || 0),
        toSuccessMessage: data => `Truncated activity logs table (${Number(data?.deleted || 0).toLocaleString()} records removed).`,
        zeroMessage: 'Activity logs table is already empty.',
    },
};

const DB_DESTRUCTIVE_BUTTON_IDS = Object.values(DB_DESTRUCTIVE_ACTIONS).map(action => action.buttonId);

function escapeDbHtml(value) {
    return String(value ?? '')
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function getDbRetentionDays() {
    const raw = parseInt(document.getElementById('dbRetentionDays')?.value, 10);
    if (Number.isNaN(raw)) return 90;
    return Math.max(7, Math.min(365, raw));
}

function normalizeDbPhrase(value) {
    return String(value ?? '').trim().toUpperCase().replace(/\s+/g, ' ');
}

function isDbActionLocked() {
    return isExecutingDbAction || isCreatingDbBackup || isRefreshingDbStats;
}

function setDbDestructiveControlsDisabled(disabled) {
    DB_DESTRUCTIVE_BUTTON_IDS.forEach((id) => {
        const btn = document.getElementById(id);
        if (!btn) return;

        const dataDisabled = btn.getAttribute('data-disabled-by-count') === 'true';
        btn.disabled = disabled || isDbActionLocked() || dataDisabled;
    });
}

function setDbActionButtonCountState(actionKey, count, disabledByScope = false) {
    const config = DB_DESTRUCTIVE_ACTIONS[actionKey];
    if (!config) return;

    const numericCount = Math.max(0, Number(count || 0));
    DB_ACTION_COUNTS[actionKey] = numericCount;

    const countEl = document.getElementById(config.countId);
    if (countEl) {
        countEl.textContent = numericCount.toLocaleString();
    }

    const btn = document.getElementById(config.buttonId);
    if (!btn) return;

    const disabledByCount = numericCount === 0 || disabledByScope;
    btn.setAttribute('data-disabled-by-count', disabledByCount ? 'true' : 'false');
    btn.disabled = isDbActionLocked() || disabledByCount;
}

function setDbCurrentTermScope(summary) {
    const el = document.getElementById('dbCurrentTermScope');
    if (!el) return;

    if (!summary || !summary.academic_year || !summary.semester) {
        el.innerHTML = '<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">No active academic term found. Reset schedule actions are disabled.</span>';
        return;
    }

    const semester = escapeDbHtml(summary.semester);
    const year = escapeDbHtml(summary.academic_year);
    const examPeriod = escapeDbHtml(summary.exam_period || 'N/A');
    el.innerHTML = `<span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300">Scope: ${semester} | ${year} | ${examPeriod}</span>`;
}

function updateDbBackupRecencyHint(backupMeta) {
    const hintEl = document.getElementById('dbBackupRecencyHint');
    if (!hintEl) return;

    const latestIso = backupMeta?.latest_backup_at;
    if (!latestIso) {
        hintEl.className = 'mb-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-2 text-xs text-amber-700 dark:text-amber-300';
        hintEl.textContent = 'No backup detected yet. Create a backup before running reset or truncate actions.';
        return;
    }

    const formatted = formatDbDate(latestIso);
    if (backupMeta?.has_recent_backup) {
        hintEl.className = 'mb-2 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 p-2 text-xs text-emerald-700 dark:text-emerald-300';
        hintEl.textContent = `Latest backup: ${formatted}. Recent backup check passed.`;
    } else {
        hintEl.className = 'mb-2 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 p-2 text-xs text-amber-700 dark:text-amber-300';
        hintEl.textContent = `Latest backup: ${formatted}. Consider creating a fresh backup before destructive actions.`;
    }
}

function closeDbTypedConfirm(result) {
    const modal = document.getElementById('dbTypedConfirmModal');
    const input = document.getElementById('dbTypedConfirmInput');
    const error = document.getElementById('dbTypedConfirmError');
    if (!modal) return;

    modal.classList.add('hidden');
    if (typeof window.toggleSidebarBlur === 'function') {
        window.toggleSidebarBlur(false);
    }

    if (input) {
        input.value = '';
    }
    if (error) {
        error.classList.add('hidden');
    }

    const resolver = dbTypedConfirmResolver;
    dbTypedConfirmResolver = null;
    dbTypedConfirmExpectedPhrase = '';

    if (resolver) {
        resolver(!!result);
    }
}

function updateDbTypedConfirmState() {
    const input = document.getElementById('dbTypedConfirmInput');
    const btn = document.getElementById('dbTypedConfirmProceedBtn');
    const error = document.getElementById('dbTypedConfirmError');
    if (!input || !btn || !error) return;

    const matches = normalizeDbPhrase(input.value) === normalizeDbPhrase(dbTypedConfirmExpectedPhrase);
    btn.disabled = !matches;
    error.classList.toggle('hidden', matches || input.value.trim().length === 0);
}

function confirmDbTypedPhrase() {
    const input = document.getElementById('dbTypedConfirmInput');
    if (!input) {
        closeDbTypedConfirm(false);
        return;
    }

    const matches = normalizeDbPhrase(input.value) === normalizeDbPhrase(dbTypedConfirmExpectedPhrase);
    if (!matches) {
        updateDbTypedConfirmState();
        return;
    }

    closeDbTypedConfirm(true);
}

function showDbTypedConfirm(options = {}) {
    const modal = document.getElementById('dbTypedConfirmModal');
    const title = document.getElementById('dbTypedConfirmTitle');
    const message = document.getElementById('dbTypedConfirmMessage');
    const phrase = document.getElementById('dbTypedConfirmPhrase');
    const input = document.getElementById('dbTypedConfirmInput');
    const proceedBtn = document.getElementById('dbTypedConfirmProceedBtn');
    const error = document.getElementById('dbTypedConfirmError');

    if (!modal || !title || !message || !phrase || !input || !proceedBtn || !error) {
        return Promise.resolve(false);
    }

    title.textContent = options.title || 'Type confirmation phrase';
    message.textContent = options.message || 'Type the required phrase to continue.';
    phrase.textContent = options.expectedPhrase || '';
    proceedBtn.textContent = options.confirmText || 'Confirm Action';
    input.value = '';
    error.classList.add('hidden');

    dbTypedConfirmExpectedPhrase = options.expectedPhrase || '';
    updateDbTypedConfirmState();

    modal.classList.remove('hidden');
    if (typeof window.toggleSidebarBlur === 'function') {
        window.toggleSidebarBlur(true);
    }

    setTimeout(() => input.focus(), 30);

    return new Promise((resolve) => {
        dbTypedConfirmResolver = resolve;
    });
}

async function requestDbActionPreview(actionKey) {
    const config = DB_DESTRUCTIVE_ACTIONS[actionKey];
    if (!config) throw new Error('Unknown database action.');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        throw new Error('Security token missing. Refresh the page and try again.');
    }

    const payload = {
        ...config.buildPayload(),
        dry_run: true,
    };

    return fetchDbJson(config.endpoint, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify(payload),
    });
}

async function executeDbAction(actionKey, requiredPhrase) {
    const config = DB_DESTRUCTIVE_ACTIONS[actionKey];
    if (!config) throw new Error('Unknown database action.');

    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        throw new Error('Security token missing. Refresh the page and try again.');
    }

    isExecutingDbAction = true;
    const btn = document.getElementById(config.buttonId);
    const originalBtnHtml = btn ? btn.innerHTML : '';

    if (btn) {
        btn.disabled = true;
        btn.innerHTML = 'Processing...';
    }
    setDbDestructiveControlsDisabled(true);

    const payload = {
        ...config.buildPayload(),
        dry_run: false,
        confirm_phrase: requiredPhrase,
    };

    try {
        const data = await fetchDbJson(config.endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            body: JSON.stringify(payload),
        });

        const msg = config.toSuccessMessage(data);
        showToast(msg, 'success');
        await refreshDatabaseStats();
    } catch (err) {
        showToast(err?.message || 'Failed to execute database action.', 'error');
    } finally {
        isExecutingDbAction = false;
        if (btn) {
            btn.innerHTML = originalBtnHtml;
        }
        setDbDestructiveControlsDisabled(false);
    }
}

async function confirmDbAction(actionKey) {
    const config = DB_DESTRUCTIVE_ACTIONS[actionKey];
    if (!config) {
        showToast('Unknown database action.', 'error');
        return;
    }

    if (isDbActionLocked()) {
        showToast('Please wait until the current database action finishes.', 'error');
        return;
    }

    const btn = document.getElementById(config.buttonId);
    if (btn?.disabled && btn.getAttribute('data-disabled-by-count') === 'true') {
        showToast(config.zeroMessage, 'success');
        return;
    }

    try {
        const preview = await requestDbActionPreview(actionKey);
        const previewCount = Math.max(0, Number(config.toPreviewCount(preview)));

        if (previewCount === 0) {
            showToast(config.zeroMessage, 'success');
            await loadDbCleanupStats();
            return;
        }

        const backupWarning = dbLatestBackupMeta.has_recent_backup
            ? ''
            : ' Last backup is not recent. Consider creating a new backup first.';

        const details = [];
        if (preview?.term?.academic_year && preview?.term?.semester) {
            details.push(`Term scope: ${preview.term.semester} | ${preview.term.academic_year}`);
        }
        if (actionKey === 'cleanup_old_logs') {
            details.push(`Retention window: older than ${getDbRetentionDays()} days`);
        }

        const summary = `This will permanently affect ${previewCount.toLocaleString()} ${config.label}.${backupWarning}`;
        const extra = details.length ? ` ${details.join(' | ')}` : '';

        if (typeof window.showConfirm !== 'function') {
            showToast('Confirmation dialog is unavailable. Reload the page and try again.', 'error');
            return;
        }

        const proceed = await window.showConfirm({
            title: 'Review destructive action',
            message: `${summary}${extra}`,
            confirmText: 'Continue',
            confirmColor: config.confirmColor,
        });

        if (!proceed) return;

        const typed = await showDbTypedConfirm({
            title: 'Final confirmation required',
            message: 'Type the phrase exactly as shown to execute this action.',
            expectedPhrase: preview.required_phrase || '',
            confirmText: 'Execute',
        });

        if (!typed) return;

        await executeDbAction(actionKey, preview.required_phrase || '');
    } catch (err) {
        showToast(err?.message || 'Unable to prepare database action.', 'error');
    }
}

async function fetchDbJson(url, options = {}) {
    let response;
    try {
        response = await fetch(url, options);
    } catch (_) {
        throw new Error('Network error. Please check your connection and try again.');
    }

    const contentType = (response.headers.get('content-type') || '').toLowerCase();
    const isJson = contentType.includes('application/json');
    const loginRedirected = response.redirected && /\/auth\/login/i.test(response.url || '');

    if (!isJson) {
        if (response.status === 401 || response.status === 403 || loginRedirected) {
            throw new Error('Your session expired or access changed. Please sign in again and reload Settings.');
        }
        throw new Error('Unexpected server response. Please reload the page and try again.');
    }

    let data;
    try {
        data = await response.json();
    } catch (_) {
        throw new Error('Invalid server response. Please reload the page and try again.');
    }

    if (!response.ok) {
        throw new Error(data?.error || `Request failed (${response.status}).`);
    }

    if (data && data.success === false) {
        throw new Error(data.error || 'Request failed.');
    }

    return data || {};
}

function renderDbHealthLoading() {
    const dot = document.getElementById('dbHealthDot');
    const label = document.getElementById('dbHealthLabel');
    const healthInfo = document.getElementById('dbHealthInfo');
    if (dot) dot.className = 'w-2 h-2 rounded-full bg-gray-300 dark:bg-gray-600';
    if (label) label.textContent = 'Checking...';
    if (healthInfo) {
        healthInfo.innerHTML = '<div class="text-xs text-gray-400 animate-pulse">Loading health data...</div>';
    }
}

function renderDbHealthError(message) {
    const safeMessage = escapeDbHtml(message || 'Unable to load health data.');
    const dot = document.getElementById('dbHealthDot');
    const label = document.getElementById('dbHealthLabel');
    const healthInfo = document.getElementById('dbHealthInfo');
    if (dot) dot.className = 'w-2 h-2 rounded-full bg-red-500';
    if (label) label.textContent = 'Error';
    if (healthInfo) {
        healthInfo.innerHTML = `<div class="text-xs text-red-500">${safeMessage}</div>`;
    }
}

function renderDbBackupsLoading() {
    const el = document.getElementById('dbBackupsList');
    if (el) {
        el.innerHTML = '<div class="text-xs text-gray-400 animate-pulse py-4 text-center">Loading backups...</div>';
    }
}

function renderDbBackupsError(message) {
    const safeMessage = escapeDbHtml(message || 'Failed to load backups.');
    const el = document.getElementById('dbBackupsList');
    if (el) {
        el.innerHTML = `
            <div class="text-center py-4">
                <p class="text-xs text-red-500 mb-2">${safeMessage}</p>
                <button onclick="refreshDatabaseStats()" class="px-2.5 py-1 text-xs font-medium bg-gray-100 hover:bg-gray-200 dark:bg-gray-700 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md transition-colors">Retry</button>
            </div>`;
    }
}

function setDbAutoBackupControlsDisabled(disabled) {
    const enabledToggle = document.getElementById('dbAutoBackupEnabled');
    const retentionInput = document.getElementById('dbAutoBackupRetention');
    const saveBtn = document.getElementById('dbSaveAutoBackupBtn');

    if (enabledToggle) enabledToggle.disabled = disabled;
    if (retentionInput) retentionInput.disabled = disabled;
    if (saveBtn) saveBtn.disabled = disabled || isSavingDbAutoBackup;
}

function renderDbAutoBackupLoading() {
    const statusEl = document.getElementById('dbAutoBackupStatus');
    if (statusEl) {
        statusEl.textContent = 'Loading automatic backup settings...';
    }
    setDbAutoBackupControlsDisabled(true);
}

function renderDbAutoBackupError(message) {
    const statusEl = document.getElementById('dbAutoBackupStatus');
    if (statusEl) {
        statusEl.textContent = message || 'Unable to load automatic backup settings.';
    }
    setDbAutoBackupControlsDisabled(false);
}

function renderDbCleanupLoading() {
    Object.values(DB_DESTRUCTIVE_ACTIONS).forEach((action) => {
        const countEl = document.getElementById(action.countId);
        if (countEl) countEl.textContent = '--';

        const btn = document.getElementById(action.buttonId);
        if (btn) {
            btn.disabled = true;
            btn.setAttribute('data-disabled-by-count', 'true');
        }
    });
}

function refreshDatabaseStats() {
    if (isRefreshingDbStats) return Promise.resolve(false);
    isRefreshingDbStats = true;

    const btn = document.getElementById('dbRefreshBtn');
    if (btn) {
        btn.disabled = true;
        btn.querySelector('svg')?.classList.add('animate-spin');
    }

    renderDbHealthLoading();
    renderDbBackupsLoading();
    renderDbAutoBackupLoading();
    renderDbCleanupLoading();

    return Promise.allSettled([loadDbHealth(), loadDbBackups(), loadDbAutoBackupSettings(), loadDbCleanupStats()])
        .then((results) => {
            const failedCount = results.filter(result => result.status === 'rejected').length;
            if (failedCount > 0) {
                showToast(`Failed to load ${failedCount} database section${failedCount > 1 ? 's' : ''}.`, 'error');
            }
            return failedCount === 0;
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.querySelector('svg')?.classList.remove('animate-spin');
            }
            isRefreshingDbStats = false;
        });
}

function loadDbHealth() {
    return fetchDbJson('/admin/api/database/health')
        .then(data => {
            const h = data.health || {};
            const dot = document.getElementById('dbHealthDot');
            const label = document.getElementById('dbHealthLabel');
            
            if (h.status === 'connected') {
                dot.className = 'w-2 h-2 rounded-full bg-green-500';
                label.textContent = 'Connected';
                
                document.getElementById('dbHealthInfo').innerHTML = `
                    <div class="grid grid-cols-2 gap-2">
                        <div class="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <div class="text-xs text-gray-500 dark:text-gray-400">MySQL Version</div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">${h.mysql_version || '?'}</div>
                        </div>
                        <div class="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <div class="text-xs text-gray-500 dark:text-gray-400">Database</div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">${h.database_name || '?'}</div>
                        </div>
                        <div class="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <div class="text-xs text-gray-500 dark:text-gray-400">Total Size</div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">${h.total_size_mb?.toFixed(2) || '0'} MB</div>
                        </div>
                        <div class="p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                            <div class="text-xs text-gray-500 dark:text-gray-400">Uptime</div>
                            <div class="text-sm font-semibold text-gray-900 dark:text-gray-100 mt-0.5">${h.uptime || '?'}</div>
                        </div>
                    </div>
                `;
            } else {
                renderDbHealthError(h.error || 'Connection failed');
                throw new Error(h.error || 'Connection failed');
            }
        })
        .catch(e => {
            console.error('Failed to load health:', e);
            renderDbHealthError(e?.message || 'Unable to load health data.');
            throw e;
        });
}

function loadDbBackups() {
    return fetchDbJson('/admin/api/database/backups')
        .then(data => {
            const backups = data.backups || [];
            if (!backups.length) {
                document.getElementById('dbBackupsList').innerHTML = `
                    <div class="text-center py-6">
                        <svg class="w-8 h-8 mx-auto text-gray-300 dark:text-gray-600 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path>
                        </svg>
                        <p class="text-xs text-gray-400 dark:text-gray-500">No backups yet. Create your first backup above.</p>
                    </div>`;
                return;
            }
            document.getElementById('dbBackupsList').innerHTML = backups.map(b => `
                <div class="flex items-center gap-2 p-2 bg-white dark:bg-gray-800 rounded-lg border border-gray-200 dark:border-gray-700">
                    <svg class="w-4 h-4 text-emerald-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                    </svg>
                    <div class="flex-1 min-w-0">
                        <div class="text-xs font-medium text-gray-900 dark:text-gray-100 truncate">${b.filename}</div>
                        <div class="text-xs text-gray-400">${formatDbSize(b.size)} &middot; ${formatDbDate(b.created_at)}</div>
                    </div>
                    <div class="flex items-center gap-1 flex-shrink-0">
                        <a href="/admin/api/database/backups/${encodeURIComponent(b.filename)}/download" class="p-1.5 text-gray-400 hover:text-blue-600 dark:hover:text-blue-400 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" title="Download">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg>
                        </a>
                        <button onclick="confirmDbDeleteBackup('${b.filename}')" class="p-1.5 text-gray-400 hover:text-red-600 dark:hover:text-red-400 transition-colors rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700" title="Delete">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                        </button>
                    </div>
                </div>
            `).join('');
        })
        .catch(err => {
            renderDbBackupsError(err?.message || 'Failed to load backups.');
            throw err;
        });
}

function createDbBackup() {
    if (isCreatingDbBackup) return;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        showToast('Security token missing. Refresh the page and try again.', 'error');
        return;
    }
    
    isCreatingDbBackup = true;
    setDbDestructiveControlsDisabled(true);
    const btn = document.getElementById('dbCreateBackupBtn');
    btn.disabled = true;
    btn.innerHTML = '<svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path></svg> Creating...';
    
    fetchDbJson('/admin/api/database/backup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    })
    .then(data => {
        showToast(`Backup created: ${data.backup.filename} (${formatDbSize(data.backup.size)})`, 'success');
        loadDbBackups();
    })
    .catch((err) => {
        showToast(err?.message || 'Network error creating backup', 'error');
    })
    .finally(() => {
        isCreatingDbBackup = false;
        btn.disabled = false;
        btn.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6"></path></svg> Create Backup';
        setDbDestructiveControlsDisabled(false);
    });
}

function loadDbAutoBackupSettings() {
    return fetchDbJson('/admin/api/database/auto-backup-settings')
        .then(data => {
            const s = data.settings || {};
            document.getElementById('dbAutoBackupEnabled').checked = !!s.enabled;
            document.getElementById('dbAutoBackupRetention').value = s.retention_count || 30;
            document.getElementById('dbAutoBackupSchedule').textContent = s.schedule_label || 'Daily at 12:00 AM';
            document.getElementById('dbAutoBackupStatus').textContent = `Status: ${s.enabled ? 'Enabled' : 'Disabled'} | Keeping latest ${(s.retention_count || 30)} backups`;
            setDbAutoBackupControlsDisabled(false);
        })
        .catch((err) => {
            renderDbAutoBackupError(err?.message || 'Unable to load automatic backup settings.');
            throw err;
        });
}

function saveDbAutoBackupSettings() {
    if (isSavingDbAutoBackup) return;
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        showToast('Security token missing. Refresh the page and try again.', 'error');
        return;
    }
    
    const enabled = document.getElementById('dbAutoBackupEnabled')?.checked || false;
    const retention = parseInt(document.getElementById('dbAutoBackupRetention')?.value, 10);
    
    if (Number.isNaN(retention) || retention < 1 || retention > 365) {
        showToast('Retention must be between 1 and 365.', 'error');
        return;
    }
    
    isSavingDbAutoBackup = true;
    const btn = document.getElementById('dbSaveAutoBackupBtn');
    btn.disabled = true;
    btn.textContent = 'Saving...';
    
    fetchDbJson('/admin/api/database/auto-backup-settings', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
        body: JSON.stringify({ enabled, retention_count: retention }),
    })
    .then(data => {
        const s = data.settings || {};
        document.getElementById('dbAutoBackupStatus').textContent = `Status: ${s.enabled ? 'Enabled' : 'Disabled'} | Keeping latest ${(s.retention_count || 30)} backups`;
        showToast('Automatic backup settings saved', 'success');
    })
    .catch((err) => {
        showToast(err?.message || 'Network error saving settings', 'error');
    })
    .finally(() => {
        isSavingDbAutoBackup = false;
        btn.disabled = false;
        btn.textContent = 'Save Settings';
    });
}

function loadDbCleanupStats() {
    const days = getDbRetentionDays();
    return fetchDbJson(`/admin/api/database/stats?days=${days}`)
        .then(data => {
            const actions = data.actions || {};
            const currentTerm = data.current_semester || null;
            const hasActiveTerm = !!(currentTerm && currentTerm.academic_year && currentTerm.semester);

            dbLatestBackupMeta = {
                latest_backup_at: data?.backup?.latest_backup_at || null,
                has_recent_backup: !!data?.backup?.has_recent_backup,
            };

            setDbCurrentTermScope(currentTerm);
            updateDbBackupRecencyHint(dbLatestBackupMeta);

            Object.keys(DB_DESTRUCTIVE_ACTIONS).forEach((actionKey) => {
                const count = Number(actions?.[actionKey]?.count || 0);
                const disableByScope = actionKey.startsWith('reset_') && !hasActiveTerm;
                setDbActionButtonCountState(actionKey, count, disableByScope);
            });

            setDbDestructiveControlsDisabled(false);
        })
        .catch(e => {
            console.error('Failed to load cleanup stats:', e);
            renderDbCleanupLoading();
            throw e;
        });
}

function confirmDbDeleteBackup(filename) {
    const csrfToken = document.querySelector('meta[name="csrf-token"]')?.getAttribute('content');
    if (!csrfToken) {
        showToast('Security token missing. Refresh the page and try again.', 'error');
        return;
    }
    
    showConfirm({
        title: 'Delete backup?',
        message: `Delete "${filename}"? This cannot be undone.`,
        confirmText: 'Delete',
        confirmColor: 'red'
    }).then(confirmed => {
        if (confirmed) {
            fetchDbJson(`/admin/api/database/backups/${encodeURIComponent(filename)}`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
            })
            .then(data => {
                showToast('Backup deleted', 'success');
                loadDbBackups();
            })
            .catch((err) => {
                showToast(err?.message || 'Network error', 'error');
            });
        }
    });
}

function formatDbSize(bytes) {
    if (bytes >= 1048576) return (bytes / 1048576).toFixed(1) + ' MB';
    if (bytes >= 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return bytes + ' B';
}

function formatDbDate(iso) {
    try {
        if (!iso || typeof iso !== 'string') return '--';
        const d = new Date(iso);
        if (Number.isNaN(d.getTime())) return iso;
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return iso; }
}

function handleDatabaseTabActivation(options = {}) {
    const forceRefresh = !!options.forceRefresh;

    if (forceRefresh) {
        return refreshDatabaseStats();
    }

    if (hasLoadedDatabaseTab) {
        return Promise.resolve(true);
    }

    return refreshDatabaseStats().then((ok) => {
        if (ok) {
            hasLoadedDatabaseTab = true;
        }
        return ok;
    });
}

document.addEventListener(SETTINGS_TAB_CHANGED_EVENT, function(event) {
    const tabId = event?.detail?.tabId;
    if (tabId === SETTINGS_DB_TAB_ID) {
        handleDatabaseTabActivation();
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const typedInput = document.getElementById('dbTypedConfirmInput');
    if (typedInput) {
        typedInput.addEventListener('input', updateDbTypedConfirmState);
        typedInput.addEventListener('keydown', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                confirmDbTypedPhrase();
            }
        });
    }

    const typedModal = document.getElementById('dbTypedConfirmModal');
    if (typedModal) {
        typedModal.addEventListener('keydown', function(event) {
            if (event.key === 'Escape') {
                event.preventDefault();
                closeDbTypedConfirm(false);
            }
        });
    }

    const activeTab = document.querySelector('.tab-button.active')?.dataset?.tab;
    const dbContent = document.getElementById('tab-database');
    const isDbVisible = activeTab === SETTINGS_DB_TAB_ID || dbContent?.classList.contains('active');

    if (isDbVisible) {
        handleDatabaseTabActivation();
    }
});
