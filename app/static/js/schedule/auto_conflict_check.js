/**
 * Automatic Conflict Detection System
 * Automatically checks for schedule conflicts when form fields change
 * and prevents submission until conflicts are resolved
 */

// Debounce timer to prevent excessive API calls
let autoCheckDebounceTimer = null;
const AUTO_CHECK_DEBOUNCE_MS = 800;
const AUTO_CHECK_RETRY_DELAY_MS = 150;
const AUTO_CHECK_MAX_RETRIES = 8;

// Track current conflict state
let hasConflictsAdd = false;
let hasConflictsEdit = false;
let autoCheckFieldObserver = null;
let autoCheckRebindTimer = null;
const classAutoCheckCompletionState = {
    add: false,
    edit: false
};

function getAutoCheckFieldIds(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    return [
        'curriculum_id' + suffix,
        'subject_id' + suffix,
        'faculty_id' + suffix,
        'room_id' + suffix,
        'day_of_week' + suffix,
        'schedule_type' + suffix,
        'start_time' + suffix,
        'end_time' + suffix
    ];
}

function bindAutoCheckFieldEvents(field, fieldId, mode, suffix) {
    const boundAttr = `data-auto-check-bound-${mode}`;
    if (field.getAttribute(boundAttr) === '1') {
        return;
    }

    field.addEventListener('change', () => {
        updateImmediateFacultyDayWarning(mode);

        if (fieldId === ('day_of_week' + suffix)) {
            if (canRunClassAutoCheckNow(mode)) {
                runImmediateClassAutoConflictCheck(mode);
            }
            return;
        }

        scheduleAutoConflictCheck(mode);
    });

    if (fieldId.includes('time')) {
        field.addEventListener('input', () => {
            scheduleAutoConflictCheck(mode);
        });
    }

    field.setAttribute(boundAttr, '1');
}

function scheduleAutoCheckRebind() {
    if (autoCheckRebindTimer) {
        clearTimeout(autoCheckRebindTimer);
    }

    autoCheckRebindTimer = setTimeout(() => {
        setupAutoCheckForModalWithRetry('add');
        setupAutoCheckForModalWithRetry('edit');
    }, AUTO_CHECK_RETRY_DELAY_MS);
}

function initAutoCheckFieldObserver() {
    if (autoCheckFieldObserver || typeof MutationObserver === 'undefined') {
        return;
    }

    autoCheckFieldObserver = new MutationObserver((mutations) => {
        let shouldRebind = false;

        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!node || node.nodeType !== 1) {
                    continue;
                }

                if (
                    (node.matches && (
                        node.matches('.time-picker-hidden-input') ||
                        node.matches('[id^="start_time_"]') ||
                        node.matches('[id^="end_time_"]')
                    )) ||
                    (node.querySelector && (
                        node.querySelector('.time-picker-hidden-input') ||
                        node.querySelector('[id^="start_time_"]') ||
                        node.querySelector('[id^="end_time_"]')
                    ))
                ) {
                    shouldRebind = true;
                    break;
                }
            }

            if (shouldRebind) {
                break;
            }
        }

        if (shouldRebind) {
            scheduleAutoCheckRebind();
        }
    });

    autoCheckFieldObserver.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true
    });
}

/**
 * Initialize automatic conflict detection for both Add and Edit modals
 */
function initAutoConflictDetection() {
    // Initialize for Add/Edit forms and re-bind if dynamic fields render later.
    setupAutoCheckForModalWithRetry('add');
    setupAutoCheckForModalWithRetry('edit');
    initAutoCheckFieldObserver();
}

function setupAutoCheckForModalWithRetry(mode, retriesLeft = AUTO_CHECK_MAX_RETRIES) {
    const missingCount = setupAutoCheckForModal(mode);
    if (missingCount > 0 && retriesLeft > 0) {
        setTimeout(() => {
            setupAutoCheckForModalWithRetry(mode, retriesLeft - 1);
        }, AUTO_CHECK_RETRY_DELAY_MS);
    }
}

/**
 * Setup automatic conflict checking for a specific modal
 * @param {string} mode - Either 'add' or 'edit'
 */
function setupAutoCheckForModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const fields = getAutoCheckFieldIds(mode);
    let missingCount = 0;

    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            bindAutoCheckFieldEvents(field, fieldId, mode, suffix);
        } else {
            missingCount += 1;
        }
    });

    return missingCount;
}

function getClassAutoCheckSuffix(mode) {
    const isUnifiedModal = window.scheduleModalMode !== undefined;
    return (isUnifiedModal || mode === 'add') ? '_add' : '_edit';
}

function getActiveClassAutoCheckMode(mode) {
    if (window.scheduleModalMode === 'edit') {
        return 'edit';
    }
    if (window.scheduleModalMode === 'add') {
        return 'add';
    }
    return mode === 'edit' ? 'edit' : 'add';
}

