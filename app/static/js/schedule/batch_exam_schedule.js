/**
 * Batch Exam Schedule Builder - JavaScript Controller
 * Auto-spreads exams across exam period dates with editable rows.
 * Proctor fields start blank for manual selection.
 * Includes real-time conflict detection per row.
 */

// ─── State ────────────────────────────────────────────────────────
let _examBatchData = null;           // Full response from backend
let _examBatchSectionId = null;      // Current section ID
let _examBatchCurriculumId = null;   // Selected curriculum ID
let _examBatchModeActive = false;    // Whether inline batch panel is visible
let _examFacultyCache = {};          // Cache faculty lists per subject_id
let _examAvailableSubjects = null;   // Unscheduled subjects for "Add Subject"
let _examActiveDropdown = null;      // Currently open dropdown element

// ─── Conflict Detection State ─────────────────────────────────────
let _examBatchConflicts = {};        // Map of rowIndex → { status, conflicts[] }
let _examConflictCheckTimer = null;  // Debounce timer
let _examConflictCheckInFlight = false;
const EXAM_CONFLICT_CHECK_DEBOUNCE_MS = 800;
const EXAM_BATCH_STATE_KEY = 'ischedwise_batch_mode';

function syncExamBatchCalendarAlignment() {
    if (typeof queueWeekCalendarHeaderAlignmentSync === 'function') {
        queueWeekCalendarHeaderAlignmentSync();
        return;
    }

    document.querySelectorAll('.week-calendar-container').forEach(container => {
        const calendarBody = container.querySelector('.week-calendar-body');
        if (!calendarBody) {
            return;
        }

        const scrollbarOffset = Math.max(0, calendarBody.offsetWidth - calendarBody.clientWidth);
        container.style.setProperty('--week-calendar-scrollbar-offset', `${scrollbarOffset}px`);
    });
}

async function parseExamBatchApiJson(response, fallbackMessage) {
    const contentType = (response.headers.get('content-type') || '').toLowerCase();

    if (!response.ok) {
        if (contentType.includes('application/json')) {
            const payload = await response.json();
            throw new Error(payload.error || payload.message || `Request failed (${response.status})`);
        }

        const text = await response.text();
        throw new Error((text || '').slice(0, 120).trim() || fallbackMessage || `Request failed (${response.status})`);
    }

    if (!contentType.includes('application/json')) {
        const text = await response.text();
        throw new Error((text || '').slice(0, 120).trim() || fallbackMessage || 'Invalid server response');
    }

    return response.json();
}

// ─── Settings (populated from window globals) ─────────────────────
function _examPeriodStart() { return window.examPeriodStart || ''; }
function _examPeriodEnd() { return window.examPeriodEnd || ''; }
function _examDurationLimit() { return window.examDurationLimit || 120; }
function _examStartHour() { return window.examStartHour || 7; }
function _examEndHour() { return window.examEndHour || 17; }
function _examStartTime() {
    if (window.examStartTime) return window.examStartTime;
    return String(_examStartHour()).padStart(2, '0') + ':00';
}

// ─── Step Indicator & Progress Bar Helpers ────────────────────────

function _updateExamBatchStep(activeStep) {
    const steps = document.querySelectorAll('#examBatchStepIndicator .exam-batch-step');
    const lines = document.querySelectorAll('#examBatchStepIndicator .exam-batch-step-line');
    steps.forEach(s => {
        const step = parseInt(s.dataset.step);
        const dot = s.querySelector('.exam-batch-step-dot');
        const label = s.querySelector('.exam-batch-step-label');
        if (step < activeStep) {
            dot.className = 'exam-batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-orange-600 text-white shadow-sm ring-2 ring-orange-200 dark:ring-orange-800';
            dot.innerHTML = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>';
            if (label) { label.className = 'exam-batch-step-label text-[11px] font-semibold text-orange-700 dark:text-orange-300 hidden sm:inline'; }
        } else if (step === activeStep) {
            dot.className = 'exam-batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-orange-600 text-white shadow-sm ring-2 ring-orange-200 dark:ring-orange-800';
            dot.textContent = step;
            if (label) { label.className = 'exam-batch-step-label text-[11px] font-semibold text-orange-700 dark:text-orange-300 hidden sm:inline'; }
        } else {
            dot.className = 'exam-batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-gray-200 text-gray-400 dark:bg-gray-600 dark:text-gray-500';
            dot.textContent = step;
            if (label) { label.className = 'exam-batch-step-label text-[11px] font-medium text-gray-400 dark:text-gray-500 hidden sm:inline'; }
        }
    });
    lines.forEach((line, i) => {
        line.className = 'exam-batch-step-line w-10 sm:w-16 h-0.5 mx-2 rounded-full transition-all duration-500 ' + ((i + 1 < activeStep) ? 'bg-orange-400 dark:bg-orange-500' : 'bg-gray-200 dark:bg-gray-600');
    });
}

function _updateExamBatchProgressBar() {
    const stats = _examBatchData?.stats;
    if (!stats) return;
    const total = stats.total_subjects || 1;
    const placed = stats.scheduled || 0;
    const existing = stats.already_examined || stats.already_scheduled || 0;
    const unplaceable = stats.unplaceable || 0;
    const el = (id) => document.getElementById(id);
    if (el('examBatchProgressPlaced')) el('examBatchProgressPlaced').style.width = ((placed / total) * 100).toFixed(1) + '%';
    if (el('examBatchProgressExisting')) el('examBatchProgressExisting').style.width = ((existing / total) * 100).toFixed(1) + '%';
    if (el('examBatchProgressUnplaceable')) el('examBatchProgressUnplaceable').style.width = ((unplaceable / total) * 100).toFixed(1) + '%';
}

// ─── Enter / Exit Exam Batch Mode ─────────────────────────────────

function enterExamBatchMode() {
    const panel = document.getElementById('examBatchBuilderPanel');
    if (!panel) return;

    const sectionId = window.EXAM_BATCH_SECTION_ID;
    const sectionName = window.EXAM_BATCH_SECTION_NAME || '';
    if (!sectionId) {
        if (typeof showToast === 'function') showToast('Select a section first', 'error');
        return;
    }

    _examBatchData = null;
    _examBatchSectionId = sectionId;
    _examBatchCurriculumId = null;
    _examBatchModeActive = true;
    _examFacultyCache = {};
    _examAvailableSubjects = null;
    _examBatchConflicts = {};
    _examPreferredBuildingId = null;
    _examConflictCheckInFlight = false;
    if (_examConflictCheckTimer) { clearTimeout(_examConflictCheckTimer); _examConflictCheckTimer = null; }

    // Reset batch panel UI — show curriculum step first
    document.getElementById('examBatchSectionName').textContent = 'Section: ' + sectionName;
    document.getElementById('examBatchCurriculumStep').classList.remove('hidden');
    document.getElementById('examBatchLoading').classList.add('hidden');
    document.getElementById('examBatchError').classList.add('hidden');
    document.getElementById('examBatchAllDone').classList.add('hidden');
    document.getElementById('examBatchResults').classList.add('hidden');
    document.getElementById('examBatchStats').classList.add('hidden');
    document.getElementById('examBatchFooter').classList.add('hidden');
    document.getElementById('examBatchAddSubjectPanel').classList.add('hidden');
    document.getElementById('examBatchAddSubjectBtn').classList.add('hidden');
    document.getElementById('examBatchInlineViewToggle')?.classList.add('hidden');

    // Hide the exam form panel and show the batch builder panel
    const examFormPanel = document.getElementById('examFormPanel');
    if (examFormPanel) examFormPanel.classList.add('hidden');
    panel.classList.remove('hidden');
    panel.style.display = 'flex';

    // Update header buttons (match class batch pattern)
    const autoGenExamBtn = document.getElementById('autoGenExamBtn');
    const autoGenBtn = document.getElementById('autoGenBtn');
    const examSubmit = document.getElementById('submitExamScheduleAdd');
    const classSubmit = document.getElementById('submitScheduleBtn');
    const examBatchBackBtn = document.getElementById('examBatchBackBtn');
    const batchBackBtn = document.getElementById('batchBackBtn');
    const backLink = document.getElementById('unifiedBackLink');
    const tabSwitcher = document.getElementById('tabBtnClass')?.closest('.bg-gray-100');

    if (autoGenExamBtn) autoGenExamBtn.style.display = 'none';
    if (autoGenBtn) autoGenBtn.style.display = 'none';
    if (examSubmit) examSubmit.style.display = 'none';
    if (classSubmit) classSubmit.style.display = 'none';
    if (examBatchBackBtn) examBatchBackBtn.classList.remove('hidden');
    if (batchBackBtn) batchBackBtn.classList.add('hidden');
    if (backLink) backLink.classList.add('hidden');
    if (tabSwitcher) tabSwitcher.style.display = 'none';

    // Update page title
    const pageTitle = document.getElementById('unifiedPageTitle');
    if (pageTitle) {
        pageTitle._examOriginalText = pageTitle.textContent;
        pageTitle.textContent = 'Batch Exam Schedule';
    }
    // Swap header icon to exam batch palette (dark-mode aware)
    const iconAdd = document.getElementById('unifiedIconAdd');
    const iconEdit = document.getElementById('unifiedIconEdit');
    if (iconAdd) {
        if (iconAdd._examOriginalClass === undefined) iconAdd._examOriginalClass = iconAdd.className;
        if (iconAdd._examOriginalHidden === undefined) iconAdd._examOriginalHidden = iconAdd.classList.contains('hidden');
        const iconSvg = iconAdd.querySelector('svg');
        if (iconSvg && iconSvg._examOriginalClass === undefined) iconSvg._examOriginalClass = iconSvg.className.baseVal || iconSvg.className;

        iconAdd.classList.remove('hidden', 'bg-emerald-100', 'dark:bg-emerald-900/30', 'bg-blue-100', 'dark:bg-blue-900/30', 'bg-violet-100', 'dark:bg-violet-900/30');
        iconAdd.classList.add('bg-orange-100', 'dark:bg-orange-900/30');
        if (iconSvg) {
            iconSvg.classList.remove('text-emerald-600', 'dark:text-emerald-400', 'text-blue-600', 'dark:text-blue-400', 'text-violet-600', 'dark:text-violet-300');
            iconSvg.classList.add('text-orange-600', 'dark:text-orange-300');
        }
    }
    if (iconEdit) {
        if (iconEdit._examOriginalHidden === undefined) iconEdit._examOriginalHidden = iconEdit.classList.contains('hidden');
        iconEdit.classList.add('hidden');
    }

    // Load curricula for selection step
    loadExamBatchCurricula(sectionId);

    // Load buildings for preferred building dropdown
    loadExamBuildingsForBatch();

    // Reset calendar view state
    _examBatchCurrentView = 'table';

    // Hide docked assistant while in batch mode
    if (typeof applyAIAssistantBatchLock === 'function') {
        applyAIAssistantBatchLock(true, 'exam');
    } else if (typeof setAIAssistantDockVisible === 'function') {
        setAIAssistantDockVisible(false);
    } else {
        const aiBadge = document.getElementById('aiBadge');
        if (aiBadge) { aiBadge.classList.add('hidden'); aiBadge.classList.remove('flex'); }
        if (typeof closeAIDrawer === 'function') closeAIDrawer();
    }

    // Persist batch mode so a page refresh stays in batch
    sessionStorage.setItem(EXAM_BATCH_STATE_KEY, 'exam');

    // Activate step 1 indicator
    _updateExamBatchStep(1);
}

