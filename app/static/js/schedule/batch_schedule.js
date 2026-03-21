/**
 * Batch Schedule Builder - JavaScript Controller
 * Replaces auto-generate with a fully editable batch builder.
 * Auto-assigns day/time/room, user picks faculty inline.
 * Includes real-time conflict detection per row.
 */

// ─── State ────────────────────────────────────────────────────────
let _batchData = null;           // Full response from backend
let _batchSectionId = null;      // Current section ID
let _batchCurriculumId = null;   // Selected curriculum ID
let _batchModeActive = false;    // Whether inline batch panel is visible
let _facultyCache = {};          // Cache faculty lists per subject_id
let _availableSubjects = null;   // Unscheduled subjects for "Add Subject"
let _activeDropdown = null;      // Currently open dropdown element
let _preferredBuildingId = null; // Building preference for room prioritisation
let _batchScheduleMode = 'quick'; // 'quick' (greedy) or 'smart' (backtracking)

// ─── Conflict Detection State ─────────────────────────────────────
let _batchConflicts = {};        // Map of rowIndex → { status, conflicts[] }
let _conflictCheckTimer = null;  // Debounce timer
let _conflictCheckInFlight = false; // Prevent duplicate requests
const CONFLICT_CHECK_DEBOUNCE_MS = 800;

// DAYS will be overridden by template-injected window.OPERATION_DAYS if available
const DAYS = (typeof window !== 'undefined' && window.OPERATION_DAYS) ? window.OPERATION_DAYS : ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const BATCH_STATE_KEY = 'ischedwise_batch_mode';

// ─── Step Indicator & Progress Bar Helpers ────────────────────────

function _updateBatchStep(activeStep) {
    const steps = document.querySelectorAll('#batchStepIndicator .batch-step');
    const lines = document.querySelectorAll('#batchStepIndicator .batch-step-line');
    steps.forEach(s => {
        const step = parseInt(s.dataset.step);
        const dot = s.querySelector('.batch-step-dot');
        const label = s.querySelector('.batch-step-label');
        if (step < activeStep) {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-violet-600 text-white shadow-sm ring-2 ring-violet-200 dark:ring-violet-800';
            dot.innerHTML = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>';
            if (label) { label.className = 'batch-step-label text-[11px] font-semibold text-violet-700 dark:text-violet-300 hidden sm:inline'; }
        } else if (step === activeStep) {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-violet-600 text-white shadow-sm ring-2 ring-violet-200 dark:ring-violet-800';
            dot.textContent = step;
            if (label) { label.className = 'batch-step-label text-[11px] font-semibold text-violet-700 dark:text-violet-300 hidden sm:inline'; }
        } else {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-gray-200 text-gray-400 dark:bg-gray-600 dark:text-gray-500';
            dot.textContent = step;
            if (label) { label.className = 'batch-step-label text-[11px] font-medium text-gray-400 dark:text-gray-500 hidden sm:inline'; }
        }
    });
    lines.forEach((line, i) => {
        line.className = 'batch-step-line w-10 sm:w-16 h-0.5 mx-2 rounded-full transition-all duration-500 ' + ((i + 1 < activeStep) ? 'bg-violet-400 dark:bg-violet-500' : 'bg-gray-200 dark:bg-gray-600');
    });
}

function _updateBatchProgressBar() {
    const stats = _batchData?.stats;
    if (!stats) return;
    const total = stats.total_subjects || 1;
    const placed = stats.scheduled || 0;
    const existing = stats.already_scheduled || 0;
    const unplaceable = stats.unplaceable || 0;
    document.getElementById('batchProgressPlaced').style.width = ((placed / total) * 100).toFixed(1) + '%';
    document.getElementById('batchProgressExisting').style.width = ((existing / total) * 100).toFixed(1) + '%';
    document.getElementById('batchProgressUnplaceable').style.width = ((unplaceable / total) * 100).toFixed(1) + '%';
}

// ─── Enter / Exit Batch Mode (Inline Panel Switching) ─────────────

function enterBatchMode() {
    const panel = document.getElementById('batchBuilderPanel');
    const formPanel = document.getElementById('classFormPanel');
    if (!panel) {
        // Fallback: try modal approach (schedule_class.html page)
        openAutoScheduleModal(window.FORM_SECTION_ID, window.FORM_SECTION_NAME || '');
        return;
    }

    const sectionId = window.FORM_SECTION_ID;
    const sectionName = window.FORM_SECTION_NAME || '';
    if (!sectionId) {
        if (typeof showToast === 'function') showToast('Select a section first', 'error');
        return;
    }

    _batchData = null;
    _batchSectionId = sectionId;
    _batchCurriculumId = null;
    _batchModeActive = true;
    _facultyCache = {};
    _availableSubjects = null;
    _preferredBuildingId = null;
    _batchScheduleMode = 'quick';
    _batchConflicts = {};
    _conflictCheckInFlight = false;
    if (_conflictCheckTimer) { clearTimeout(_conflictCheckTimer); _conflictCheckTimer = null; }

    // Reset mode toggle UI
    if (document.getElementById('batchModeQuick')) setBatchScheduleMode('quick');

    // Reset step indicator to step 1
    _updateBatchStep(1);

    // Reset batch panel UI — show curriculum step first
    document.getElementById('autoScheduleSectionName').textContent = 'Section: ' + sectionName;
    document.getElementById('batchCurriculumStep').classList.remove('hidden');
    document.getElementById('autoScheduleLoading').classList.add('hidden');
    document.getElementById('autoScheduleError').classList.add('hidden');
    document.getElementById('autoScheduleAllDone').classList.add('hidden');
    document.getElementById('autoScheduleResults').classList.add('hidden');
    document.getElementById('autoScheduleStats').classList.add('hidden');
    document.getElementById('autoScheduleFooter').classList.add('hidden');
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');
    document.getElementById('batchAddSubjectBtn').classList.add('hidden');

    // Load buildings list for the building preference dropdown
    loadBuildingsForBatch();

    // Swap panels: hide form, show batch builder
    if (formPanel) formPanel.classList.add('hidden');
    panel.classList.remove('hidden');
    panel.style.display = 'flex';

    // Update header buttons
    const autoGenBtn = document.getElementById('autoGenBtn');
    const submitBtn = document.getElementById('submitScheduleBtn');
    const backBtn = document.getElementById('batchBackBtn');
    const backLink = document.getElementById('unifiedBackLink');
    const tabSwitcher = document.getElementById('tabBtnClass')?.closest('.bg-gray-100');

    if (autoGenBtn) autoGenBtn.style.display = 'none';
    if (submitBtn) submitBtn.style.display = 'none';
    if (backBtn) backBtn.classList.remove('hidden');
    if (backLink) backLink.classList.add('hidden');
    if (tabSwitcher) tabSwitcher.style.display = 'none';

    // Update page title
    const pageTitle = document.getElementById('unifiedPageTitle');
    if (pageTitle) {
        pageTitle._originalText = pageTitle.textContent;
        pageTitle.textContent = 'Batch Schedule';
    }
    // Swap header icon to batch palette (dark-mode aware)
    const iconAdd = document.getElementById('unifiedIconAdd');
    const iconEdit = document.getElementById('unifiedIconEdit');
    if (iconAdd) {
        if (iconAdd._batchOriginalClass === undefined) iconAdd._batchOriginalClass = iconAdd.className;
        if (iconAdd._batchOriginalHidden === undefined) iconAdd._batchOriginalHidden = iconAdd.classList.contains('hidden');
        const iconSvg = iconAdd.querySelector('svg');
        if (iconSvg && iconSvg._batchOriginalClass === undefined) iconSvg._batchOriginalClass = iconSvg.className.baseVal || iconSvg.className;

        iconAdd.classList.remove('hidden', 'bg-emerald-100', 'dark:bg-emerald-900/30', 'bg-blue-100', 'dark:bg-blue-900/30', 'bg-orange-100', 'dark:bg-orange-900/30');
        iconAdd.classList.add('bg-violet-100', 'dark:bg-violet-900/30');
        if (iconSvg) {
            iconSvg.classList.remove('text-emerald-600', 'dark:text-emerald-400', 'text-blue-600', 'dark:text-blue-400', 'text-orange-600', 'dark:text-orange-400');
            iconSvg.classList.add('text-violet-600', 'dark:text-violet-300');
        }
    }
    if (iconEdit) {
        if (iconEdit._batchOriginalHidden === undefined) iconEdit._batchOriginalHidden = iconEdit.classList.contains('hidden');
        iconEdit.classList.add('hidden');
    }

    // Hide AI Assistant badge while in batch mode
    const aiBadge = document.getElementById('aiBadge');
    if (aiBadge) { aiBadge.classList.add('hidden'); aiBadge.classList.remove('flex'); }
    if (typeof closeAIDrawer === 'function') closeAIDrawer();

    // Persist batch mode so a page refresh stays in batch
    sessionStorage.setItem(BATCH_STATE_KEY, 'class');

    // Load curricula for selection step (don't start preview yet)
    loadBatchCurricula(sectionId);
}

// ─── Curriculum Selection Step ──────────────────────────────────────────

async function loadBatchCurricula(sectionId) {
    const select = document.getElementById('batchCurriculumSelect');
    const btn = document.getElementById('batchCurriculumConfirmBtn');
    if (!select) return;

    select.innerHTML = '<option value="">Loading curricula...</option>';
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`/schedule/get-curricula/${sectionId}`);
        const data = await res.json();
        const curricula = data.curricula || [];

        if (curricula.length === 0) {
            select.innerHTML = '<option value="">No curricula found for this program</option>';
            return;
        }

        select.innerHTML = '<option value="">Select a curriculum...</option>';
        curricula.forEach(c => {
            const opt = document.createElement('option');
            opt.value = c.id;
            opt.textContent = `${c.curriculum_code} — ${c.degree_program}`;
            select.appendChild(opt);
        });

        // If only one curriculum, auto-select and proceed immediately
        if (curricula.length === 1) {
            select.value = curricula[0].id;
            if (btn) btn.disabled = false;
            // Auto-confirm if there's only one
            confirmBatchCurriculum();
            return;
        }

        // Enable button when selection changes
        select.onchange = function() {
            if (btn) btn.disabled = !this.value;
        };
    } catch (e) {
        select.innerHTML = '<option value="">Error loading curricula</option>';
    }
}

function confirmBatchCurriculum() {
    const select = document.getElementById('batchCurriculumSelect');
    const curriculumId = select ? select.value : null;
    if (!curriculumId || !_batchSectionId) return;

    _batchCurriculumId = parseInt(curriculumId);

    // Hide curriculum step, show loading
    document.getElementById('batchCurriculumStep').classList.add('hidden');
    document.getElementById('autoScheduleLoading').classList.remove('hidden');

    generateBatchPreview(_batchSectionId);
}

// ─── Building Preference ─────────────────────────────────────────────

async function loadBuildingsForBatch() {
    const select = document.getElementById('batchBuildingSelect');
    if (!select) return;

    try {
        const res = await fetch('/schedule/get-buildings');
        const data = await res.json();
        const buildings = data.buildings || [];

        // Keep "All Buildings" default, append fetched options
        select.innerHTML = '<option value="">All Buildings</option>';
        buildings.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            opt.textContent = b.building_name;
            select.appendChild(opt);
        });

        // Restore previous selection if any
        if (_preferredBuildingId) {
            select.value = _preferredBuildingId;
        }
    } catch (e) {
        console.warn('Could not load buildings for batch filter:', e);
    }
}

