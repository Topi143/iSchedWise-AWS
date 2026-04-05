/**
 * batch_select.js — Reusable batch selection system for master-detail pages
 * 
 * Provides toggle-based batch mode with checkboxes on list items,
 * select-all, count display, and bulk action execution.
 * 
 * Usage:
 *   BatchSelect.init({ entityType: 'faculty', ... });
 *   Then wire the toggle button: onclick="BatchSelect.toggle('faculty')"
 */

const BatchSelect = (function () {
    'use strict';

    // ── State ──────────────────────────────────────────────
    const _state = {};          // { entityType: { active, selectedIds, config } }
    const _origOnClick = {};    // Store original onclick handlers per entity

    // ── Public API ─────────────────────────────────────────

    /**
     * Register a new entity type for batch selection.
     * @param {Object} cfg
        *   entityType      – 'faculty' | 'building' | 'curriculum' | 'program'
     *   listContainerId – ID of the scrollable list container (e.g. 'facultyList')
     *   itemSelector    – CSS selector for list items (e.g. '.faculty-list-item')
     *   idAttribute     – data attribute holding the entity ID (e.g. 'data-faculty-id')
     *   bulkActionUrl   – POST URL for bulk actions (e.g. '/faculty/bulk-action')
     *   toggleBtnId     – ID of the toggle button
     *   toolbarId       – ID of the batch toolbar div
     *   countId         – ID of the count label span
     *   selectAllId     – ID of the select-all checkbox
     *   deleteBtnId     – ID of the "Delete/Archive" button (optional)
     *   actions         – Array of available actions, e.g. ['archive','activate','deactivate']
     *   entityLabel     – Human-readable label, e.g. 'faculty member' (singular)
     *   entityLabelPlural – e.g. 'faculty members'
     *   onComplete      – callback after successful bulk action (optional)
     */
    function init(cfg) {
        _state[cfg.entityType] = {
            active: false,
            selectedIds: new Set(),
            config: cfg
        };
    }

    /** Toggle batch mode on/off */
    function toggle(type) {
        if (!_state[type]) return;
        if (_state[type].active) {
            exit(type);
        } else {
            enter(type);
        }
    }

    /** Enter batch selection mode */
    function enter(type) {
        const s = _state[type];
        if (!s) return;
        s.active = true;
        s.selectedIds.clear();

        const cfg = s.config;

        // Show toolbar
        const toolbar = document.getElementById(cfg.toolbarId);
        if (toolbar) toolbar.style.display = 'flex';

        // Style toggle button as active
        const btn = document.getElementById(cfg.toggleBtnId);
        if (btn) {
            if (!btn.dataset.batchToggleBaseClasses) {
                btn.dataset.batchToggleBaseClasses = btn.className;
            }
            btn.classList.remove(
                'text-red-600',
                'dark:text-red-400',
                'hover:bg-red-50',
                'dark:hover:bg-red-900/20',
                'dark:hover:bg-red-900/30',
                'bg-white',
                'dark:bg-gray-800'
            );
            btn.classList.add(
                'bg-red-600',
                'dark:bg-red-600',
                'text-white',
                'dark:text-white',
                'hover:bg-red-700',
                'dark:hover:bg-red-700'
            );
        }

        // Show checkboxes
        _showCheckboxes(type, true);

        // Reset select-all
        const selectAll = document.getElementById(cfg.selectAllId);
        if (selectAll) { selectAll.checked = false; selectAll.indeterminate = false; }

        _updateCount(type);

        // Intercept clicks on list items — toggle checkbox instead of navigating
        _interceptClicks(type);

        _emitStateChange(type, true);
    }

    /** Exit batch selection mode */
    function exit(type) {
        const s = _state[type];
        if (!s) return;
        s.active = false;
        s.selectedIds.clear();

        const cfg = s.config;

        // Hide toolbar
        const toolbar = document.getElementById(cfg.toolbarId);
        if (toolbar) toolbar.style.display = 'none';

        // Restore toggle button style
        const btn = document.getElementById(cfg.toggleBtnId);
        if (btn) {
            if (btn.dataset.batchToggleBaseClasses) {
                btn.className = btn.dataset.batchToggleBaseClasses;
                delete btn.dataset.batchToggleBaseClasses;
            } else {
                btn.classList.remove(
                    'bg-red-600',
                    'dark:bg-red-600',
                    'text-white',
                    'dark:text-white',
                    'hover:bg-red-700',
                    'dark:hover:bg-red-700'
                );
                btn.classList.add(
                    'text-red-600',
                    'dark:text-red-400',
                    'hover:bg-red-50',
                    'dark:hover:bg-red-900/20'
                );
            }
        }

        // Hide checkboxes and uncheck them
        _showCheckboxes(type, false);

        // Restore original click behavior
        _restoreClicks(type);

        _emitStateChange(type, false);
    }

    /** Toggle select all */
    function selectAll(type, checked) {
        const s = _state[type];
        if (!s) return;
        const cfg = s.config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container) return;

        const checkboxes = container.querySelectorAll('.batch-check-' + type);
        checkboxes.forEach(cb => {
            cb.checked = checked;
            const id = parseInt(cb.value);
            if (checked) { s.selectedIds.add(id); } else { s.selectedIds.delete(id); }
        });
        _updateCount(type);
    }

    /** Handle individual checkbox change */
    function onCheckChange(type, checkbox) {
        const s = _state[type];
        if (!s) return;
        const id = parseInt(checkbox.value);
        if (checkbox.checked) { s.selectedIds.add(id); } else { s.selectedIds.delete(id); }
        _updateSelectAll(type);
        _updateCount(type);
    }

    /** Execute a bulk action */
    function execute(type, action) {
        const s = _state[type];
        if (!s || s.selectedIds.size === 0) return;

        const cfg = s.config;
        const count = s.selectedIds.size;
        const label = count === 1 ? cfg.entityLabel : cfg.entityLabelPlural;

        if (action === 'archive') {
            _showArchiveReasonModal(type, count, label, function (reason) {
                _doBulkAction(type, action, reason);
            });
        } else if (action === 'delete') {
            _showConfirmModal(
                'Bulk Delete',
                `Are you sure you want to permanently delete <strong>${count} ${label}</strong>? This action cannot be undone.`,
                `Delete ${count}`,
                'red',
                function () { _doBulkAction(type, action, null); }
            );
        } else if (action === 'restore') {
            _showConfirmModal(
                'Bulk Restore',
                `Restore <strong>${count} ${label}</strong> back to the active list?`,
                `Restore ${count}`,
                'green',
                function () { _doBulkAction(type, action, null); }
            );
        } else if (action === 'unarchive') {
            _showConfirmModal(
                'Bulk Unarchive',
                `Unarchive <strong>${count} ${label}</strong> and make them active again?`,
                `Unarchive ${count}`,
                'green',
                function () { _doBulkAction(type, action, null); }
            );
        } else {
            const actionLabel = action === 'activate' ? 'activate' : action === 'deactivate' ? 'deactivate' : action;
            _showConfirmModal(
                `Bulk ${_capitalize(actionLabel)}`,
                `Are you sure you want to ${actionLabel} <strong>${count} ${label}</strong>?`,
                `${_capitalize(actionLabel)} ${count}`,
                action === 'deactivate' ? 'amber' : action === 'activate' ? 'green' : 'red',
                function () { _doBulkAction(type, action, null); }
            );
        }
    }

    /** Check if batch mode is active for a type */
    function isActive(type) {
        return _state[type] ? _state[type].active : false;
    }

    /** Re-inject checkboxes after dynamic list re-render (e.g. AJAX reload) */
    function refreshCheckboxes(type) {
        const s = _state[type];
        if (!s || !s.active) return;
        _showCheckboxes(type, true);
        // Re-check previously selected items
        const cfg = s.config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container) return;
        container.querySelectorAll('.batch-check-' + type).forEach(cb => {
            const id = parseInt(cb.value);
            cb.checked = s.selectedIds.has(id);
        });
        _updateSelectAll(type);
        _updateCount(type);
    }

    // ── Private helpers ────────────────────────────────────

    function _showCheckboxes(type, show) {
        const cfg = _state[type].config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container) return;
        const items = container.querySelectorAll(cfg.itemSelector);

        items.forEach(item => {
            const idVal = item.getAttribute(cfg.idAttribute);
            if (!idVal) return;

            const isTableRow = item.tagName === 'TR';

            let cbWrap = item.querySelector('.batch-cb-wrap-' + type);
            if (show) {
                if (!cbWrap) {
                    if (isTableRow) {
                        cbWrap = document.createElement('td');
                        cbWrap.className = 'batch-cb-wrap-' + type + ' hidden px-2 align-middle text-center';
                        cbWrap.innerHTML = `<input type="checkbox" class="batch-check-${type} w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer" value="${idVal}" onclick="event.stopPropagation(); BatchSelect.onCheckChange('${type}', this)">`;
                        item.insertBefore(cbWrap, item.firstChild);
                    } else {
                        cbWrap = document.createElement('div');
                        cbWrap.className = 'batch-cb-wrap-' + type + ' flex items-center pl-2 mr-2 flex-shrink-0';
                        cbWrap.innerHTML = `<input type="checkbox" class="batch-check-${type} w-4 h-4 rounded border-gray-300 text-red-600 focus:ring-red-500 cursor-pointer" value="${idVal}" onclick="event.stopPropagation(); BatchSelect.onCheckChange('${type}', this)">`;
                        // Insert checkbox at the item level to avoid breaking responsive child layouts
                        item.insertBefore(cbWrap, item.firstChild);
                    }
                }
                if (isTableRow) {
                    cbWrap.classList.remove('hidden');
                    cbWrap.style.display = 'table-cell';
                } else {
                    cbWrap.style.display = 'flex';
                    // Save original display and make item a flex row
                    if (!item.dataset.batchOrigDisplay) {
                        item.dataset.batchOrigDisplay = item.style.display || '';
                    }
                    item.style.display = 'flex';
                    item.style.alignItems = 'center';
                    // Apply flex:1 to content children so they fill the space.
                    // Skip children with flex-shrink-0 (e.g. action button containers).
                    const siblings = Array.from(item.children).filter(c => c !== cbWrap);
                    siblings.forEach(child => {
                        if (child.classList.contains('flex-shrink-0')) return;
                        if (!child.dataset.batchOrigFlex) {
                            child.dataset.batchOrigFlex = child.style.flex || '';
                            child.dataset.batchOrigMinW = child.style.minWidth || '';
                        }
                        child.style.flex = '1';
                        child.style.minWidth = '0';
                    });
                }
            } else {
                if (cbWrap) {
                    cbWrap.style.display = 'none';
                    if (isTableRow) {
                        cbWrap.classList.add('hidden');
                    }
                    const cb = cbWrap.querySelector('input');
                    if (cb) cb.checked = false;
                }

                if (isTableRow) {
                    return;
                }

                // Restore original styles
                if (item.dataset.batchOrigDisplay !== undefined) {
                    item.style.display = item.dataset.batchOrigDisplay || '';
                    item.style.alignItems = '';
                    delete item.dataset.batchOrigDisplay;
                }
                const siblings = Array.from(item.children).filter(c => !c.classList.contains('batch-cb-wrap-' + type));
                siblings.forEach(child => {
                    if (child.dataset.batchOrigFlex !== undefined) {
                        child.style.flex = child.dataset.batchOrigFlex || '';
                        child.style.minWidth = child.dataset.batchOrigMinW || '';
                        delete child.dataset.batchOrigFlex;
                        delete child.dataset.batchOrigMinW;
                    }
                });
            }
        });
    }

    function _interceptClicks(type) {
        const cfg = _state[type].config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container) return;

        // Store handler reference for removal later
        const handler = function (e) {
            if (!_state[type] || !_state[type].active) return;

            // Find the list-item ancestor
            const item = e.target.closest(cfg.itemSelector);
            if (!item) return;

            // Don't intercept if clicking directly on checkbox
            if (e.target.tagName === 'INPUT' && e.target.type === 'checkbox') return;

            e.preventDefault();
            e.stopPropagation();

            // Toggle the checkbox
            const cb = item.querySelector('.batch-check-' + type);
            if (cb) {
                cb.checked = !cb.checked;
                onCheckChange(type, cb);
            }
        };

        _origOnClick[type] = handler;
        container.addEventListener('click', handler, true);  // capture phase
    }

    function _restoreClicks(type) {
        const cfg = _state[type].config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container || !_origOnClick[type]) return;
        container.removeEventListener('click', _origOnClick[type], true);
        delete _origOnClick[type];
    }

    function _updateCount(type) {
        const s = _state[type];
        const cfg = s.config;
        const el = document.getElementById(cfg.countId);
        if (el) el.textContent = s.selectedIds.size;

        // Enable/disable action buttons
        const archiveBtn = document.getElementById(cfg.toolbarId + 'ArchiveBtn');
        const activateBtn = document.getElementById(cfg.toolbarId + 'ActivateBtn');
        const deactivateBtn = document.getElementById(cfg.toolbarId + 'DeactivateBtn');
        const deleteBtn = document.getElementById(cfg.toolbarId + 'DeleteBtn');
        const restoreBtn = document.getElementById(cfg.toolbarId + 'RestoreBtn');
        const unarchiveBtn = document.getElementById(cfg.toolbarId + 'UnarchiveBtn');
        const disabled = s.selectedIds.size === 0;
        [archiveBtn, activateBtn, deactivateBtn, deleteBtn, restoreBtn, unarchiveBtn].forEach(b => {
            if (b) b.disabled = disabled;
        });
    }

    function _updateSelectAll(type) {
        const cfg = _state[type].config;
        const container = document.getElementById(cfg.listContainerId);
        if (!container) return;
        const checkboxes = container.querySelectorAll('.batch-check-' + type);
        const selectAllEl = document.getElementById(cfg.selectAllId);
        if (!selectAllEl) return;
        const allChecked = checkboxes.length > 0 && Array.from(checkboxes).every(c => c.checked);
        const someChecked = Array.from(checkboxes).some(c => c.checked);
        selectAllEl.checked = allChecked;
        selectAllEl.indeterminate = someChecked && !allChecked;
    }

    async function _doBulkAction(type, action, reason) {
        const s = _state[type];
        const cfg = s.config;
        const ids = Array.from(s.selectedIds);

        // Disable buttons and show loading
        const toolbar = document.getElementById(cfg.toolbarId);
        const buttons = toolbar ? toolbar.querySelectorAll('button') : [];
        buttons.forEach(b => { b.disabled = true; });

        // Resolve URL: per-action map takes priority over single URL
        let url = cfg.bulkActionUrl;
        if (cfg.bulkActionUrls && cfg.bulkActionUrls[action]) {
            url = cfg.bulkActionUrls[action];
        }

        // Build request body: allow custom formatter or use default
        let body;
        if (cfg.bulkRequestFormatter && typeof cfg.bulkRequestFormatter === 'function') {
            body = cfg.bulkRequestFormatter(action, ids, reason);
        } else {
            body = { action: action, ids: ids, reason: reason };
        }

        // Get CSRF token
        const csrfToken = document.querySelector('meta[name="csrf-token"]')?.content || '';

        try {
            const resp = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
                body: JSON.stringify(body)
            });
            const data = await resp.json();

            if (data.success) {
                if (typeof showToast === 'function') {
                    showToast(data.message || `${_capitalize(action)} completed successfully`, 'success');
                }
                exit(type);

                // Callback or reload
                if (cfg.onComplete && typeof cfg.onComplete === 'function') {
                    cfg.onComplete(action, ids, data);
                } else {
                    setTimeout(() => window.location.reload(), 600);
                }
            } else {
                if (typeof showToast === 'function') {
                    showToast(data.message || data.error || 'Operation failed', 'error');
                }
                buttons.forEach(b => { b.disabled = false; });
            }
        } catch (err) {
            console.error('Bulk action error:', err);
            if (typeof showToast === 'function') {
                showToast('Network error — please try again', 'error');
            }
            buttons.forEach(b => { b.disabled = false; });
        }
    }

    // ── Modal helpers ──────────────────────────────────────

    function _showConfirmModal(title, message, confirmText, color, onConfirm) {
        _buildModal(title, message, confirmText, color, onConfirm);
    }

    function _showArchiveReasonModal(type, count, label, onConfirm) {
        const existing = document.getElementById('batchArchiveReasonModal');
        if (existing) existing.remove();

        const modal = document.createElement('div');
        modal.id = 'batchArchiveReasonModal';
        modal.className = 'fixed inset-0 z-[80] flex items-center justify-center';
        modal.innerHTML = `
            <div class="fixed inset-0 bg-black/40" onclick="BatchSelect._closeArchiveModal()"></div>
            <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100">
                    <h3 class="text-sm font-semibold text-gray-900 flex items-center gap-2">
                        <svg class="w-4 h-4 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path>
                        </svg>
                        Batch Archive
                    </h3>
                </div>
                <div class="px-5 py-4 space-y-3">
                    <p class="text-sm text-gray-600">Archive <strong>${count} ${label}</strong>? Related schedules will also be deleted.</p>
                    <div>
                        <label class="block text-xs font-medium text-gray-700 mb-1">Reason (optional)</label>
                        <textarea id="batchArchiveReasonInput" rows="2" class="w-full text-sm border border-gray-300 rounded-lg px-3 py-2 focus:ring-2 focus:ring-amber-500 focus:border-amber-500" placeholder="Enter archive reason...">Bulk archive by admin</textarea>
                    </div>
                </div>
                <div class="px-5 py-3 border-t border-gray-100 bg-gray-50 flex justify-end gap-2">
                    <button onclick="BatchSelect._closeArchiveModal()" class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
                    <button id="batchArchiveConfirmBtn" class="px-4 py-1.5 text-xs font-medium text-white bg-amber-600 hover:bg-amber-700 rounded-lg transition-colors">
                        <svg class="w-3.5 h-3.5 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
                        Archive ${count}
                    </button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);

        document.getElementById('batchArchiveConfirmBtn').addEventListener('click', function () {
            const reason = document.getElementById('batchArchiveReasonInput').value.trim() || 'Bulk archive';
            BatchSelect._closeArchiveModal();
            onConfirm(reason);
        });
    }

    function _closeArchiveModal() {
        const m = document.getElementById('batchArchiveReasonModal');
        if (m) m.remove();
    }

    function _buildModal(title, message, confirmText, color, onConfirm) {
        const existing = document.getElementById('batchConfirmModal');
        if (existing) existing.remove();

        const colorMap = {
            red:   { bg: 'bg-red-600 hover:bg-red-700',   icon: 'text-red-500' },
            amber: { bg: 'bg-amber-600 hover:bg-amber-700', icon: 'text-amber-500' },
            green: { bg: 'bg-green-600 hover:bg-green-700', icon: 'text-green-500' },
            blue:  { bg: 'bg-blue-600 hover:bg-blue-700',  icon: 'text-blue-500' }
        };
        const c = colorMap[color] || colorMap.blue;

        const modal = document.createElement('div');
        modal.id = 'batchConfirmModal';
        modal.className = 'fixed inset-0 z-[80] flex items-center justify-center';
        modal.innerHTML = `
            <div class="fixed inset-0 bg-black/40" onclick="document.getElementById('batchConfirmModal').remove()"></div>
            <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
                <div class="px-5 py-4 border-b border-gray-100">
                    <h3 class="text-sm font-semibold text-gray-900 flex items-center gap-2">
                        <svg class="w-4 h-4 ${c.icon}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                        </svg>
                        ${title}
                    </h3>
                </div>
                <div class="px-5 py-4">
                    <p class="text-sm text-gray-600">${message}</p>
                </div>
                <div class="px-5 py-3 border-t border-gray-100 bg-gray-50 flex justify-end gap-2">
                    <button onclick="document.getElementById('batchConfirmModal').remove()" class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
                    <button id="batchConfirmActionBtn" class="px-4 py-1.5 text-xs font-medium text-white ${c.bg} rounded-lg transition-colors">${confirmText}</button>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        document.getElementById('batchConfirmActionBtn').addEventListener('click', function () {
            document.getElementById('batchConfirmModal').remove();
            onConfirm();
        });
    }

    function _capitalize(s) {
        return s.charAt(0).toUpperCase() + s.slice(1);
    }

    function _emitStateChange(type, active) {
        document.dispatchEvent(new CustomEvent('batchselect:change', {
            detail: { type: type, active: active }
        }));
    }

    /** Get array of currently selected IDs for a type */
    function getSelected(type) {
        const s = _state[type];
        return s ? Array.from(s.selectedIds) : [];
    }

    // ── Expose public interface ────────────────────────────
    return {
        init,
        toggle,
        enter,
        exit,
        selectAll,
        onCheckChange,
        execute,
        isActive,
        refreshCheckboxes,
        getSelected,
        _closeArchiveModal  // exposed for modal onclick
    };

})();