function exitExamBatchMode(silent) {
    // Clear persisted batch mode state
    sessionStorage.removeItem(EXAM_BATCH_STATE_KEY);

    _examBatchModeActive = false;
    _examBatchData = null;
    _examBatchSectionId = null;
    _examBatchCurriculumId = null;
    _examActiveDropdown = null;
    _examBatchConflicts = {};
    _examPreferredBuildingId = null;
    _examConflictCheckInFlight = false;
    if (_examConflictCheckTimer) { clearTimeout(_examConflictCheckTimer); _examConflictCheckTimer = null; }

    // Remove any open tooltip
    const tooltip = document.getElementById('examBatchConflictTooltip');
    if (tooltip) tooltip.remove();

    const panel = document.getElementById('examBatchBuilderPanel');
    const examFormPanel = document.getElementById('examFormPanel');

    if (panel) {
        panel.classList.add('hidden');
        panel.style.display = '';
    }
    if (examFormPanel) examFormPanel.classList.remove('hidden');

    // Restore header buttons
    const autoGenExamBtn = document.getElementById('autoGenExamBtn');
    const examSubmit = document.getElementById('submitExamScheduleAdd');
    const examBatchBackBtn = document.getElementById('examBatchBackBtn');
    const backLink = document.getElementById('unifiedBackLink');
    const tabSwitcher = document.getElementById('tabBtnClass')?.closest('.bg-gray-100');

    if (autoGenExamBtn && window.FORM_SECTION_ID) autoGenExamBtn.style.display = 'flex';
    if (examSubmit) examSubmit.style.display = 'flex';
    if (examBatchBackBtn) examBatchBackBtn.classList.add('hidden');
    if (backLink) backLink.classList.remove('hidden');
    if (tabSwitcher) tabSwitcher.style.display = '';

    // Restore page title
    const pageTitle = document.getElementById('unifiedPageTitle');
    if (pageTitle && pageTitle._examOriginalText) {
        pageTitle.textContent = pageTitle._examOriginalText;
    }
    // Restore icon state
    const iconAdd = document.getElementById('unifiedIconAdd');
    const iconEdit = document.getElementById('unifiedIconEdit');
    if (iconAdd && iconAdd._examOriginalClass !== undefined) {
        iconAdd.className = iconAdd._examOriginalClass;
        if (iconAdd._examOriginalHidden) iconAdd.classList.add('hidden');
        else iconAdd.classList.remove('hidden');
        const iconSvg = iconAdd.querySelector('svg');
        if (iconSvg && iconSvg._examOriginalClass !== undefined) {
            iconSvg.setAttribute('class', iconSvg._examOriginalClass);
        }
    }
    if (iconEdit && iconEdit._examOriginalHidden !== undefined) {
        if (iconEdit._examOriginalHidden) iconEdit.classList.add('hidden');
        else iconEdit.classList.remove('hidden');
    }

    // Restore docked assistant
    if (typeof applyAIAssistantBatchLock === 'function') {
        applyAIAssistantBatchLock(false, 'exam');
    } else if (typeof setAIAssistantDockVisible === 'function') {
        setAIAssistantDockVisible(true);
    } else {
        const aiBadge = document.getElementById('aiBadge');
        if (aiBadge) { aiBadge.classList.remove('hidden'); aiBadge.classList.add('flex'); }
    }
}

// ─── Curriculum Selection Step ──────────────────────────────────────

async function loadExamBatchCurricula(sectionId) {
    const select = document.getElementById('examBatchCurriculumSelect');
    const btn = document.getElementById('examBatchCurriculumConfirmBtn');
    if (!select) return;

    select.innerHTML = '<option value="">Loading curricula...</option>';
    if (btn) btn.disabled = true;

    try {
        const res = await fetch(`/schedule/get-curricula/${sectionId}`);
        const data = await parseExamBatchApiJson(res, 'Unable to load curricula');
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

        // Auto-select and proceed if only one curriculum
        if (curricula.length === 1) {
            select.value = curricula[0].id;
            if (btn) btn.disabled = false;
            confirmExamBatchCurriculum();
            return;
        }

        select.onchange = function() {
            if (btn) btn.disabled = !this.value;
        };
    } catch (e) {
        console.error('[EXAM BATCH] Failed to load curricula:', e);
        select.innerHTML = '<option value="">Error loading curricula</option>';
        if (typeof showToast === 'function') {
            showToast(e.message || 'Error loading curricula', 'error');
        }
    }
}

function confirmExamBatchCurriculum() {
    const select = document.getElementById('examBatchCurriculumSelect');
    const curriculumId = select ? select.value : null;
    if (!curriculumId || !_examBatchSectionId) return;

    _examBatchCurriculumId = parseInt(curriculumId);

    document.getElementById('examBatchCurriculumStep').classList.add('hidden');
    document.getElementById('examBatchLoading').classList.remove('hidden');

    generateExamBatchPreview(_examBatchSectionId);
}

// ─── API: Generate Preview ────────────────────────────────────────