function onBatchBuildingChange(value) {
    _preferredBuildingId = value ? parseInt(value) : null;
    // If batch data is already rendered, regenerate to apply building preference
    if (_batchData && _batchSectionId) {
        document.getElementById('autoScheduleLoading').classList.remove('hidden');
        document.getElementById('autoScheduleResults').classList.add('hidden');
        generateBatchPreview(_batchSectionId);
    }
}

// ─── Schedule Mode Toggle (Quick / Smart) ─────────────────────────

function setBatchScheduleMode(mode) {
    _batchScheduleMode = mode || 'quick';

    const quickBtn = document.getElementById('batchModeQuick');
    const smartBtn = document.getElementById('batchModeSmart');
    const hint = document.getElementById('batchModeHint');

    const activeClass = 'flex-1 px-2 py-1.5 text-[11px] font-semibold rounded-md transition-all shadow-sm ring-1 ring-gray-200 dark:ring-gray-500';
    const inactiveClass = 'flex-1 px-2 py-1.5 text-[11px] font-semibold rounded-md transition-all text-gray-500 dark:text-gray-400 hover:bg-gray-50 dark:hover:bg-gray-600';

    if (quickBtn && smartBtn) {
        if (mode === 'smart') {
            smartBtn.className = activeClass + ' bg-purple-50 dark:bg-gray-600 text-purple-700 dark:text-purple-300';
            quickBtn.className = inactiveClass;
            if (hint) hint.textContent = 'Backtracking search — fewer unplaceable subjects';
        } else {
            quickBtn.className = activeClass + ' bg-violet-50 dark:bg-gray-600 text-violet-700 dark:text-violet-300';
            smartBtn.className = inactiveClass;
            if (hint) hint.textContent = 'First-fit heuristic — fast results';
        }
    }
}

function exitBatchMode(silent) {
    // Clear persisted batch mode state
    sessionStorage.removeItem(BATCH_STATE_KEY);

    _batchModeActive = false;
    _batchData = null;
    _batchSectionId = null;
    _batchCurriculumId = null;
    _activeDropdown = null;
    _preferredBuildingId = null;
    _batchConflicts = {};
    _conflictCheckInFlight = false;
    if (_conflictCheckTimer) { clearTimeout(_conflictCheckTimer); _conflictCheckTimer = null; }

    // Remove any open tooltip
    const tooltip = document.getElementById('batchConflictTooltip');
    if (tooltip) tooltip.remove();

    const panel = document.getElementById('batchBuilderPanel');
    const formPanel = document.getElementById('classFormPanel');

    // Swap panels back: show form, hide batch builder
    if (panel) {
        panel.classList.add('hidden');
        panel.style.display = '';
    }
    if (formPanel) formPanel.classList.remove('hidden');

    // Restore header buttons
    const autoGenBtn = document.getElementById('autoGenBtn');
    const submitBtn = document.getElementById('submitScheduleBtn');
    const backBtn = document.getElementById('batchBackBtn');
    const backLink = document.getElementById('unifiedBackLink');
    const tabSwitcher = document.getElementById('tabBtnClass')?.closest('.bg-gray-100');

    if (autoGenBtn && window.FORM_SECTION_ID) autoGenBtn.style.display = 'flex';
    if (submitBtn) submitBtn.style.display = 'flex';
    if (backBtn) backBtn.classList.add('hidden');
    if (backLink) backLink.classList.remove('hidden');
    if (tabSwitcher) tabSwitcher.style.display = '';

    // Restore page title
    const pageTitle = document.getElementById('unifiedPageTitle');
    if (pageTitle && pageTitle._originalText) {
        pageTitle.textContent = pageTitle._originalText;
    }
    // Restore icon state
    const iconAdd = document.getElementById('unifiedIconAdd');
    const iconEdit = document.getElementById('unifiedIconEdit');
    if (iconAdd && iconAdd._batchOriginalClass !== undefined) {
        iconAdd.className = iconAdd._batchOriginalClass;
        if (iconAdd._batchOriginalHidden) iconAdd.classList.add('hidden');
        else iconAdd.classList.remove('hidden');
        const iconSvg = iconAdd.querySelector('svg');
        if (iconSvg && iconSvg._batchOriginalClass !== undefined) {
            iconSvg.setAttribute('class', iconSvg._batchOriginalClass);
        }
    }
    if (iconEdit && iconEdit._batchOriginalHidden !== undefined) {
        if (iconEdit._batchOriginalHidden) iconEdit.classList.add('hidden');
        else iconEdit.classList.remove('hidden');
    }

    // Restore AI Assistant badge
    const aiBadge = document.getElementById('aiBadge');
    if (aiBadge) { aiBadge.classList.remove('hidden'); aiBadge.classList.add('flex'); }
}

// ─── Modal-based Open / Close (for schedule_class.html backward compat) ─

function openAutoScheduleModal(sectionId, sectionName) {
    // If the inline panel exists (form page), use it instead
    if (document.getElementById('batchBuilderPanel')) {
        window.FORM_SECTION_ID = sectionId;
        window.FORM_SECTION_NAME = sectionName;
        enterBatchMode();
        return;
    }

    // Fallback: modal approach (schedule_class.html)
    const modal = document.getElementById('autoScheduleModal');
    if (!modal) return;

    _batchData = null;
    _batchSectionId = sectionId;
    _facultyCache = {};
    _availableSubjects = null;

    document.getElementById('autoScheduleSectionName').textContent = 'Section: ' + sectionName;
    document.getElementById('autoScheduleLoading').classList.remove('hidden');
    document.getElementById('autoScheduleError').classList.add('hidden');
    document.getElementById('autoScheduleAllDone').classList.add('hidden');
    document.getElementById('autoScheduleResults').classList.add('hidden');
    document.getElementById('autoScheduleStats').classList.add('hidden');
    document.getElementById('autoScheduleFooter').classList.add('hidden');
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    generateBatchPreview(sectionId);
}

function closeBatchModal() {
    // If inline mode, use exitBatchMode
    if (_batchModeActive) {
        exitBatchMode();
        return;
    }
    // Modal approach
    const modal = document.getElementById('autoScheduleModal');
    if (modal) {
        modal.classList.add('hidden');
        document.body.style.overflow = '';
    }
    _batchData = null;
    _batchSectionId = null;
    _activeDropdown = null;
}

// Backward compatibility
function closeAutoScheduleModal() { closeBatchModal(); }

// ─── API: Generate Preview ────────────────────────────────────────