function maybeRevealClassScheduleCheckPanel(mode, allRequiredDetailsFilled) {
    const activeMode = getActiveClassAutoCheckMode(mode);

    if (!allRequiredDetailsFilled) {
        classAutoCheckCompletionState[activeMode] = false;
        return;
    }

    if (classAutoCheckCompletionState[activeMode]) {
        return;
    }

    classAutoCheckCompletionState[activeMode] = true;

    const openButtonId = activeMode === 'edit'
        ? 'aiPanelEditScheduleOpenBtn'
        : 'aiPanelAddScheduleOpenBtn';
    const openButton = document.getElementById(openButtonId);

    if (openButton && !openButton.classList.contains('hidden')) {
        openButton.click();
    }

    if (typeof autoOpenDrawer === 'function') {
        autoOpenDrawer();
    }
}

function canRunClassAutoCheckNow(mode) {
    const suffix = getClassAutoCheckSuffix(mode);
    const sectionId = document.getElementById('section_id' + suffix)?.value;
    const curriculumId = document.getElementById('curriculum_id' + suffix)?.value || null;
    const subjectId = document.getElementById('subject_id' + suffix)?.value || null;
    const facultyId = document.getElementById('faculty_id' + suffix)?.value || null;
    const roomId = document.getElementById('room_id' + suffix)?.value || null;
    const dayOfWeek = document.getElementById('day_of_week' + suffix)?.value;
    const scheduleTypeField = document.getElementById('schedule_type' + suffix);
    const scheduleType = scheduleTypeField ? String(scheduleTypeField.value || '').trim() : 'lecture';
    const startTime = document.getElementById('start_time' + suffix)?.value;
    const endTime = document.getElementById('end_time' + suffix)?.value;

    return Boolean(
        sectionId &&
        curriculumId &&
        subjectId &&
        facultyId &&
        roomId &&
        dayOfWeek &&
        scheduleType &&
        startTime &&
        endTime
    );
}

function runImmediateClassAutoConflictCheck(mode) {
    if (autoCheckDebounceTimer) {
        clearTimeout(autoCheckDebounceTimer);
        autoCheckDebounceTimer = null;
    }
    performAutoConflictCheck(mode);
}

function getFacultyDayMismatchWarning(mode) {
    const suffix = getClassAutoCheckSuffix(mode);
    const dayOfWeek = document.getElementById('day_of_week' + suffix)?.value;
    const facultyId = document.getElementById('faculty_id' + suffix)?.value;

    if (!dayOfWeek || !facultyId) return null;

    const cache = window.facultyDataCache || {};
    const facultyList = cache[mode] || cache.add || cache.edit || [];
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
        type: 'warning',
        message: `${faculty.full_name || 'Selected faculty'} is not marked as available on ${dayOfWeek}.`,
        status: 'not_in_schedule',
        faculty_name: faculty.full_name || ''
    };
}

function updateImmediateFacultyDayWarning(mode) {
    const warning = getFacultyDayMismatchWarning(mode);
    displayFacultyAvailabilityWarning(mode, warning);
}

/**
 * Schedule an automatic conflict check (with debouncing)
 * @param {string} mode - Either 'add' or 'edit'
 */
function scheduleAutoConflictCheck(mode) {
    // Clear existing timer
    if (autoCheckDebounceTimer) {
        clearTimeout(autoCheckDebounceTimer);
    }
    
    // Schedule new check after debounce delay
    autoCheckDebounceTimer = setTimeout(() => {
        performAutoConflictCheck(mode);
    }, AUTO_CHECK_DEBOUNCE_MS);
}

/**
 * Perform automatic conflict check
 * @param {string} mode - Either 'add' or 'edit'
 */