async function generateExamBatchPreview(sectionId) {
    try {
        const body = { section_id: sectionId };
        if (_examBatchCurriculumId) body.curriculum_id = _examBatchCurriculumId;
        if (_examPreferredBuildingId) body.preferred_building_id = _examPreferredBuildingId;

        const response = await fetch('/exam-schedule/batch-generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await response.json();

        document.getElementById('examBatchLoading').classList.add('hidden');

        if (!data.success) {
            showExamBatchError(data.error || 'Unknown error');
            return;
        }

        if (data.proposed.length === 0 && (!data.unplaceable || data.unplaceable.length === 0)) {
            // If backend returned existing exams, render them as editable rows
            if (data.existing && data.existing.length > 0) {
                data.proposed = data.existing.map(item => ({ ...item, is_existing: true }));
                data.stats = data.stats || {};
                data.stats.scheduled = data.stats.scheduled || 0;
                data.stats.already_examined = data.stats.already_examined || data.existing.length;
                _examBatchData = data;
                renderExamBatchResults(data);
                // Mark existing rows with green border
                const rows = document.querySelectorAll('#examBatchTableBody tr');
                rows.forEach(row => {
                    row.dataset.isExisting = 'true';
                });
                // Show info banner
                document.getElementById('examBatchAllDone').classList.remove('hidden');
                return;
            }
            document.getElementById('examBatchAllDone').classList.remove('hidden');
            return;
        }

        _examBatchData = data;
        renderExamBatchResults(data);

    } catch (err) {
        document.getElementById('examBatchLoading').classList.add('hidden');
        showExamBatchError(err.message || 'Network error');
    }
}

// ─── Render Results ───────────────────────────────────────────────

function renderExamBatchResults(data) {
    const stats = data.stats || {};

    // Step indicator & progress bar
    _updateExamBatchStep(2);
    _updateExamBatchProgressBar();

    // Stats
    const total = stats.total_subjects || 0;
    const scheduled = stats.scheduled || 0;
    const existing = stats.already_examined || stats.already_scheduled || 0;
    const unplaceable = stats.unplaceable || 0;
    const ready = scheduled + existing;
    const needAttention = total - ready;

    document.getElementById('examBatchStatTotal').textContent = total;
    document.getElementById('examBatchStatScheduled').textContent = scheduled;
    document.getElementById('examBatchStatExisting').textContent = existing;
    document.getElementById('examBatchStats').classList.remove('hidden');

    // Plain-English summary line
    const summaryEl = document.getElementById('examBatchSummaryLine');
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

    // Show Add Subject button
    const addSubBtn = document.getElementById('examBatchAddSubjectBtn');
    if (addSubBtn) addSubBtn.classList.remove('hidden');
    document.getElementById('examBatchInlineViewToggle')?.classList.remove('hidden');

    if (unplaceable > 0) {
        document.getElementById('examBatchStatUnplaceable').textContent = unplaceable;
        document.getElementById('examBatchStatUnplaceableWrap').classList.remove('hidden');
    } else {
        document.getElementById('examBatchStatUnplaceableWrap').classList.add('hidden');
    }

    // Proposed table
    const tbody = document.getElementById('examBatchTableBody');
    tbody.innerHTML = '';

    if (data.proposed && data.proposed.length > 0) {
        data.proposed.forEach((item, idx) => {
            const row = buildExamBatchRow(item, idx);
            tbody.appendChild(row);
            // Pre-load faculty/proctor list for this subject
            loadExamFacultyForRow(idx, item.subject_id);
        });
        if (window.TimePicker && typeof window.TimePicker.init === 'function') {
            window.TimePicker.init();
        }
    }

    // Unplaceable
    renderExamUnplaceableItems(data.unplaceable);

    // Show results & footer
    document.getElementById('examBatchResults').classList.remove('hidden');
    if (data.proposed && data.proposed.length > 0) {
        document.getElementById('examBatchFooter').classList.remove('hidden');
    }

    examValidateAllRows();

    // Initial conflict check with delay for async proctor list rendering
    setTimeout(() => {
        performExamBatchConflictCheck();
    }, 1500);

    // Build calendar view (hidden by default but ready)
    buildExamBatchCalendar();
}

function buildExamBatchRow(item, idx) {
    const row = document.createElement('tr');
    const isExisting = item.is_existing === true || item.is_existing === 'true';
    row.className = 'hover:bg-orange-50/30 dark:hover:bg-gray-750 transition-all group';
    row.dataset.rowIndex = idx;
    row.dataset.subjectId = item.subject_id;
    row.dataset.scheduleType = item.schedule_type || 'lecture';
    row.dataset.subjectCode = item.subject_code || '';
    row.dataset.isExisting = isExisting ? 'true' : 'false';
    row.dataset.examScheduleId = item.exam_schedule_id || '';
    row.dataset.isDirty = 'false';
    row.dataset.originalFacultyId = item.faculty_id ? String(item.faculty_id) : '';
    row.dataset.originalRoomId = item.room_id ? String(item.room_id) : '';
    row.dataset.originalExamDate = item.exam_date || '';
    row.dataset.originalStartTime = item.start_time || '';
    row.dataset.originalEndTime = item.end_time || '';

    const examDate = item.exam_date || '';
    const startTime = item.start_time || '';
    const endTime = item.end_time || '';

    const proctorDisplay = item.faculty_name || '';
    const hasProctor = !!item.faculty_id;
    const hasRoom = !!item.room_id;

    const schedType = (item.schedule_type || 'lecture').toLowerCase();
    const typeDot = schedType === 'lab'
        ? '<span class="inline-block w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0"></span>'
        : '<span class="inline-block w-1.5 h-1.5 rounded-full bg-blue-500 flex-shrink-0"></span>';
    const schedTypeBadge = schedType === 'lab'
        ? '<span class="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-semibold bg-green-100 text-green-700 ml-1">LAB</span>'
        : '<span class="inline-flex items-center px-1 py-0.5 rounded text-[9px] font-semibold bg-blue-100 text-blue-700 ml-1">LEC</span>';

    row.innerHTML = `
        <td class="px-3 py-2.5 text-center">
            <div class="exam-batch-status-icon flex items-center justify-center" title="Pending conflict check">
                <div class="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <svg class="w-2.5 h-2.5 text-gray-400" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 text-center">
            <span class="exam-batch-row-num text-[10px] font-medium text-gray-400">${idx + 1}</span>
        </td>
        <td class="px-3 py-2.5 min-w-0">
            <div class="flex items-center gap-1.5 mb-0.5">
                ${typeDot}
                <span data-subject-code class="font-bold text-gray-900 dark:text-gray-100 text-[11px] leading-tight">${examEscapeHtml(item.subject_code)}</span>
                ${schedTypeBadge}
            </div>
            <div class="text-gray-400 dark:text-gray-500 truncate max-w-[180px] text-[10px] leading-tight" title="${examEscapeHtml(item.course_description || '')}">${examEscapeHtml(item.course_description || '')}</div>
        </td>
        <td class="px-3 py-2.5">
            <input type="date" data-field="exam_date" value="${examDate}"
                   min="${_examPeriodStart()}" max="${_examPeriodEnd()}"
                   onchange="onExamDateChange(this)"
                   class="exam-batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-orange-400 dark:focus:border-orange-500 focus:ring-1 focus:ring-orange-200 dark:focus:ring-orange-800 w-full min-w-[110px] sm:w-[128px] cursor-pointer">
        </td>
        <td class="px-3 py-2.5 whitespace-nowrap">
            <div class="flex items-center gap-0.5">
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="start_time"
                     data-value="${startTime || ''}"
                     data-onchange="onExamStartTimeChange(input)"
                     data-input-class="exam-batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-orange-400 dark:focus:border-orange-500 focus:ring-1 focus:ring-orange-200 dark:focus:ring-orange-800 w-full min-w-[96px] sm:w-[104px]">
                </div>
                <span class="text-gray-300 dark:text-gray-600 text-[9px] select-none px-0.5">–</span>
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="end_time"
                     data-value="${endTime || ''}"
                     data-onchange="onExamEndTimeChange(input)"
                     data-input-class="exam-batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-orange-400 dark:focus:border-orange-500 focus:ring-1 focus:ring-orange-200 dark:focus:ring-orange-800 w-full min-w-[96px] sm:w-[104px]">
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 relative">
            <div class="exam-batch-proctor-picker" data-row="${idx}">
                <button type="button" onclick="toggleExamProctorDropdown(this, ${idx})"
                        class="exam-batch-proctor-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasProctor
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-orange-300'
                            : 'border-dashed border-orange-400 bg-orange-50 dark:bg-orange-900/20 text-orange-700 dark:text-orange-400 hover:border-orange-500'}"
                        title="${hasProctor ? '' : 'Proctor not assigned'}">
                    ${!hasProctor ? '<svg class="exam-batch-proctor-warning-icon w-3 h-3 flex-shrink-0 text-orange-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M12 2a10 10 0 100 20 10 10 0 000-20z"/></svg>' : ''}
                    <span class="exam-batch-proctor-label truncate flex-1 min-w-0">${hasProctor ? examEscapeHtml(proctorDisplay) : 'Assign Proctor'}</span>
                    <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </button>
                <input type="hidden" data-field="faculty_id" value="${item.faculty_id || ''}">
                <input type="hidden" data-field="faculty_name" value="${examEscapeHtml(proctorDisplay)}">
                <div class="exam-batch-proctor-dropdown hidden fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl max-h-[260px] flex flex-col overflow-hidden" style="width:min(290px, calc(100vw - 2rem));">
                    <div class="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <input type="text" placeholder="Search proctor..." class="exam-batch-proctor-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-orange-400 dark:focus:border-orange-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-orange-200 dark:focus:ring-orange-800" oninput="filterExamProctorDropdown(this, ${idx})">
                    </div>
                    <div class="exam-batch-proctor-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 relative">
            <div class="exam-batch-room-picker" data-row="${idx}">
                <button type="button" onclick="toggleExamRoomDropdown(this, ${idx})"
                        class="exam-batch-room-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasRoom
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-orange-300'
                            : 'border-dashed border-gray-300 dark:border-gray-600 bg-gray-50 dark:bg-gray-700/50 text-gray-500 dark:text-gray-400 hover:border-gray-400'}">
                    <span class="truncate flex-1 min-w-0">
                        ${item.room_name ? examEscapeHtml(item.room_name) + (item.building_name ? '<span class="text-gray-400 dark:text-gray-500"> · ' + examEscapeHtml(item.building_name) + '</span>' : '') : 'Select Room'}
                    </span>
                    <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </button>
                <input type="hidden" data-field="room_id" value="${item.room_id || ''}">
                <input type="hidden" data-field="room_name" value="${examEscapeHtml(item.room_name || '')}">
                <input type="hidden" data-field="building_name" value="${examEscapeHtml(item.building_name || '')}">
                <div class="exam-batch-room-dropdown hidden fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl max-h-[220px] flex flex-col overflow-hidden" style="width:min(250px, calc(100vw - 2rem));">
                    <div class="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <input type="text" placeholder="Search rooms..." class="exam-batch-room-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-orange-400 dark:focus:border-orange-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-orange-200 dark:focus:ring-orange-800" oninput="filterExamRoomDropdown(this, ${idx})">
                    </div>
                    <div class="exam-batch-room-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 text-center">
            <button type="button" onclick="removeExamBatchRow(this)" class="p-1.5 rounded-md hover:bg-red-100 dark:hover:bg-red-900/30 text-gray-300 dark:text-gray-600 hover:text-red-500 dark:hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100" title="Remove row">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
                </svg>
            </button>
        </td>
    `;

    return row;
}

function renderExamUnplaceableItems(items) {
    const section = document.getElementById('examBatchUnplaceableSection');
    const list = document.getElementById('examBatchUnplaceableList');
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
                    <span class="font-semibold text-red-700 text-[11px]">${examEscapeHtml(item.subject_code)}</span>
                    <p class="text-[10px] text-red-400 mt-0.5">${examEscapeHtml(item.reason)}</p>
                </div>
            `;
            list.appendChild(div);
        });
    } else {
        section.classList.add('hidden');
    }
}

// ─── Proctor (Faculty) Dropdown ───────────────────────────────────

async function loadExamFacultyForRow(rowIdx, subjectId) {
    if (_examFacultyCache[subjectId]) {
        renderExamProctorOptions(rowIdx, _examFacultyCache[subjectId]);
        return;
    }
    try {
        const res = await fetch(`/schedule/get-faculty/${subjectId}`);
        const data = await res.json();
        _examFacultyCache[subjectId] = data.faculty || [];
        renderExamProctorOptions(rowIdx, _examFacultyCache[subjectId]);
    } catch (e) {
        console.error('Failed to load faculty for subject', subjectId, e);
    }
}

function renderExamProctorOptions(rowIdx, facultyList) {
    const list = document.querySelector(`.exam-batch-proctor-list[data-row="${rowIdx}"]`);
    if (!list) return;

    if (!facultyList || facultyList.length === 0) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">No faculty available</div>';
        return;
    }

    // Get current row date/time for intra-batch comparison
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    const curDate = row?.querySelector('[data-field="exam_date"]')?.value || '';
    const curSt = row?.querySelector('[data-field="start_time"]')?.value || '';
    const curEt = row?.querySelector('[data-field="end_time"]')?.value || '';
    const otherAssignments = getExamIntraBatchAssignments(rowIdx);

    list.innerHTML = '';

    facultyList.forEach(f => {
        const availColor = {
            'available': 'bg-green-100 text-green-700',
            'moderate': 'bg-blue-100 text-blue-700',
            'high_load': 'bg-amber-100 text-amber-700',
            'overloaded': 'bg-red-100 text-red-700'
        }[f.availability] || 'bg-gray-100 text-gray-600';

        // Check intra-batch conflict
        let batchConflictLabel = '';
        for (const other of otherAssignments) {
            if (other.faculty_id == f.id && other.exam_date === curDate && examTimesOverlap(curSt, curEt, other.start_time, other.end_time)) {
                batchConflictLabel = `Busy · Row ${other.idx + 1}`;
                break;
            }
        }

        const opt = document.createElement('div');
        opt.className = 'exam-batch-proctor-option px-3 py-2 hover:bg-orange-50 dark:hover:bg-orange-900/30 cursor-pointer transition-colors flex items-center justify-between gap-2' + (batchConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
        opt.dataset.facultyId = f.id;
        opt.dataset.facultyName = f.full_name;
        opt.dataset.searchText = (f.full_name + ' ' + (f.department_code || '')).toLowerCase();
        opt.onclick = () => selectExamProctor(rowIdx, f.id, f.full_name);

        opt.innerHTML = `
            <div class="min-w-0 flex-1">
                <div class="text-[11px] font-medium text-gray-800 dark:text-gray-200 truncate">${examEscapeHtml(f.full_name)}</div>
                <div class="text-[10px] text-gray-400">${examEscapeHtml(f.department_code || '')} ${f.is_assigned ? '· Assigned' : ''} ${batchConflictLabel ? `<span class="text-red-500 font-medium">· ${examEscapeHtml(batchConflictLabel)}</span>` : ''}</div>
            </div>
            <span class="text-[9px] px-1.5 py-0.5 rounded-full font-medium flex-shrink-0 ${batchConflictLabel ? 'bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400' : availColor}">
                ${batchConflictLabel ? '⚠' : ''} ${f.weekly_units}/${f.max_units}u
            </span>
        `;
        list.appendChild(opt);
    });
}

function toggleExamProctorDropdown(btn, rowIdx) {
    const dropdown = btn.closest('.exam-batch-proctor-picker').querySelector('.exam-batch-proctor-dropdown');
    if (!dropdown) return;

    examCloseAllDropdowns(dropdown);

    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        examPositionDropdown(btn, dropdown);
        _examActiveDropdown = dropdown;
        const search = dropdown.querySelector('.exam-batch-proctor-search');
        if (search) { search.value = ''; search.focus(); }
        dropdown.querySelectorAll('.exam-batch-proctor-option').forEach(o => o.style.display = '');
    } else {
        dropdown.classList.add('hidden');
        _examActiveDropdown = null;
    }
}

function filterExamProctorDropdown(searchInput, rowIdx) {
    const term = searchInput.value.toLowerCase();
    const list = searchInput.closest('.exam-batch-proctor-dropdown').querySelector('.exam-batch-proctor-list');
    list.querySelectorAll('.exam-batch-proctor-option').forEach(opt => {
        opt.style.display = (opt.dataset.searchText || '').includes(term) ? '' : 'none';
    });
}

function setExamProctorTriggerState(row, facultyId, facultyName) {
    const trigger = row?.querySelector('.exam-batch-proctor-trigger');
    if (!trigger) return;

    const label = trigger.querySelector('.exam-batch-proctor-label');
    const normalizedId = String(facultyId || '').trim();
    const hasProctor = !!normalizedId && normalizedId !== 'null' && normalizedId !== 'undefined';
    const safeName = String(facultyName || '').trim();

    const assignedClasses = [
        'border-gray-200', 'dark:border-gray-600', 'bg-white', 'dark:bg-gray-700',
        'text-gray-700', 'dark:text-gray-200', 'hover:border-orange-300'
    ];
    const unassignedClasses = [
        'border-dashed', 'border-orange-400', 'border-orange-300', 'bg-orange-50', 'dark:bg-orange-900/20',
        'text-orange-700', 'dark:text-orange-400', 'text-gray-400', 'hover:border-orange-500'
    ];

    trigger.classList.remove(...assignedClasses, ...unassignedClasses);
    trigger.classList.add(...(hasProctor ? assignedClasses : unassignedClasses));
    trigger.title = hasProctor ? '' : 'Proctor not assigned';

    if (label) {
        label.textContent = hasProctor ? (safeName || 'Assigned Proctor') : 'Assign Proctor';
    }

    let warningIcon = trigger.querySelector('.exam-batch-proctor-warning-icon');
    if (hasProctor) {
        if (warningIcon) warningIcon.remove();
    } else if (!warningIcon) {
        warningIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        warningIcon.setAttribute('class', 'exam-batch-proctor-warning-icon w-3 h-3 flex-shrink-0 text-orange-500');
        warningIcon.setAttribute('fill', 'none');
        warningIcon.setAttribute('stroke', 'currentColor');
        warningIcon.setAttribute('viewBox', '0 0 24 24');

        const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('d', 'M12 9v2m0 4h.01M12 2a10 10 0 100 20 10 10 0 000-20z');
        warningIcon.appendChild(path);

        const chevron = trigger.querySelector('svg:last-child');
        if (label) {
            trigger.insertBefore(warningIcon, label);
        } else if (chevron) {
            trigger.insertBefore(warningIcon, chevron);
        } else {
            trigger.appendChild(warningIcon);
        }
    }
}

function selectExamProctor(rowIdx, facultyId, facultyName) {
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    row.querySelector('[data-field="faculty_id"]').value = facultyId;
    row.querySelector('[data-field="faculty_name"]').value = facultyName;
    setExamProctorTriggerState(row, facultyId, facultyName);

    const dropdown = row.querySelector('.exam-batch-proctor-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    _examActiveDropdown = null;

    _markExamBatchRowDirtyState(row);

    scheduleExamConflictCheck();
    examValidateAllRows();
    _refreshExamBatchCalendarIfVisible();
}

// ─── Room Dropdown ────────────────────────────────────────────────

async function toggleExamRoomDropdown(btn, rowIdx) {
    const dropdown = btn.closest('.exam-batch-room-picker').querySelector('.exam-batch-room-dropdown');
    if (!dropdown) return;

    examCloseAllDropdowns(dropdown);

    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        examPositionDropdown(btn, dropdown);
        _examActiveDropdown = dropdown;
        const search = dropdown.querySelector('.exam-batch-room-search');
        if (search) { search.value = ''; search.focus(); }
        await loadExamAvailableRooms(rowIdx);
    } else {
        dropdown.classList.add('hidden');
        _examActiveDropdown = null;
    }
}

async function loadExamAvailableRooms(rowIdx) {
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    const examDate = row.querySelector('[data-field="exam_date"]').value;
    const startTime = row.querySelector('[data-field="start_time"]').value;
    const endTime = row.querySelector('[data-field="end_time"]').value;

    if (!examDate || !startTime || !endTime) {
        const list = row.querySelector('.exam-batch-room-list');
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-amber-500">Set date & time first</div>';
        return;
    }

    const list = row.querySelector('.exam-batch-room-list');
    list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">Loading rooms...</div>';

    try {
        const params = new URLSearchParams({ exam_date: examDate, start_time: startTime, end_time: endTime });
        const hasPreferredBuilding = !!_examPreferredBuildingId;
        if (hasPreferredBuilding) params.set('building_id', _examPreferredBuildingId);

        const res = await fetch(`/exam-schedule/batch-available-rooms?${params}`);
        const data = await res.json();

        let rooms = data.rooms || [];
        let usedFallback = false;

        // Preferred building is soft; if empty, retry once without building hint.
        if (hasPreferredBuilding && rooms.length === 0) {
            const fallbackParams = new URLSearchParams(params);
            fallbackParams.delete('building_id');
            const fallbackRes = await fetch(`/exam-schedule/batch-available-rooms?${fallbackParams}`);
            const fallbackData = await fallbackRes.json();
            rooms = fallbackData.rooms || [];
            usedFallback = rooms.length > 0;
        }

        renderExamRoomOptions(rowIdx, rooms, usedFallback);
    } catch (e) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-red-400">Failed to load rooms</div>';
    }
}

function renderExamRoomOptions(rowIdx, rooms, usedFallback = false) {
    const list = document.querySelector(`.exam-batch-room-list[data-row="${rowIdx}"]`);
    if (!list) return;

    if (!rooms || rooms.length === 0) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">No rooms found</div>';
        return;
    }

    // Intra-batch collision hints
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    const curDate = row?.querySelector('[data-field="exam_date"]')?.value || '';
    const curSt = row?.querySelector('[data-field="start_time"]')?.value || '';
    const curEt = row?.querySelector('[data-field="end_time"]')?.value || '';
    const otherAssignments = getExamIntraBatchAssignments(rowIdx);

    list.innerHTML = '';
    if (usedFallback) {
        const hint = document.createElement('div');
        hint.className = 'px-3 py-2 text-[10px] text-amber-600 bg-amber-50/80 dark:bg-amber-900/20 dark:text-amber-300 border-b border-amber-100 dark:border-amber-800/40';
        hint.textContent = 'Preferred building has no available rooms for this slot. Showing alternatives.';
        list.appendChild(hint);
    }

    rooms.forEach(r => {
        const occupiedLabel = (r && typeof r.occupied_note === 'string') ? r.occupied_note : '';
        const isOccupied = Boolean(r && r.is_occupied);

        let batchConflictLabel = '';
        for (const other of otherAssignments) {
            if (other.room_id == r.id && other.exam_date === curDate && examTimesOverlap(curSt, curEt, other.start_time, other.end_time)) {
                batchConflictLabel = `Used by Row ${other.idx + 1} (${other.subject_code})`;
                break;
            }
        }

        const hasConflictLabel = Boolean(isOccupied || batchConflictLabel);

        const opt = document.createElement('div');
        opt.className = 'exam-batch-room-option px-3 py-2 hover:bg-orange-50 dark:hover:bg-orange-900/30 cursor-pointer transition-colors' + (hasConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
        opt.dataset.roomId = r.id;
        opt.dataset.roomNumber = r.room_number;
        opt.dataset.buildingName = r.building_name || '';
        opt.dataset.searchText = (r.room_number + ' ' + (r.building_name || '')).toLowerCase();
        opt.onclick = () => selectExamRoom(rowIdx, r.id, r.room_number, r.building_name || '');

        opt.innerHTML = `
            <div class="flex items-center justify-between gap-2">
                <div class="min-w-0">
                    <div class="text-[11px] font-medium text-gray-800 dark:text-gray-200">${examEscapeHtml(r.room_number)}</div>
                    <div class="text-[10px] text-gray-400">${examEscapeHtml(r.building_name || '')} · ${examEscapeHtml(r.room_type || '')}</div>
                </div>
                <div class="flex items-center gap-1.5 flex-shrink-0">
                    ${isOccupied && occupiedLabel ? `<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 font-medium whitespace-nowrap">${examEscapeHtml(occupiedLabel)}</span>` : ''}
                    ${batchConflictLabel ? `<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 font-medium whitespace-nowrap">${examEscapeHtml(batchConflictLabel)}</span>` : ''}
                </div>
            </div>
        `;
        list.appendChild(opt);
    });
}

function filterExamRoomDropdown(searchInput, rowIdx) {
    const term = searchInput.value.toLowerCase();
    const list = searchInput.closest('.exam-batch-room-dropdown').querySelector('.exam-batch-room-list');
    list.querySelectorAll('.exam-batch-room-option').forEach(opt => {
        opt.style.display = (opt.dataset.searchText || '').includes(term) ? '' : 'none';
    });
}

function selectExamRoom(rowIdx, roomId, roomNumber, buildingName) {
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    row.querySelector('[data-field="room_id"]').value = roomId;
    row.querySelector('[data-field="room_name"]').value = roomNumber;
    row.querySelector('[data-field="building_name"]').value = buildingName;

    const trigger = row.querySelector('.exam-batch-room-trigger span');
    trigger.textContent = roomNumber + (buildingName ? ' · ' + buildingName : '');

    const dropdown = row.querySelector('.exam-batch-room-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    _examActiveDropdown = null;

    _markExamBatchRowDirtyState(row);

    scheduleExamConflictCheck();
    examValidateAllRows();
    _refreshExamBatchCalendarIfVisible();
}

// ─── Inline Edit Handlers ─────────────────────────────────────────

function onExamDateChange(input) {
    const row = input.closest('tr');
    _markExamBatchRowDirtyState(row);

    const rowIdx = parseInt(row.dataset.rowIndex, 10);
    const dayWarning = buildExamBatchFacultyDayWarning(row);
    if (dayWarning && Number.isInteger(rowIdx)) {
        _examBatchConflicts[rowIdx] = { status: 'warning', conflicts: [dayWarning] };
        renderExamRowConflictStatus(row, rowIdx, _examBatchConflicts[rowIdx]);
    }

    const hasFullConflictPayload = Boolean(
        row.querySelector('[data-field="faculty_id"]')?.value &&
        row.querySelector('[data-field="exam_date"]')?.value &&
        row.querySelector('[data-field="start_time"]')?.value &&
        row.querySelector('[data-field="end_time"]')?.value
    );

    if (hasFullConflictPayload) {
        showExamConflictCheckingState();
        if (_examConflictCheckTimer) {
            clearTimeout(_examConflictCheckTimer);
            _examConflictCheckTimer = null;
        }
        performExamBatchConflictCheck();
    } else {
        scheduleExamConflictCheck();
    }

    examValidateAllRows();
    _refreshExamBatchCalendarIfVisible();
}

function onExamStartTimeChange(input) {
    const row = input.closest('tr');
    const durationMinutes = _examDurationLimit();
    examRecalcEndTime(row, input.value, durationMinutes);
    _markExamBatchRowDirtyState(row);
    scheduleExamConflictCheck();
    examValidateAllRows();
    _refreshExamBatchCalendarIfVisible();
}

function onExamEndTimeChange(input) {
    const row = input.closest('tr');
    _markExamBatchRowDirtyState(row);
    scheduleExamConflictCheck();
    examValidateAllRows();
    _refreshExamBatchCalendarIfVisible();
}

function examRecalcEndTime(row, startTimeStr, durationMinutes) {
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

function removeExamBatchRow(btn) {
    const row = btn.closest('tr');
    const idx = parseInt(row.dataset.rowIndex);

    if (_examBatchData && _examBatchData.proposed) {
        _examBatchData.proposed.splice(idx, 1);
        if (_examBatchData.stats) {
            _examBatchData.stats.scheduled = _examBatchData.proposed.length;
        }
        document.getElementById('examBatchStatScheduled').textContent = _examBatchData.proposed.length;
    }

    row.style.transition = 'opacity 0.2s, transform 0.2s';
    row.style.opacity = '0';
    row.style.transform = 'translateX(20px)';
    setTimeout(() => {
        row.remove();
        examReindexRows();
        if (!document.querySelectorAll('#examBatchTableBody tr').length) {
            document.getElementById('examBatchFooter').classList.add('hidden');
        }
        examValidateAllRows();
        scheduleExamConflictCheck();
        _refreshExamBatchCalendarIfVisible();
    }, 200);
}

function examReindexRows() {
    _examBatchConflicts = {};
    document.querySelectorAll('#examBatchTableBody tr').forEach((r, i) => {
        r.dataset.rowIndex = i;
        r.querySelectorAll('[data-row]').forEach(el => el.dataset.row = i);
        const rowNum = r.querySelector('.exam-batch-row-num');
        if (rowNum) rowNum.textContent = i + 1;
        const proctorBtn = r.querySelector('.exam-batch-proctor-trigger');
        if (proctorBtn) proctorBtn.setAttribute('onclick', `toggleExamProctorDropdown(this, ${i})`);
        const proctorSearch = r.querySelector('.exam-batch-proctor-search');
        if (proctorSearch) proctorSearch.setAttribute('oninput', `filterExamProctorDropdown(this, ${i})`);
        const roomBtn = r.querySelector('.exam-batch-room-trigger');
        if (roomBtn) roomBtn.setAttribute('onclick', `toggleExamRoomDropdown(this, ${i})`);
        const roomSearch = r.querySelector('.exam-batch-room-search');
        if (roomSearch) roomSearch.setAttribute('oninput', `filterExamRoomDropdown(this, ${i})`);
    });
}

// ─── Add Subject ──────────────────────────────────────────────────

async function openExamAddSubjectDropdown() {
    const panel = document.getElementById('examBatchAddSubjectPanel');
    panel.classList.remove('hidden');

    const select = document.getElementById('examBatchSubjectSelect');
    select.innerHTML = '<option value="">Loading subjects...</option>';

    try {
        let url = `/exam-schedule/batch-unscheduled-subjects/${_examBatchSectionId}?include_all=true`;
        if (_examBatchCurriculumId) url += `&curriculum_id=${_examBatchCurriculumId}`;

        const res = await fetch(url);
        const data = await res.json();

        if (!data.success || !data.subjects || data.subjects.length === 0) {
            select.innerHTML = '<option value="">No more subjects available</option>';
            return;
        }

        _examAvailableSubjects = data.subjects;

        select.innerHTML = '<option value="">Select a subject to add...</option>';

        _examAvailableSubjects.forEach((s, i) => {
            const opt = document.createElement('option');
            opt.value = i;
            const typeLabel = (s.schedule_type || 'lecture') === 'lab' ? ' [LAB]' : ' [LEC]';
            opt.textContent = `${s.subject_code}${typeLabel} - ${s.course_description}`;
            select.appendChild(opt);
        });

    } catch (e) {
        select.innerHTML = '<option value="">Failed to load subjects</option>';
    }
}

function closeExamAddSubjectDropdown() {
    document.getElementById('examBatchAddSubjectPanel').classList.add('hidden');
}

function addExamSelectedSubject() {
    const select = document.getElementById('examBatchSubjectSelect');
    const selectedIdx = select.value;
    if (!selectedIdx && selectedIdx !== 0) {
        if (typeof showToast === 'function') showToast('Select a subject first', 'error');
        return;
    }

    const subject = _examAvailableSubjects[parseInt(selectedIdx)];
    if (!subject) return;

    // Default to first available exam period date, morning time
    const defaultDate = _examPeriodStart();
    const defaultStart = _examStartTime();
    const defaultEnd = examCalculateEndTimeStr(defaultStart, _examDurationLimit());

    const newItem = {
        subject_id: subject.subject_id,
        subject_code: subject.subject_code,
        course_description: subject.course_description || '',
        schedule_type: subject.schedule_type || 'lecture',
        faculty_id: null,
        faculty_name: '',
        room_id: null,
        room_name: '',
        building_name: '',
        exam_date: defaultDate,
        start_time: defaultStart,
        end_time: defaultEnd,
    };

    if (!_examBatchData) {
        _examBatchData = { proposed: [], unplaceable: [], section: { id: _examBatchSectionId }, stats: {} };
    }

    _examBatchData.proposed.push(newItem);
    const newIdx = _examBatchData.proposed.length - 1;

    const tbody = document.getElementById('examBatchTableBody');
    const row = buildExamBatchRow(newItem, newIdx);
    tbody.appendChild(row);
    if (window.TimePicker && typeof window.TimePicker.init === 'function') {
        window.TimePicker.init();
    }

    loadExamFacultyForRow(newIdx, subject.subject_id);

    document.getElementById('examBatchStatScheduled').textContent = _examBatchData.proposed.length;

    // Keep option available so users can intentionally add duplicate subjects
    select.value = '';

    document.getElementById('examBatchFooter').classList.remove('hidden');
    document.getElementById('examBatchResults').classList.remove('hidden');
    document.getElementById('examBatchLoading').classList.add('hidden');

    examValidateAllRows();
    scheduleExamConflictCheck();

    row.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    row.classList.add('bg-orange-50', 'dark:bg-orange-900/20');
    setTimeout(() => row.classList.remove('bg-orange-50', 'dark:bg-orange-900/20'), 1500);

    closeExamAddSubjectDropdown();
}

function examCalculateEndTimeStr(startStr, durationMinutes) {
    const [h, m] = startStr.split(':').map(Number);
    const totalMin = h * 60 + m + durationMinutes;
    const endH = Math.floor(totalMin / 60);
    const endM = totalMin % 60;
    return String(endH).padStart(2, '0') + ':' + String(endM).padStart(2, '0');
}

// ─── Validation ───────────────────────────────────────────────────

function examValidateAllRows() {
    const rows = document.querySelectorAll('#examBatchTableBody tr');
    let missingRoom = 0;
    let invalidTime = 0;
    let missingDate = 0;
    let missingProctor = 0;
    let saveableRows = 0;

    rows.forEach(row => {
        _markExamBatchRowDirtyState(row);
        if (!_isExamBatchRowSaveable(row)) return;

        saveableRows++;
        const roomId = row.querySelector('[data-field="room_id"]')?.value;
        const startTime = row.querySelector('[data-field="start_time"]')?.value;
        const endTime = row.querySelector('[data-field="end_time"]')?.value;
        const examDate = row.querySelector('[data-field="exam_date"]')?.value;
        const facultyId = row.querySelector('[data-field="faculty_id"]')?.value;
        const facultyName = row.querySelector('[data-field="faculty_name"]')?.value;

        setExamProctorTriggerState(row, facultyId, facultyName);

        if (!roomId) missingRoom++;
        if (!startTime || !endTime || startTime >= endTime) invalidTime++;
        if (!examDate) missingDate++;
        if (!facultyId) missingProctor++;
    });

    const confirmBtn = document.getElementById('examBatchConfirmBtn');
    const msgEl = document.getElementById('examBatchValidationMsg');
    const msgText = document.getElementById('examBatchValidationText');

    if (rows.length === 0 || saveableRows === 0) {
        confirmBtn.disabled = true;
        msgEl.classList.add('hidden');
        updateExamFooterBanner('empty');
        return;
    }

    const formIssues = [];
    if (missingDate > 0) formIssues.push(`${missingDate} need date`);
    if (missingProctor > 0) formIssues.push(`${missingProctor} need proctor`);
    if (missingRoom > 0) formIssues.push(`${missingRoom} need room`);
    if (invalidTime > 0) formIssues.push(`${invalidTime} invalid time`);

    // Check conflict state
    let conflictRows = 0;
    Object.entries(_examBatchConflicts).forEach(([idx, r]) => {
        if (r.status !== 'conflict') return;
        const row = rows[parseInt(idx, 10)];
        if (_isExamBatchRowSaveable(row)) conflictRows++;
    });

    const hasFormIssues = formIssues.length > 0;
    const hasConflicts = conflictRows > 0;

    if (hasFormIssues || hasConflicts) {
        confirmBtn.disabled = true;
        const allIssues = [...formIssues];
        if (hasConflicts) allIssues.push(`${conflictRows} conflict(s)`);
        msgText.textContent = allIssues.join(', ');
        msgEl.classList.remove('hidden');
    } else {
        confirmBtn.disabled = false;
        msgEl.classList.add('hidden');
    }
}

// ─── Confirm & Save ───────────────────────────────────────────────

async function confirmExamBatchSchedule() {
    const editedItems = collectExamBatchItems();

    if (!editedItems || editedItems.length === 0) {
        const existingRows = document.querySelectorAll('#examBatchTableBody tr[data-is-existing="true"]');
        if (existingRows.length > 0) {
            if (typeof showToast === 'function') showToast('All exams are already saved. Use + Add Subject to add new ones.', 'info');
        } else {
            if (typeof showToast === 'function') showToast('No exams to save.', 'error');
        }
        return;
    }

    // Basic form validation
    for (let i = 0; i < editedItems.length; i++) {
        const item = editedItems[i];
        if (!item.exam_date) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Exam date is required.`, 'error');
            return;
        }
        if (!item.start_time || !item.end_time || item.start_time >= item.end_time) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Invalid time range.`, 'error');
            return;
        }
        if (!item.room_id) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Room is required.`, 'error');
            return;
        }
        if (!item.faculty_id) {
            if (typeof showToast === 'function') showToast(`Row ${i + 1} (${item.subject_code}): Proctor is required.`, 'error');
            return;
        }
    }

    // Block if conflicts remain
    const allRows = document.querySelectorAll('#examBatchTableBody tr');
    const conflictRows = Object.entries(_examBatchConflicts)
        .filter(([idx, r]) => r.status === 'conflict' && _isExamBatchRowSaveable(allRows[parseInt(idx, 10)]));
    if (conflictRows.length > 0) {
        if (typeof showToast === 'function') showToast(`${conflictRows.length} row(s) have conflicts. Resolve them before saving.`, 'error');
        return;
    }

    const confirmBtn = document.getElementById('examBatchConfirmBtn');
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
        const response = await fetch('/exam-schedule/batch-confirm', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: _examBatchData.section.id,
                proposed: editedItems
            })
        });

        const result = await response.json();

        if (result.success) {
            const rowErrors = result.row_errors || [];
            const updated = result.updated || 0;
            const skipped = result.skipped || 0;
            if (rowErrors.length > 0) {
                let msg = `Saved ${result.created + updated} exam(s) (${result.created} created, ${updated} updated). ${rowErrors.length} row(s) had conflicts.`;
                if (skipped > 0) msg += ` ${skipped} already scheduled.`;
                if (typeof showToast === 'function') {
                    showToast(msg, 'error');
                }
                rowErrors.forEach(e => {
                    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${e.row - 1}"]`);
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
            sessionStorage.removeItem(EXAM_BATCH_STATE_KEY);

            _updateExamBatchStep(3);

            exitExamBatchMode();
            if (typeof showToast === 'function') {
                let msg = '';
                if ((result.created + updated) > 0 && skipped > 0) {
                    msg = `Saved ${result.created + updated} exam schedule(s) (${result.created} created, ${updated} updated), ${skipped} already scheduled.`;
                } else if ((result.created + updated) > 0) {
                    msg = `Saved ${result.created + updated} exam schedule(s) (${result.created} created, ${updated} updated).`;
                } else if (skipped > 0) {
                    msg = `All ${skipped} exam(s) were already scheduled.`;
                }
                showToast(msg, (result.created + updated) > 0 ? 'success' : 'info');
            }

            // Stay on the current page (add exam form) — just refresh to show updated data
            setTimeout(() => {
                window.location.reload();
            }, 1200);
        } else {
            // Show row-level errors if available
            const rowErrors = result.row_errors || [];
            const skipped = result.skipped || 0;
            if (rowErrors.length > 0) {
                const firstErr = rowErrors[0];
                let msg = rowErrors.length === 1
                    ? `${firstErr.subject_code || 'Row ' + firstErr.row}: ${firstErr.error}`
                    : `${rowErrors.length} row(s) failed. First: ${firstErr.error}`;
                if (skipped > 0) msg += ` (${skipped} already scheduled)`;
                if (typeof showToast === 'function') showToast(msg, 'error');

                rowErrors.forEach(e => {
                    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${e.row - 1}"]`);
                    if (row) {
                        row.classList.add('bg-red-50');
                        row.title = e.error;
                    }
                });
            } else {
                if (typeof showToast === 'function') showToast(result.error || 'Failed to save exams', 'error');
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

function collectExamBatchItems() {
    const rows = document.querySelectorAll('#examBatchTableBody tr');
    const items = [];

    rows.forEach((row, idx) => {
        _markExamBatchRowDirtyState(row);
        if (!_isExamBatchRowSaveable(row)) return;

        const original = (_examBatchData && _examBatchData.proposed && _examBatchData.proposed[idx]) || {};

        const rowObj = {
            subject_id: parseInt(row.dataset.subjectId) || original.subject_id,
            subject_code: original.subject_code || '',
            course_description: original.course_description || '',
            schedule_type: row.dataset.scheduleType || original.schedule_type || 'lecture',
            faculty_id: parseInt(row.querySelector('[data-field="faculty_id"]')?.value) || null,
            faculty_name: row.querySelector('[data-field="faculty_name"]')?.value || '',
            room_id: parseInt(row.querySelector('[data-field="room_id"]')?.value) || null,
            room_name: row.querySelector('[data-field="room_name"]')?.value || '',
            building_name: row.querySelector('[data-field="building_name"]')?.value || '',
            exam_date: row.querySelector('[data-field="exam_date"]')?.value || '',
            start_time: row.querySelector('[data-field="start_time"]')?.value || '',
            end_time: row.querySelector('[data-field="end_time"]')?.value || '',
        };

        const examScheduleId = parseInt(row.dataset.examScheduleId) || original.exam_schedule_id;
        if (row.dataset.isExisting === 'true' && examScheduleId) {
            rowObj.exam_schedule_id = examScheduleId;
            rowObj.is_existing = true;
        }

        items.push(rowObj);
    });

    return items;
}

// ─── Conflict Detection Engine ────────────────────────────────────

function scheduleExamConflictCheck() {
    if (!_examBatchModeActive) return;
    if (_examConflictCheckTimer) clearTimeout(_examConflictCheckTimer);

    showExamConflictCheckingState();

    _examConflictCheckTimer = setTimeout(() => {
        performExamBatchConflictCheck();
    }, EXAM_CONFLICT_CHECK_DEBOUNCE_MS);
}

async function performExamBatchConflictCheck() {
    if (!_examBatchModeActive || !_examBatchSectionId) return;

    const rows = document.querySelectorAll('#examBatchTableBody tr');
    if (rows.length === 0) {
        _examBatchConflicts = {};
        updateExamConflictSummary({ total: 0, ok: 0, conflicts: 0, warnings: 0 });
        updateExamFooterBanner('empty');
        return;
    }

    if (_examConflictCheckInFlight) return;
    _examConflictCheckInFlight = true;

    const rowData = [];
    rows.forEach((row, idx) => {
        const original = (_examBatchData && _examBatchData.proposed && _examBatchData.proposed[idx]) || {};
        const rowObj = {
            subject_id: parseInt(row.dataset.subjectId) || original.subject_id,
            subject_code: original.subject_code || '',
            schedule_type: row.dataset.scheduleType || original.schedule_type || 'lecture',
            faculty_id: row.querySelector('[data-field="faculty_id"]')?.value || null,
            room_id: row.querySelector('[data-field="room_id"]')?.value || null,
            exam_date: row.querySelector('[data-field="exam_date"]')?.value || '',
            start_time: row.querySelector('[data-field="start_time"]')?.value || '',
            end_time: row.querySelector('[data-field="end_time"]')?.value || '',
        };
        // Include exam_schedule_id for existing rows so backend can exclude self-conflicts
        if (original.exam_schedule_id) rowObj.exam_schedule_id = original.exam_schedule_id;
        rowData.push(rowObj);
    });

    try {
        const response = await fetch('/exam-schedule/batch-check-conflicts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                section_id: _examBatchSectionId,
                rows: rowData
            })
        });

        const data = await response.json();
        _examConflictCheckInFlight = false;

        if (!data.success) {
            console.error('[EXAM-BATCH-CHECK] Server error:', data.error);
            hideExamConflictCheckingState();
            examValidateAllRows();
            return;
        }

        _examBatchConflicts = {};
        (data.rows || []).forEach(r => {
            _examBatchConflicts[r.index] = { status: r.status, conflicts: r.conflicts || [] };
        });

        const allRows = document.querySelectorAll('#examBatchTableBody tr');
        allRows.forEach((row, idx) => {
            const result = _examBatchConflicts[idx] || { status: 'ok', conflicts: [] };
            renderExamRowConflictStatus(row, idx, result);
        });

        updateExamConflictSummary(data.summary || { total: 0, ok: 0, conflicts: 0, warnings: 0 });
        examValidateAllRows();

    } catch (err) {
        _examConflictCheckInFlight = false;
        console.error('[EXAM-BATCH-CHECK] Network error:', err);
        hideExamConflictCheckingState();
        examValidateAllRows();
    }
}

function renderExamRowConflictStatus(row, idx, result) {
    const statusCell = row.querySelector('.exam-batch-status-icon');
    if (!statusCell) return;

    row.className = row.className.replace(/\bbg-(?:red|amber|emerald)-50\/50\b|\bdark:bg-(?:red|amber)-900\/20\b/g, '').trim();

    if (result.status === 'conflict') {
        row.classList.add('bg-red-50/50', 'dark:bg-red-900/20');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showExamRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center hover:bg-red-200 dark:hover:bg-red-900/60 focus-visible:ring-2 focus-visible:ring-red-400/60 transition-colors cursor-pointer" title="${count} conflict(s) — click for details">
                <svg class="w-3 h-3 text-red-600 dark:text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </button>`;
    } else if (result.status === 'warning') {
        row.classList.add('bg-amber-50/50', 'dark:bg-amber-900/20');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showExamRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center hover:bg-amber-200 dark:hover:bg-amber-900/60 focus-visible:ring-2 focus-visible:ring-amber-400/60 transition-colors cursor-pointer" title="${count} warning(s) — click for details">
                <svg class="w-3 h-3 text-amber-600 dark:text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </button>`;
    } else {
        statusCell.innerHTML = `
            <div class="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center" title="No conflicts">
                <svg class="w-3 h-3 text-emerald-600 dark:text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            </div>`;
    }
}

function showExamRowConflictTooltip(rowIdx) {
    const result = _examBatchConflicts[rowIdx];
    if (!result || !result.conflicts || result.conflicts.length === 0) return;

    const existing = document.getElementById('examBatchConflictTooltip');
    if (existing) existing.remove();

    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    const rect = row.getBoundingClientRect();
    const tooltip = document.createElement('div');
    tooltip.id = 'examBatchConflictTooltip';
    tooltip.className = 'fixed z-[10000] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl p-3 max-w-sm w-80';
    tooltip.style.left = Math.max(8, Math.min(rect.left, window.innerWidth - 340)) + 'px';

    const spaceBelow = window.innerHeight - rect.bottom;
    if (spaceBelow > 200) {
        tooltip.style.top = (rect.bottom + 4) + 'px';
    } else {
        tooltip.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
    }

    const conflictHtml = result.conflicts.map(c => {
        const isError = c.severity === 'critical' || c.severity === 'high';
        const borderColor = isError ? 'border-red-200 dark:border-red-800/40 bg-red-50 dark:bg-red-900/20' : 'border-amber-200 dark:border-amber-800/40 bg-amber-50 dark:bg-amber-900/20';
        const textColor = isError ? 'text-red-700 dark:text-red-300' : 'text-amber-700 dark:text-amber-300';
        const iconColor = isError ? 'text-red-500 dark:text-red-400' : 'text-amber-500 dark:text-amber-400';
        const icon = isError
            ? '<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>'
            : '<svg class="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';

        const label = c.type.replace('_batch', ' (batch)').replace('_', ' ');
        return `
            <div class="flex items-start gap-2 p-2 ${borderColor} rounded-lg border">
                <span class="${iconColor} mt-0.5">${icon}</span>
                <div class="min-w-0">
                    <span class="text-[10px] font-bold tracking-wide uppercase ${textColor}">${examEscapeHtml(label)}</span>
                    <p class="text-[11px] leading-relaxed ${textColor} mt-0.5">${examEscapeHtml(c.message)}</p>
                </div>
            </div>`;
    }).join('');

    const rowLabel = _examBatchData?.proposed?.[rowIdx]?.subject_code || `Row ${rowIdx + 1}`;

    tooltip.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-bold text-gray-800 dark:text-gray-100">Row ${rowIdx + 1} · ${examEscapeHtml(rowLabel)}</h4>
            <button onclick="document.getElementById('examBatchConflictTooltip')?.remove()" class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:ring-2 focus-visible:ring-gray-400/50">
                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            </button>
        </div>
        <div class="space-y-1.5 max-h-48 overflow-y-auto custom-scrollbar">${conflictHtml}</div>
    `;

    document.body.appendChild(tooltip);

    const closeHandler = (e) => {
        if (!tooltip.contains(e.target) && !row.contains(e.target)) {
            tooltip.remove();
            document.removeEventListener('click', closeHandler);
        }
    };
    setTimeout(() => document.addEventListener('click', closeHandler), 100);
}

function updateExamConflictSummary(summary) {
    const conflictBadge = document.getElementById('examBatchConflictBadge');
    const warningBadge = document.getElementById('examBatchWarningBadge');
    const allClearBadge = document.getElementById('examBatchAllClearBadge');
    const checkingBadge = document.getElementById('examBatchCheckingBadge');
    const conflictCount = document.getElementById('examBatchConflictCount');
    const warningCount = document.getElementById('examBatchWarningCount');

    if (checkingBadge) checkingBadge.classList.add('hidden');

    if (summary.total === 0) {
        if (conflictBadge) conflictBadge.classList.add('hidden');
        if (warningBadge) warningBadge.classList.add('hidden');
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateExamFooterBanner('empty');
        return;
    }

    if (summary.conflicts > 0) {
        if (conflictCount) conflictCount.textContent = summary.conflicts;
        if (conflictBadge) conflictBadge.classList.remove('hidden');
    } else {
        if (conflictBadge) conflictBadge.classList.add('hidden');
    }

    if (summary.warnings > 0) {
        if (warningCount) warningCount.textContent = summary.warnings;
        if (warningBadge) warningBadge.classList.remove('hidden');
    } else {
        if (warningBadge) warningBadge.classList.add('hidden');
    }

    if (summary.conflicts === 0 && summary.warnings === 0 && summary.ok > 0) {
        if (allClearBadge) allClearBadge.classList.remove('hidden');
        updateExamFooterBanner('ok');
    } else if (summary.conflicts > 0) {
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateExamFooterBanner('conflict', summary.conflicts);
    } else if (summary.warnings > 0) {
        if (allClearBadge) allClearBadge.classList.add('hidden');
        updateExamFooterBanner('warning', summary.warnings);
    }
}

function showExamConflictCheckingState() {
    const checkingBadge = document.getElementById('examBatchCheckingBadge');
    const allClearBadge = document.getElementById('examBatchAllClearBadge');
    if (checkingBadge) checkingBadge.classList.remove('hidden');
    if (allClearBadge) allClearBadge.classList.add('hidden');
}

function hideExamConflictCheckingState() {
    const checkingBadge = document.getElementById('examBatchCheckingBadge');
    if (checkingBadge) checkingBadge.classList.add('hidden');
}

function updateExamFooterBanner(status, count) {
    const banner = document.getElementById('examBatchFooterBanner');
    const icon = document.getElementById('examBatchFooterBannerIcon');
    const text = document.getElementById('examBatchFooterBannerText');
    if (!banner || !icon || !text) return;

    banner.className = 'px-4 sm:px-5 py-1.5 text-[11px] font-medium flex items-center gap-2 border-b border-gray-100 dark:border-gray-700';

    if (status === 'conflict') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-red-50', 'dark:bg-red-900/20', 'text-red-700', 'dark:text-red-300');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>';
        text.textContent = `${count} row(s) have conflicts — resolve before saving`;
    } else if (status === 'warning') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-amber-50', 'dark:bg-amber-900/20', 'text-amber-700', 'dark:text-amber-300');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        text.textContent = `${count} row(s) have warnings — review recommended`;
    } else if (status === 'ok') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-emerald-50', 'dark:bg-emerald-900/20', 'text-emerald-700', 'dark:text-emerald-300');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>';
        text.textContent = 'All exam schedules look good!';
    } else {
        banner.classList.add('hidden');
    }
}

// ─── Intra-batch Awareness ────────────────────────────────────────

function getExamIntraBatchAssignments(excludeRowIdx) {
    const rows = document.querySelectorAll('#examBatchTableBody tr');
    const assignments = [];
    rows.forEach((row, idx) => {
        if (idx === excludeRowIdx) return;
        const examDate = row.querySelector('[data-field="exam_date"]')?.value || '';
        const st = row.querySelector('[data-field="start_time"]')?.value || '';
        const et = row.querySelector('[data-field="end_time"]')?.value || '';
        const fid = row.querySelector('[data-field="faculty_id"]')?.value || '';
        const rid = row.querySelector('[data-field="room_id"]')?.value || '';
        const subjectCode = _examBatchData?.proposed?.[idx]?.subject_code || `Row ${idx + 1}`;
        if (examDate && st && et) {
            assignments.push({ idx, exam_date: examDate, start_time: st, end_time: et, faculty_id: fid, room_id: rid, subject_code: subjectCode });
        }
    });
    return assignments;
}

function examTimesOverlap(s1, e1, s2, e2) {
    return s1 < e2 && e1 > s2;
}

function buildExamBatchFacultyDayWarning(row) {
    if (!row) return null;

    const facultyId = row.querySelector('[data-field="faculty_id"]')?.value;
    const examDate = row.querySelector('[data-field="exam_date"]')?.value;
    const subjectId = row.dataset.subjectId;

    if (!facultyId || !examDate || !subjectId) return null;

    const parsedDate = new Date(`${examDate}T00:00:00`);
    if (Number.isNaN(parsedDate.getTime())) return null;

    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const examDayName = dayNames[parsedDate.getDay()];

    const facultyList = _examFacultyCache[subjectId] || [];
    const faculty = Array.isArray(facultyList)
        ? facultyList.find(item => String(item.id) === String(facultyId))
        : null;

    if (!faculty || !Array.isArray(faculty.available_days) || faculty.available_days.length === 0) {
        return null;
    }

    const normalizedDays = faculty.available_days.map(day => String(day).trim().toLowerCase());
    if (normalizedDays.includes(examDayName.toLowerCase())) {
        return null;
    }

    return {
        type: 'faculty_availability',
        severity: 'medium',
        message: `${faculty.full_name || 'Selected proctor'} is not marked as available on ${examDayName} at this time`,
        details: { faculty_id: facultyId, status: 'not_in_schedule' }
    };
}

// ─── Dropdown Positioning ─────────────────────────────────────────

function examPositionDropdown(triggerBtn, dropdown) {
    const rect = triggerBtn.getBoundingClientRect();
    const dropdownWidth = dropdown.offsetWidth || 260;
    const dropdownHeight = dropdown.offsetHeight || 240;
    const spaceBelow = window.innerHeight - rect.bottom;
    const spaceAbove = rect.top;
    const viewportPadding = 8;

    let left = rect.left;
    const maxLeft = window.innerWidth - dropdownWidth - viewportPadding;
    if (left > maxLeft) {
        left = Math.max(viewportPadding, maxLeft);
    }
    if (left < viewportPadding) {
        left = viewportPadding;
    }

    dropdown.style.left = left + 'px';

    if (spaceBelow >= dropdownHeight + 8 || spaceBelow >= spaceAbove) {
        dropdown.style.top = (rect.bottom + 4) + 'px';
        dropdown.style.bottom = 'auto';
    } else {
        dropdown.style.bottom = (window.innerHeight - rect.top + 4) + 'px';
        dropdown.style.top = 'auto';
    }
}

function examCloseAllDropdowns(except) {
    document.querySelectorAll('.exam-batch-proctor-dropdown, .exam-batch-room-dropdown').forEach(dd => {
        if (dd !== except) {
            dd.classList.add('hidden');
            dd.style.top = '';
            dd.style.left = '';
            dd.style.bottom = '';
        }
    });
    if (except && _examActiveDropdown !== except) _examActiveDropdown = null;
}

document.addEventListener('click', function(e) {
    if (!_examActiveDropdown) return;
    if (!_examActiveDropdown.contains(e.target) && !e.target.closest('.exam-batch-proctor-trigger') && !e.target.closest('.exam-batch-room-trigger')) {
        _examActiveDropdown.classList.add('hidden');
        _examActiveDropdown = null;
    }
});

// ─── Utilities ────────────────────────────────────────────────────

function showExamBatchError(message) {
    document.getElementById('examBatchErrorMsg').textContent = message;
    document.getElementById('examBatchError').classList.remove('hidden');
}

function examEscapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

// ─── Preferred Building ───────────────────────────────────────────

let _examPreferredBuildingId = null;

async function loadExamBuildingsForBatch() {
    const select = document.getElementById('examBatchBuildingSelect');
    if (!select) return;

    try {
        const res = await fetch('/schedule/get-buildings');
        const data = await res.json();
        const buildings = data.buildings || [];

        select.innerHTML = '<option value="">All Buildings</option>';
        buildings.forEach(b => {
            const opt = document.createElement('option');
            opt.value = b.id;
            opt.textContent = b.building_name;
            select.appendChild(opt);
        });

        if (_examPreferredBuildingId) {
            select.value = _examPreferredBuildingId;
        }
    } catch (e) {
        console.warn('Could not load buildings for exam batch:', e);
    }
}

function onExamBatchBuildingChange(value) {
    _examPreferredBuildingId = value ? parseInt(value) : null;
    // If data already rendered, regenerate with building preference
    if (_examBatchData && _examBatchSectionId) {
        document.getElementById('examBatchLoading').classList.remove('hidden');
        document.getElementById('examBatchResults').classList.add('hidden');
        document.getElementById('examBatchInlineViewToggle')?.classList.add('hidden');
        generateExamBatchPreview(_examBatchSectionId);
    }
}

// ─── Batch Exam Calendar View ─────────────────────────────────────

let _examBatchCurrentView = 'table'; // 'table' or 'calendar'

function switchExamBatchView(view) {
    _examBatchCurrentView = view;
    const tableView = document.getElementById('examBatchTableView');
    const calView = document.getElementById('examBatchCalendarView');
    const btnTable = document.getElementById('examBatchViewTable');
    const btnCal = document.getElementById('examBatchViewCalendar');
    if (!tableView || !calView) return;

    if (view === 'calendar') {
        tableView.classList.add('hidden');
        calView.classList.remove('hidden');
        btnTable.className = 'batch-view-toggle-btn batch-view-toggle-btn-inactive';
        btnCal.className = 'batch-view-toggle-btn batch-view-toggle-btn-active';
        buildExamBatchCalendar();
        syncExamBatchCalendarAlignment();
    } else {
        calView.classList.add('hidden');
        tableView.classList.remove('hidden');
        btnTable.className = 'batch-view-toggle-btn batch-view-toggle-btn-active';
        btnCal.className = 'batch-view-toggle-btn batch-view-toggle-btn-inactive';
        syncExamBatchCalendarAlignment();
    }
}

function buildExamBatchCalendar() {
    const header = document.getElementById('examBatchCalendarHeader');
    const body = document.getElementById('examBatchCalendarBody');
    if (!body || !header) return;

    // Gather current rows from the table
    const rows = document.querySelectorAll('#examBatchTableBody tr[data-row-index]');
    if (!rows.length) {
        body.innerHTML = '';
        syncExamBatchCalendarAlignment();
        return;
    }

    // Collect events and unique dates
    let minHour = 24, maxHour = 0;
    const events = [];
    const dateSet = new Set();

    rows.forEach(row => {
        const dateVal = row.querySelector('[data-field="exam_date"]')?.value;
        const st = row.querySelector('[data-field="start_time"]')?.value;
        const et = row.querySelector('[data-field="end_time"]')?.value;
        const subjectCode = (
            row.dataset.subjectCode ||
            row.querySelector('td:nth-child(3) [data-subject-code]')?.textContent ||
            row.querySelector('td:nth-child(3) .font-bold, td:nth-child(3) .font-semibold')?.textContent ||
            ''
        ).trim();
        const desc = row.querySelector('td:nth-child(3) .text-gray-400')?.getAttribute('title') || '';
        const roomName = row.querySelector('[data-field="room_name"]')?.value || '';
        const buildingName = row.querySelector('[data-field="building_name"]')?.value || '';
        const facultyName = row.querySelector('[data-field="faculty_name"]')?.value || '';
        const rowIdx = row.dataset.rowIndex;

        if (!dateVal || !st || !et) return;

        dateSet.add(dateVal);

        const [sh, sm] = st.split(':').map(Number);
        const [eh, em] = et.split(':').map(Number);

        if (sh < minHour) minHour = sh;
        if (eh > maxHour || (eh === maxHour && em > 0)) maxHour = em > 0 ? eh + 1 : eh;

        events.push({
            dateVal, startHour: sh, startMin: sm, endHour: eh, endMin: em,
            subjectCode, desc, roomName, buildingName, facultyName, rowIdx
        });
    });

    // Sort dates chronologically
    const sortedDates = [...dateSet].sort();

    // Use school settings for full day range (consistent with modal calendars)
    const globalStartHour = _examStartHour();
    let globalEndHour = _examEndHour();
    const examEndMin = window.examEndMinute || 0;
    
    // Expand the logical view to bound both events AND global limits
    minHour = Math.min(minHour, globalStartHour);
    let maxHourTotalMin = Math.max(maxHour * 60, globalEndHour * 60 + examEndMin);
    // Let's determine maxHour explicitly for grid looping
    maxHour = Math.ceil(maxHourTotalMin / 60);

    const totalHours = maxHour - minHour;
    const totalGridHeight = totalHours * 60;
    const colCount = sortedDates.length || 1;

    // Build header with date columns
    header.style.gridTemplateColumns = `56px repeat(${colCount}, 1fr)`;
    header.innerHTML = '<div class="week-time-header" style="font-size:0.6rem;">TIME</div>';
    sortedDates.forEach(dateStr => {
        const d = new Date(dateStr + 'T00:00:00');
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
        const label = `${monthNames[d.getMonth()]} ${d.getDate()} (${dayNames[d.getDay()]})`;
        const div = document.createElement('div');
        div.className = 'week-day-header';
        div.dataset.date = dateStr;
        div.textContent = label;
        header.appendChild(div);
    });

    // Build grid body
    body.style.gridTemplateColumns = `56px repeat(${colCount}, 1fr)`;
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

    // Date columns
    sortedDates.forEach(dateStr => {
        const dayCol = document.createElement('div');
        dayCol.className = 'week-day-column';
        dayCol.dataset.date = dateStr;
        // set height exactly up to maxHourTotalMin
        const dayColHeight = maxHourTotalMin - (minHour * 60);
        dayCol.style.minHeight = dayColHeight + 'px';

        // Hour & half-hour grid lines
        for (let m = 0; m < dayColHeight; m += 30) {
            const line = document.createElement('div');
            line.className = m % 60 === 0 ? 'week-hour-line' : 'week-half-hour-line';
            line.style.top = (m + 8) + 'px';
            dayCol.appendChild(line);
        }
        
        // Final bottom line
        const endLine = document.createElement('div');
        endLine.className = 'week-hour-line';
        endLine.style.top = (dayColHeight + 8) + 'px';
        dayCol.appendChild(endLine);

        // Events container
        const evContainer = document.createElement('div');
        evContainer.className = 'week-events-container';

        // Collect events for this date
        const dateEvents = events.filter(e => e.dateVal === dateStr);

        // Detect overlaps
        const overlapGroups = _detectExamBatchOverlaps(dateEvents);

        dateEvents.forEach(ev => {
            const top = ((ev.startHour - minHour) * 60 + ev.startMin) + 8;
            const height = Math.max(((ev.endHour - ev.startHour) * 60 + (ev.endMin - ev.startMin)), 20);

            const hasProctor = !!ev.facultyName;

            // Overlap stacking
            const group = overlapGroups.get(ev);
            let leftPct, rightPct;
            if (group && group.total > 1) {
                const w = 100 / group.total;
                leftPct = w * group.index;
                rightPct = 100 - w * (group.index + 1);
            }

            const evEl = document.createElement('div');
            evEl.className = 'week-event event-exam';
            evEl.style.top = top + 'px';
            evEl.style.height = height + 'px';
            evEl.style.cursor = 'pointer';
            if (group && group.total > 1) {
                evEl.style.left = leftPct + '%';
                evEl.style.right = rightPct + '%';
            }

            // Unassigned proctor → amber accent
            if (!hasProctor) {
                evEl.classList.add('event-unassigned');
                evEl.style.borderLeftColor = '#f59e0b';
                evEl.style.background = 'linear-gradient(135deg, #fffbeb 0%, #fef3c7 100%)';
            }

            const stFmt = _examFmtTime12(ev.startHour, ev.startMin);
            const etFmt = _examFmtTime12(ev.endHour, ev.endMin);
            const roomDisplay = ev.roomName || 'TBA';

            evEl.innerHTML = `
                <div class="event-content">
                    <div class="event-subject">${examEscapeHtml(ev.subjectCode)}</div>
                    ${height >= 45 ? `<div class="event-room">${examEscapeHtml(roomDisplay)}</div>` : ''}
                    ${height >= 60 ? `<div class="event-faculty">${hasProctor ? examEscapeHtml(ev.facultyName) : '<span style="color:#d97706">No proctor</span>'}</div>` : ''}
                    ${height >= 75 ? `<div class="event-time">${stFmt} - ${etFmt}</div>` : ''}
                </div>
            `;

            evEl.title = `${ev.subjectCode}\n${roomDisplay}${ev.buildingName ? ' · ' + ev.buildingName : ''}\n${hasProctor ? ev.facultyName : 'No proctor'}\n${stFmt} - ${etFmt}`;
            evEl.onclick = () => _focusExamBatchRow(ev.rowIdx);

            evContainer.appendChild(evEl);
        });

        dayCol.appendChild(evContainer);
        body.appendChild(dayCol);
    });

    syncExamBatchCalendarAlignment();
}

function _detectExamBatchOverlaps(dateEvents) {
    const map = new Map();
    if (!dateEvents.length) return map;

    const sorted = [...dateEvents].sort((a, b) => (a.startHour * 60 + a.startMin) - (b.startHour * 60 + b.startMin));

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

function _focusExamBatchRow(rowIdx) {
    switchExamBatchView('table');
    const row = document.querySelector(`#examBatchTableBody tr[data-row-index="${rowIdx}"]`);
    if (row) {
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
        row.classList.add('bg-orange-50', 'dark:bg-orange-900/20', 'ring-2', 'ring-orange-300', 'dark:ring-orange-700');
        setTimeout(() => { row.classList.remove('bg-orange-50', 'dark:bg-orange-900/20', 'ring-2', 'ring-orange-300', 'dark:ring-orange-700'); }, 2000);
    }
}

function _examFmtTime12(h, m) {
    const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
    const ampm = h >= 12 ? 'PM' : 'AM';
    return hr12 + ':' + String(m).padStart(2, '0') + ' ' + ampm;
}

function _refreshExamBatchCalendarIfVisible() {
    if (_examBatchCurrentView === 'calendar') {
        buildExamBatchCalendar();
    }
}

function _isExamBatchRowSaveable(row) {
    if (!row) return false;
    if (row.dataset.isExisting !== 'true') return true;
    return row.dataset.isDirty === 'true';
}

function _markExamBatchRowDirtyState(row) {
    if (!row || row.dataset.isExisting !== 'true') return;

    const original = {
        facultyId: row.dataset.originalFacultyId || '',
        roomId: row.dataset.originalRoomId || '',
        examDate: row.dataset.originalExamDate || '',
        start: row.dataset.originalStartTime || '',
        end: row.dataset.originalEndTime || ''
    };

    const current = {
        facultyId: String(row.querySelector('[data-field="faculty_id"]')?.value || ''),
        roomId: String(row.querySelector('[data-field="room_id"]')?.value || ''),
        examDate: String(row.querySelector('[data-field="exam_date"]')?.value || ''),
        start: String(row.querySelector('[data-field="start_time"]')?.value || ''),
        end: String(row.querySelector('[data-field="end_time"]')?.value || '')
    };

    const isDirty = (
        current.facultyId !== original.facultyId ||
        current.roomId !== original.roomId ||
        current.examDate !== original.examDate ||
        current.start !== original.start ||
        current.end !== original.end
    );

    row.dataset.isDirty = isDirty ? 'true' : 'false';
}