async function generateBatchPreview(sectionId) {
    try {
        const body = { section_id: sectionId };
        if (_batchCurriculumId) body.curriculum_id = _batchCurriculumId;
        if (_preferredBuildingId) body.preferred_building_id = _preferredBuildingId;
        if (_batchScheduleMode) body.mode = _batchScheduleMode;

        // Update loading text for Smart mode
        const loadTitle = document.getElementById('autoScheduleLoadingTitle');
        const loadHint = document.getElementById('autoScheduleLoadingHint');
        if (loadTitle && loadHint) {
            if (_batchScheduleMode === 'smart') {
                loadTitle.textContent = 'Optimizing schedule...';
                loadHint.textContent = 'Running backtracking search — this may take up to 30 seconds';
            } else {
                loadTitle.textContent = 'Building schedule preview...';
                loadHint.textContent = 'Finding optimal time slots and rooms';
            }
        }

        const response = await fetch('/schedule/batch-generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();

        document.getElementById('autoScheduleLoading').classList.add('hidden');

        if (!data.success) {
            showBatchError(data.error || 'Unknown error');
            return;
        }

        if (data.proposed.length === 0 && (!data.unplaceable || data.unplaceable.length === 0)) {
            // If backend returned existing schedules, render them as editable rows
            if (data.existing && data.existing.length > 0) {
                // Treat existing items as proposed so renderBatchResults works
                data.proposed = data.existing;
                data.stats = data.stats || {};
                data.stats.scheduled = data.existing.length;
                data.stats.already_scheduled = 0;
                _batchData = data;
                renderBatchResults(data);
                // Mark existing rows with green border
                const rows = document.querySelectorAll('#autoScheduleTableBody tr');
                rows.forEach(row => {
                    row.classList.remove('border-l-gray-200');
                    row.classList.add('border-l-emerald-400');
                    row.dataset.isExisting = 'true';
                });
                // Show info banner
                document.getElementById('autoScheduleAllDone').classList.remove('hidden');
                return;
            }
            document.getElementById('autoScheduleAllDone').classList.remove('hidden');
            return;
        }

        _batchData = data;
        renderBatchResults(data);

    } catch (err) {
        document.getElementById('autoScheduleLoading').classList.add('hidden');
        showBatchError(err.message || 'Network error');
    }
}

// ─── Render Results ───────────────────────────────────────────────

function renderBatchResults(data) {
    const stats = data.stats || {};

    // Step indicator → step 2
    _updateBatchStep(2);

    // Stats
    const total = stats.total_subjects || 0;
    const scheduled = stats.scheduled || 0;
    const existing = stats.already_scheduled || 0;
    const unplaceable = stats.unplaceable || 0;
    const ready = scheduled + existing;
    const needAttention = total - ready;

    document.getElementById('autoStatTotal').textContent = total;
    document.getElementById('autoStatScheduled').textContent = scheduled;
    document.getElementById('autoStatExisting').textContent = existing;
    document.getElementById('autoScheduleStats').classList.remove('hidden');

    // Plain-English summary line
    const summaryEl = document.getElementById('batchSummaryLine');
    if (summaryEl) {
        if (total === 0) {
            summaryEl.textContent = '';
        } else if (needAttention > 0) {
            summaryEl.textContent = `${ready} of ${total} subjects scheduled — ${needAttention} need attention`;
            summaryEl.className = 'text-[11px] font-medium text-amber-600 dark:text-amber-400 mb-1.5';
        } else {
            summaryEl.textContent = `All ${total} subjects scheduled ✓`;
            summaryEl.className = 'text-[11px] font-medium text-emerald-600 dark:text-emerald-400 mb-1.5';
        }
    }

    // Progress bar
    _updateBatchProgressBar();

    // Show Add Subject button in header
    const addSubBtn = document.getElementById('batchAddSubjectBtn');
    if (addSubBtn) addSubBtn.classList.remove('hidden');

    if (unplaceable > 0) {
        document.getElementById('autoStatUnplaceable').textContent = unplaceable;
        document.getElementById('autoStatUnplaceableWrap').classList.remove('hidden');
    } else {
        document.getElementById('autoStatUnplaceableWrap').classList.add('hidden');
    }

    // Proposed table
    const tbody = document.getElementById('autoScheduleTableBody');
    tbody.innerHTML = '';

    if (data.proposed && data.proposed.length > 0) {
        data.proposed.forEach((item, idx) => {
            const row = buildBatchRow(item, idx);
            tbody.appendChild(row);
            // Pre-load faculty for this subject
            loadFacultyForRow(idx, item.subject_id);
        });
        if (window.TimePicker && typeof window.TimePicker.init === 'function') {
            window.TimePicker.init();
        }
    }

    // Unplaceable
    renderUnplaceableItems(data.unplaceable);

    // Show results & footer
    document.getElementById('autoScheduleResults').classList.remove('hidden');
    if (data.proposed && data.proposed.length > 0) {
        document.getElementById('autoScheduleFooter').classList.remove('hidden');
    }

    validateAllRows();

    // Initial conflict check — slight delay to let faculty auto-select settle
    setTimeout(() => {
        performBatchConflictCheck();
    }, 1500);

    // Build calendar view (hidden by default but ready)
    buildBatchCalendar();
}

// ─── Batch Calendar View ──────────────────────────────────────────

let _batchCurrentView = 'table'; // 'table' or 'calendar'

function switchBatchView(view) {
    _batchCurrentView = view;
    const tableView = document.getElementById('batchTableView');
    const calView = document.getElementById('batchCalendarView');
    const btnTable = document.getElementById('batchViewTable');
    const btnCal = document.getElementById('batchViewCalendar');
    if (!tableView || !calView) return;

    if (view === 'calendar') {
        tableView.classList.add('hidden');
        calView.classList.remove('hidden');
        btnTable.className = 'px-2.5 py-1 text-[10px] font-semibold rounded-md transition-all text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-gray-100';
        btnCal.className = 'px-2.5 py-1 text-[10px] font-semibold rounded-md transition-all bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-100 shadow-sm';
        buildBatchCalendar();
    } else {
        calView.classList.add('hidden');
        tableView.classList.remove('hidden');
        btnTable.className = 'px-2.5 py-1 text-[10px] font-semibold rounded-md transition-all bg-white dark:bg-gray-600 text-gray-700 dark:text-gray-100 shadow-sm';
        btnCal.className = 'px-2.5 py-1 text-[10px] font-semibold rounded-md transition-all text-gray-400 dark:text-gray-300 hover:text-gray-600 dark:hover:text-gray-100';
    }
}

function buildBatchCalendar() {
    const body = document.getElementById('batchCalendarBody');
    if (!body) return;

    // Gather current rows from the table
    const rows = document.querySelectorAll('#autoScheduleTableBody tr[data-row-index]');
    if (!rows.length) { body.innerHTML = ''; return; }

    // Determine time range from data
    let minHour = 24, maxHour = 0;
    const events = [];

    rows.forEach(row => {
        const day = row.querySelector('[data-field="day_of_week"]')?.value;
        const st = row.querySelector('[data-field="start_time"]')?.value;
        const et = row.querySelector('[data-field="end_time"]')?.value;
        const type = row.querySelector('[data-field="schedule_type"]')?.value || 'lecture';
        const subjectCode = row.querySelector('td:nth-child(3) .font-semibold')?.textContent || '';
        const desc = row.querySelector('td:nth-child(3) .text-gray-400')?.getAttribute('title') || '';
        const roomName = row.querySelector('[data-field="room_name"]')?.value || '';
        const buildingName = row.querySelector('[data-field="building_name"]')?.value || '';
        const facultyName = row.querySelector('[data-field="faculty_name"]')?.value || '';
        const rowIdx = row.dataset.rowIndex;

        if (!day || !st || !et) return;

        const [sh, sm] = st.split(':').map(Number);
        const [eh, em] = et.split(':').map(Number);

        if (sh < minHour) minHour = sh;
        if (eh > maxHour || (eh === maxHour && em > 0)) maxHour = em > 0 ? eh + 1 : eh;

        events.push({
            day, startHour: sh, startMin: sm, endHour: eh, endMin: em,
            type, subjectCode, desc, roomName, buildingName, facultyName, rowIdx
        });
    });

    // Use school settings for full day range (consistent with modal calendars)
    const globalStartHour = window.scheduleStartHour || 7;
    let globalEndHour = window.scheduleEndHour || 20;
    const schedEndMinute = window.scheduleEndMinute || 0;
    
    // Expand the logical view to bound both events AND global limits
    minHour = Math.min(minHour, globalStartHour);
    let maxHourTotalMin = Math.max(maxHour * 60, globalEndHour * 60 + schedEndMinute);
    // Let's determine maxHour explicitly for grid looping
    maxHour = Math.ceil(maxHourTotalMin / 60);

    const totalHours = maxHour - minHour;
    const totalGridHeight = totalHours * 60;

    // Build grid
    body.innerHTML = '';

    // Time column
    const timeCol = document.createElement('div');
    timeCol.className = 'week-time-column';
    
    // We render time labels for every 30 mins
    for (let m = minHour * 60; m < maxHourTotalMin; m += 30) {
        const h = Math.floor(m / 60);
        const min = m % 60;
        const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const minStr = min === 0 ? '00' : '30';
        
        const slot = document.createElement('div');
        slot.className = 'week-time-slot';
        slot.innerHTML = `<span class="time-label">${hr12}:${minStr}</span><span class="time-period">${ampm}</span>`;
        timeCol.appendChild(slot);
    }
    
    // Final boundary label
    {
        const finalH = Math.floor(maxHourTotalMin / 60);
        const finalMin = maxHourTotalMin % 60;
        const hr12 = finalH > 12 ? finalH - 12 : (finalH === 0 ? 12 : finalH);
        const ampm = finalH >= 12 ? 'PM' : 'AM';
        const minStr = finalMin === 0 ? '00' : '30';
        
        const slotEnd = document.createElement('div');
        slotEnd.className = 'week-time-slot';
        slotEnd.style.height = '0';
        slotEnd.style.position = 'relative';
        slotEnd.style.overflow = 'visible';
        slotEnd.innerHTML = `<div style="position: absolute; left: 0; right: 0; top: 0; display: flex; justify-content: flex-end; gap: 2px; padding: 0 8px 0 4px;"><span class="time-label">${hr12}:${minStr}</span><span class="time-period">${ampm}</span></div>`;
        timeCol.appendChild(slotEnd);
    }
    body.appendChild(timeCol);

    // Day grid wrapper
    const dayNames = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];

    dayNames.forEach(dayName => {
        const dayCol = document.createElement('div');
        dayCol.className = 'week-day-column';
        dayCol.dataset.day = dayName;
        dayCol.style.minHeight = (totalHours * 60) + 'px';

        // Hour grid lines
        for (let h = 0; h < totalHours; h++) {
            const hourLine = document.createElement('div');
            hourLine.className = 'week-hour-line';
            hourLine.style.top = ((h * 60) + 8) + 'px';
            dayCol.appendChild(hourLine);

            const halfLine = document.createElement('div');
            halfLine.className = 'week-half-hour-line';
            halfLine.style.top = ((h * 60 + 30) + 8) + 'px';
            dayCol.appendChild(halfLine);
        }

        // Events container
        const evContainer = document.createElement('div');
        evContainer.className = 'week-events-container';

        // Collect events for this day
        const dayEvents = events.filter(e => e.day === dayName);

        // Detect overlaps for side-by-side stacking
        const overlapGroups = _detectBatchOverlaps(dayEvents);

        dayEvents.forEach(ev => {
            const top = ((ev.startHour - minHour) * 60 + ev.startMin) + 8;
            const height = Math.max(((ev.endHour - ev.startHour) * 60 + (ev.endMin - ev.startMin)), 20);

            const hasFaculty = !!ev.facultyName;
            let eventClass = 'week-event';
            if (ev.type === 'lab') {
                eventClass += ' event-lab';
            } else {
                eventClass += ' event-lecture';
            }

            // Overlap stacking
            const group = overlapGroups.get(ev);
            if (group && group.total > 1) {
                const w = 100 / group.total;
                var leftPct = w * group.index;
                var rightPct = 100 - w * (group.index + 1);
            }

            const evEl = document.createElement('div');
            evEl.className = eventClass;
            evEl.style.top = top + 'px';
            evEl.style.height = height + 'px';
            evEl.style.cursor = 'pointer';
            if (group && group.total > 1) {
                evEl.style.left = leftPct + '%';
                evEl.style.right = rightPct + '%';
            }

            // Unassigned faculty → yellow accent
            if (!hasFaculty) {
                evEl.classList.add('event-unassigned');
                evEl.style.borderLeftColor = '#f59e0b';
                evEl.style.background = 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)';
            }

            const stFmt = _fmtTime12(ev.startHour, ev.startMin);
            const etFmt = _fmtTime12(ev.endHour, ev.endMin);
            const roomDisplay = ev.roomName || 'TBA';

            evEl.innerHTML = `
                <div class="event-content">
                    <div class="event-subject">${_escHtml(ev.subjectCode)}</div>
                    ${height >= 45 ? `<div class="event-room">${_escHtml(roomDisplay)}</div>` : ''}
                    ${height >= 60 ? `<div class="event-faculty">${hasFaculty ? _escHtml(ev.facultyName) : '<span style=\"color:#d97706\">No faculty</span>'}</div>` : ''}
                    ${height >= 75 ? `<div class="event-time">${stFmt} - ${etFmt}</div>` : ''}
                </div>
                <div class="event-type-badge">${ev.type === 'lab' ? 'LAB' : 'LEC'}</div>
            `;

            evEl.title = `${ev.subjectCode} (${ev.type.toUpperCase()})\n${roomDisplay}\n${hasFaculty ? ev.facultyName : 'No faculty'}\n${stFmt} - ${etFmt}`;
            evEl.onclick = () => _focusBatchRow(ev.rowIdx);

            evContainer.appendChild(evEl);
        });

        dayCol.appendChild(evContainer);
        body.appendChild(dayCol);
    });
}

function _detectBatchOverlaps(dayEvents) {
    // Returns a Map: event → { index, total } for overlap stacking
    const map = new Map();
    if (!dayEvents.length) return map;

    // Sort by start time
    const sorted = [...dayEvents].sort((a, b) => (a.startHour * 60 + a.startMin) - (b.startHour * 60 + b.startMin));

    // Group overlapping events
    const groups = [];
    let currentGroup = [sorted[0]];

    for (let i = 1; i < sorted.length; i++) {
        const prev = currentGroup[currentGroup.length - 1];
        const cur = sorted[i];
        const prevEnd = prev.endHour * 60 + prev.endMin;
        const curStart = cur.startHour * 60 + cur.startMin;
        if (curStart < prevEnd) {
            currentGroup.push(cur);
        } else {
            groups.push(currentGroup);
            currentGroup = [cur];
        }
    }
    groups.push(currentGroup);

    groups.forEach(g => {
        g.forEach((ev, idx) => {
            map.set(ev, { index: idx, total: g.length });
        });
    });
    return map;
}

function _focusBatchRow(rowIdx) {
    // Switch to table view and scroll/highlight the row
    switchBatchView('table');
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.classList.add('bg-violet-50', 'dark:bg-violet-900/20', 'ring-2', 'ring-violet-300', 'dark:ring-violet-700');
        setTimeout(() => { row.classList.remove('bg-violet-50', 'dark:bg-violet-900/20', 'ring-2', 'ring-violet-300', 'dark:ring-violet-700'); }, 2000);
    }
}

