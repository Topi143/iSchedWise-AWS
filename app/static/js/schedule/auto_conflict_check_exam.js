/**
 * Automatic Conflict Detection System for Exam Schedules
 * Automatically checks for exam schedule conflicts when form fields change
 * and prevents submission until conflicts are resolved
 */

// Debounce timer to prevent excessive API calls
let autoCheckExamDebounceTimer = null;
const AUTO_CHECK_EXAM_DEBOUNCE_MS = 800;
const AUTO_CHECK_EXAM_RETRY_DELAY_MS = 150;
const AUTO_CHECK_EXAM_MAX_RETRIES = 8;

// Track current conflict state
let hasExamConflictsAdd = false;
let hasExamConflictsEdit = false;
let autoCheckExamFieldObserver = null;
let autoCheckExamRebindTimer = null;

function getExamAutoCheckFieldIds(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    return [
        'section_id_exam' + suffix,
        'curriculum_id_exam' + suffix,
        'subject_id_exam' + suffix,
        'schedule_type_exam' + suffix,
        'faculty_id_exam' + suffix,
        'room_id_exam' + suffix,
        'exam_date' + suffix,
        'start_time_exam' + suffix,
        'end_time_exam' + suffix
    ];
}

function bindExamAutoCheckFieldEvents(field, fieldId, mode, suffix) {
    const boundAttr = `data-auto-check-exam-bound-${mode}`;
    if (field.getAttribute(boundAttr) === '1') {
        return;
    }

    field.addEventListener('change', () => {
        updateImmediateExamFacultyDayWarning(mode);

        if (fieldId === ('exam_date' + suffix)) {
            if (canRunExamAutoCheckNow(mode)) {
                runImmediateExamAutoConflictCheck(mode);
            }
            return;
        }

        scheduleAutoExamConflictCheck(mode);
    });

    if (fieldId.includes('time') || fieldId.includes('date')) {
        field.addEventListener('input', () => {
            scheduleAutoExamConflictCheck(mode);
        });
    }

    field.setAttribute(boundAttr, '1');
}

function scheduleExamAutoCheckRebind() {
    if (autoCheckExamRebindTimer) {
        clearTimeout(autoCheckExamRebindTimer);
    }

    autoCheckExamRebindTimer = setTimeout(() => {
        setupAutoCheckForExamModalWithRetry('add');
        setupAutoCheckForExamModalWithRetry('edit');
    }, AUTO_CHECK_EXAM_RETRY_DELAY_MS);
}

function initAutoCheckExamFieldObserver() {
    if (autoCheckExamFieldObserver || typeof MutationObserver === 'undefined') {
        return;
    }

    autoCheckExamFieldObserver = new MutationObserver((mutations) => {
        let shouldRebind = false;

        for (const mutation of mutations) {
            for (const node of mutation.addedNodes) {
                if (!node || node.nodeType !== 1) {
                    continue;
                }

                if (
                    (node.matches && (
                        node.matches('.time-picker-hidden-input') ||
                        node.matches('[id^="start_time_exam_"]') ||
                        node.matches('[id^="end_time_exam_"]') ||
                        node.matches('[id^="exam_date_"]')
                    )) ||
                    (node.querySelector && (
                        node.querySelector('.time-picker-hidden-input') ||
                        node.querySelector('[id^="start_time_exam_"]') ||
                        node.querySelector('[id^="end_time_exam_"]') ||
                        node.querySelector('[id^="exam_date_"]')
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
            scheduleExamAutoCheckRebind();
        }
    });

    autoCheckExamFieldObserver.observe(document.body || document.documentElement, {
        childList: true,
        subtree: true
    });
}

/**
 * Initialize automatic conflict detection for both Add and Edit exam modals
 */
function initAutoConflictDetectionExam() {
    setupAutoCheckForExamModalWithRetry('add');
    setupAutoCheckForExamModalWithRetry('edit');
    initAutoCheckExamFieldObserver();
}

function setupAutoCheckForExamModalWithRetry(mode, retriesLeft = AUTO_CHECK_EXAM_MAX_RETRIES) {
    const missingCount = setupAutoCheckForExamModal(mode);
    if (missingCount > 0 && retriesLeft > 0) {
        setTimeout(() => {
            setupAutoCheckForExamModalWithRetry(mode, retriesLeft - 1);
        }, AUTO_CHECK_EXAM_RETRY_DELAY_MS);
    }
}

/**
 * Setup automatic conflict checking for a specific exam modal
 * @param {string} mode - Either 'add' or 'edit'
 */
function setupAutoCheckForExamModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const fields = getExamAutoCheckFieldIds(mode);
    let missingCount = 0;

    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            bindExamAutoCheckFieldEvents(field, fieldId, mode, suffix);
        } else {
            missingCount += 1;
        }
    });

    return missingCount;
}

