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
let _batchCurricula = [];        // Available curricula for selected section
let _batchModeActive = false;    // Whether inline batch panel is visible
let _facultyCache = {};          // Cache faculty lists per subject_id
let _availableSubjects = null;   // Unscheduled subjects for "Add Subject"
let _activeDropdown = null;      // Currently open dropdown element
let _preferredBuildingId = null; // Soft room-filter hint; stays empty without configure step

// ─── Conflict Detection State ─────────────────────────────────────
let _batchConflicts = {};        // Map of rowIndex → { status, conflicts[] }
let _conflictCheckTimer = null;  // Debounce timer
let _conflictCheckInFlight = false; // Prevent duplicate requests
const CONFLICT_CHECK_DEBOUNCE_MS = 800;

// DAYS will be overridden by template-injected window.OPERATION_DAYS if available
const DAYS = (typeof window !== 'undefined' && window.OPERATION_DAYS) ? window.OPERATION_DAYS : ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
const BATCH_STATE_KEY = 'ischedwise_batch_mode';
const BATCH_CURRICULUM_MEMORY_KEY = 'ischedwise_curriculum_by_year';

function syncBatchCalendarAlignment() {
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

async function parseBatchApiJson(response, fallbackMessage) {
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

function resolveFullSectionName(sectionId, fallbackName) {
    const fallback = (fallbackName || '').trim();
    const switcher = document.getElementById('modalSectionSwitcher');
    if (!switcher || !sectionId) return fallback;

    const idStr = String(sectionId);
    const opt = Array.from(switcher.options).find(o => String(o.value) === idStr);
    if (!opt) return fallback;

    const fullName = (opt.dataset.name || opt.textContent || '').trim();
    return fullName || fallback;
}
// ─── Step Indicator & Progress Bar Helpers ────────────────────────

function _updateBatchStep(activeStep) {
    const steps = document.querySelectorAll('#batchStepIndicator .batch-step');
    const lines = document.querySelectorAll('#batchStepIndicator .batch-step-line');
    steps.forEach(s => {
        const step = parseInt(s.dataset.step);
        const dot = s.querySelector('.batch-step-dot');
        const label = s.querySelector('.batch-step-label');
        if (step < activeStep) {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-blue-600 text-white shadow-sm ring-2 ring-blue-200 dark:ring-blue-800';
            dot.innerHTML = '<svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/></svg>';
            if (label) { label.className = 'batch-step-label text-[11px] font-semibold text-blue-700 dark:text-blue-300 hidden sm:inline'; }
        } else if (step === activeStep) {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-blue-600 text-white shadow-sm ring-2 ring-blue-200 dark:ring-blue-800';
            dot.textContent = step;
            if (label) { label.className = 'batch-step-label text-[11px] font-semibold text-blue-700 dark:text-blue-300 hidden sm:inline'; }
        } else {
            dot.className = 'batch-step-dot w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold transition-all bg-gray-200 text-gray-400 dark:bg-gray-600 dark:text-gray-500';
            dot.textContent = step;
            if (label) { label.className = 'batch-step-label text-[11px] font-medium text-gray-400 dark:text-gray-500 hidden sm:inline'; }
        }
    });
    lines.forEach((line, i) => {
        line.className = 'batch-step-line w-10 sm:w-16 h-0.5 mx-2 rounded-full transition-all duration-500 ' + ((i + 1 < activeStep) ? 'bg-blue-400 dark:bg-blue-500' : 'bg-gray-200 dark:bg-gray-600');
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
    _batchCurricula = [];
    _batchModeActive = true;
    _facultyCache = {};
    _availableSubjects = null;
    _batchConflicts = {};
    _conflictCheckInFlight = false;
    if (_conflictCheckTimer) { clearTimeout(_conflictCheckTimer); _conflictCheckTimer = null; }

    // Reset step indicator to step 1
    _updateBatchStep(1);

    // Reset batch panel UI
    const displaySectionName = resolveFullSectionName(sectionId, sectionName);
    document.getElementById('autoScheduleSectionName').textContent = 'Section: ' + displaySectionName;
    document.getElementById('autoScheduleLoading').classList.remove('hidden');
    document.getElementById('autoScheduleError').classList.add('hidden');
    document.getElementById('autoScheduleCurriculumPrompt')?.classList.add('hidden');
    document.getElementById('autoScheduleAllDone').classList.add('hidden');
    document.getElementById('autoScheduleResults').classList.add('hidden');
    document.getElementById('autoScheduleStats').classList.add('hidden');
    document.getElementById('autoScheduleFooter').classList.add('hidden');
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');
    document.getElementById('batchAddSubjectBtn').classList.add('hidden');
    document.getElementById('batchInlineViewToggle')?.classList.add('hidden');

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
        iconAdd.classList.add('bg-blue-100', 'dark:bg-blue-900/30');
        if (iconSvg) {
            iconSvg.classList.remove('text-emerald-600', 'dark:text-emerald-400', 'text-blue-600', 'dark:text-blue-400', 'text-orange-600', 'dark:text-orange-400');
            iconSvg.classList.add('text-blue-600', 'dark:text-blue-300');
        }
    }
    if (iconEdit) {
        if (iconEdit._batchOriginalHidden === undefined) iconEdit._batchOriginalHidden = iconEdit.classList.contains('hidden');
        iconEdit.classList.add('hidden');
    }

    // Hide docked assistant while in batch mode
    if (typeof applyAIAssistantBatchLock === 'function') {
        applyAIAssistantBatchLock(true, 'class');
    } else if (typeof setAIAssistantDockVisible === 'function') {
        setAIAssistantDockVisible(false);
    } else {
        const aiBadge = document.getElementById('aiBadge');
        if (aiBadge) { aiBadge.classList.add('hidden'); aiBadge.classList.remove('flex'); }
        if (typeof closeAIDrawer === 'function') closeAIDrawer();
    }

    // Persist batch mode so a page refresh stays in batch
    sessionStorage.setItem(BATCH_STATE_KEY, 'class');

    // Load curricula first; preview starts only after explicit curriculum selection.
    if (document.getElementById('batchCurriculumSelect')) {
        _loadBatchCurriculaIntoSelector(sectionId);
    } else {
        // Legacy modal fallback when selector UI is unavailable.
        _startBatchPreview(sectionId);
    }
}

// ─── Curriculum Selection & Preview Gating ────────────────────────────

function _getBatchSectionOption(sectionId) {
    if (!sectionId) return null;

    const sectionIdStr = String(sectionId);
    const switcherIds = ['modalSectionSwitcher', 'section_id_add', 'section_id_edit', 'section_id'];

    for (const switcherId of switcherIds) {
        const switcher = document.getElementById(switcherId);
        if (!switcher) continue;

        const option = Array.from(switcher.options || []).find((candidate) => String(candidate.value) === sectionIdStr);
        if (option) return option;
    }

    return null;
}

function _getBatchCurriculumMemoryKey(sectionId) {
    const sectionOption = _getBatchSectionOption(sectionId);
    if (!sectionOption) return '';

    const yearLevel = String(sectionOption.dataset.yearLevel || '').trim();
    if (!yearLevel) return '';

    const programId = String(sectionOption.dataset.programId || '').trim() || '0';
    return `class:${programId}:${yearLevel}`;
}

function _readBatchCurriculumMemoryMap() {
    try {
        const raw = sessionStorage.getItem(BATCH_CURRICULUM_MEMORY_KEY);
        const parsed = raw ? JSON.parse(raw) : {};
        return parsed && typeof parsed === 'object' ? parsed : {};
    } catch (error) {
        return {};
    }
}

function _writeBatchCurriculumMemoryMap(memoryMap) {
    try {
        sessionStorage.setItem(BATCH_CURRICULUM_MEMORY_KEY, JSON.stringify(memoryMap));
    } catch (error) {
        // Ignore storage write failures and keep flow working.
    }
}

function _rememberBatchCurriculumId(sectionId, curriculumId) {
    if (!sectionId || !curriculumId) return;

    const memoryKey = _getBatchCurriculumMemoryKey(sectionId);
    if (!memoryKey) return;

    const memoryMap = _readBatchCurriculumMemoryMap();
    memoryMap[memoryKey] = String(curriculumId);
    _writeBatchCurriculumMemoryMap(memoryMap);
}

function _showBatchLoadingState(title, hint) {
    const loading = document.getElementById('autoScheduleLoading');
    const error = document.getElementById('autoScheduleError');
    const prompt = document.getElementById('autoScheduleCurriculumPrompt');
    const allDone = document.getElementById('autoScheduleAllDone');
    const results = document.getElementById('autoScheduleResults');
    const stats = document.getElementById('autoScheduleStats');
    const footer = document.getElementById('autoScheduleFooter');
    const addPanel = document.getElementById('batchAddSubjectPanel');
    const addBtn = document.getElementById('batchAddSubjectBtn');
    const viewToggle = document.getElementById('batchInlineViewToggle');
    const titleEl = document.getElementById('autoScheduleLoadingTitle');
    const hintEl = document.getElementById('autoScheduleLoadingHint');

    if (titleEl && title) titleEl.textContent = title;
    if (hintEl && hint) hintEl.textContent = hint;

    loading?.classList.remove('hidden');
    error?.classList.add('hidden');
    prompt?.classList.add('hidden');
    allDone?.classList.add('hidden');
    results?.classList.add('hidden');
    stats?.classList.add('hidden');
    footer?.classList.add('hidden');
    addPanel?.classList.add('hidden');
    addBtn?.classList.add('hidden');
    viewToggle?.classList.add('hidden');
}

function _showBatchCurriculumPrompt() {
    const loading = document.getElementById('autoScheduleLoading');
    const error = document.getElementById('autoScheduleError');
    const prompt = document.getElementById('autoScheduleCurriculumPrompt');
    const allDone = document.getElementById('autoScheduleAllDone');
    const results = document.getElementById('autoScheduleResults');
    const stats = document.getElementById('autoScheduleStats');
    const footer = document.getElementById('autoScheduleFooter');
    const addPanel = document.getElementById('batchAddSubjectPanel');
    const addBtn = document.getElementById('batchAddSubjectBtn');
    const viewToggle = document.getElementById('batchInlineViewToggle');

    loading?.classList.add('hidden');
    error?.classList.add('hidden');
    prompt?.classList.remove('hidden');
    allDone?.classList.add('hidden');
    results?.classList.add('hidden');
    stats?.classList.add('hidden');
    footer?.classList.add('hidden');
    addPanel?.classList.add('hidden');
    addBtn?.classList.add('hidden');
    viewToggle?.classList.add('hidden');
}

async function _loadBatchCurriculaIntoSelector(sectionId) {
    const curriculumSelect = document.getElementById('batchCurriculumSelect');
    const hint = document.getElementById('batchCurriculumHint');
    if (!curriculumSelect) return;

    _batchCurriculumId = null;
    _batchCurricula = [];
    curriculumSelect.disabled = true;
    curriculumSelect.innerHTML = '<option value="">Loading curricula...</option>';

    _showBatchLoadingState('Loading curricula...', 'Fetching available curricula for this section');

    try {
        const response = await fetch(`/schedule/get-curricula/${sectionId}`);
        const data = await parseBatchApiJson(response, 'Unable to load curricula');
        const curricula = Array.isArray(data.curricula) ? data.curricula : [];
        _batchCurricula = curricula;

        if (!curricula.length) {
            curriculumSelect.innerHTML = '<option value="">No curricula available</option>';
            curriculumSelect.disabled = true;
            if (hint) hint.textContent = 'No curricula are available for this section.';
            showBatchError('No curricula are available for this section.');
            return;
        }

        const memoryKey = _getBatchCurriculumMemoryKey(sectionId);
        const memoryMap = _readBatchCurriculumMemoryMap();
        const rememberedCurriculumId = memoryKey ? String(memoryMap[memoryKey] || '') : '';
        const hasRememberedCurriculum = rememberedCurriculumId
            && curricula.some((curriculum) => String(curriculum.id) === rememberedCurriculumId);

        curriculumSelect.innerHTML = '<option value="">Select a curriculum...</option>';
        curricula.forEach((curriculum) => {
            const option = document.createElement('option');
            option.value = curriculum.id;
            option.textContent = curriculum.display;
            curriculumSelect.appendChild(option);
        });

        curriculumSelect.disabled = false;

        if (hasRememberedCurriculum) {
            curriculumSelect.value = rememberedCurriculumId;
            if (hint) {
                hint.textContent = 'Select a curriculum to load schedule preview.';
            }
            await onBatchCurriculumSelectionChange(curriculumSelect);
            return;
        }

        curriculumSelect.value = '';
        if (hint) {
            hint.textContent = 'Select a curriculum to load schedule preview.';
        }

        _showBatchCurriculumPrompt();
    } catch (error) {
        console.error('[BATCH] Failed to load curricula:', error);
        curriculumSelect.innerHTML = '<option value="">Error loading curricula</option>';
        curriculumSelect.disabled = false;
        if (hint) hint.textContent = 'Unable to load curricula. Retry and select a curriculum.';
        showBatchError(error.message || 'Unable to load curricula for this section.');
        if (typeof showToast === 'function') {
            showToast(error.message || 'Unable to load curricula for this section.', 'error');
        }
    }
}

async function onBatchCurriculumSelectionChange(selectElement) {
    if (!_batchSectionId) return;

    const selectedValue = String(selectElement?.value || '').trim();
    if (!selectedValue) {
        _batchCurriculumId = null;
        _showBatchCurriculumPrompt();
        return;
    }

    _batchCurriculumId = parseInt(selectedValue, 10);
    if (!Number.isInteger(_batchCurriculumId) || _batchCurriculumId <= 0) {
        _batchCurriculumId = null;
        showBatchError('Invalid curriculum selection. Please choose a valid curriculum.');
        return;
    }

    _rememberBatchCurriculumId(_batchSectionId, _batchCurriculumId);
    await _startBatchPreview(_batchSectionId);
}

window.onBatchCurriculumSelectionChange = onBatchCurriculumSelectionChange;

function _syncBatchCurriculumToClassDetails(sectionId, curriculumId) {
    if (!sectionId || !curriculumId) return;

    const sectionIdStr = String(sectionId);
    const curriculumIdStr = String(curriculumId);

    const sectionInput = document.getElementById('section_id_add');
    if (sectionInput) {
        sectionInput.value = sectionIdStr;
    }

    const sectionSwitcher = document.getElementById('modalSectionSwitcher');
    if (sectionSwitcher) {
        sectionSwitcher.value = sectionIdStr;
    }

    if (typeof window.loadCurriculaForSection === 'function') {
        window.loadCurriculaForSection(sectionIdStr, 'add');
    }

    const applyCurriculumSelection = () => {
        const curriculumSelect = document.getElementById('curriculum_id_add');
        if (!curriculumSelect) return false;

        const hasMatchingOption = Array.from(curriculumSelect.options || []).some(
            (option) => String(option.value) === curriculumIdStr
        );
        if (!hasMatchingOption) return false;

        curriculumSelect.value = curriculumIdStr;
        if (typeof window.loadSubjectsForCurriculum === 'function') {
            window.loadSubjectsForCurriculum('add');
        } else {
            curriculumSelect.dispatchEvent(new Event('change', { bubbles: true }));
        }

        return true;
    };

    if (applyCurriculumSelection()) {
        return;
    }

    let attempts = 0;
    const maxAttempts = 20;
    const timer = setInterval(() => {
        attempts += 1;
        if (applyCurriculumSelection() || attempts >= maxAttempts) {
            clearInterval(timer);
        }
    }, 100);
}

async function _resolveBatchCurriculumId(sectionId) {
    const response = await fetch(`/schedule/get-curricula/${sectionId}`);
    const data = await parseBatchApiJson(response, 'Unable to load curricula');
    const curricula = data.curricula || [];

    if (!curricula.length) {
        throw new Error('No curricula are available for this section.');
    }

    const memoryKey = _getBatchCurriculumMemoryKey(sectionId);
    if (!memoryKey) {
        throw new Error('Cannot auto-resolve curriculum for this section. Select a curriculum first in regular scheduling.');
    }

    const memoryMap = _readBatchCurriculumMemoryMap();
    const rememberedCurriculumId = String(memoryMap[memoryKey] || '');
    if (!rememberedCurriculumId) {
        throw new Error('No remembered curriculum for this year level. Select a curriculum first in regular scheduling.');
    }

    const isRememberedCurriculumAvailable = curricula.some((curriculum) => String(curriculum.id) === rememberedCurriculumId);
    if (!isRememberedCurriculumAvailable) {
        throw new Error('Remembered curriculum is no longer available. Re-select curriculum in regular scheduling first.');
    }

    return parseInt(rememberedCurriculumId, 10);
}

async function _startBatchPreview(sectionId) {
    const hasSelector = !!document.getElementById('batchCurriculumSelect');

    try {
        if (!_batchCurriculumId) {
            if (hasSelector) {
                _showBatchCurriculumPrompt();
                return;
            }

            // Legacy fallback for old modal flows without selector UI.
            _batchCurriculumId = await _resolveBatchCurriculumId(sectionId);
        }

        _showBatchLoadingState(
            'Building schedule preview...',
            'Fast pass first, with optimized fallback when needed'
        );

        await generateBatchPreview(sectionId);
    } catch (error) {
        console.error('[BATCH] Curriculum preview bootstrap failed:', error);
        document.getElementById('autoScheduleLoading').classList.add('hidden');
        showBatchError(error.message || 'Unable to load schedule preview for the selected curriculum.');
        if (typeof showToast === 'function') {
            showToast(error.message || 'Unable to load schedule preview for the selected curriculum.', 'error');
        }
    }
}

function retryBatchPreview() {
    if (!_batchSectionId) return;

    if (document.getElementById('batchCurriculumSelect') && !_batchCurriculumId) {
        _showBatchCurriculumPrompt();
        if (typeof showToast === 'function') {
            showToast('Select a curriculum first to load schedule preview.', 'error');
        }
        return;
    }

    document.getElementById('autoScheduleError').classList.add('hidden');
    _startBatchPreview(_batchSectionId);
}

function exitBatchMode(silent) {
    const exitSectionId = _batchSectionId;
    const exitCurriculumId = _batchCurriculumId;

    // Clear persisted batch mode state
    sessionStorage.removeItem(BATCH_STATE_KEY);

    _batchModeActive = false;
    _batchData = null;
    _batchSectionId = null;
    _batchCurriculumId = null;
    _batchCurricula = [];
    _activeDropdown = null;
    _batchConflicts = {};
    _conflictCheckInFlight = false;
    if (_conflictCheckTimer) { clearTimeout(_conflictCheckTimer); _conflictCheckTimer = null; }

    const curriculumSelect = document.getElementById('batchCurriculumSelect');
    if (curriculumSelect) {
        curriculumSelect.value = '';
    }

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

    // Restore docked assistant
    if (typeof applyAIAssistantBatchLock === 'function') {
        applyAIAssistantBatchLock(false, 'class');
    } else if (typeof setAIAssistantDockVisible === 'function') {
        setAIAssistantDockVisible(true);
    } else {
        const aiBadge = document.getElementById('aiBadge');
        if (aiBadge) { aiBadge.classList.remove('hidden'); aiBadge.classList.add('flex'); }
    }

    _syncBatchCurriculumToClassDetails(exitSectionId, exitCurriculumId);
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
    _batchCurriculumId = null;
    _batchCurricula = [];
    _facultyCache = {};
    _availableSubjects = null;

    const displaySectionName = resolveFullSectionName(sectionId, sectionName);
    document.getElementById('autoScheduleSectionName').textContent = 'Section: ' + displaySectionName;
    document.getElementById('autoScheduleLoading').classList.remove('hidden');
    document.getElementById('autoScheduleError').classList.add('hidden');
    document.getElementById('autoScheduleAllDone').classList.add('hidden');
    document.getElementById('autoScheduleResults').classList.add('hidden');
    document.getElementById('autoScheduleStats').classList.add('hidden');
    document.getElementById('autoScheduleFooter').classList.add('hidden');
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';

    if (document.getElementById('batchCurriculumSelect')) {
        _loadBatchCurriculaIntoSelector(sectionId);
    } else {
        _startBatchPreview(sectionId);
    }
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

        // Update loading text for auto scheduling mode
        const loadTitle = document.getElementById('autoScheduleLoadingTitle');
        const loadHint = document.getElementById('autoScheduleLoadingHint');
        if (loadTitle && loadHint) {
            loadTitle.textContent = 'Building schedule preview...';
            loadHint.textContent = 'Fast pass first, with optimized fallback when needed';
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

        const proposedItems = Array.isArray(data.proposed) ? data.proposed : [];
        const existingItems = Array.isArray(data.existing) ? data.existing : [];
        const unplaceableItems = Array.isArray(data.unplaceable) ? data.unplaceable : [];

        const existingRows = existingItems.map(item => ({ ...item, is_existing: true }));
        const unplaceableRows = unplaceableItems.map(mapBatchUnplaceableToRowItem);
        data.proposed = existingRows.concat(proposedItems, unplaceableRows);
        // Keep unplaceable count in stats, but render all subjects directly in table rows.
        data.unplaceable = [];
        data.stats = data.stats || {};
        data.stats.already_scheduled = data.stats.already_scheduled || existingItems.length;

        const noNewProposals = proposedItems.length === 0;
        const noUnplaceable = unplaceableItems.length === 0;

        if (noNewProposals && noUnplaceable) {
            if (existingRows.length > 0) {
                _batchData = data;
                renderBatchResults(data);
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

function mapBatchUnplaceableToRowItem(item) {
    const scheduleType = (item?.schedule_type || 'lecture').toLowerCase();
    return {
        subject_id: item?.subject_id || null,
        subject_code: item?.subject_code || '',
        course_description: item?.course_description || '',
        schedule_type: scheduleType,
        faculty_id: null,
        faculty_name: '',
        room_id: null,
        room_name: '',
        building_name: '',
        day_of_week: 'Monday',
        start_time: '',
        end_time: '',
        lec_units: 0,
        lab_units: 0,
        total_units: 0,
        is_existing: false,
        unplaceable_reason: item?.reason || ''
    };
}

// ─── Render Results ───────────────────────────────────────────────

function renderBatchResults(data) {
    const stats = data.stats || {};

    // Step indicator: Review & Edit
    _updateBatchStep(1);

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
    document.getElementById('batchInlineViewToggle')?.classList.remove('hidden');

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

    // Initial conflict check — slight delay to let async faculty lists render
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
        btnTable.className = 'batch-view-toggle-btn batch-view-toggle-btn-inactive';
        btnCal.className = 'batch-view-toggle-btn batch-view-toggle-btn-active';
        buildBatchCalendar();
        syncBatchCalendarAlignment();
    } else {
        calView.classList.add('hidden');
        tableView.classList.remove('hidden');
        btnTable.className = 'batch-view-toggle-btn batch-view-toggle-btn-active';
        btnCal.className = 'batch-view-toggle-btn batch-view-toggle-btn-inactive';
        syncBatchCalendarAlignment();
    }
}

function buildBatchCalendar() {
    const body = document.getElementById('batchCalendarBody');
    if (!body) return;

    // Gather current rows from the table
    const rows = document.querySelectorAll('#autoScheduleTableBody tr[data-row-index]');
    if (!rows.length) {
        body.innerHTML = '';
        syncBatchCalendarAlignment();
        return;
    }

    // Determine time range from data
    let minHour = 24, maxHour = 0;
    const events = [];

    rows.forEach(row => {
        const day = row.querySelector('[data-field="day_of_week"]')?.value;
        const st = row.querySelector('[data-field="start_time"]')?.value;
        const et = row.querySelector('[data-field="end_time"]')?.value;
        const type = row.querySelector('[data-field="schedule_type"]')?.value || 'lecture';
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

    syncBatchCalendarAlignment();
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
        row.classList.add('bg-blue-50', 'dark:bg-blue-900/20', 'ring-2', 'ring-blue-300', 'dark:ring-blue-700');
        setTimeout(() => { row.classList.remove('bg-blue-50', 'dark:bg-blue-900/20', 'ring-2', 'ring-blue-300', 'dark:ring-blue-700'); }, 2000);
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

function _isBatchRowSaveable(row) {
    if (!row) return false;
    if (row.dataset.isExisting !== 'true') return true;
    return row.dataset.isDirty === 'true';
}

function _markBatchRowDirtyState(row) {
    if (!row || row.dataset.isExisting !== 'true') return;

    const original = {
        scheduleType: row.dataset.originalScheduleType || '',
        facultyId: row.dataset.originalFacultyId || '',
        roomId: row.dataset.originalRoomId || '',
        day: row.dataset.originalDayOfWeek || '',
        start: row.dataset.originalStartTime || '',
        end: row.dataset.originalEndTime || ''
    };

    const current = {
        scheduleType: String(row.querySelector('[data-field="schedule_type"]')?.value || ''),
        facultyId: String(row.querySelector('[data-field="faculty_id"]')?.value || ''),
        roomId: String(row.querySelector('[data-field="room_id"]')?.value || ''),
        day: String(row.querySelector('[data-field="day_of_week"]')?.value || ''),
        start: String(row.querySelector('[data-field="start_time"]')?.value || ''),
        end: String(row.querySelector('[data-field="end_time"]')?.value || '')
    };

    const isDirty = (
        current.scheduleType !== original.scheduleType ||
        current.facultyId !== original.facultyId ||
        current.roomId !== original.roomId ||
        current.day !== original.day ||
        current.start !== original.start ||
        current.end !== original.end
    );

    row.dataset.isDirty = isDirty ? 'true' : 'false';
}

function buildBatchRow(item, idx) {
    const row = document.createElement('tr');
    const isExisting = item.is_existing === true || item.is_existing === 'true';
    row.className = 'hover:bg-blue-50/30 dark:hover:bg-gray-750 transition-all group';
    row.dataset.rowIndex = idx;
    row.dataset.subjectId = item.subject_id;
    row.dataset.isExisting = isExisting ? 'true' : 'false';
    row.dataset.subjectCode = item.subject_code || '';
    row.dataset.lecUnits = item.lec_units || 0;
    row.dataset.labUnits = item.lab_units || 0;
    row.dataset.scheduleId = item.schedule_id || '';
    row.dataset.isDirty = 'false';
    row.dataset.originalScheduleType = item.schedule_type || 'lecture';
    row.dataset.originalFacultyId = item.faculty_id ? String(item.faculty_id) : '';
    row.dataset.originalRoomId = item.room_id ? String(item.room_id) : '';
    row.dataset.originalDayOfWeek = item.day_of_week || 'Monday';
    row.dataset.originalStartTime = item.start_time || '';
    row.dataset.originalEndTime = item.end_time || '';

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
        <td class="px-3 py-2.5 text-center">
            <div class="batch-status-icon flex items-center justify-center" title="Pending conflict check">
                <div class="w-5 h-5 rounded-full bg-gray-100 dark:bg-gray-700 flex items-center justify-center">
                    <svg class="w-2.5 h-2.5 text-gray-400" fill="currentColor" viewBox="0 0 24 24"><circle cx="12" cy="12" r="4"/></svg>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 text-center">
            <span class="batch-row-num text-[10px] font-medium text-gray-400 tabular-nums">${idx + 1}</span>
        </td>
        <td class="px-3 py-2.5 min-w-0">
            <div class="inline-flex items-center gap-1 mb-0.5">
                <span data-subject-code class="font-bold text-gray-900 dark:text-gray-100 text-[11px] leading-tight">${escapeHtml(item.subject_code)}</span>
            </div>
            <div class="text-gray-400 dark:text-gray-500 truncate max-w-[160px] text-[10px] leading-tight" title="${escapeHtml(item.course_description || '')}">${escapeHtml(item.course_description || '')}</div>
        </td>
        <td class="px-3 py-2.5">
            <div class="flex items-center gap-1">
                ${typeDot}
                <select data-field="schedule_type" onchange="onTypeChange(this)" class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800 w-[52px] cursor-pointer">
                    ${typeOptions}
                </select>
            </div>
        </td>
        <td class="px-3 py-2.5 relative">
            <div class="batch-faculty-picker" data-row="${idx}">
                <button type="button" onclick="toggleBatchFacultyDropdown(this, ${idx})"
                        class="batch-faculty-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasFaculty
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-blue-300'
                            : 'border-dashed border-amber-400 bg-amber-50 dark:bg-amber-900/20 text-amber-700 dark:text-amber-400 hover:border-amber-500'}"
                        title="${hasFaculty ? '' : 'Faculty not assigned'}">
                    ${!hasFaculty ? '<svg class="batch-faculty-warning-icon w-3 h-3 flex-shrink-0 text-amber-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01M12 2a10 10 0 100 20 10 10 0 000-20z"/></svg>' : ''}
                    <span class="batch-faculty-label truncate flex-1 min-w-0">${hasFaculty ? escapeHtml(facultyDisplay) : 'Assign Faculty'}</span>
                    <svg class="w-3 h-3 flex-shrink-0 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"/></svg>
                </button>
                <input type="hidden" data-field="faculty_id" value="${item.faculty_id || ''}">
                <input type="hidden" data-field="faculty_name" value="${escapeHtml(facultyDisplay)}">
                <div class="batch-faculty-dropdown hidden fixed z-[9999] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl w-[290px] max-h-[260px] flex flex-col overflow-hidden">
                    <div class="p-2 border-b border-gray-100 dark:border-gray-700 flex-shrink-0">
                        <input type="text" placeholder="Search faculty..." class="batch-faculty-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800" oninput="filterBatchFacultyDropdown(this, ${idx})">
                    </div>
                    <div class="batch-faculty-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5">
            <select data-field="day_of_week" onchange="onDayTimeChange(this)" class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800 w-[70px] cursor-pointer">
                ${dayOptions}
            </select>
        </td>
        <td class="px-3 py-2.5 whitespace-nowrap">
            <div class="flex items-center gap-0.5">
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="start_time"
                     data-value="${item.start_time || ''}"
                     data-onchange="onStartTimeChange(input)"
                     data-input-class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800 min-w-[96px] sm:w-[104px]">
                </div>
                <span class="text-gray-300 dark:text-gray-600 text-[9px] select-none px-0.5">–</span>
                <div class="custom-time-picker !w-fit" data-time-picker
                     data-hidden-field="end_time"
                     data-value="${item.end_time || ''}"
                     data-onchange="onEndTimeChange(input)"
                     data-input-class="batch-field text-[10px] px-1.5 py-1 rounded-md border border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800 min-w-[96px] sm:w-[104px]">
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 relative">
            <div class="batch-room-picker" data-row="${idx}">
                <button type="button" onclick="toggleBatchRoomDropdown(this, ${idx})"
                        class="batch-room-trigger w-full text-left px-2 py-1.5 rounded-md border text-[11px] flex items-center justify-between gap-1 min-w-0 transition-colors
                        ${hasRoom
                            ? 'border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-200 hover:border-blue-300'
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
                        <input type="text" placeholder="Search rooms..." class="batch-room-search w-full text-[11px] px-2.5 py-1.5 rounded-lg border border-gray-200 dark:border-gray-600 bg-gray-50 dark:bg-gray-700 dark:text-gray-200 focus:border-blue-400 dark:focus:border-blue-500 focus:bg-white dark:focus:bg-gray-600 focus:ring-1 focus:ring-blue-200 dark:focus:ring-blue-800" oninput="filterBatchRoomDropdown(this, ${idx})">
                    </div>
                    <div class="batch-room-list flex-1 overflow-y-auto custom-scrollbar" data-row="${idx}">
                        <div class="p-3 text-center text-[10px] text-gray-400">Loading...</div>
                    </div>
                </div>
            </div>
        </td>
        <td class="px-3 py-2.5 text-center">
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
    if (list) list.innerHTML = '';
    if (section) section.classList.add('hidden');
}

// ─── Faculty Dropdown ─────────────────────────────────────────────

async function loadFacultyForRow(rowIdx, subjectId) {
    if (_facultyCache[subjectId]) {
        renderFacultyOptions(rowIdx, _facultyCache[subjectId]);
        applyHybridFacultyDefaultForRow(rowIdx, _facultyCache[subjectId]);
        return;
    }
    try {
        const res = await fetch(`/schedule/get-faculty/${subjectId}`);
        const data = await res.json();
        _facultyCache[subjectId] = data.faculty || [];
        renderFacultyOptions(rowIdx, _facultyCache[subjectId]);
        applyHybridFacultyDefaultForRow(rowIdx, _facultyCache[subjectId]);
    } catch (e) {
        console.error('Failed to load faculty for subject', subjectId, e);
    }
}

function applyHybridFacultyDefaultForRow(rowIdx, facultyList) {
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    const facultyIdInput = row.querySelector('[data-field="faculty_id"]');
    const currentFacultyId = String(facultyIdInput?.value || '').trim();

    // Preserve existing selection (e.g., existing schedule rows or manual picks).
    if (currentFacultyId && currentFacultyId !== 'null' && currentFacultyId !== 'undefined') {
        return;
    }

    const list = Array.isArray(facultyList) ? facultyList : [];
    const assignedFaculty = list.filter(f => f && f.is_assigned);

    // Hybrid rule: auto-select only for a single assigned match.
    if (assignedFaculty.length === 1) {
        const selected = assignedFaculty[0];
        selectBatchFaculty(rowIdx, selected.id, selected.full_name);
        return;
    }

    // Reset for none/ambiguous assignment cases.
    row.querySelector('[data-field="faculty_id"]').value = '';
    row.querySelector('[data-field="faculty_name"]').value = '';
    setBatchFacultyTriggerState(row, '', '');
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
        opt.className = 'batch-faculty-option px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 cursor-pointer transition-colors flex items-center justify-between gap-2' + (batchConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
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

function setBatchFacultyTriggerState(row, facultyId, facultyName) {
    const trigger = row?.querySelector('.batch-faculty-trigger');
    if (!trigger) return;

    const label = trigger.querySelector('.batch-faculty-label');
    const normalizedId = String(facultyId || '').trim();
    const hasFaculty = !!normalizedId && normalizedId !== 'null' && normalizedId !== 'undefined';
    const safeName = String(facultyName || '').trim();

    const assignedClasses = [
        'border-gray-200', 'dark:border-gray-600', 'bg-white', 'dark:bg-gray-700',
        'text-gray-700', 'dark:text-gray-200', 'hover:border-blue-300'
    ];
    const unassignedClasses = [
        'border-dashed', 'border-amber-400', 'border-amber-300', 'bg-amber-50', 'dark:bg-amber-900/20',
        'text-amber-700', 'dark:text-amber-400', 'text-amber-600', 'hover:border-amber-500'
    ];

    trigger.classList.remove(...assignedClasses, ...unassignedClasses);
    trigger.classList.add(...(hasFaculty ? assignedClasses : unassignedClasses));
    trigger.title = hasFaculty ? '' : 'Faculty not assigned';

    if (label) {
        label.textContent = hasFaculty ? (safeName || 'Assigned Faculty') : 'Assign Faculty';
    }

    let warningIcon = trigger.querySelector('.batch-faculty-warning-icon');
    if (hasFaculty) {
        if (warningIcon) warningIcon.remove();
    } else if (!warningIcon) {
        warningIcon = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        warningIcon.setAttribute('class', 'batch-faculty-warning-icon w-3 h-3 flex-shrink-0 text-amber-500');
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

function selectBatchFaculty(rowIdx, facultyId, facultyName) {
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    if (!row) return;

    row.querySelector('[data-field="faculty_id"]').value = facultyId;
    row.querySelector('[data-field="faculty_name"]').value = facultyName;
    setBatchFacultyTriggerState(row, facultyId, facultyName);

    const dropdown = row.querySelector('.batch-faculty-dropdown');
    if (dropdown) dropdown.classList.add('hidden');
    _activeDropdown = null;

    _markBatchRowDirtyState(row);

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
    const scheduleId = row.dataset.scheduleId || '';

    if (!day || !startTime || !endTime) return;

    const list = row.querySelector('.batch-room-list');
    list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">Loading rooms...</div>';

    try {
        const params = new URLSearchParams({ day, start_time: startTime, end_time: endTime, schedule_type: scheduleType });
        if (subjectId) params.set('subject_id', subjectId);
        if (scheduleId) params.set('schedule_id', scheduleId);
        const hasPreferredBuilding = !!_preferredBuildingId;
        if (hasPreferredBuilding) params.set('building_id', _preferredBuildingId);

        const res = await fetch(`/schedule/batch-available-rooms?${params}`);
        const data = await res.json();

        let rooms = data.rooms || [];
        let usedFallback = false;

        // Preferred building is a soft hint only; if no options, retry once without building hint.
        if (hasPreferredBuilding && rooms.length === 0) {
            const fallbackParams = new URLSearchParams(params);
            fallbackParams.delete('building_id');
            const fallbackRes = await fetch(`/schedule/batch-available-rooms?${fallbackParams}`);
            const fallbackData = await fallbackRes.json();
            rooms = fallbackData.rooms || [];
            usedFallback = rooms.length > 0;
        }

        renderRoomOptions(rowIdx, rooms, usedFallback);
    } catch (e) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-red-400">Failed to load rooms</div>';
    }
}

function renderRoomOptions(rowIdx, rooms, usedFallback = false) {
    const list = document.querySelector(`.batch-room-list[data-row="${rowIdx}"]`);
    if (!list) return;

    if (!rooms || rooms.length === 0) {
        list.innerHTML = '<div class="p-3 text-center text-[10px] text-gray-400">No rooms found</div>';
        return;
    }

    // Get current row's day/time for intra-batch comparison
    const row = document.querySelector(`#autoScheduleTableBody tr[data-row-index="${rowIdx}"]`);
    const curDay = row?.querySelector('[data-field="day_of_week"]')?.value || '';
    const curSt = row?.querySelector('[data-field="start_time"]')?.value || '';
    const curEt = row?.querySelector('[data-field="end_time"]')?.value || '';
    const otherAssignments = getIntraBatchAssignments(rowIdx);

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

        // Check if this room is used by another batch row at overlapping time
        let batchConflictLabel = '';
        for (const other of otherAssignments) {
            if (other.room_id == r.id && other.day === curDay && timesOverlap(curSt, curEt, other.start_time, other.end_time)) {
                batchConflictLabel = `Used by Row ${other.idx + 1} (${other.subject_code})`;
                break;
            }
        }

        const hasConflictLabel = Boolean(isOccupied || batchConflictLabel);

        const opt = document.createElement('div');
        opt.className = 'batch-room-option px-3 py-2 hover:bg-blue-50 dark:hover:bg-blue-900/30 cursor-pointer transition-colors' + (hasConflictLabel ? ' bg-red-50/60 dark:bg-red-900/20' : '');
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
                <div class="flex items-center gap-1.5 flex-shrink-0">
                    ${isOccupied && occupiedLabel ? `<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300 font-medium whitespace-nowrap">${escapeHtml(occupiedLabel)}</span>` : ''}
                    ${batchConflictLabel ? `<span class="text-[9px] px-1.5 py-0.5 rounded-full bg-red-100 text-red-600 dark:bg-red-900/40 dark:text-red-400 font-medium whitespace-nowrap">${escapeHtml(batchConflictLabel)}</span>` : ''}
                </div>
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

    _markBatchRowDirtyState(row);

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

    _markBatchRowDirtyState(row);

    scheduleConflictCheck();
    validateAllRows();
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
    _markBatchRowDirtyState(row);
    scheduleConflictCheck();
    validateAllRows();
    _refreshBatchCalendarIfVisible();
}

function onEndTimeChange(input) {
    // End time manually changed — trigger conflict check
    const row = input.closest('tr');
    _markBatchRowDirtyState(row);
    scheduleConflictCheck();
    validateAllRows();
    _refreshBatchCalendarIfVisible();
}

function onDayTimeChange(select) {
    // Room availability may have changed - clear room cache visual hint
    // The room dropdown reloads when opened, so no action needed here
    const row = select.closest('tr');
    _markBatchRowDirtyState(row);

    const rowIdx = parseInt(row.dataset.rowIndex, 10);
    const dayWarning = buildBatchFacultyDayWarning(row);
    if (dayWarning && Number.isInteger(rowIdx)) {
        _batchConflicts[rowIdx] = { status: 'warning', conflicts: [dayWarning] };
        renderRowConflictStatus(row, rowIdx, _batchConflicts[rowIdx]);
    }

    const hasFullConflictPayload = Boolean(
        row.querySelector('[data-field="faculty_id"]')?.value &&
        row.querySelector('[data-field="day_of_week"]')?.value &&
        row.querySelector('[data-field="start_time"]')?.value &&
        row.querySelector('[data-field="end_time"]')?.value
    );

    if (hasFullConflictPayload) {
        showConflictCheckingState();
        if (_conflictCheckTimer) {
            clearTimeout(_conflictCheckTimer);
            _conflictCheckTimer = null;
        }
        performBatchConflictCheck();
    } else {
        scheduleConflictCheck();
    }

    validateAllRows();
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

        select.innerHTML = '<option value="">Select a subject to add...</option>';

        _availableSubjects.forEach((s, i) => {
            const opt = document.createElement('option');
            opt.value = i;
            opt.textContent = `${s.subject_code} - ${s.course_description} (${s.schedule_type}, ${s.duration_minutes}min)`;
            select.appendChild(opt);
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

    // Keep option available so users can intentionally add duplicate subjects
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
    row.classList.add('bg-blue-50', 'dark:bg-blue-900/20');
    setTimeout(() => row.classList.remove('bg-blue-50', 'dark:bg-blue-900/20'), 1500);

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
        if (!_isBatchRowSaveable(row)) return;

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
    let saveableRows = 0;

    rows.forEach((row, idx) => {
        _markBatchRowDirtyState(row);
        if (!_isBatchRowSaveable(row)) return;

        saveableRows++;
        const hasFaculty = isFacultyAssignedForRow(row);
        const facultyId = row.querySelector('[data-field="faculty_id"]')?.value;
        const facultyName = row.querySelector('[data-field="faculty_name"]')?.value;
        setBatchFacultyTriggerState(row, hasFaculty ? facultyId : '', facultyName);
        const roomId = row.querySelector('[data-field="room_id"]')?.value;
        const startTime = row.querySelector('[data-field="start_time"]')?.value;
        const endTime = row.querySelector('[data-field="end_time"]')?.value;

        if (!hasFaculty) {
            missingFaculty++;
            facultyRowDetails.push({
                row: idx + 1,
                reason: _getFacultyResolveReason(row)
            });
        }
        if (!roomId) missingRoom++;
        if (!startTime || !endTime || startTime >= endTime) invalidTime++;
    });

    const confirmBtn = document.getElementById('autoScheduleConfirmBtn');
    const msgEl = document.getElementById('batchValidationMsg');
    const msgText = document.getElementById('batchValidationText');

    if (rows.length === 0 || saveableRows === 0) {
        confirmBtn.disabled = true;
        msgEl.classList.add('hidden');
        updateFooterBanner('empty');
        return;
    }

    const reasonLabel = (reason) => {
        switch (reason) {
            case 'missing selection':
                return 'faculty not selected';
            case 'no faculty candidates loaded':
                return 'no available faculty loaded yet';
            case 'name does not match available faculty':
                return 'selected name does not match available faculty';
            case 'ambiguous faculty name':
                return 'multiple faculty match this name';
            case 'missing id sync':
                return 'faculty selection not synced yet';
            default:
                return reason || 'faculty issue';
        }
    };

    const formIssues = [];
    if (missingFaculty > 0) formIssues.push(`${missingFaculty} row${missingFaculty > 1 ? 's' : ''} missing faculty assignment`);
    if (missingRoom > 0) formIssues.push(`${missingRoom} row${missingRoom > 1 ? 's' : ''} missing room`);
    if (invalidTime > 0) formIssues.push(`${invalidTime} row${invalidTime > 1 ? 's' : ''} with invalid time range`);

    // Check conflict state — count rows with CRITICAL/HIGH conflicts
    let conflictRows = 0;
    Object.entries(_batchConflicts).forEach(([idx, r]) => {
        if (r.status !== 'conflict') return;
        const row = rows[parseInt(idx, 10)];
        if (_isBatchRowSaveable(row)) conflictRows++;
    });

    const hasFormIssues = formIssues.length > 0;
    const hasConflicts = conflictRows > 0;

    if (hasFormIssues || hasConflicts) {
        confirmBtn.disabled = true;
        const allIssues = [...formIssues];
        if (facultyRowDetails.length > 0) {
            const examples = facultyRowDetails
                .slice(0, 3)
                .map(entry => `Row ${entry.row}: ${reasonLabel(entry.reason)}`)
                .join(' · ');
            allIssues.push(`Examples — ${examples}`);
        }
        if (allIssues.length > 0) {
            msgText.textContent = allIssues.join(', ');
            msgEl.classList.remove('hidden');
        } else {
            msgEl.classList.add('hidden');
        }
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
    const allRows = document.querySelectorAll('#autoScheduleTableBody tr');
    const conflictRows = Object.entries(_batchConflicts)
        .filter(([idx, r]) => r.status === 'conflict' && _isBatchRowSaveable(allRows[parseInt(idx, 10)]));
    if (conflictRows.length > 0) {
        if (typeof showToast === 'function') showToast('Some rows still need review before saving.', 'error');
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
            const updated = result.updated || 0;
            if (rowErrors.length > 0) {
                if (typeof showToast === 'function') {
                    showToast(`Saved ${result.created + updated} schedule(s) (${result.created} created, ${updated} updated). ${rowErrors.length} row(s) were skipped.`, 'error');
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
            _updateBatchStep(2);
            if (typeof showToast === 'function') {
                showToast(`Saved ${result.created + updated} schedule(s) (${result.created} created, ${updated} updated).`, 'success');
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
        _markBatchRowDirtyState(row);
        if (!_isBatchRowSaveable(row)) return;

        // Self-heal any row where faculty is visible but hidden id was not synced yet.
        resolveFacultyIdForRow(row);

        const original = (_batchData && _batchData.proposed && _batchData.proposed[idx]) || {};

        const rowObj = {
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
        };

        const scheduleId = parseInt(row.dataset.scheduleId) || original.schedule_id;
        if (row.dataset.isExisting === 'true' && scheduleId) {
            rowObj.schedule_id = scheduleId;
            rowObj.is_existing = true;
        }

        items.push(rowObj);
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

    // Remove old state classes
    row.classList.remove('bg-red-50/50', 'dark:bg-red-900/20', 'bg-amber-50/50', 'dark:bg-amber-900/20');

    if (result.status === 'conflict') {
        // CRITICAL/HIGH — red
        row.classList.add('bg-red-50/50', 'dark:bg-red-900/20');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-red-100 dark:bg-red-900/40 flex items-center justify-center hover:bg-red-200 dark:hover:bg-red-900/60 focus-visible:ring-2 focus-visible:ring-red-400/60 transition-colors cursor-pointer" title="${count} issue(s) — click for details">
                <svg class="w-3 h-3 text-red-600 dark:text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/></svg>
            </button>`;
    } else if (result.status === 'warning') {
        // MEDIUM/LOW — amber
        row.classList.add('bg-amber-50/50', 'dark:bg-amber-900/20');
        const count = result.conflicts.length;
        statusCell.innerHTML = `
            <button type="button" onclick="showRowConflictTooltip(${idx})" class="w-5 h-5 rounded-full bg-amber-100 dark:bg-amber-900/40 flex items-center justify-center hover:bg-amber-200 dark:hover:bg-amber-900/60 focus-visible:ring-2 focus-visible:ring-amber-400/60 transition-colors cursor-pointer" title="${count} warning(s) — click for details">
                <svg class="w-3 h-3 text-amber-600 dark:text-amber-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>
            </button>`;
    } else {
        // OK — green
        statusCell.innerHTML = `
            <div class="w-5 h-5 rounded-full bg-emerald-100 dark:bg-emerald-900/40 flex items-center justify-center" title="No conflicts">
                <svg class="w-3 h-3 text-emerald-600 dark:text-emerald-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
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
    tooltip.className = 'fixed z-[10000] bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-2xl p-3 max-w-sm w-80';
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
                    <span class="text-[10px] font-bold tracking-wide uppercase ${textColor}">${escapeHtml(label)}</span>
                    <p class="text-[11px] leading-relaxed ${textColor} mt-0.5">${escapeHtml(c.message)}</p>
                </div>
            </div>`;
    }).join('');

    const rowLabel = row.dataset.subjectId ? ((_batchData?.proposed?.[rowIdx]?.subject_code) || `Row ${rowIdx + 1}`) : `Row ${rowIdx + 1}`;

    tooltip.innerHTML = `
        <div class="flex items-center justify-between mb-2">
            <h4 class="text-xs font-bold text-gray-800 dark:text-gray-100">Row ${rowIdx + 1} · ${escapeHtml(rowLabel)}</h4>
            <button onclick="document.getElementById('batchConflictTooltip')?.remove()" class="p-0.5 rounded hover:bg-gray-100 dark:hover:bg-gray-700 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300 focus-visible:ring-2 focus-visible:ring-gray-400/50">
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
        banner.classList.add('hidden');
    } else if (status === 'warning') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-amber-50', 'dark:bg-amber-900/20', 'text-amber-700', 'dark:text-amber-300');
        icon.innerHTML = '<svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/></svg>';
        text.textContent = `${count} row(s) have warnings — review recommended`;
    } else if (status === 'ok') {
        banner.classList.remove('hidden');
        banner.classList.add('bg-emerald-50', 'dark:bg-emerald-900/20', 'text-emerald-700', 'dark:text-emerald-300');
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

function buildBatchFacultyDayWarning(row) {
    if (!row) return null;

    const facultyId = row.querySelector('[data-field="faculty_id"]')?.value;
    const dayOfWeek = row.querySelector('[data-field="day_of_week"]')?.value;
    const subjectId = row.dataset.subjectId;

    if (!facultyId || !dayOfWeek || !subjectId) return null;

    const facultyList = _facultyCache[subjectId] || [];
    const faculty = Array.isArray(facultyList)
        ? facultyList.find(item => String(item.id) === String(facultyId))
        : null;

    if (!faculty || !Array.isArray(faculty.available_days) || faculty.available_days.length === 0) {
        return null;
    }

    const normalizedDays = faculty.available_days.map(day => String(day).trim().toLowerCase());
    if (normalizedDays.includes(String(dayOfWeek).trim().toLowerCase())) {
        return null;
    }

    return {
        type: 'faculty_availability',
        severity: 'medium',
        message: `${faculty.full_name || 'Selected faculty'} is not marked as available on ${dayOfWeek} at this time`,
        details: { faculty_id: facultyId, status: 'not_in_schedule' }
    };
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
    document.getElementById('autoScheduleLoading').classList.add('hidden');
    document.getElementById('autoScheduleCurriculumPrompt')?.classList.add('hidden');
    document.getElementById('autoScheduleResults').classList.add('hidden');
    document.getElementById('autoScheduleStats').classList.add('hidden');
    document.getElementById('autoScheduleFooter').classList.add('hidden');
    document.getElementById('batchAddSubjectPanel').classList.add('hidden');
    document.getElementById('batchAddSubjectBtn').classList.add('hidden');
    document.getElementById('batchInlineViewToggle')?.classList.add('hidden');
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