function _fmtTime12(h, m) {
    const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
    const ampm = h >= 12 ? 'PM' : 'AM';
    return hr12 + ':' + String(m).padStart(2, '0') + ' ' + ampm;
}

function _escHtml(str) {
    return typeof escapeHtml === 'function' ? escapeHtml(str) : (str || '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Refresh calendar if it's currently visible (called after any inline edit)
function _refreshBatchCalendarIfVisible() {
    if (_batchCurrentView === 'calendar') {
        buildBatchCalendar();
    }
}

function buildBatchRow(item, idx) {
    const row = document.createElement('tr');
    row.className = 'hover:bg-violet-50/30 dark:hover:bg-gray-750 transition-all group border-l-[3px] border-l-gray-200 dark:border-l-gray-600';
    row.dataset.rowIndex = idx;
    row.dataset.subjectId = item.subject_id;
    row.dataset.lecUnits = item.lec_units || 0;
    row.dataset.labUnits = item.lab_units || 0;

    const dayOptions = DAYS.map(d =>
        `<option value="${d}" ${d === item.day_of_week ? 'selected' : ''}>${d.substring(0, 3)}</option>`
    ).join('');

    const isLab = item.schedule_type === 'lab';
    const typeOptions = `
        <option value="lecture" ${!isLab ? 'selected' : ''}>Lec</option>
        <option value="lab" ${isLab ? 'selected' : ''}>Lab</option>
    `;
    // Color dot for type
    const typeDot = isLab
        ? '<span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1 flex-shrink-0"></span>'
        : '<span class="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 mr-1 flex-shrink-0"></span>';

    const facultyDisplay = item.faculty_name || '';
    const hasFaculty = !!item.faculty_id;
    const hasRoom = !!item.room_id;

    row.innerHTML = `
        <td class="px-2 py-2.5 text-center">
            <div class="batch-status-icon flex items-center justify-center" title="Pending conflict check">
                <div class="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <svg class="w-2.5 h-2.5 text-gray-400" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>
                </div>
            </div>
        </td>
        <td class="px-2 py-2.5 text-center">
            <span class="batch-row-num text-[10px] font-medium text-gray-400 tabular-nums">${idx + 1}</span>
        </td>
        <td class="px-3 py-2.5 min-w-0">
            <div class="inline-flex items-center gap-1 mb-0.5">
                <span class="font-bold text-gray-900 dark:text-gray-100 text-[11px] leading-tight">${escapeHtml(item.subject_code)}</span>
            </div>
            <div class="text-gray-400 dark:text-gray-500 truncate max-w-[160px] text-[10px] leading-tight" title="${escapeHtml(item.course_description || '')}">${escapeHtml(item.course_description || '')}</div>
        </td>
        <td class="px-2 py-2.5">
            <div class="flex items-center gap-1">
                ${typeDot}
                <select data-field="schedule_type" onchange="onTypeChange(this)" class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800 w-[52px] cursor-pointer">
                    ${typeOptions}
                </select>
            </div>
        </td>
        <td class="px-2 py-2.5 relative">
            <div class="batch-faculty-picker" data-row="${idx}">
                <button type="button" onclick="toggleBatchFacultyDropdown(this, ${idx})"
                        class="batch-faculty-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasFaculty
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-violet-300'
                            : 'border-dashed border-amber-400 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 hover:border-amber-500'}"
                        title="${hasFaculty ? '' : 'Faculty not assigned'}">
                    ${!hasFaculty ? '<svg class="w-3 h-3 flex-shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M12 2a10 10 0 100 20 10 10 0 000-20z"/></svg>' : ''}
                    <span class="truncate flex-1 min-w-0">${hasFaculty ? escapeHtml(facultyDisplay) : 'Assign Faculty'}</span>
                    <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </button>
                <input type="hidden" data-field="faculty_id" value="${item.faculty_id || ''}">
                <input type="hidden" data-field="faculty_name" value="${escapeHtml(facultyDisplay)}">
                <div class="batch-faculty-dropdown hidden fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl w-[290px] max-h-[260px] flex flex-col overflow-hidden">
                    <div class="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <input type="text" placeholder="Search faculty..." class="batch-faculty-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800" oninput="filterBatchFacultyDropdown(this, ${idx})">
                    </div>
                    <div class="batch-faculty-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-2 py-2.5">
            <select data-field="day_of_week" onchange="onDayTimeChange(this)" class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800 w-[70px] cursor-pointer">
                ${dayOptions}
            </select>
        </td>
        <td class="px-2 py-2.5 whitespace-nowrap">
            <div class="flex items-center gap-0.5">
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="start_time"
                     data-value="${item.start_time || ''}"
                     data-onchange="onStartTimeChange(input)"
                     data-input-class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800 w-[84px]">
                </div>
                <span class="text-gray-300 dark:text-gray-600 text-[9px] select-none px-0.5">–</span>
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="end_time"
                     data-value="${item.end_time || ''}"
                     data-onchange="onEndTimeChange(input)"
                     data-input-class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800 w-[84px]">
                </div>
            </div>
        </td>
        <td class="px-2 py-2.5 relative">
            <div class="batch-room-picker" data-row="${idx}">
                <button type="button" onclick="toggleBatchRoomDropdown(this, ${idx})"
                        class="batch-room-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasRoom
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-violet-300'
                            : 'border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 hover:border-gray-400'}">
                    <span class="truncate flex-1 min-w-0">
                        ${item.room_name ? escapeHtml(item.room_name) + (item.building_name ? '<span class="text-gray-400 dark:text-gray-500"> · ' + escapeHtml(item.building_name) + '</span>' : '') : 'Select Room'}
                    </span>
                    <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </button>
                <input type="hidden" data-field="room_id" value="${item.room_id || ''}">
                <input type="hidden" data-field="room_name" value="${escapeHtml(item.room_name || '')}">
                <input type="hidden" data-field="building_name" value="${escapeHtml(item.building_name || '')}">
                <div class="batch-room-dropdown hidden fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl w-[250px] max-h-[220px] flex flex-col overflow-hidden">
                    <div class="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <input type="text" placeholder="Search rooms..." class="batch-room-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-violet-400 dark:focus:border-violet-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-violet-200 dark:focus:ring-violet-800" oninput="filterBatchRoomDropdown(this, ${idx})">
                    </div>
                    <div class="batch-room-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-2 py-2.5 text-center">
            <button type="button" onclick="removeBatchRow(this)" class="p-1.5 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100" title="Remove row">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            </button>
        </td>
    `;

    return row;
}

function renderUnplaceableItems(items) {
    const section = document.getElementById('autoScheduleUnplaceableSection');
    const list = document.getElementById('autoScheduleUnplaceableList');
    list.innerHTML = '';

    if (items && items.length > 0) {
        section.classList.remove('hidden');
        items.forEach(item => {
            const div = document.createElement('div');
            div.className = 'flex items-start gap-2 p-2 bg-red-50 dark:bg-red-900/20 border border-red-100 dark:border-red-800/30 rounded-lg';
            div.innerHTML = `
                <svg class="w-3.5 h-3.5 text-red-400 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                </svg>
                <div>
                    <span class="font-semibold text-red-700 text-[11px]">${escapeHtml(item.subject_code)}</span>
                    <span class="text-red-500 ml-1 text-[10px]">(${item.schedule_type || 'lecture'})</span>
                    <p class="text-[10px] text-red-400 mt-0.5">${escapeHtml(item.reason)}</p>
                </div>
            `;
            list.appendChild(div);
        });
    } else {
        section.classList.add('hidden');
    }
}

// ─── Faculty Dropdown ─────────────────────────────────────────────

async function loadFacultyForRow(rowIdx, subjectId) {
    const doAutoSelect = (list) => {
        const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
        const currentFacultyId = row?.querySelector('[data-field="faculty_id"]')?.value;
        if (currentFacultyId) return; // Already has a faculty selected

        // Try to auto-pick the best candidate so rows don't remain unassigned.
        // Preference order: assigned -> availability/load -> lower utilization,
        // while avoiding obvious intra-batch time overlaps when possible.
        const day = row?.querySelector('[data-field="day_of_week"]')?.value || '';
        const startTime = row?.querySelector('[data-field="start_time"]')?.value || '';
        const endTime = row?.querySelector('[data-field="end_time"]')?.value || '';
        const otherAssignments = getIntraBatchAssignments(rowIdx);

        const availabilityRank = {
            'available': 0,
            'moderate': 1,
            'high_load': 2,
            'overloaded': 3
        };

        const hasIntraBatchConflict = (facultyId) => {
            if (!day || !startTime || !endTime) return false;
            return otherAssignments.some(other =>
                String(other.faculty_id) === String(facultyId) &&
                other.day === day &&
                timesOverlap(startTime, endTime, other.start_time, other.end_time)
            );
        };

        const ranked = [...list].sort((a, b) => {
            if (!!a.is_assigned !== !!b.is_assigned) return a.is_assigned ? -1 : 1;
            const ar = availabilityRank[a.availability] ?? 4;
            const br = availabilityRank[b.availability] ?? 4;
            if (ar !== br) return ar - br;
            const au = Number(a.utilization_pct || 0);
            const bu = Number(b.utilization_pct || 0);
            if (au !== bu) return au - bu;
            return String(a.full_name || '').localeCompare(String(b.full_name || ''));
        });

        const nonConflicting = ranked.filter(f => !hasIntraBatchConflict(f.id));
        const pool = nonConflicting.length > 0 ? nonConflicting : ranked;
        const best = pool.find(f => f.availability !== 'overloaded') || pool[0];

        if (best) {
            selectBatchFaculty(rowIdx, best.id, best.full_name);
        }
    };

    if (_facultyCache[subjectId]) {
        renderFacultyOptions(rowIdx, _facultyCache[subjectId]);
        doAutoSelect(_facultyCache[subjectId]);
        return;
    }
    try {
        const res = await fetch(`/schedule/get-faculty/${subjectId}`);
        const data = await res.json();
        _facultyCache[subjectId] = data.faculty || [];
        renderFacultyOptions(rowIdx, _facultyCache[subjectId]);
        doAutoSelect(_facultyCache[subjectId]);
    } catch (e) {
        console.error('Failed to load faculty for subject', subjectId, e);
    }
}

function renderFacultyOptions(rowIdx, facultyList) {
    const list = document.querySelector(`.batch-faculty-list[data-row="${rowIdx}"]`);
    if (!list) return;

    if (!facultyList || facultyList.length === 0) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">No faculty available</div>';
        return;
    }

    // Get current row's day/time for intra-batch comparison
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    const curDay = row?.querySelector('[data-field="day_of_week"]')?.value || '';
    const curSt = row?.querySelector('[data-field="start_time"]')?.value || '';
    const curEt = row?.querySelector('[data-field="end_time"]')?.value || '';
    const otherAssignments = getIntraBatchAssignments(rowIdx);

    list.innerHTML = '';
    facultyList.forEach(f => {
        const availColor = {
            'available': 'bg-green-100 text-green-700',
            'moderate': 'bg-blue-100 text-blue-700',
            'high_load': 'bg-amber-100 text-amber-700',
            'overloaded': 'bg-red-100 text-red-700'
        }[f.availability] || 'bg-gray-100 text-gray-600';

        // Check intra-batch conflict for this faculty
        let batchConflictLabel = '';
        for (const other of otherAssignments) {
            if (other.faculty_id == f.id && other.day === curDay && timesOverlap(curSt, curEt, other.start_time, other.end_time)) {
                batchConflictLabel = `Busy · Row ${other.idx + 1}`;
                break;
            }
        }

        const opt = document.createElement('div');
        opt.className = 'batch-faculty-option px-3 py-2 hover:bg-violet-50 dark:hover:bg-violet-900/30 cursor-pointer transition-colors flex items-center justify-between gap-2' + (batchConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
        opt.dataset.facultyId = f.id;
        opt.dataset.facultyName = f.full_name;
        opt.dataset.searchText = (f.full_name + ' ' + (f.department_code || '')).toLowerCase();
        opt.onclick = () => selectBatchFaculty(rowIdx, f.id, f.full_name);

        opt.innerHTML = `
            <div class="min-w-0 flex-1">
                <div class="text-[11px] font-medium text-gray-800 dark:text-gray-200 truncate">${escapeHtml(f.full_name)}</div>
                <div class="text-[10px] text-gray-400">${escapeHtml(f.department_code || '')} ${f.is_assigned ? '· Assigned' : ''} ${batchConflictLabel ? `<span class="text-red-500 font-medium">· ${escapeHtml(batchConflictLabel)}</span>` : ''}</div>
            </div>
            <span class="text-[9px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${batchConflictLabel ? 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400' : availColor}">
                ${batchConflictLabel ? '⚠' : ''} ${f.weekly_units}/${f.max_units}u
            </span>
        `;
        list.appendChild(opt);
    });
}

function toggleBatchFacultyDropdown(btn, rowIdx) {
    const dropdown = btn.closest('.batch-faculty-picker').querySelector('.batch-faculty-dropdown');
    if (!dropdown) return;

    closeAllDropdowns(dropdown);

    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        positionDropdown(btn, dropdown);
        _activeDropdown = dropdown;
        const search = dropdown.querySelector('.batch-faculty-search');
        if (search) { search.value = ''; search.focus(); }
        // Show all options
        dropdown.querySelectorAll('.batch-faculty-option').forEach(o => o.style.display = '');
    } else {
        dropdown.classList.add('hidden');
        _activeDropdown = null;
    }
}

function filterBatchFacultyDropdown(searchInput, rowIdx) {
    const term = searchInput.value.toLowerCase();
    const list = searchInput.closest('.batch-faculty-dropdown').querySelector('.batch-faculty-list');
    list.querySelectorAll('.batch-faculty-option').forEach(opt => {
        opt.style.display = opt.dataset.searchText.includes(term) ? '' : 'none';
    });
}

function selectBatchFaculty(rowIdx, facultyId, facultyName) {
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    row.querySelector('[data-field="faculty_id"]').value = facultyId;
    row.querySelector('[data-field="faculty_name"]').value = facultyName;

    const trigger = row.querySelector('.batch-faculty-trigger');
    trigger.querySelector('span').textContent = facultyName;
    trigger.classList.remove('border-amber-300', 'bg-amber-50', 'text-amber-600');
    trigger.classList.add('border-gray-200', 'bg-white', 'text-gray-700');

    const dropdown = row.querySelector('.batch-faculty-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    _activeDropdown = null;

    scheduleConflictCheck();
    validateAllRows();
    _refreshBatchCalendarIfVisible();
}

// ─── Room Dropdown ────────────────────────────────────────────────

async function toggleBatchRoomDropdown(btn, rowIdx) {
    const dropdown = btn.closest('.batch-room-picker').querySelector('.batch-room-dropdown');
    if (!dropdown) return;

    closeAllDropdowns(dropdown);

    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        positionDropdown(btn, dropdown);
        _activeDropdown = dropdown;
        const search = dropdown.querySelector('.batch-room-search');
        if (search) { search.value = ''; search.focus(); }
        // Load available rooms based on current row day/time
        await loadAvailableRoomsForRow(rowIdx);
    } else {
        dropdown.classList.add('hidden');
        _activeDropdown = null;
    }
}

async function loadAvailableRoomsForRow(rowIdx) {
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    const day = row.querySelector('[data-field="day_of_week"]').value;
    const startTime = row.querySelector('[data-field="start_time"]').value;
    const endTime = row.querySelector('[data-field="end_time"]').value;
    const scheduleType = row.querySelector('[data-field="schedule_type"]').value;
    const subjectId = row.dataset.subjectId || '';

    if (!day || !startTime || !endTime) return;

    const list = row.querySelector('.batch-room-list');
    list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">Loading rooms...</div>';

    try {
        const params = new URLSearchParams({ day, start_time: startTime, end_time: endTime, schedule_type: scheduleType });
        if (subjectId) params.set('subject_id', subjectId);
        if (_preferredBuildingId) params.set('building_id', _preferredBuildingId);
        const res = await fetch(`/schedule/batch-available-rooms?${params}`);
        const data = await res.json();

        renderRoomOptions(rowIdx, data.rooms || []);
    } catch (e) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-red-400">Failed to load rooms</div>';
    }
}