function canRunExamAutoCheckNow(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const sectionId = document.getElementById('section_id_exam' + suffix)?.value;
    const subjectId = document.getElementById('subject_id_exam' + suffix)?.value || null;
    const facultyId = document.getElementById('faculty_id_exam' + suffix)?.value || null;
    const roomId = document.getElementById('room_id_exam' + suffix)?.value || null;
    const examDate = document.getElementById('exam_date' + suffix)?.value;
    const startTime = document.getElementById('start_time_exam' + suffix)?.value;
    const endTime = document.getElementById('end_time_exam' + suffix)?.value;

    return Boolean(sectionId && subjectId && facultyId && roomId && examDate && startTime && endTime);
}

function runImmediateExamAutoConflictCheck(mode) {
    if (autoCheckExamDebounceTimer) {
        clearTimeout(autoCheckExamDebounceTimer);
        autoCheckExamDebounceTimer = null;
    }
    performAutoExamConflictCheck(mode);
}

function getDayNameFromExamDate(examDateValue) {
    if (!examDateValue) return null;
    const parsed = new Date(`${examDateValue}T00:00:00`);
    if (Number.isNaN(parsed.getTime())) return null;
    const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    return dayNames[parsed.getDay()];
}

function getExamFacultyDayMismatchWarning(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const facultyId = document.getElementById('faculty_id_exam' + suffix)?.value;
    const examDate = document.getElementById('exam_date' + suffix)?.value;

    if (!facultyId || !examDate) return null;

    const examDayName = getDayNameFromExamDate(examDate);
    if (!examDayName) return null;

    const option = document.querySelector(`#faculty_dropdown_exam_${mode} .faculty-option[data-faculty-id="${facultyId}"]`);
    if (!option) return null;

    const facultyName = option.dataset.facultyName || 'Selected proctor';
    const availableDaysRaw = option.dataset.availableDays || '';
    const availableDays = availableDaysRaw
        .split(',')
        .map(day => day.trim())
        .filter(Boolean);

    if (availableDays.length === 0) return null;

    const normalizedDays = availableDays.map(day => day.toLowerCase());
    if (normalizedDays.includes(examDayName.toLowerCase())) {
        return null;
    }

    return {
        type: 'warning',
        message: `${facultyName} is not marked as available on ${examDayName}.`,
        status: 'not_in_schedule',
        faculty_name: facultyName
    };
}

function updateImmediateExamFacultyDayWarning(mode) {
    const warning = getExamFacultyDayMismatchWarning(mode);
    displayExamFacultyAvailabilityWarning(mode, warning);
}

/**
 * Schedule an automatic exam conflict check (with debouncing)
 * @param {string} mode - Either 'add' or 'edit'
 */
function scheduleAutoExamConflictCheck(mode) {
    // Clear existing timer
    if (autoCheckExamDebounceTimer) {
        clearTimeout(autoCheckExamDebounceTimer);
    }
    
    // Schedule new check after debounce delay
    autoCheckExamDebounceTimer = setTimeout(() => {
        performAutoExamConflictCheck(mode);
    }, AUTO_CHECK_EXAM_DEBOUNCE_MS);
}

/**
 * Perform automatic exam conflict check
 * @param {string} mode - Either 'add' or 'edit'
 */