function performAutoConflictCheck(mode) {
    // For the unified modal, always use '_add' suffix for form fields
    // The modal uses 'add' form elements even when editing
    const isUnifiedModal = window.scheduleModalMode !== undefined;
    const suffix = (isUnifiedModal || mode === 'add') ? '_add' : '_edit';
    
    // Get form data
    const sectionId = document.getElementById('section_id' + suffix)?.value;
    const curriculumId = document.getElementById('curriculum_id' + suffix)?.value || null;
    const subjectId = document.getElementById('subject_id' + suffix)?.value || null;
    const facultyId = document.getElementById('faculty_id' + suffix)?.value || null;
    const roomId = document.getElementById('room_id' + suffix)?.value || null;
    const dayOfWeek = document.getElementById('day_of_week' + suffix)?.value;
    const scheduleTypeField = document.getElementById('schedule_type' + suffix);
    const scheduleType = scheduleTypeField ? String(scheduleTypeField.value || '').trim() : 'lecture';
    const startTime = document.getElementById('start_time' + suffix)?.value;
    const endTime = document.getElementById('end_time' + suffix)?.value;
    
    // Get schedule ID for edit mode - check unified modal first (schedule_id), then fallback to legacy (schedule_id_edit)
    let scheduleId = null;
    if (window.scheduleModalMode === 'edit' || mode === 'edit') {
        scheduleId = document.getElementById('schedule_id')?.value || document.getElementById('schedule_id_edit')?.value || null;
    }
    const allRequiredDetailsFilled = Boolean(
        sectionId &&
        curriculumId &&
        subjectId &&
        facultyId &&
        roomId &&
        dayOfWeek &&
        scheduleType &&
        startTime &&
        endTime
    );

    maybeRevealClassScheduleCheckPanel(mode, allRequiredDetailsFilled);

    if (!allRequiredDetailsFilled) {
        const panelSuffix = mode === 'add' ? 'Add' : 'Edit';

        showAutoCheckStatus(mode, 'warning', 'Complete all required schedule details to start conflict checking.');
        updateConflictState(mode, false, true);

        document.getElementById('aiRecommendations' + panelSuffix)?.classList.add('hidden');
        document.getElementById('aiResolveAll' + panelSuffix)?.classList.add('hidden');
        document.getElementById('aiExplanationWrapper' + panelSuffix)?.classList.add('hidden');
        document.getElementById('aiWorkloadSummary' + panelSuffix)?.classList.add('hidden');

        hideResolveAllOption(mode);
        displayFacultyAvailabilityWarning(mode, null);
        displayScheduleHoursWarning(mode, null);

        return;
    }
    
    // Validate time range
    if (startTime && endTime && startTime >= endTime) {
        showAutoCheckStatus(mode, 'error', 'End time must be after start time.');
        updateConflictState(mode, true);
        return;
    }
    
    // Show checking status
    showAutoCheckStatus(mode, 'checking', 'Checking for conflicts...');
    
    // Disable recommendation buttons while checking
    setRecommendationButtonsState(mode, true);
    
    // Prepare request data
    const requestData = {
        section_id: parseInt(sectionId),
        subject_id: subjectId ? parseInt(subjectId) : null,
        faculty_id: facultyId ? parseInt(facultyId) : null,
        room_id: roomId ? parseInt(roomId) : null,
        day_of_week: dayOfWeek,
        schedule_type: scheduleType,
        start_time: startTime,
        end_time: endTime,
        schedule_id: scheduleId ? parseInt(scheduleId) : null,
        use_ai: typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : true
    };
    // Call AI API
    fetch('/schedule/ai-check-conflicts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.text().then(text => {
                console.error('[AUTO-CHECK] Server error response:', text);
                throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // Re-enable recommendation buttons after response
        setRecommendationButtonsState(mode, false);

        const wantsAi = typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : true;
        const explicitFallback = data.ai_fallback === true;
        const usingFallback = explicitFallback || (wantsAi && !data.ai_enabled);
        const fallbackMessage = typeof data.ai_fallback_message === 'string' ? data.ai_fallback_message.trim() : '';
        const fallbackReason = typeof data.ai_fallback_reason === 'string' ? data.ai_fallback_reason.trim() : '';
        if (typeof setAIFallbackNotice === 'function') {
            setAIFallbackNotice(usingFallback ? (fallbackMessage || fallbackReason || 'AI insights are currently unavailable. Running Quick mode checks (offline) so you can keep scheduling.') : '');
        }
        
        if (!data.ai_enabled) {
            // ── Quick Mode (concise info, full actions) ─────────────────────
            const suffix = mode === 'add' ? 'Add' : 'Edit';

            if (data.has_conflicts && data.conflicts && data.conflicts.length > 0) {
                showAutoCheckStatus(mode, 'error', 'Conflicts found. Review items below.');
                displayAIConflicts(data.conflicts, mode);

                const explanationText = data.ai_explanation || 'Conflicts detected. Make changes to auto-recheck.';
                displayExplanation(suffix, explanationText, false);

                if (data.recommendations && data.recommendations.length > 0) {
                    displayAIRecommendations(data.recommendations, mode, false);
                } else {
                    document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
                }

                // Keep resolve plan available in Quick mode for parity.
                showResolveAllOption(data.conflicts, mode);

                // Workload panel remains Detailed-only.
                const wlEl = document.getElementById('aiWorkloadSummary' + suffix);
                if (wlEl) wlEl.classList.add('hidden');

                updateConflictState(mode, true);
                if (typeof autoOpenDrawer === 'function') autoOpenDrawer();
            } else {
                showAutoCheckStatus(mode, 'success', 'No conflicts found. You can proceed.');
                updateConflictState(mode, false, false);
                hideResolveAllOption(mode);

                document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
                const expWrapper = document.getElementById('aiExplanationWrapper' + suffix);
                if (expWrapper) expWrapper.classList.add('hidden');
                const wlEl = document.getElementById('aiWorkloadSummary' + suffix);
                if (wlEl) wlEl.classList.add('hidden');
            }

            // Process warnings in Quick mode.
            displayFacultyAvailabilityWarning(mode, data.faculty_availability_warning || null);
            displayScheduleHoursWarning(mode, data.schedule_hours_warning || null);

            if (data.schedule_hours_warning) {
                showAutoCheckStatus(mode, 'error', data.schedule_hours_warning);
                hideResolveAllOption(mode);
                updateConflictState(mode, true);
            }
            return;
        }
        
        if (data.error) {
            showAutoCheckStatus(mode, 'error', data.error);
            updateConflictState(mode, true);
            return;
        }
        
        // ── Detailed Mode ───────────────────────────────────────
        // Handle faculty availability warning (separate from conflicts)
        const facultyWarning = data.faculty_availability_warning;
        displayFacultyAvailabilityWarning(mode, facultyWarning);
        
        // Handle schedule hours warning (now blocking)
        const scheduleHoursWarning = data.schedule_hours_warning;
        displayScheduleHoursWarning(mode, scheduleHoursWarning);
        
        // Check for schedule hours violation first (blocking)
        if (scheduleHoursWarning) {
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckStatus(mode, 'error', scheduleHoursWarning);
            updateConflictState(mode, true);
            
            // Hide conflict/recommendation panels
            document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
            const wlEl = document.getElementById('aiWorkloadSummary' + suffix);
            if (wlEl) wlEl.classList.add('hidden');
        } else if (data.has_conflicts) {
            // Has conflicts - disable submit
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckStatus(mode, 'error', 'Conflicts found. Review items below.');
            displayAIConflicts(data.conflicts, mode);
            displayAIRecommendations(data.recommendations, mode, false); // readOnly=false (interactive)
            // Show auto-resolve option (available in Detailed mode and Quick mode)
            showResolveAllOption(data.conflicts, mode);
            updateConflictState(mode, true);
            
            // Show AI explanation in purple card ("AI Analysis")
            const explanationText = data.ai_explanation || 'Conflicts detected. Make changes to auto-recheck.';
            displayExplanation(suffix, explanationText, true);

            // Show workload summary (Detailed mode only)
            displayWorkloadSummary(suffix, data.workload_summary || null);
            
            // Auto-open AI drawer to show conflicts
            if (typeof autoOpenDrawer === 'function') autoOpenDrawer();
        } else if (facultyWarning && facultyWarning.type === 'error') {
            // Faculty is explicitly unavailable - this is a hard block
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckStatus(mode, 'error', facultyWarning.message);
            updateConflictState(mode, true);
            
            // Hide conflict/recommendation panels since this is an availability issue
            document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
        } else {
            // No conflicts - enable submit
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            
            // Check if there's a soft warning about faculty availability
            if (facultyWarning && facultyWarning.type === 'warning') {
                showAutoCheckStatus(mode, 'warning', `No scheduling conflicts, but ${facultyWarning.message}`);
            } else {
                showAutoCheckStatus(mode, 'success', 'No conflicts found. This schedule looks good.');
            }
            updateConflictState(mode, false);
            
            // Hide conflict/recommendation/resolve panels
            document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
            hideResolveAllOption(mode);
            
            // Hide explanation and workload when no conflicts
            const expWrapper = document.getElementById('aiExplanationWrapper' + suffix);
            if (expWrapper) expWrapper.classList.add('hidden');
            const wlEl = document.getElementById('aiWorkloadSummary' + suffix);
            if (wlEl) wlEl.classList.add('hidden');
        }
    })
    .catch(error => {
        console.error('[AUTO-CHECK] Error:', error);
        
        // Re-enable recommendation buttons on error
        setRecommendationButtonsState(mode, false);
        
        // Provide more specific error messages
        let errorMessage = 'Network error. Please check your connection.';
        if (error.message) {
            if (error.message.includes('Server error')) {
                errorMessage = error.message;
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = 'Cannot connect to server. Please ensure the server is running.';
            } else if (error.message.includes('NetworkError')) {
                errorMessage = 'Network error. Check your internet connection.';
            }
        }
        
        showAutoCheckStatus(mode, 'error', errorMessage);
        // Allow submission on network errors (don't block user)
        updateConflictState(mode, false, false);
    });
}