function renderRoomOptions(rowIdx, rooms) {
    const list = document.querySelector(`.batch-room-list[data-row="${rowIdx}"]`);
    if (!list) return;

    if (!rooms || rooms.length === 0) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">No available rooms</div>';
        return;
    }

    // Get current row's day/time for intra-batch comparison
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    const curDay = row?.querySelector('[data-field="day_of_week"]')?.value || '';
    const curSt = row?.querySelector('[data-field="start_time"]')?.value || '';
    const curEt = row?.querySelector('[data-field="end_time"]')?.value || '';
    const otherAssignments = getIntraBatchAssignments(rowIdx);

    list.innerHTML = '';
    rooms.forEach(r => {
        // Check if this room is used by another batch row at overlapping time
        let batchConflictLabel = '';
        for (const other of otherAssignments) {
            if (other.room_id == r.id && other.day === curDay && timesOverlap(curSt, curEt, other.start_time, other.end_time)) {
                batchConflictLabel = `Used by Row ${other.idx + 1} (${other.subject_code})`;
                break;
            }
        }

        const opt = document.createElement('div');
        opt.className = 'batch-room-option px-3 py-2 hover:bg-violet-50 dark:hover:bg-violet-900/30 cursor-pointer transition-colors' + (batchConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
        opt.dataset.roomId = r.id;
        opt.dataset.roomNumber = r.room_number;
        opt.dataset.buildingName = r.building_name || '';
        opt.dataset.searchText = (r.room_number + ' ' + (r.building_name || '')).toLowerCase();
        opt.onclick = () => selectBatchRoom(rowIdx, r.id, r.room_number, r.building_name || '');

        opt.innerHTML = `
            <div class="flex items-center justify-between gap-2">
                <div class="min-w-0">
                    <div class="text-[11px] font-medium text-gray-800 dark:text-gray-200">${escapeHtml(r.room_number)}</div>
                    <div class="text-[10px] text-gray-400">${escapeHtml(r.building_name || '')} · ${escapeHtml(r.room_type || '')}</div>
                </div>
                ${batchConflictLabel ? `<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 font-medium flex-shrink-0 whitespace-nowrap">${escapeHtml(batchConflictLabel)}</span>` : ''}
            </div>
        `;
        list.appendChild(opt);
    });
}

function filterBatchRoomDropdown(searchInput, rowIdx) {
    const term = searchInput.value.toLowerCase();
    const list = searchInput.closest('.batch-room-dropdown').querySelector('.batch-room-list');
    list.querySelectorAll('.batch-room-option').forEach(opt => {
        opt.style.display = opt.dataset.searchText.includes(term) ? '' : 'none';
    });
}

function selectBatchRoom(rowIdx, roomId, roomNumber, buildingName) {
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    row.querySelector('[data-field="room_id"]').value = roomId;
    row.querySelector('[data-field="room_name"]').value = roomNumber;
    row.querySelector('[data-field="building_name"]').value = buildingName;

    const trigger = row.querySelector('.batch-room-trigger span');
    trigger.textContent = roomNumber + (buildingName ? ' · ' + buildingName : '');

    const dropdown = row.querySelector('.batch-room-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    _activeDropdown = null;

    validateAllRows();
    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();
}

// ─── Inline Edit Handlers ─────────────────────────────────────────

function onTypeChange(select) {
    const row = select.closest('tr');
    const idx = parseInt(row.dataset.rowIndex);
    const scheduleType = select.value;
    const lecUnits = parseFloat(row.dataset.lecUnits) || 0;
    const labUnits = parseFloat(row.dataset.labUnits) || 0;

    // Recalculate duration based on type and subject composition
    let units = scheduleType === 'lab' ? labUnits : lecUnits;
    if (units <= 0) units = 1.5; // fallback
    const hasLec = lecUnits > 0;
    const hasLab = labUnits > 0;
    let durationMinutes;
    if (hasLec && hasLab) {
        // Subject has both LEC and LAB: 2 units = 3hrs, 1 unit = 2hrs
        durationMinutes = units >= 2 ? 180 : 120;
    } else if (hasLec && !hasLab && scheduleType === 'lecture') {
        // LEC-only subject: always 3hrs
        durationMinutes = 180;
    } else {
        durationMinutes = Math.max(60, Math.min(units * 60, scheduleType === 'lab' ? 240 : 180));
    }

    // Recalc end time
    const startInput = row.querySelector('[data-field="start_time"]');
    if (startInput.value) {
        recalcEndTime(row, startInput.value, durationMinutes);
    }

    // Update _batchData if available
    if (_batchData && _batchData.proposed[idx]) {
        _batchData.proposed[idx].schedule_type = scheduleType;
    }

    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();
}

function onStartTimeChange(input) {
    const row = input.closest('tr');
    const scheduleType = row.querySelector('[data-field="schedule_type"]').value;
    const lecUnits = parseFloat(row.dataset.lecUnits) || 0;
    const labUnits = parseFloat(row.dataset.labUnits) || 0;

    let units = scheduleType === 'lab' ? labUnits : lecUnits;
    if (units <= 0) units = 1.5;
    const hasLec = lecUnits > 0;
    const hasLab = labUnits > 0;
    let durationMinutes;
    if (hasLec && hasLab) {
        // Subject has both LEC and LAB: 2 units = 3hrs, 1 unit = 2hrs
        durationMinutes = units >= 2 ? 180 : 120;
    } else if (hasLec && !hasLab && scheduleType === 'lecture') {
        // LEC-only subject: always 3hrs
        durationMinutes = 180;
    } else {
        durationMinutes = Math.max(60, Math.min(units * 60, scheduleType === 'lab' ? 240 : 180));
    }

    recalcEndTime(row, input.value, durationMinutes);
    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();
}

function onEndTimeChange(input) {
    // End time manually changed — trigger conflict check
    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();
}

function onDayTimeChange(select) {
    // Room availability may have changed - clear room cache visual hint
    // The room dropdown reloads when opened, so no action needed here
    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();
}

function recalcEndTime(row, startTimeStr, durationMinutes) {
    if (!startTimeStr) return;
    const [h, m] = startTimeStr.split(':').map(Number);
    const totalMin = h * 60 + m + durationMinutes;
    const endH = Math.floor(totalMin / 60);
    const endM = totalMin % 60;
    if (endH < 24) {
        row.querySelector('[data-field="end_time"]').value =
            String(endH).padStart(2, '0') + ':' + String(endM).padStart(2, '0');
    }
}

// ─── Remove Row ───────────────────────────────────────────────────

function removeBatchRow(btn) {
    const row = btn.closest('tr');
    const idx = parseInt(row.dataset.rowIndex);

    if (_batchData && _batchData.proposed) {
        _batchData.proposed.splice(idx, 1);
        if (_batchData.stats) {
            _batchData.stats.scheduled = _batchData.proposed.length;
        }
        document.getElementById('autoStatScheduled').textContent = _batchData.proposed.length;
    }

    row.style.transition = 'opacity 0.2s, transform 0.2s';
    row.style.opacity = '0';
    row.style.transform = 'translateX(20px)';
    setTimeout(() => {
        row.remove();
        reindexRows();
        if (!document.querySelectorAll('#autoScheduleTableBody tr').length) {
            document.getElementById('autoScheduleFooter').classList.add('hidden');
        }
        validateAllRows();
        scheduleConflictCheck();
        _refreshBatchCalendarIfVisible();
    }, 200);
}

// Also support the old function name in case anything calls it
function removeAutoScheduleRow(btn) { removeBatchRow(btn); }

function reindexRows() {
    // Clear stale conflict state — will be repopulated by next check
    _batchConflicts = {};
    document.querySelectorAll('#autoScheduleTableBody tr').forEach((r, i) => {
        r.dataset.rowIndex = i;
        // Update row number
        const numSpan = r.querySelector('.batch-row-num');
        if (numSpan) numSpan.textContent = i + 1;
        // Update faculty/room picker data-row attributes
        r.querySelectorAll('[data-row]').forEach(el => el.dataset.row = i);
        // Update onclick handlers with new index
        const facBtn = r.querySelector('.batch-faculty-trigger');
        if (facBtn) facBtn.setAttribute('onclick', `toggleBatchFacultyDropdown(this, ${i})`);
        const facSearch = r.querySelector('.batch-faculty-search');
        if (facSearch) facSearch.setAttribute('oninput', `filterBatchFacultyDropdown(this, ${i})`);
        const roomBtn = r.querySelector('.batch-room-trigger');
        if (roomBtn) roomBtn.setAttribute('onclick', `toggleBatchRoomDropdown(this, ${i})`);
        const roomSearch = r.querySelector('.batch-room-search');
        if (roomSearch) roomSearch.setAttribute('oninput', `filterBatchRoomDropdown(this, ${i})`);
    });
}

// ─── Add Subject ──────────────────────────────────────────────────

async function openAddSubjectDropdown() {
    const panel = document.getElementById('batchAddSubjectPanel');
    panel.classList.remove('hidden');

    const select = document.getElementById('batchSubjectSelect');
    select.innerHTML = '<option value="">Loading subjects...</option>';

    try {
        let url = `/schedule/batch-unscheduled-subjects/${_batchSectionId}?include_all=true`;
        if (_batchCurriculumId) url += `&curriculum_id=${_batchCurriculumId}`;

        const res = await fetch(url);
        const data = await res.json();

        if (!data.success || !data.subjects || data.subjects.length === 0) {
            select.innerHTML = '<option value="">No more subjects available</option>';
            return;
        }

        _availableSubjects = data.subjects;

        const existingSubjects = new Set();
        document.querySelectorAll('#autoScheduleTableBody tr').forEach(row => {
            const subjectId = row.dataset.subjectId;
            const type = row.querySelector('[data-field="schedule_type"]').value;
            existingSubjects.add(subjectId + '_' + type);
        });

        select.innerHTML = '<option value="">Select a subject to add...</option>';

        _availableSubjects.forEach((s, i) => {
            const key = s.subject_id + '_' + s.schedule_type;
            if (!existingSubjects.has(key)) {
                const opt = document.createElement('option');
                opt.value = i;
                opt.textContent = `${s.subject_code} - ${s.course_description} (${s.schedule_type}, ${s.duration_minutes}min)`;
                select.appendChild(opt);
            }
        });

    } catch (e) {
        select.innerHTML = '<option value="">Failed to load subjects</option>';
    }
}

function closeAddSubjectDropdown() {
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');
}

function addSelectedSubject() {
    const select = document.getElementById('batchSubjectSelect');
    const selectedIdx = select.value;
    if (!selectedIdx && selectedIdx !== 0) {
        if (typeof showToast === 'function') showToast('Select a subject first', 'error');
        return;
    }

    const subject = _availableSubjects[parseInt(selectedIdx)];
    if (!subject) return;

    // Create a new proposed item with blank faculty and auto time
    const newItem = {
        subject_id: subject.subject_id,
        subject_code: subject.subject_code,
        course_description: subject.course_description || '',
        faculty_id: null,
        faculty_name: '',
        room_id: null,
        room_name: '',
        room_type: '',
        building_name: '',
        day_of_week: 'Monday',
        start_time: '08:00',
        end_time: calculateEndTimeStr('08:00', subject.duration_minutes),
        start_time_display: '',
        end_time_display: '',
        schedule_type: subject.schedule_type,
        score: 0,
        lec_units: subject.lec_units || 0,
        lab_units: subject.lab_units || 0,
        total_units: subject.total_units || 0
    };

    if (!_batchData) {
        _batchData = { proposed: [], unplaceable: [], section: { id: _batchSectionId }, stats: {} };
    }

    _batchData.proposed.push(newItem);
    const newIdx = _batchData.proposed.length - 1;

    const tbody = document.getElementById('autoScheduleTableBody');
    const row = buildBatchRow(newItem, newIdx);
    tbody.appendChild(row);
    if (window.TimePicker && typeof window.TimePicker.init === 'function') {
        window.TimePicker.init();
    }

    loadFacultyForRow(newIdx, subject.subject_id);

    // Update stats
    document.getElementById('autoStatScheduled').textContent = _batchData.proposed.length;

    // Remove from dropdown
    const opt = select.querySelector(`option[value="${selectedIdx}"]`);
    if (opt) opt.remove();
    select.value = '';

    // Show footer if hidden
    document.getElementById('autoScheduleFooter').classList.remove('hidden');
    document.getElementById('autoScheduleResults').classList.remove('hidden');
    document.getElementById('autoScheduleLoading').classList.add('hidden');

    validateAllRows();
    scheduleConflictCheck();
    _refreshBatchCalendarIfVisible();

    // Scroll to new row
    row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    row.classList.add('bg-violet-50', 'dark:bg-violet-900/20');
    setTimeout(() => row.classList.remove('bg-violet-50', 'dark:bg-violet-900/20'), 1500);

    closeAddSubjectDropdown();
}

function calculateEndTimeStr(startStr, durationMinutes) {
    const [h, m] = startStr.split(':').map(Number);
    const totalMin = h * 60 + m + durationMinutes;
    const endH = Math.floor(totalMin / 60);
    const endM = totalMin % 60;
    return String(endH).padStart(2, '0') + ':' + String(endM).padStart(2, '0');
}

// ─── Validation ───────────────────────────────────────────────────

function _normalizeName(str) {
    return String(str || '').replace(/\s+/g, ' ').trim().toLowerCase();
}

function _isPlaceholderFacultyLabel(str) {
    return _normalizeName(str) === 'assign faculty';
}

function _getFacultyCandidatesForRow(row) {
    if (!row) return [];

    const subjectId = row.dataset.subjectId;
    const cacheList = subjectId ? (_facultyCache[subjectId] || []) : [];
    const optionNodes = row.querySelectorAll('.batch-faculty-option');
    const optionList = Array.from(optionNodes).map(opt => ({
        id: parseInt(opt.dataset.facultyId),
        full_name: (opt.dataset.facultyName || '').trim()
    })).filter(f => !!f.id && !!f.full_name);

    const combined = [...(Array.isArray(cacheList) ? cacheList : []), ...optionList];
    const dedup = new Map();
    combined.forEach(f => {
        const id = parseInt(f.id);
        const fullName = String(f.full_name || '').trim();
        if (!id || !fullName) return;
        if (!dedup.has(id)) dedup.set(id, { id, full_name: fullName });
    });

    return Array.from(dedup.values());
}

function _getFacultyResolveReason(row) {
    const idInput = row?.querySelector('[data-field="faculty_id"]');
    const nameInput = row?.querySelector('[data-field="faculty_name"]');
    const triggerText = row?.querySelector('.batch-faculty-trigger span')?.textContent || '';

    const currentId = String(idInput?.value || '').trim();
    if (currentId && currentId !== 'null' && currentId !== 'undefined') return 'ok';

    const rawName = (nameInput?.value || triggerText || '').trim();
    if (!rawName || _isPlaceholderFacultyLabel(rawName)) return 'missing selection';

    const candidates = _getFacultyCandidatesForRow(row);
    if (candidates.length === 0) return 'no faculty candidates loaded';

    const target = _normalizeName(rawName);
    const exactMatches = candidates.filter(f => _normalizeName(f.full_name) === target);
    if (exactMatches.length > 1) return 'ambiguous faculty name';
    if (exactMatches.length === 0) return 'name does not match available faculty';
    return 'missing id sync';
}

function resolveFacultyIdForRow(row) {
    if (!row) return false;

    const idInput = row.querySelector('[data-field="faculty_id"]');
    const nameInput = row.querySelector('[data-field="faculty_name"]');
    if (!idInput) return false;

    const currentId = String(idInput.value || '').trim();
    if (currentId && currentId !== 'null' && currentId !== 'undefined') return true;

    const triggerText = row.querySelector('.batch-faculty-trigger span')?.textContent || '';
    const rawName = (nameInput?.value || triggerText || '').trim();
    if (!rawName || _isPlaceholderFacultyLabel(rawName)) return false;

    const list = _getFacultyCandidatesForRow(row);
    if (!Array.isArray(list) || list.length === 0) return false;

    const target = _normalizeName(rawName);
    const exactMatches = list.filter(f => _normalizeName(f.full_name) === target);
    if (exactMatches.length !== 1) return false;
    const match = exactMatches[0];

    idInput.value = String(match.id);
    if (nameInput) nameInput.value = match.full_name || rawName;
    return true;
}

function isFacultyAssignedForRow(row) {
    if (!row) return false;

    const idInput = row.querySelector('[data-field="faculty_id"]');
    const nameInput = row.querySelector('[data-field="faculty_name"]');
    const triggerText = row.querySelector('.batch-faculty-trigger span')?.textContent || '';

    const facultyId = String(idInput?.value || '').trim();
    if (facultyId && facultyId !== 'null' && facultyId !== 'undefined') return true;

    // If name is present but id is missing, attempt deterministic id reconciliation.
    if (resolveFacultyIdForRow(row)) return true;

    return false;
}

function reconcileFacultyAssignmentsBeforeSubmit() {
    const rows = document.querySelectorAll('#autoScheduleTableBody tr');
    const unresolved = [];

    rows.forEach((row, visualIdx) => {
        if (row.dataset.isExisting === 'true') return;

        const resolved = isFacultyAssignedForRow(row);
        const rowIndex = parseInt(row.dataset.rowIndex);
        if (!resolved) {
            const reason = _getFacultyResolveReason(row);
            unresolved.push({
                row: visualIdx + 1,
                rowIndex: Number.isInteger(rowIndex) ? rowIndex : visualIdx,
                reason,
                subjectCode: row.querySelector('td:first-child span')?.textContent?.trim() || `Row ${visualIdx + 1}`
            });
        }
    });

    return unresolved;
}

function validateAllRows() {
    const rows = document.querySelectorAll('#autoScheduleTableBody tr');
    let missingFaculty = 0;
    let missingRoom = 0;
    let invalidTime = 0;
    const facultyRowDetails = [];

    rows.forEach((row, idx) => {
        const hasFaculty = isFacultyAssignedForRow(row);
        const roomId = row.querySelector('[data-field="room_id"]')?.value;
        const startTime = row.querySelector('[data-field="start_time"]')?.value;
        const endTime = row.querySelector('[data-field="end_time"]')?.value;

        if (!hasFaculty) {
            missingFaculty++;
            facultyRowDetails.push(`R${idx + 1}: ${_getFacultyResolveReason(row)}`);
        }
        if (!roomId) missingRoom++;
        if (!startTime || !endTime || startTime >= endTime) invalidTime++;
    });

    const confirmBtn = document.getElementById('autoScheduleConfirmBtn');
    const msgEl = document.getElementById('batchValidationMsg');
    const msgText = document.getElementById('batchValidationText');

    if (rows.length === 0) {
        confirmBtn.disabled = true;
        msgEl.classList.add('hidden');
        updateFooterBanner('empty');
        return;
    }

    const formIssues = [];
    if (missingFaculty > 0) formIssues.push(`${missingFaculty} need faculty`);
    if (missingRoom > 0) formIssues.push(`${missingRoom} need room`);
    if (invalidTime > 0) formIssues.push(`${invalidTime} invalid time`);

    // Check conflict state — count rows with CRITICAL/HIGH conflicts
    let conflictRows = 0;
    Object.values(_batchConflicts).forEach(r => {
        if (r.status === 'conflict') conflictRows++;
    });

    const hasFormIssues = formIssues.length > 0;
    const hasConflicts = conflictRows > 0;

    if (hasFormIssues || hasConflicts) {
        confirmBtn.disabled = true;
        const allIssues = [...formIssues];
        if (hasConflicts) allIssues.push(`${conflictRows} conflict(s)`);
        if (facultyRowDetails.length > 0) {
            allIssues.push(facultyRowDetails.slice(0, 3).join(' · '));
        }
        msgText.textContent = allIssues.join(', ');
        msgEl.classList.remove('hidden');
    } else {
        confirmBtn.disabled = false;
        msgEl.classList.add('hidden');
    }
}

// ─── Confirm & Save ───────────────────────────────────────────────

async function confirmBatchSchedule() {
    const unresolvedFaculty = reconcileFacultyAssignmentsBeforeSubmit();
    if (unresolvedFaculty.length > 0) {
        unresolvedFaculty.forEach(entry => {
            const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${entry.rowIndex}"]`);
            if (row) {
                row.classList.add('bg-red-50');
                row.title = `Faculty unresolved: ${entry.reason}`;
            }
        });

        const preview = unresolvedFaculty
            .slice(0, 3)
            .map(e => `Row ${e.row} (${e.subjectCode}): ${e.reason}`)
            .join('; ');
        if (typeof showToast === 'function') {
            showToast(`Faculty assignment unresolved. ${preview}`, 'error');
        }
        validateAllRows();
        return;
    }

    const editedItems = collectBatchItems();

    if (!editedItems || editedItems.length === 0) {
        // Check if there are existing rows (already saved) — that's ok, nothing new to save
        const existingRows = document.querySelectorAll('#autoScheduleTableBody tr[data-is-existing="true"]');
        if (existingRows.length > 0) {
            if (typeof showToast === 'function') showToast('All schedules are already saved. Use + Add Subject to add new ones.', 'info');
        } else {
            if (typeof showToast === 'function') showToast('No schedules to save.', 'error');
        }
        return;
    }

    // Final form validation
    for (let i = 0; i < editedItems.length; i++) {
        const item = editedItems[i];
        if (!item.faculty_id) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Faculty is required.`, 'error');
            return;
        }
        if (!item.start_time || !item.end_time || item.start_time >= item.end_time) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Invalid time range.`, 'error');
            return;
        }
    }

    // Pre-save conflict check — if conflicts exist, block
    const conflictRows = Object.values(_batchConflicts).filter(r => r.status === 'conflict');
    if (conflictRows.length > 0) {
        if (typeof showToast === 'function') showToast(`${conflictRows.length} row(s) have conflicts. Resolve them before saving.`, 'error');
        return;
    }

    const confirmBtn = document.getElementById('autoScheduleConfirmBtn');
    const originalText = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `
        <svg class="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
        </svg>
        Saving...
    `;

    try {
        const response = await fetch('/schedule/batch-confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: _batchData.section.id,
                proposed: editedItems
            })
        });

        const result = await response.json();

        if (result.success) {
            // Check for partial errors
            const rowErrors = result.row_errors || [];
            if (rowErrors.length > 0) {
                const errorMsgs = rowErrors.map(e => `Row ${e.row} (${e.subject_code}): ${e.error}`).join('\n');
                if (typeof showToast === 'function') {
                    showToast(`Created ${result.created} schedule(s). ${rowErrors.length} row(s) had conflicts.`, 'error');
                }
                // Highlight error rows
                rowErrors.forEach(e => {
                    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${e.row - 1}"]`);
                    if (row) {
                        row.classList.add('bg-red-50');
                        row.title = e.error;
                    }
                });
                confirmBtn.disabled = false;
                confirmBtn.innerHTML = originalText;
                return;
            }

            // Clear batch state before redirect
            sessionStorage.removeItem(BATCH_STATE_KEY);

            closeBatchModal();
            _updateBatchStep(3);
            if (typeof showToast === 'function') {
                showToast(`Successfully created ${result.created} schedule(s)!`, 'success');
            }

            setTimeout(() => {
                if (window.UNIFIED_FORM_PAGE && _batchSectionId) {
                    window.location.href = '/schedule/class?section_id=' + (_batchData ? _batchData.section.id : _batchSectionId);
                } else {
                    window.location.reload();
                }
            }, 1200);
        } else {
            if (Array.isArray(result.row_errors) && result.row_errors.length > 0) {
                const first = result.row_errors[0];
                const prefix = first?.row ? `Row ${first.row}` : 'Row validation';
                if (typeof showToast === 'function') showToast(`${prefix}: ${first.error}`, 'error');
            } else {
                if (typeof showToast === 'function') showToast(result.error || 'Failed to save schedules', 'error');
            }
            confirmBtn.disabled = false;
            confirmBtn.innerHTML = originalText;
        }
    } catch (err) {
        if (typeof showToast === 'function') showToast('Network error: ' + err.message, 'error');
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalText;
    }
}