function performAutoExamConflictCheck(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Get form data - with detailed element checking
    const sectionIdEl = document.getElementById('section_id_exam' + suffix);
    const subjectIdEl = document.getElementById('subject_id_exam' + suffix);
    const facultyIdEl = document.getElementById('faculty_id_exam' + suffix);
    const roomIdEl = document.getElementById('room_id_exam' + suffix);
    const examDateEl = document.getElementById('exam_date' + suffix);
    const startTimeEl = document.getElementById('start_time_exam' + suffix);
    const endTimeEl = document.getElementById('end_time_exam' + suffix);
    
    // Log which elements were found
    const sectionId = sectionIdEl?.value;
    const subjectId = subjectIdEl?.value || null;
    const facultyId = facultyIdEl?.value || null;
    const roomId = roomIdEl?.value || null;
    const examDate = examDateEl?.value;
    const startTime = startTimeEl?.value;
    const endTime = endTimeEl?.value;
    const examScheduleId = mode === 'edit' ? document.getElementById('exam_schedule_id_edit')?.value : null;
    const allFieldsFilled = Boolean(
        sectionId &&
        subjectId &&
        facultyId &&
        roomId &&
        examDate &&
        startTime &&
        endTime
    );

    if (!allFieldsFilled) {
        const modeSuffix = mode === 'add' ? 'Add' : 'Edit';
        const examModeSuffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';

        showAutoCheckExamStatus(mode, 'warning', 'Complete all exam details to start AI conflict checking.');
        updateExamConflictState(mode, false, true);

        document.getElementById('aiConflictsExam' + modeSuffix)?.classList.add('hidden');
        document.getElementById('aiRecommendationsExam' + modeSuffix)?.classList.add('hidden');
        document.getElementById('aiExplanationWrapperExam' + modeSuffix)?.classList.add('hidden');
        document.getElementById('aiWorkloadSummaryExam' + modeSuffix)?.classList.add('hidden');

        document.getElementById('aiRecommendations' + examModeSuffix)?.classList.add('hidden');
        document.getElementById('aiExplanationWrapper' + examModeSuffix)?.classList.add('hidden');
        document.getElementById('aiWorkloadSummary' + examModeSuffix)?.classList.add('hidden');

        hideExamResolveAllOption(mode);
        displayExamFacultyAvailabilityWarning(mode, null);
        displayExamScheduleHoursWarning(mode, null);

        return;
    }
    
    // Validate exam date is not in the past
    const today = new Date();
    today.setHours(0, 0, 0, 0); // Set to start of today
    const selectedDate = new Date(examDate);
    selectedDate.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
        showAutoCheckExamStatus(mode, 'error', '⚠️ Cannot schedule exams in the past. Please select a future date.');
        updateExamConflictState(mode, true, false);
        return;
    }
    
    // Validate time range
    if (startTime && endTime && startTime >= endTime) {
        showAutoCheckExamStatus(mode, 'error', '⚠️ End time must be after start time');
        updateExamConflictState(mode, true, false);
        return;
    }
    
    // Show checking status
    showAutoCheckExamStatus(mode, 'checking', '🔍 Checking for exam conflicts...');
    
    // Prepare request data
    const requestData = {
        section_id: parseInt(sectionId),
        subject_id: subjectId ? parseInt(subjectId) : null,
        faculty_id: facultyId ? parseInt(facultyId) : null,
        room_id: roomId ? parseInt(roomId) : null,
        exam_date: examDate,
        start_time: startTime,
        end_time: endTime,
        exam_schedule_id: examScheduleId ? parseInt(examScheduleId) : null,
        use_ai: typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : true
    };
    // Call AI API
    fetch('/exam-schedule/ai-check-conflicts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestData)
    })
    .then(response => {
        if (!response.ok) {
            return response.json().catch(() => {
                // If response is not JSON, throw with status
                throw new Error(`Server error (${response.status}: ${response.statusText})`);
            }).then(errorData => {
                // If response IS JSON, include error details
                throw new Error(`Server error (${response.status}): ${errorData.error || response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        const wantsAi = typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : true;
        const explicitFallback = data.ai_fallback === true;
        const usingFallback = explicitFallback || (wantsAi && !data.ai_enabled);
        const fallbackMessage = typeof data.ai_fallback_message === 'string' ? data.ai_fallback_message.trim() : '';
        const fallbackReason = typeof data.ai_fallback_reason === 'string' ? data.ai_fallback_reason.trim() : '';
        if (typeof setAIFallbackNotice === 'function') {
            setAIFallbackNotice(usingFallback ? (fallbackMessage || fallbackReason || 'AI guidance is currently unavailable. Running Manual Assist (Offline) so you can keep scheduling.') : '');
        }

        if (!data.ai_enabled) {
            // Basic Mode — show conflicts + read-only recommendations + explanation
            const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
            if (data.has_conflicts && data.conflicts && data.conflicts.length > 0) {
                const conflictCount = data.conflicts.length;
                const modeLabel = usingFallback ? 'Fallback: Manual Assist' : 'Manual Assist';
                showAutoCheckExamStatus(mode, 'error', `⚠️ ${conflictCount} conflict${conflictCount > 1 ? 's' : ''} detected (${modeLabel})`);
                displayExamAIConflicts(data.conflicts, mode);

                // Show explanation as Conflict Summary (gray card)
                if (data.ai_explanation && typeof displayExplanation === 'function') {
                    displayExplanation(suffix, data.ai_explanation, false);
                }

                // Show recommendations in read-only mode
                if (data.recommendations && data.recommendations.length > 0) {
                    displayExamRecommendations(data.recommendations, mode, true);
                } else {
                    document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
                }

                // Gate auto-resolve: show placeholder instead of button
                const resolveBtn = document.getElementById('aiResolveAll' + suffix);
                if (resolveBtn) {
                    resolveBtn.innerHTML = `<div class="flex items-center gap-1.5 px-3 py-2 text-xs text-gray-400 bg-gray-50 border border-dashed border-gray-300 rounded-lg"><svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>Auto-Resolve available in AI-Powered mode</div>`;
                    resolveBtn.classList.remove('hidden');
                }

                // Hide workload summary in Basic Mode
                document.getElementById('aiWorkloadSummary' + suffix)?.classList.add('hidden');

                updateExamConflictState(mode, true, false);
                if (typeof autoOpenDrawer === 'function') autoOpenDrawer();
            } else {
                // No conflicts in Basic Mode
                // Hide explanation and workload
                const wrapperEl = document.getElementById('aiExplanationWrapper' + suffix);
                if (wrapperEl) wrapperEl.classList.add('hidden');
                document.getElementById('aiWorkloadSummary' + suffix)?.classList.add('hidden');

                const modeLabel = usingFallback ? 'Fallback: Manual Assist' : 'Manual Assist';
                if (!allFieldsFilled) {
                    showAutoCheckExamStatus(mode, 'success', `✅ No conflicts detected (${modeLabel}) — Fill remaining fields to submit`);
                    updateExamConflictState(mode, false, true);
                } else {
                    showAutoCheckExamStatus(mode, 'success', `✅ No conflicts detected (${modeLabel})`);
                    updateExamConflictState(mode, false, false);
                }
                if (typeof autoCloseDrawer === 'function') autoCloseDrawer();
            }
            
            // Process faculty availability & schedule hours warnings even in offline mode
            displayExamFacultyAvailabilityWarning(mode, data.faculty_availability_warning || null);
            displayExamScheduleHoursWarning(mode, data.schedule_hours_warning || null);
            
            // Schedule hours violation blocks submit even in offline mode
            if (data.schedule_hours_warning) {
                showAutoCheckExamStatus(mode, 'error', `🚫 ${data.schedule_hours_warning}`);
                updateExamConflictState(mode, true, false);
            }
            return;
        }
        
        if (data.error) {
            showAutoCheckExamStatus(mode, 'error', `❌ ${data.error}`);
            updateExamConflictState(mode, true);
            return;
        }
        
        // Handle schedule hours warning (now blocking)
        const scheduleHoursWarning = data.schedule_hours_warning;
        displayExamScheduleHoursWarning(mode, scheduleHoursWarning);
        
        // Handle faculty (proctor) availability warning (separate from conflicts)
        const facultyWarning = data.faculty_availability_warning;
        displayExamFacultyAvailabilityWarning(mode, facultyWarning);
        
        // Check for schedule hours violation first (blocking)
        if (scheduleHoursWarning) {
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckExamStatus(mode, 'error', `🚫 ${scheduleHoursWarning}`);
            hideExamResolveAllOption(mode);
            updateExamConflictState(mode, true);
            
            // Hide conflict/recommendation panels
            document.getElementById('aiConflictsExam' + suffix)?.classList.add('hidden');
            document.getElementById('aiRecommendationsExam' + suffix)?.classList.add('hidden');
        } else if (data.has_conflicts) {
            // AI-Powered: Has conflicts - disable submit
            const conflictCount = data.conflicts.length;
            const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
            showAutoCheckExamStatus(mode, 'error', `⚠️ ${conflictCount} conflict${conflictCount > 1 ? 's' : ''} detected! Adjust schedule and conflicts will auto-recheck.`);
            displayExamConflicts(data.conflicts, mode);
            displayExamRecommendations(data.recommendations, mode, false);
            showExamResolveAllOption(data.conflicts, mode);
            updateExamConflictState(mode, true);
            
            // Show AI explanation as purple AI Analysis card
            const explanationText = data.ai_explanation || 'Conflicts detected. Make changes to auto-recheck.';
            if (typeof displayExplanation === 'function') {
                displayExplanation(suffix, explanationText, true);
            }
            
            // Auto-open AI drawer to show conflicts
            if (typeof autoOpenDrawer === 'function') autoOpenDrawer();
        } else if (facultyWarning && facultyWarning.type === 'error') {
            // Faculty is explicitly unavailable - this is a hard block
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckExamStatus(mode, 'error', `🚫 ${facultyWarning.message}`);
            hideExamResolveAllOption(mode);
            updateExamConflictState(mode, true);
            
            // Hide conflict/recommendation panels since this is an availability issue
            document.getElementById('aiConflictsExam' + suffix)?.classList.add('hidden');
            document.getElementById('aiRecommendationsExam' + suffix)?.classList.add('hidden');
        } else {
            // No conflicts - enable submit
            hideExamResolveAllOption(mode);
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            
            // Check if there's a soft warning about faculty availability
            if (facultyWarning && facultyWarning.type === 'warning') {
                showAutoCheckExamStatus(mode, 'warning', `✅ No conflicts, but: ${facultyWarning.message}`);
            } else {
                showAutoCheckExamStatus(mode, 'success', '✅ No conflicts detected! This exam schedule looks good.');
            }
            // Only enable submit if all fields are filled
            if (!allFieldsFilled) {
                updateExamConflictState(mode, false, true);
            } else {
                updateExamConflictState(mode, false);
            }
            
            // Hide conflict/recommendation panels
            document.getElementById('aiConflictsExam' + suffix)?.classList.add('hidden');
            document.getElementById('aiRecommendationsExam' + suffix)?.classList.add('hidden');
            
            // Hide explanation and workload wrappers when no conflicts
            const explanationWrapper = document.getElementById('aiExplanationWrapperExam' + suffix);
            if (explanationWrapper) explanationWrapper.classList.add('hidden');
            document.getElementById('aiWorkloadSummaryExam' + suffix)?.classList.add('hidden');
            
            // Auto-close drawer if conflicts were resolved
            if (typeof autoCloseDrawer === 'function') autoCloseDrawer();
        }
    })
    .catch(error => {
        console.error('[AUTO-CHECK-EXAM] Error:', error);
        console.error('[AUTO-CHECK-EXAM] Error details:', {
            message: error.message,
            stack: error.stack,
            type: error.constructor.name
        });
        
        // Provide more specific error messages
        let errorMessage = '❌ Network error - Please check your connection';
        if (error.message) {
            if (error.message.includes('Server error')) {
                errorMessage = `❌ ${error.message}`;
            } else if (error.message.includes('Failed to fetch')) {
                errorMessage = '❌ Cannot connect to server - Please ensure the server is running';
            } else if (error.message.includes('NetworkError')) {
                errorMessage = '❌ Network error - Check your internet connection';
            }
        }
        
        showAutoCheckExamStatus(mode, 'error', errorMessage);
        // Allow submission on network errors (don't block user)
        updateExamConflictState(mode, false, false);
    });
}

/**
 * Show auto-check exam status message
 * @param {string} mode - Either 'add' or 'edit'
 * @param {string} type - 'checking', 'success', 'error', 'warning'
 * @param {string} message - Status message to display
 */
function showAutoCheckExamStatus(mode, type, message) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const statusContainer = document.getElementById('autoCheckStatusExam' + suffix);
    const aiPanel = document.getElementById('aiAssistantExam' + suffix);
    const emptyState = document.getElementById('aiEmptyStateExam' + suffix);
    
    // Update floating AI badge state
    if (typeof updateAIBadge === 'function') {
        const badgeMap = { checking: 'checking', success: 'clear', error: 'conflicts', warning: 'warnings' };
        updateAIBadge(badgeMap[type] || 'idle');
    }
    
    // Hide empty state when showing status
    if (emptyState) {
        emptyState.classList.add('hidden');
    }
    
    // Show AI panel for conflicts/recommendations
    if (type === 'success' || type === 'error') {
        if (aiPanel) aiPanel.classList.remove('hidden');
    }
    
    // Lightweight inline status: colored dot + text
    let dotColor = '';
    let textColor = '';
    let dotHtml = '';
    
    switch(type) {
        case 'checking':
            textColor = 'text-blue-600 dark:text-blue-400';
            dotHtml = '<svg class="w-3 h-3 text-blue-500 dark:text-blue-400 animate-spin flex-shrink-0" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
            break;
        case 'success':
            dotColor = 'bg-emerald-400';
            textColor = 'text-emerald-700 dark:text-emerald-300';
            dotHtml = `<span class="w-2 h-2 rounded-full ${dotColor} flex-shrink-0"></span>`;
            break;
        case 'error':
            dotColor = 'bg-red-400';
            textColor = 'text-red-700 dark:text-red-300';
            dotHtml = `<span class="w-2 h-2 rounded-full ${dotColor} flex-shrink-0"></span>`;
            break;
        case 'warning':
            dotColor = 'bg-amber-400';
            textColor = 'text-amber-700 dark:text-amber-300';
            dotHtml = `<span class="w-2 h-2 rounded-full ${dotColor} flex-shrink-0"></span>`;
            break;
    }
    
    // Render status in drawer
    if (statusContainer) {
        statusContainer.innerHTML = `
            <div class="flex items-start gap-2.5 py-2.5 px-3 mb-2.5 rounded-xl border border-gray-200/90 dark:border-gray-700 bg-white dark:bg-gray-900/35 shadow-sm">
                <div class="mt-0.5">${dotHtml}</div>
                <div class="min-w-0">
                    <p class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide">Live Conflict Check</p>
                    <p class="text-xs font-medium ${textColor} leading-relaxed">${message}</p>
                </div>
            </div>
        `;
    }
}

/**
 * Update exam conflict state and submit button
 * @param {string} mode - Either 'add' or 'edit'
 * @param {boolean} hasConflicts - Whether conflicts exist
 * @param {boolean} allowSubmit - Force allow submission (for incomplete forms or errors)
 */
function updateExamConflictState(mode, hasConflicts, allowSubmit = false) {
    // Update global state
    if (mode === 'add') {
        hasExamConflictsAdd = hasConflicts;
    } else {
        hasExamConflictsEdit = hasConflicts;
    }
    
    // Get submit button and text element by ID (for workspace modal style)
    const submitButton = document.getElementById('submitExamSchedule' + (mode === 'add' ? 'Add' : 'Edit'));
    const submitButtonText = document.getElementById('submitExamSchedule' + (mode === 'add' ? 'Add' : 'Edit') + 'Text');
    
    if (!submitButton) return;
    
    // Define base classes for workspace modal button style
    const baseClasses = 'flex items-center px-2.5 sm:px-4 py-1.5 sm:py-2 text-xs sm:text-sm font-semibold text-white rounded-lg transition-all';
    const disabledClasses = baseClasses + ' bg-gray-400 cursor-not-allowed';
    const enabledClasses = baseClasses + ' bg-gradient-to-r from-orange-500 to-amber-600 hover:from-orange-600 hover:to-amber-700 shadow-sm';
    
    // Determine actual mode for button text - use window.examModalMode for unified modal
    const actualMode = (mode === 'add' && typeof window.examModalMode !== 'undefined') 
        ? window.examModalMode 
        : mode;
    
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
            submitButtonText.textContent = actualMode === 'add' ? 'Add Exam' : 'Update Exam';
        }
    }
}

/**
 * Reset auto-check exam state when modal is closed
 * @param {string} mode - Either 'add' or 'edit'
 */
function resetAutoCheckExamState(mode) {
    // Clear debounce timer
    if (autoCheckExamDebounceTimer) {
        clearTimeout(autoCheckExamDebounceTimer);
        autoCheckExamDebounceTimer = null;
    }
    
    // Reset conflict state
    updateExamConflictState(mode, false, true);
    
    // Reset resolve-all state
    hideExamResolveAllOption(mode);
    
    // Reset floating AI badge to idle
    if (typeof updateAIBadge === 'function') updateAIBadge('idle');
    
    // Hide AI panel and show empty state
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const aiPanel = document.getElementById('aiAssistantExam' + suffix);
    const emptyState = document.getElementById('aiEmptyStateExam' + suffix);
    const statusContainer = document.getElementById('autoCheckStatusExam' + suffix);
    
    if (aiPanel) aiPanel.classList.add('hidden');
    
    if (emptyState) emptyState.classList.remove('hidden');
    
    if (statusContainer) statusContainer.innerHTML = '';
    
    // Hide conflict/recommendation sections
    const conflictsSection = document.getElementById('aiConflictsExam' + suffix);
    const recommendationsSection = document.getElementById('aiRecommendationsExam' + suffix);
    const explanationSection = document.getElementById('aiExplanationExam' + suffix);
    
    if (conflictsSection) conflictsSection.classList.add('hidden');
    if (recommendationsSection) recommendationsSection.classList.add('hidden');
    if (explanationSection) explanationSection.classList.add('hidden');
    
    // Clear schedule hours warning
    displayExamScheduleHoursWarning(mode, null);
    
    // Clear faculty availability warning
    displayExamFacultyAvailabilityWarning(mode, null);
}

/**
 * Display faculty availability warning for exam schedules
 * @param {string} mode - Either 'add' or 'edit'
 * @param {object} warning - Faculty availability warning object or null
 */
function displayExamFacultyAvailabilityWarning(mode, warning) {
    const suffixCap = mode === 'add' ? 'Add' : 'Edit';
    
    // Get the warning container (should exist in HTML)
    const warningContainer = document.getElementById('examFacultyAvailabilityWarning' + suffixCap);
    
    if (!warningContainer) {
        return;
    }
    
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
            <div class="flex items-center gap-2 px-3 py-2 mt-2 bg-red-50 border border-red-200 rounded-lg">
                <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
                </svg>
                <p class="text-xs text-red-700"><strong>Unavailable:</strong> ${warning.message}</p>
            </div>
        `;
    } else if (warning.type === 'warning') {
        // Soft warning - faculty has schedule but not available at this time
        warningContainer.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 mt-2 bg-amber-50 border border-amber-200 rounded-lg">
                <svg class="w-4 h-4 text-amber-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-xs text-amber-700"><strong>Note:</strong> Proctor not marked available for this day/time. You can still proceed.</p>
            </div>
        `;
    } else if (warning.type === 'success') {
        // Positive confirmation - proctor is available
        warningContainer.innerHTML = `
            <div class="flex items-center gap-2 px-3 py-2 mt-2 bg-green-50 border border-green-200 rounded-lg">
                <svg class="w-4 h-4 text-green-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <p class="text-xs text-green-700"><strong>Available:</strong> ${warning.message}</p>
            </div>
        `;
    }
}

/**
 * Display schedule hours warning for exam schedules (non-blocking)
 * @param {string} mode - Either 'add' or 'edit'
 * @param {string} warning - Schedule hours warning message or null
 */
function displayExamScheduleHoursWarning(mode, warning) {
    const suffixCap = mode === 'add' ? 'Add' : 'Edit';
    
    // Get the warning container (should exist in HTML)
    const warningContainer = document.getElementById('examScheduleHoursWarning' + suffixCap);
    
    if (!warningContainer) {
        return;
    }
    
    if (!warning) {
        // Clear warning
        warningContainer.innerHTML = '';
        warningContainer.classList.add('hidden');
        return;
    }
    
    warningContainer.classList.remove('hidden');
    
    // Display as red error (blocking)
    warningContainer.innerHTML = `
        <div class="flex items-center gap-2 px-3 py-2 mt-2 bg-red-50 border border-red-200 rounded-lg">
            <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <p class="text-xs text-red-700"><strong>Invalid Time:</strong> ${warning}</p>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════
// RESOLVE-ALL FOR EXAM SCHEDULES
// ═══════════════════════════════════════════════════════════

let _currentExamConflicts = [];
let _currentExamFormData = {};
let _currentExamResolutionPlan = null;

/**
 * Show the "Auto-Resolve Available" section after exam conflicts are detected.
 * @param {Array} conflicts - List of conflict objects
 * @param {string} mode - 'add' or 'edit'
 */
function showExamResolveAllOption(conflicts, mode) {
    const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
    const container = document.getElementById('aiResolveAll' + suffix);

    if (!container) return;

    const resolvableConflicts = conflicts.filter(
        c => c.severity === 'critical' || c.severity === 'high'
    );

    if (resolvableConflicts.length === 0) {
        container.classList.add('hidden');
        container.innerHTML = '';
        return;
    }

    _currentExamConflicts = conflicts;
    _currentExamResolutionPlan = null;

    container.classList.remove('hidden');
    container.innerHTML = `
        <div class="flex items-center justify-between gap-2 py-2">
            <p class="text-[10px] text-gray-500"><span class="font-medium text-gray-600">${resolvableConflicts.length}</span> conflict${resolvableConflicts.length > 1 ? 's' : ''} can be auto-resolved</p>
            <button type="button" onclick="generateExamResolutionPlan('${mode}')"
                    id="resolveAllExamBtn${suffix}"
                    class="flex-shrink-0 px-3 py-1.5 bg-blue-600 text-white text-[11px] font-medium rounded-md hover:bg-blue-700 transition-colors">
                Generate Plan
            </button>
        </div>
    `;
}

/**
 * Hide the exam resolve-all section
 * @param {string} mode - 'add' or 'edit'
 */
function hideExamResolveAllOption(mode) {
    const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
    const container = document.getElementById('aiResolveAll' + suffix);
    if (container) {
        container.classList.add('hidden');
        container.innerHTML = '';
    }
    _currentExamConflicts = [];
    _currentExamResolutionPlan = null;
}

/**
 * Gather current exam form values into a data object
 * @param {string} mode - 'add' or 'edit'
 * @returns {object} exam form data
 */
function _gatherExamFormData(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';

    return {
        section_id: parseInt(document.getElementById('section_id_exam' + suffix)?.value) || null,
        subject_id: parseInt(document.getElementById('subject_id_exam' + suffix)?.value) || null,
        faculty_id: parseInt(document.getElementById('faculty_id_exam' + suffix)?.value) || null,
        room_id: parseInt(document.getElementById('room_id_exam' + suffix)?.value) || null,
        exam_date: document.getElementById('exam_date' + suffix)?.value || '',
        start_time: document.getElementById('start_time_exam' + suffix)?.value || '',
        end_time: document.getElementById('end_time_exam' + suffix)?.value || '',
        exam_schedule_id: mode === 'edit' ? (document.getElementById('exam_schedule_id_edit')?.value || null) : null
    };
}

/**
 * Call backend to generate an exam resolution plan
 * @param {string} mode - 'add' or 'edit'
 */
async function generateExamResolutionPlan(mode) {
    const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
    const btn = document.getElementById('resolveAllExamBtn' + suffix);
    const container = document.getElementById('aiResolveAll' + suffix);

    if (!container) return;

    const formData = _gatherExamFormData(mode);
    _currentExamFormData = formData;

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
        const response = await fetch('/exam-schedule/resolve-conflicts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                ...formData,
                conflicts: _currentExamConflicts
            })
        });

        if (!response.ok) {
            throw new Error(`Server error (${response.status})`);
        }

        const plan = await response.json();

        if (plan.error) {
            throw new Error(plan.error);
        }

        _currentExamResolutionPlan = plan;
        showExamResolutionPlan(plan, mode);

    } catch (err) {
        console.error('[EXAM-RESOLVE-ALL] Error:', err);
        container.innerHTML = `
            <div class="p-3 bg-red-50 border border-red-200 rounded-xl">
                <div class="flex items-center gap-2">
                    <svg class="w-4 h-4 text-red-500 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                    <p class="text-xs text-red-700">${err.message || 'Failed to generate exam resolution plan'}</p>
                </div>
            </div>
        `;
    }
}

/**
 * Display the exam resolution plan
 * @param {object} plan - Resolution plan from backend
 * @param {string} mode - 'add' or 'edit'
 */
function showExamResolutionPlan(plan, mode) {
    const suffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
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

    const hasChanges = dedupedResolutions.length > 0 && actionableCount > 0;

    let html = '';

    if (hasChanges) {
        const totalConflicts = Number(stats.total_conflicts || 0);
        html += `
            <div class="mb-2">
                <div class="flex items-center gap-2 mb-2">
                    <div class="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0"></div>
                    <p class="text-xs font-medium text-emerald-700">${actionableCount} change${actionableCount > 1 ? 's' : ''} can auto-resolve ${totalConflicts} conflict${totalConflicts > 1 ? 's' : ''}</p>
                </div>
        `;

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

        html += `
                <button type="button" onclick="applyExamResolutionPlan('${mode}')"
                        id="applyExamResolutionBtn${suffix}"
                        class="w-full mt-2 py-1.5 bg-emerald-600 text-white text-xs font-medium rounded-md hover:bg-emerald-700 transition-colors flex items-center justify-center gap-1.5">
                    Apply ${actionableCount} Change${actionableCount > 1 ? 's' : ''}
                </button>
            </div>
        `;
    } else {
        html += `
            <div class="flex items-center gap-2 py-1.5 mb-2">
                <div class="w-2 h-2 rounded-full bg-amber-400 flex-shrink-0"></div>
                <p class="text-xs text-amber-700">Manual resolution needed — adjust using recommendations below</p>
            </div>
        `;
    }

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
 * Apply the exam resolution plan by updating form fields and re-triggering conflict check.
 * @param {string} mode - 'add' or 'edit'
 */
function applyExamResolutionPlan(mode) {
    const plan = _currentExamResolutionPlan;
    if (!plan || !plan.form_changes) return;

    const suffix = mode === 'add' ? '_add' : '_edit';
    const formChanges = plan.form_changes;

    if (formChanges.start_time) {
        const el = document.getElementById('start_time_exam' + suffix);
        if (el) { el.value = formChanges.start_time; highlightExamField('start_time_exam' + suffix); }
    }
    if (formChanges.end_time) {
        const el = document.getElementById('end_time_exam' + suffix);
        if (el) { el.value = formChanges.end_time; highlightExamField('end_time_exam' + suffix); }
    }
    if (formChanges.exam_date) {
        const el = document.getElementById('exam_date' + suffix);
        if (el) { el.value = formChanges.exam_date; highlightExamField('exam_date' + suffix); }
    }
    if (formChanges.room_id) {
        const el = document.getElementById('room_id_exam' + suffix);
        if (el) { el.value = String(formChanges.room_id); highlightExamField('room_id_exam' + suffix); }
    }
    if (formChanges.faculty_id) {
        const el = document.getElementById('faculty_id_exam' + suffix);
        if (el) { el.value = String(formChanges.faculty_id); highlightExamField('faculty_id_exam' + suffix); }
    }

    // Show brief success flash
    const uiSuffix = mode === 'add' ? 'ExamAdd' : 'ExamEdit';
    const container = document.getElementById('aiResolveAll' + uiSuffix);
    if (container) {
        container.innerHTML = `
            <div class="flex items-center gap-2 py-1.5">
                <div class="w-2 h-2 rounded-full bg-emerald-500 flex-shrink-0"></div>
                <p class="text-xs text-emerald-700">Changes applied — re-checking conflicts...</p>
            </div>
        `;
    }

    _currentExamResolutionPlan = null;
    _currentExamConflicts = [];

    setTimeout(() => {
        performAutoExamConflictCheck(mode);
    }, 300);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    initAutoConflictDetectionExam();
});

// Export functions for use in other scripts
window.initAutoConflictDetectionExam = initAutoConflictDetectionExam;
window.resetAutoCheckExamState = resetAutoCheckExamState;
window.performAutoExamConflictCheck = performAutoExamConflictCheck;
window.showExamResolveAllOption = showExamResolveAllOption;
window.hideExamResolveAllOption = hideExamResolveAllOption;
window.generateExamResolutionPlan = generateExamResolutionPlan;
window.applyExamResolutionPlan = applyExamResolutionPlan;