function renderAutoCheckInlineNotice(mode, type, message) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const conflictsContainer = document.getElementById('aiConflicts' + suffix);
    const conflictsList = document.getElementById('aiConflictsList' + suffix);

    if (!conflictsContainer || !conflictsList) {
        return;
    }

    let toneClass = 'border-gray-200/90 dark:border-gray-700 text-gray-700 dark:text-gray-300';
    let indicatorHtml = '<span class="mt-1 w-2 h-2 rounded-full bg-gray-400 dark:bg-gray-500 flex-shrink-0"></span>';

    if (type === 'checking') {
        toneClass = 'border-blue-200/90 dark:border-blue-800 text-blue-700 dark:text-blue-300';
        indicatorHtml = '<svg class="w-3 h-3 mt-0.5 text-blue-500 dark:text-blue-400 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
    } else if (type === 'success') {
        toneClass = 'border-emerald-200/90 dark:border-emerald-800 text-emerald-700 dark:text-emerald-300';
        indicatorHtml = '<span class="mt-1 w-2 h-2 rounded-full bg-emerald-500 dark:bg-emerald-400 flex-shrink-0"></span>';
    } else if (type === 'error') {
        toneClass = 'border-red-200/90 dark:border-red-800 text-red-700 dark:text-red-300';
        indicatorHtml = '<span class="mt-1 w-2 h-2 rounded-full bg-red-500 dark:bg-red-400 flex-shrink-0"></span>';
    } else if (type === 'warning') {
        toneClass = 'border-amber-200/90 dark:border-amber-800 text-amber-700 dark:text-amber-300';
        indicatorHtml = '<span class="mt-1 w-2 h-2 rounded-full bg-amber-500 dark:bg-amber-400 flex-shrink-0"></span>';
    }

    conflictsList.innerHTML = `
        <div class="mb-2 rounded-lg border ${toneClass} bg-white dark:bg-gray-900/25 p-2.5">
            <div class="flex items-start gap-2">
                ${indicatorHtml}
                <p class="text-xs font-medium leading-relaxed">${message}</p>
            </div>
        </div>
    `;
    conflictsContainer.classList.remove('hidden');
}