function collectBatchItems() {
    const rows = document.querySelectorAll('#autoScheduleTableBody tr');
    const items = [];

    rows.forEach((row, idx) => {
        // Skip rows that represent already-saved schedules
        if (row.dataset.isExisting === 'true') return;

        // Self-heal any row where faculty is visible but hidden id was not synced yet.
        resolveFacultyIdForRow(row);

        const original = (_batchData && _batchData.proposed && _batchData.proposed[idx]) || {};

        items.push({
            subject_id: parseInt(row.dataset.subjectId) || original.subject_id,
            subject_code: original.subject_code || '',
            course_description: original.course_description || '',
            schedule_type: row.querySelector('[data-field="schedule_type"]')?.value || 'lecture',
            faculty_id: parseInt(row.querySelector('[data-field="faculty_id"]')?.value) || null,
            faculty_name: row.querySelector('[data-field="faculty_name"]')?.value || '',
            room_id: parseInt(row.querySelector('[data-field="room_id"]')?.value) || null,
            room_name: row.querySelector('[data-field="room_name"]')?.value || '',
            building_name: row.querySelector('[data-field="building_name"]')?.value || '',
            day_of_week: row.querySelector('[data-field="day_of_week"]')?.value || 'Monday',
            start_time: row.querySelector('[data-field="start_time"]')?.value || '',
            end_time: row.querySelector('[data-field="end_time"]')?.value || '',
            lec_units: parseFloat(row.dataset.lecUnits) || 0,
            lab_units: parseFloat(row.dataset.labUnits) || 0,
        });
    });

    return items;
}