/**
 * Show auto-check status message
 * @param {string} mode - Either 'add' or 'edit'
 * @param {string} type - 'checking', 'success', 'error', 'warning'
 * @param {string} message - Status message to display
 */
function showAutoCheckStatus(mode, type, message) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const statusContainer = document.getElementById('autoCheckStatus' + suffix);
    const aiPanel = document.getElementById('aiAssistant' + suffix);
    const emptyState = document.getElementById('aiEmptyState' + suffix);
    
    // Update floating AI badge state
    if (typeof updateAIBadge === 'function') {
        const badgeMap = { checking: 'checking', success: 'clear', error: 'conflicts', warning: 'warnings' };
        updateAIBadge(badgeMap[type] || 'idle');
    }
    
    // Hide empty state when showing status
    if (emptyState) {
        emptyState.classList.add('hidden');
    }
    
    // Keep assistant panel visible because status now renders inside conflict/result area.
    if (aiPanel) aiPanel.classList.remove('hidden');

    if (statusContainer) {
        statusContainer.innerHTML = '';
        statusContainer.classList.add('hidden');
    }

    renderAutoCheckInlineNotice(mode, type, message);
}

/**
 * Update conflict state and submit button
 * @param {string} mode - Either 'add' or 'edit'
 * @param {boolean} hasConflicts - Whether conflicts exist
 * @param {boolean} allowSubmit - Force allow submission (for incomplete forms or errors)
 */
function updateConflictState(mode, hasConflicts, allowSubmit = false) {
    // Update global state
    if (mode === 'add') {
        hasConflictsAdd = hasConflicts;
    } else {
        hasConflictsEdit = hasConflicts;
    }
    
    // Get submit button and text element - use unified button for 'add' mode (which is now both add and edit)
    const submitButton = document.getElementById('submitScheduleBtn');
    const submitButtonText = document.getElementById('submitScheduleBtnText');
    
    if (!submitButton) return;
    
    // Check if we're in edit mode via the unified modal
    const isEditMode = window.scheduleModalMode === 'edit';
    const displayMode = isEditMode ? 'edit' : 'add';
    
    // Define base classes for workspace modal button style
    const baseClasses = 'flex items-center px-2.5 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold text-white rounded-lg transition-all';
    const disabledClasses = baseClasses + ' bg-gray-400 cursor-not-allowed';
    const enabledClasses = baseClasses + ' bg-gradient-to-r from-blue-600 to-blue-700 hover:from-blue-700 hover:to-blue-800 shadow-sm';
    
    // Update button state
    if (hasConflicts && !allowSubmit) {
        // Conflicts exist - DISABLE button
        submitButton.disabled = true;
        submitButton.className = disabledClasses;
        submitButton.title = 'Resolve conflicts before submitting';
        if (submitButtonText) {
            submitButtonText.textContent = 'Resolve Conflicts';
        }
    } else if (allowSubmit) {
        // Incomplete form - DISABLE button with appropriate message
        submitButton.disabled = true;
        submitButton.className = disabledClasses;
        submitButton.title = 'Fill in all required fields';
        if (submitButtonText) {
            submitButtonText.textContent = 'Fill Required';
        }
    } else {
        // No conflicts - ENABLE button
        submitButton.disabled = false;
        submitButton.className = enabledClasses;
        submitButton.title = '';
        if (submitButtonText) {
            submitButtonText.textContent = isEditMode ? 'Update Schedule' : 'Add Schedule';
        }
    }
}

/**
 * Reset auto-check state when modal is closed
 * @param {string} mode - Either 'add' or 'edit'
 */
function resetAutoCheckState(mode) {
    // Clear debounce timer
    if (autoCheckDebounceTimer) {
        clearTimeout(autoCheckDebounceTimer);
        autoCheckDebounceTimer = null;
    }
    
    // Reset conflict state
    updateConflictState(mode, false, true);

    const activeMode = getActiveClassAutoCheckMode(mode);
    classAutoCheckCompletionState[activeMode] = false;
    
    // Reset floating AI badge to idle
    if (typeof updateAIBadge === 'function') updateAIBadge('idle');
    
    // Hide AI panel and show empty state
    const aiPanel = document.getElementById('aiAssistant' + (mode === 'add' ? 'Add' : 'Edit'));
    const emptyState = document.getElementById('aiEmptyState' + (mode === 'add' ? 'Add' : 'Edit'));
    const statusContainer = document.getElementById('autoCheckStatus' + (mode === 'add' ? 'Add' : 'Edit'));
    const recheckButton = document.getElementById('recheckButtonContainer' + (mode === 'add' ? 'Add' : 'Edit'));
    
    if (aiPanel) {
        aiPanel.classList.add('hidden');
    }
    
    if (emptyState) {
        emptyState.classList.remove('hidden');
    }
    
    if (statusContainer) {
        statusContainer.innerHTML = '';
    }
    
    // Hide conflict/recommendation sections
    const conflictsSection = document.getElementById('aiConflicts' + (mode === 'add' ? 'Add' : 'Edit'));
    const recommendationsSection = document.getElementById('aiRecommendations' + (mode === 'add' ? 'Add' : 'Edit'));
    
    if (conflictsSection) conflictsSection.classList.add('hidden');
    if (recommendationsSection) recommendationsSection.classList.add('hidden');
    
    // Hide resolve-all section (D2)
    hideResolveAllOption(mode);
    
    // Clear faculty availability warning
    displayFacultyAvailabilityWarning(mode, null);
    
    // Clear schedule hours warning
    displayScheduleHoursWarning(mode, null);
}

/**
 * Display faculty availability warning in the form
 * @param {string} mode - Either 'add' or 'edit'
 * @param {object} warning - Faculty availability warning object or null
 */
function displayFacultyAvailabilityWarning(mode, warning) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    
    // Get or create the warning container
    let warningContainer = document.getElementById('facultyAvailabilityWarning' + suffix);
    
    if (!warningContainer) {
        // Find the faculty picker container and insert warning after it
        const facultyPicker = document.getElementById('facultyPicker' + (mode === 'add' ? 'Add' : 'Add'));
        if (facultyPicker) {
            warningContainer = document.createElement('div');
            warningContainer.id = 'facultyAvailabilityWarning' + suffix;
            warningContainer.className = 'mt-2';
            facultyPicker.parentNode.insertBefore(warningContainer, facultyPicker.nextSibling);
        }
    }
    
    if (!warningContainer) return;
    
    if (!warning) {
        // Clear warning
        warningContainer.innerHTML = '';
        warningContainer.classList.add('hidden');
        return;
    }
    
    warningContainer.classList.remove('hidden');
    
    if (warning.type === 'error') {
        // Hard block - faculty explicitly unavailable
        warningContainer.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
                <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
                </svg>
                <p class="text-xs text-red-700"><strong>Unavailable:</strong> ${warning.message}</p>
            </div>
        `;
    } else if (warning.type === 'warning') {
        // Soft warning - faculty has schedule but not available at this time
        warningContainer.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 bg-amber-50 border border-amber-200 rounded-lg">
                <svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-xs text-amber-700"><strong>Note:</strong> Faculty not marked available for this day/time. You can still proceed.</p>
            </div>
        `;
    } else if (warning.type === 'success') {
        // Positive confirmation - faculty is available
        warningContainer.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg">
                <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-xs text-green-700"><strong>Available:</strong> ${warning.message}</p>
            </div>
        `;
    }
}

/**
 * Display schedule hours warning in the form (non-blocking)
 * @param {string} mode - Either 'add' or 'edit'
 * @param {string} warning - Schedule hours warning message or null
 */
function displayScheduleHoursWarning(mode, warning) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    
    // Get or create the warning container
    let warningContainer = document.getElementById('scheduleHoursWarning' + suffix);
    
    if (!warningContainer) {
        // Find the time fields container and insert warning after it
        const startTimeField = document.getElementById('start_time_' + (mode === 'add' ? 'add' : 'edit'));
        if (startTimeField) {
            const parentContainer = startTimeField.closest('.grid') || startTimeField.parentNode.parentNode;
            if (parentContainer) {
                warningContainer = document.createElement('div');
                warningContainer.id = 'scheduleHoursWarning' + suffix;
                warningContainer.className = 'mt-2 col-span-2';
                parentContainer.parentNode.insertBefore(warningContainer, parentContainer.nextSibling);
            }
        }
    }
    
    if (!warningContainer) return;
    
    if (!warning) {
        // Clear warning
        warningContainer.innerHTML = '';
        warningContainer.classList.add('hidden');
        return;
    }
    
    warningContainer.classList.remove('hidden');
    
    // Display as red error (blocking)
    warningContainer.innerHTML = `
        <div class="flex items-center gap-2 px-3 py-2 bg-red-50 border border-red-200 rounded-lg">
            <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <p class="text-xs text-red-700"><strong>Invalid Time:</strong> ${warning}</p>
        </div>
    `;
}

/**
 * Enable or disable recommendation buttons during loading
 * @param {string} mode - Either 'add' or 'edit'
 * @param {boolean} disabled - True to disable, false to enable
 */
function setRecommendationButtonsState(mode, disabled) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    
    // Get recommendation container (inside AI drawer)
    const containers = [
        document.getElementById('aiRecommendations' + suffix)
    ];
    
    containers.forEach(container => {
        if (!container) return;
        
        // Find all buttons within the recommendations section
        const buttons = container.querySelectorAll('button[onclick*="apply"]');
        buttons.forEach(btn => {
            btn.disabled = disabled;
            if (disabled) {
                btn.classList.add('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
            } else {
                btn.classList.remove('opacity-50', 'cursor-not-allowed', 'pointer-events-none');
            }
        });
    });
}

// ══════════════════════════════════════════════════════════════════
// D2 — Conflict Chain Resolution ("Resolve All" Button)
// ══════════════════════════════════════════════════════════════════

// Store current conflicts and form data for resolution flow
let _currentConflicts = [];
let _currentScheduleFormData = {};
let _currentResolutionPlan = null;

/**
 * Show the "Auto-Resolve Available" section after conflicts are detected.
 * Called from performAutoConflictCheck after displayAIConflicts.
 * @param {Array} conflicts - List of conflict objects
 * @param {string} mode - 'add' or 'edit'
 */
function showResolveAllOption(conflicts, mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const container = document.getElementById('aiResolveAll' + suffix);

    if (!container) return;

    // Only show for CRITICAL/HIGH conflicts
    const resolvableConflicts = conflicts.filter(
        c => c.severity === 'critical' || c.severity === 'high'
    );

    if (resolvableConflicts.length === 0) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    // Store conflicts for later use
    _currentConflicts = conflicts;
    _currentResolutionPlan = null;

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="flex items-center justify-between gap-2 py-2">
            <p class="text-[10px] text-gray-500"><span class="font-medium text-gray-600">${resolvableConflicts.length}</span> conflict${resolvableConflicts.length > 1 ? 's' : ''} can be auto-resolved</p>
            <button type="button" onclick="generateResolutionPlan('${mode}')"
                    id="resolveAllBtn${suffix}"
                    class="flex-shrink-0 px-3 py-1.5 bg-blue-600 text-white text-[11px] font-medium rounded-md hover:bg-blue-700 transition-colors">
                Generate Plan
            </button>
        </div>
    `;
}