// ─── Conflict Detection Engine ────────────────────────────────────

/**
 * Schedule a debounced conflict check (800ms after last change)
 */
function scheduleConflictCheck() {
    if (!_batchModeActive) return;
    if (_conflictCheckTimer) clearTimeout(_conflictCheckTimer);

    // Show "checking" state in stats bar immediately
    showConflictCheckingState();

    _conflictCheckTimer = setTimeout(() => {
        performBatchConflictCheck();
    }, CONFLICT_CHECK_DEBOUNCE_MS);
}

/**
 * Perform the actual conflict check — POST all rows to the server
 */
async function performBatchConflictCheck() {
    if (!_batchModeActive || !_batchSectionId) return;

    const rows = document.querySelectorAll('#autoScheduleTableBody tr');
    if (rows.length === 0) {
        _batchConflicts = {};
        updateConflictSummary({ total: 0, ok: 0, conflicts: 0, warnings: 0 });
        updateFooterBanner('empty');
        return;
    }

    // Prevent duplicate in-flight requests
    if (_conflictCheckInFlight) return;
    _conflictCheckInFlight = true;

    // Collect current row data
    const rowData = [];
    rows.forEach((row, idx) => {
        const original = (_batchData && _batchData.proposed && _batchData.proposed[idx]) || {};
        const rowObj = {
            subject_id: parseInt(row.dataset.subjectId) || original.subject_id,
            subject_code: original.subject_code || '',
            faculty_id: row.querySelector('[data-field="faculty_id"]')?.value || null,
            room_id: row.querySelector('[data-field="room_id"]')?.value || null,
            day_of_week: row.querySelector('[data-field="day_of_week"]')?.value || '',
            start_time: row.querySelector('[data-field="start_time"]')?.value || '',
            end_time: row.querySelector('[data-field="end_time"]')?.value || '',
            schedule_type: row.querySelector('[data-field="schedule_type"]')?.value || 'lecture',
        };
        // Include schedule_id for existing rows so backend can exclude self-conflicts
        if (original.schedule_id) rowObj.schedule_id = original.schedule_id;
        rowData.push(rowObj);
    });

    try {
        const response = await fetch('/schedule/batch-check-conflicts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: _batchSectionId,
                rows: rowData
            })
        });

        const data = await response.json();
        _conflictCheckInFlight = false;

        if (!data.success) {
            console.error('[BATCH-CHECK] Server error:', data.error);
            hideConflictCheckingState();
            return;
        }

        // Update conflict state
        _batchConflicts = {};
        (data.rows || []).forEach(r => {
            _batchConflicts[r.index] = { status: r.status, conflicts: r.conflicts || [] };
        });

        // Render per-row status
        const allRows = document.querySelectorAll('#autoScheduleTableBody tr');
        allRows.forEach((row, idx) => {
            const result = _batchConflicts[idx] || { status: 'ok', conflicts: [] };
            renderRowConflictStatus(row, idx, result);
        });

        // Update summary badges and footer
        updateConflictSummary(data.summary || { total: 0, ok: 0, conflicts: 0, warnings: 0 });
        validateAllRows(); // Re-run to merge form validation + conflict state

    } catch (err) {
        _conflictCheckInFlight = false;
        console.error('[BATCH-CHECK] Network error:', err);
        hideConflictCheckingState();
        // Allow save on network error — don't block user
    }
}