/**
 * Hide the resolve-all section
 * @param {string} mode - 'add' or 'edit'
 */
function hideResolveAllOption(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const container = document.getElementById('aiResolveAll' + suffix);
    if (container) {
        container.classList.add('hidden');
        container.innerHTML = '';
    }
    _currentConflicts = [];
    _currentResolutionPlan = null;
}

/**
 * Gather current form values into a schedule data object
 * @param {string} mode - 'add' or 'edit'
 * @returns {object} schedule form data
 */
function _gatherScheduleFormData(mode) {
    const isUnifiedModal = window.scheduleModalMode !== undefined;
    const suffix = (isUnifiedModal || mode === 'add') ? '_add' : '_edit';
    const scheduleTypeField = document.getElementById('schedule_type' + suffix);
    const scheduleType = scheduleTypeField ? String(scheduleTypeField.value || '').trim() : 'lecture';

    return {
        section_id: parseInt(document.getElementById('section_id' + suffix)?.value) || null,
        subject_id: parseInt(document.getElementById('subject_id' + suffix)?.value) || null,
        faculty_id: parseInt(document.getElementById('faculty_id' + suffix)?.value) || null,
        room_id: parseInt(document.getElementById('room_id' + suffix)?.value) || null,
        day_of_week: document.getElementById('day_of_week' + suffix)?.value || '',
        schedule_type: scheduleType,
        start_time: document.getElementById('start_time' + suffix)?.value || '',
        end_time: document.getElementById('end_time' + suffix)?.value || '',
        schedule_id: document.getElementById('schedule_id')?.value || document.getElementById('schedule_id_edit')?.value || null
    };
}

/**
 * Call backend to generate a resolution plan
 * @param {string} mode - 'add' or 'edit'
 */
async function generateResolutionPlan(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const btn = document.getElementById('resolveAllBtn' + suffix);
    const container = document.getElementById('aiResolveAll' + suffix);

    if (!container) return;

    // Gather current form data
    const formData = _gatherScheduleFormData(mode);
    _currentScheduleFormData = formData;

    // Show loading state on button
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = `
            <svg class="w-3.5 h-3.5 animate-spin inline mr-1" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Analyzing...
        `;
    }

    try {
        const response = await fetch('/schedule/resolve-conflicts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...formData,
                conflicts: _currentConflicts
            })
        });

        if (!response.ok) {
            throw new Error(`Server error (${response.status})`);
        }

        const plan = await response.json();

        if (plan.error) {
            throw new Error(plan.error);
        }

        _currentResolutionPlan = plan;
        showResolutionPlan(plan, mode);

    } catch (err) {
        console.error('[RESOLVE-ALL] Error:', err);
        container.innerHTML = `
            <div class="p-3 bg-red-50 border border-red-200 rounded-xl">
                <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p class="text-xs text-red-700">${err.message || 'Failed to generate resolution plan'}</p>
                </div>
            </div>
        `;
    }
}

/**
 * Display the resolution plan inside the resolve-all container
 * @param {object} plan - Resolution plan from backend
 * @param {string} mode - 'add' or 'edit'
 */
function showResolutionPlan(plan, mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const container = document.getElementById('aiResolveAll' + suffix);

    if (!container) return;

    const stats = plan.stats || {};
    const resolvable = plan.resolvable || [];
    const unresolvable = plan.unresolvable || [];
    const formChanges = plan.form_changes || {};
    const actionableKeys = Object.keys(formChanges).filter((key) => !key.startsWith('_'));
    const actionableCount = actionableKeys.length;

    const dedupedResolutions = [];
    const seenResolutionKeys = new Set();
    resolvable.forEach((item) => {
        const res = item.resolution || {};
        const dedupKey = `${res.action || ''}|${res.description || ''}`;
        if (!seenResolutionKeys.has(dedupKey)) {
            seenResolutionKeys.add(dedupKey);
            dedupedResolutions.push(item);
        }
    });

    // Check if there are changes to apply
    const hasChanges = dedupedResolutions.length > 0 && actionableCount > 0;

    let html = '';

    // ── Plan header ─────────────────────────────────────────
    if (hasChanges) {
        const totalConflicts = Number(stats.total_conflicts || 0);
        html += `
            <div class="mb-2">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0"></div>
                    <p class="text-xs font-medium text-emerald-700">${actionableCount} change${actionableCount > 1 ? 's' : ''} can auto-resolve ${totalConflicts} conflict${totalConflicts > 1 ? 's' : ''}</p>
                </div>
        `;

        // ── Resolvable items ────────────────────────────────
        dedupedResolutions.forEach((item) => {
            const res = item.resolution || {};
            const affectedConflicts = Number(item.affected_conflicts || 0);
            const affectedConflictsText = affectedConflicts > 1
                ? ` <span class="text-[10px] text-emerald-700">(fixes ${affectedConflicts} conflicts)</span>`
                : '';
            html += `
                <div class="flex items-center gap-2 py-1 pl-3 border-l-2 border-emerald-300 mb-1 last:mb-0">
                    <p class="text-[11px] text-gray-700 truncate">${res.description || res.action || 'Change'}${affectedConflictsText}</p>
                </div>
            `;
        });

        // ── Apply All button ────────────────────────────────
        html += `
                <button type="button" onclick="applyResolutionPlan('${mode}')"
                        id="applyResolutionBtn${suffix}"
                        class="w-full mt-2 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-md hover:bg-emerald-700 transition-colors flex items-center justify-center gap-1.5">
                    Apply ${actionableCount} Change${actionableCount > 1 ? 's' : ''}
                </button>
            </div>
        `;
    } else {
        // No auto-resolutions possible
        html += `
            <div class="flex items-center gap-2 py-1.5 mb-2">
                <div class="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"></div>
                <p class="text-xs text-amber-700">Manual resolution needed — adjust using recommendations below</p>
            </div>
        `;
    }

    // ── Unresolvable items ──────────────────────────────────
    if (unresolvable.length > 0) {
        unresolvable.forEach((item) => {
            html += `
                <div class="flex items-center gap-2 py-1 pl-3 border-l-2 border-amber-300 mb-1 last:mb-0">
                    <p class="text-[10px] text-amber-700">${item.reason || 'Needs manual adjustment'}</p>
                </div>
            `;
        });
    }

    container.innerHTML = html;
    container.classList.remove('hidden');
}

/**
 * Apply the resolution plan by updating form fields and re-triggering conflict check.
 * For ADD mode: updates form fields only. For EDIT mode: can optionally save to DB.
 * @param {string} mode - 'add' or 'edit'
 */
function applyResolutionPlan(mode) {
    const plan = _currentResolutionPlan;
    if (!plan || !plan.form_changes) return;

    const isUnifiedModal = window.scheduleModalMode !== undefined;
    const suffix = (isUnifiedModal || mode === 'add') ? '_add' : '_edit';
    const formChanges = plan.form_changes;

    // Apply each form change
    if (formChanges.start_time) {
        const el = document.getElementById('start_time' + suffix);
        if (el) { el.value = formChanges.start_time; highlightField(el); }
    }
    if (formChanges.end_time) {
        const el = document.getElementById('end_time' + suffix);
        if (el) { el.value = formChanges.end_time; highlightField(el); }
    }
    if (formChanges.day_of_week) {
        const el = document.getElementById('day_of_week' + suffix);
        if (el) { el.value = formChanges.day_of_week; highlightField(el); }
    }
    if (formChanges.room_id) {
        const el = document.getElementById('room_id' + suffix);
        if (el) { el.value = String(formChanges.room_id); highlightField(el); }
    }
    if (formChanges.faculty_id) {
        const el = document.getElementById('faculty_id' + suffix);
        if (el) { el.value = String(formChanges.faculty_id); highlightField(el); }
    }

    // Show brief success flash
    const uiSuffix = mode === 'add' ? 'Add' : 'Edit';
    const container = document.getElementById('aiResolveAll' + uiSuffix);
    if (container) {
        container.innerHTML = `
            <div class="flex items-center gap-2 py-1.5">
                <div class="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0"></div>
                <p class="text-xs text-emerald-700">Changes applied — re-checking conflicts...</p>
            </div>
        `;
    }

    // Clear stored plan
    _currentResolutionPlan = null;
    _currentConflicts = [];

    // Trigger auto-conflict re-check after a short delay
    setTimeout(() => {
        performAutoConflictCheck(mode);
    }, 300);
}

/**
 * Briefly highlight a form field to show it was changed
 * @param {HTMLElement} el - The form element to highlight
 */
function highlightField(el) {
    if (!el) return;
    el.classList.add('ring-2', 'ring-emerald-400', 'ring-offset-1');
    setTimeout(() => {
        el.classList.remove('ring-2', 'ring-emerald-400', 'ring-offset-1');
    }, 2000);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initAutoConflictDetection();
});

// Export functions for use in other scripts
window.initAutoConflictDetection = initAutoConflictDetection;
window.resetAutoCheckState = resetAutoCheckState;
window.performAutoConflictCheck = performAutoConflictCheck;
window.showResolveAllOption = showResolveAllOption;
window.hideResolveAllOption = hideResolveAllOption;
window.generateResolutionPlan = generateResolutionPlan;
window.applyResolutionPlan = applyResolutionPlan;