/**
 * Render the status icon and border color for a single row
 */
function renderRowConflictStatus(row, idx, result) {
    const statusCell = row.querySelector('.batch-status-icon');
    if (!statusCell) return;

    // Remove old border classes
    row.classList.remove('border-l-[3px]', 'border-l-gray-200', 'dark:border-l-gray-600', 'border-l-green-400', 'border-l-red-400', 'border-l-amber-400');
    row.classList.remove('bg-red-50/50', 'bg-amber-50/50');
    
    // Always keep the 3px thickness for status
    row.classList.add('border-l-[3px]');

    if (result.status === 'conflict') {
        // CRITICAL/HIGH — red
        row.classList.add('border-l-red-400', 'bg-red-50/50');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-red-100 flex items-center justify-center hover:bg-red-200 transition-colors cursor-pointer" title="${count} conflict(s) — click for details">
                <svg class="w-3 h-3 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </button>`;
    } else if (result.status === 'warning') {
        // MEDIUM/LOW — amber
        row.classList.add('border-l-amber-400', 'bg-amber-50/50');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-amber-100 flex items-center justify-center hover:bg-amber-200 transition-colors cursor-pointer" title="${count} warning(s) — click for details">
                <svg class="w-3 h-3 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </button>`;
    } else {
        // OK — green
        row.classList.add('border-l-green-400');
        statusCell.innerHTML = `
            <div class="w-5 h-5 rounded-full bg-emerald-100 flex items-center justify-center" title="No conflicts">
                <svg class="w-3 h-3 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            </div>`;
    }
}

/**
 * Show a popover/toast listing all conflicts for a specific row
 */
function showRowConflictTooltip(rowIdx) {
    const result = _batchConflicts[rowIdx];
    if (!result || !result.conflicts || result.conflicts.length === 0) return;

    // Close any existing tooltip
    const existing = document.getElementById('batchConflictTooltip');
    if (existing) existing.remove();

    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    const rect = row.getBoundingClientRect();
    const tooltip = document.createElement('div');
    tooltip.id = 'batchConflictTooltip';
    tooltip.className = 'fixed z-[10000] bg-white border border-gray-200 rounded-xl shadow-2xl p-3 max-w-sm w-80';
    tooltip.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - 340)) + 'px';

    // Position below row if space, else above
    const spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 200) {
        tooltip.style.top = (rect.bottom + 4) + 'px';
    } else {
        tooltip.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
    }

    const conflictHtml = result.conflicts.map(c => {
        const isError = c.severity === 'critical' || c.severity === 'high';
        const borderColor = isError ? 'border-red-200 bg-red-50' : 'border-amber-200 bg-amber-50';
        const textColor = isError ? 'text-red-700' : 'text-amber-700';
        const iconColor = isError ? 'text-red-500' : 'text-amber-500';
        const icon = isError
            ? '<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
            : '<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';

        const label = c.type.replace('_batch', ' (batch)').replace('_', ' ');
        return `
            <div class="flex items-start gap-2 p-2 ${borderColor} rounded-lg border">
                <span class="${iconColor} mt-0.5">${icon}</span>
                <div class="min-w-0">
                    <span class="text-[10px] font-semibold uppercase ${textColor}">${escapeHtml(label)}</span>
                    <p class="text-[11px] ${textColor} mt-0.5">${escapeHtml(c.message)}</p>
                </div>
            </div>`;
    }).join('');

    const rowLabel = row.dataset.subjectId ? ((_batchData?.proposed?.[rowIdx]?.subject_code) || `Row ${rowIdx + 1}`) : `Row ${rowIdx + 1}`;

    tooltip.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-bold text-gray-800">Row ${rowIdx + 1} · ${escapeHtml(rowLabel)}</h4>
            <button onclick="document.getElementById('batchConflictTooltip')?.remove()" class="p-0.5 rounded hover:bg-gray-100 text-gray-400 hover:text-gray-600">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
        </div>
        <div class="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">${conflictHtml}</div>
    `;

    document.body.appendChild(tooltip);

    // Auto-close on outside click
    const closeHandler = (e) => {
        if (!tooltip.contains(e.target) && !row.contains(e.target)) {
            tooltip.remove();
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 100);
}

/**
 * Update the stats bar conflict/warning badges and footer banner
 */
function updateConflictSummary(summary) {
    const conflictBadge = document.getElementById('batchConflictBadge');
    const warningBadge = document.getElementById('batchWarningBadge');
    const allClearBadge = document.getElementById('batchAllClearBadge');
    const checkingBadge = document.getElementById('batchCheckingBadge');
    const conflictCount = document.getElementById('batchConflictCount');
    const warningCount = document.getElementById('batchWarningCount');

    // Hide checking badge
    if (checkingBadge) checkingBadge.classList.add('hidden');

    if (summary.total === 0) {
        if (conflictBadge) conflictBadge.classList.add('hidden');
        if (warningBadge) warningBadge.classList.add('hidden');
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateFooterBanner('empty');
        return;
    }

    // Conflicts badge
    if (summary.conflicts > 0) {
        if (conflictCount) conflictCount.textContent = summary.conflicts;
        if (conflictBadge) conflictBadge.classList.remove('hidden');
    } else {
        if (conflictBadge) conflictBadge.classList.add('hidden');
    }

    // Warnings badge
    if (summary.warnings > 0) {
        if (warningCount) warningCount.textContent = summary.warnings;
        if (warningBadge) warningBadge.classList.remove('hidden');
    } else {
        if (warningBadge) warningBadge.classList.add('hidden');
    }

    // All clear badge
    if (summary.conflicts === 0 && summary.warnings === 0 && summary.ok > 0) {
        if (allClearBadge) allClearBadge.classList.remove('hidden');
        updateFooterBanner('ok');
    } else if (summary.conflicts > 0) {
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateFooterBanner('conflict', summary.conflicts);
    } else if (summary.warnings > 0) {
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateFooterBanner('warning', summary.warnings);
    }
}

/**
 * Show "Checking..." state in the stats bar
 */
function showConflictCheckingState() {
    const checkingBadge = document.getElementById('batchCheckingBadge');
    const allClearBadge = document.getElementById('batchAllClearBadge');
    if (checkingBadge) checkingBadge.classList.remove('hidden');
    if (allClearBadge) allClearBadge.classList.add('hidden');
}

function hideConflictCheckingState() {
    const checkingBadge = document.getElementById('batchCheckingBadge');
    if (checkingBadge) checkingBadge.classList.add('hidden');
}

/**
 * Update the footer banner with conflict/ok/warning status
 */
function updateFooterBanner(status, count) {
    const banner = document.getElementById('batchFooterBanner');
    const icon = document.getElementById('batchFooterBannerIcon');
    const text = document.getElementById('batchFooterBannerText');
    if (!banner || !icon || !text) return;

    // Reset classes
    banner.className = 'px-4 sm:px-5 py-1.5 text-[11px] font-medium flex items-center gap-2 border-b border-gray-100 dark:border-gray-700';

    if (status === 'conflict') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-red-50', 'text-red-700');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>';
        text.textContent = `${count} row(s) have conflicts — resolve before saving`;
    } else if (status === 'warning') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-amber-50', 'text-amber-700');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        text.textContent = `${count} row(s) have warnings — review recommended`;
    } else if (status === 'ok') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-emerald-50', 'text-emerald-700');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
        text.textContent = 'All schedules look good!';
    } else {
        banner.classList.add('hidden');
    }
}

// ─── Intra-batch Room/Faculty Awareness ───────────────────────────

/**
 * Get other batch rows' room/faculty assignments for intra-batch hints
 */
function getIntraBatchAssignments(excludeRowIdx) {
    const rows = document.querySelectorAll('#autoScheduleTableBody tr');
    const assignments = [];
    rows.forEach((row, idx) => {
        if (idx === excludeRowIdx) return;
        const day = row.querySelector('[data-field="day_of_week"]')?.value || '';
        const st = row.querySelector('[data-field="start_time"]')?.value || '';
        const et = row.querySelector('[data-field="end_time"]')?.value || '';
        const fid = row.querySelector('[data-field="faculty_id"]')?.value || '';
        const rid = row.querySelector('[data-field="room_id"]')?.value || '';
        const subjectCode = _batchData?.proposed?.[idx]?.subject_code || `Row ${idx + 1}`;
        if (day && st && et) {
            assignments.push({ idx, day, start_time: st, end_time: et, faculty_id: fid, room_id: rid, subject_code: subjectCode });
        }
    });
    return assignments;
}

/**
 * Check if two time strings overlap
 */
function timesOverlap(s1, e1, s2, e2) {
    return s1 < e2 && e1 > s2;
}

// ─── Dropdown Positioning Helper ──────────────────────────────────

function positionDropdown(triggerBtn, dropdown) {
    const rect = triggerBtn.getBoundingClientRect();
    const dropdownHeight = dropdown.offsetHeight || 240;
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;

    // Position horizontally aligned with the button
    dropdown.style.left = rect.left + 'px';

    // Open below if enough space, otherwise above
    if (spaceBelow >= dropdownHeight + 8 || spaceBelow >= spaceAbove) {
        dropdown.style.top = (rect.bottom + 4) + 'px';
        dropdown.style.bottom = 'auto';
    } else {
        dropdown.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
        dropdown.style.top = 'auto';
    }
}

// ─── Close Dropdowns on Outside Click ─────────────────────────────

function closeAllDropdowns(except) {
    document.querySelectorAll('.batch-faculty-dropdown, .batch-room-dropdown').forEach(dd => {
        if (dd !== except) {
            dd.classList.add('hidden');
            dd.style.top = '';
            dd.style.left = '';
            dd.style.bottom = '';
        }
    });
    if (except && _activeDropdown !== except) _activeDropdown = null;
}

document.addEventListener('click', function(e) {
    if (!_activeDropdown) return;
    if (!_activeDropdown.contains(e.target) && !e.target.closest('.batch-faculty-trigger') && !e.target.closest('.batch-room-trigger')) {
        _activeDropdown.classList.add('hidden');
        _activeDropdown = null;
    }
});

// ─── Utilities ────────────────────────────────────────────────────

function showBatchError(message) {
    document.getElementById('autoScheduleErrorMsg').textContent = message;
    document.getElementById('autoScheduleError').classList.remove('hidden');
}

// Keep old name too
function showAutoScheduleError(msg) { showBatchError(msg); }

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// Legacy compatibility
function confirmAutoSchedule() { confirmBatchSchedule(); }
function collectEditedProposedItems() { return collectBatchItems(); }
