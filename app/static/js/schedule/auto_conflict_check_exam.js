/**
 * Automatic Conflict Detection System for Exam Schedules
 * Automatically checks for exam schedule conflicts when form fields change
 * and prevents submission until conflicts are resolved
 */

// Debounce timer to prevent excessive API calls
let autoCheckExamDebounceTimer = null;
const AUTO_CHECK_EXAM_DEBOUNCE_MS = 800;

// Track current conflict state
let hasExamConflictsAdd = false;
let hasExamConflictsEdit = false;

/**
 * Initialize automatic conflict detection for both Add and Edit exam modals
 */
function initAutoConflictDetectionExam() {
    console.log('[AUTO-CHECK-EXAM] Initializing automatic conflict detection for exams...');
    
    // Initialize for Add Modal
    setupAutoCheckForExamModal('add');
    
    // Initialize for Edit Modal
    setupAutoCheckForExamModal('edit');
}

/**
 * Setup automatic conflict checking for a specific exam modal
 * @param {string} mode - Either 'add' or 'edit'
 */
function setupAutoCheckForExamModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Get all form fields that should trigger conflict check
    const fields = [
        'subject_id_exam' + suffix,
        'faculty_id_exam' + suffix,
        'room_id_exam' + suffix,
        'exam_date' + suffix,
        'start_time_exam' + suffix,
        'end_time_exam' + suffix
    ];
    
    // Add change listeners to all fields
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('change', () => {
                console.log(`[AUTO-CHECK-EXAM] ${fieldId} changed, scheduling check...`);
                scheduleAutoExamConflictCheck(mode);
            });
            
            // Also check on input for date and time fields
            if (fieldId.includes('time') || fieldId.includes('date')) {
                field.addEventListener('input', () => {
                    scheduleAutoExamConflictCheck(mode);
                });
            }
        }
    });
    
    console.log(`[AUTO-CHECK-EXAM] Listeners attached for ${mode} exam modal`);
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
    
    // Get form data
    const sectionId = document.getElementById('section_id_exam' + suffix)?.value;
    const subjectId = document.getElementById('subject_id_exam' + suffix)?.value || null;
    const facultyId = document.getElementById('faculty_id_exam' + suffix)?.value || null;
    const roomId = document.getElementById('room_id_exam' + suffix)?.value || null;
    const examDate = document.getElementById('exam_date' + suffix)?.value;
    const startTime = document.getElementById('start_time_exam' + suffix)?.value;
    const endTime = document.getElementById('end_time_exam' + suffix)?.value;
    const examScheduleId = mode === 'edit' ? document.getElementById('exam_schedule_id_edit')?.value : null;
    
    console.log('[AUTO-CHECK-EXAM] Form data:', {
        sectionId, subjectId, facultyId, roomId, 
        examDate, startTime, endTime, examScheduleId
    });
    
    // Check if we have minimum required fields
    if (!sectionId || !examDate || !startTime || !endTime) {
        console.log('[AUTO-CHECK-EXAM] Missing required fields, skipping check');
        // Reset conflict state when fields are incomplete
        updateExamConflictState(mode, false, true);
        return;
    }
    
    // Validate time range
    if (startTime && endTime && startTime >= endTime) {
        console.log('[AUTO-CHECK-EXAM] Invalid time range');
        showAutoCheckExamStatus(mode, 'error', '⚠️ End time must be after start time');
        updateExamConflictState(mode, true);
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
        exam_schedule_id: examScheduleId ? parseInt(examScheduleId) : null
    };
    
    console.log('[AUTO-CHECK-EXAM] Sending request:', requestData);
    
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
            throw new Error(`Server error (${response.status})`);
        }
        return response.json();
    })
    .then(data => {
        console.log('[AUTO-CHECK-EXAM] Response:', data);
        
        if (!data.ai_enabled) {
            showAutoCheckExamStatus(mode, 'warning', 'ℹ️ AI conflict detection not enabled - Manual validation required');
            // Allow submission when AI is disabled
            updateExamConflictState(mode, false, false);
            return;
        }
        
        if (data.error) {
            showAutoCheckExamStatus(mode, 'error', `❌ ${data.error}`);
            updateExamConflictState(mode, true);
            return;
        }
        
        if (data.has_conflicts) {
            // Has conflicts - disable submit
            const conflictCount = data.conflicts.length;
            showAutoCheckExamStatus(mode, 'error', `⚠️ ${conflictCount} conflict${conflictCount > 1 ? 's' : ''} detected! Adjust schedule and conflicts will auto-recheck.`);
            displayExamConflicts(data.conflicts, mode);
            displayExamRecommendations(data.recommendations, mode);
            updateExamConflictState(mode, true);
            
            // Show full AI explanation (desktop and mobile)
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            const explanationEl = document.getElementById('aiExplanationExam' + suffix);
            const explanationElMobile = document.getElementById('aiExplanationExam' + suffix + 'Mobile');
            const explanationText = data.ai_explanation || 'Conflicts detected. Make changes to auto-recheck.';
            if (explanationEl) {
                explanationEl.textContent = explanationText;
            }
            if (explanationElMobile) {
                explanationElMobile.textContent = explanationText;
            }
        } else {
            // No conflicts - enable submit
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckExamStatus(mode, 'success', '✅ No conflicts detected! This exam schedule looks good.');
            updateExamConflictState(mode, false);
            
            // Hide conflict/recommendation panels (desktop and mobile)
            document.getElementById('aiConflictsExam' + suffix)?.classList.add('hidden');
            document.getElementById('aiConflictsExam' + suffix + 'Mobile')?.classList.add('hidden');
            document.getElementById('aiRecommendationsExam' + suffix)?.classList.add('hidden');
            document.getElementById('aiRecommendationsExam' + suffix + 'Mobile')?.classList.add('hidden');
            
            // Hide explanation elements when no conflicts (message already in status)
            const explanationEl = document.getElementById('aiExplanationExam' + suffix);
            const explanationElMobile = document.getElementById('aiExplanationExam' + suffix + 'Mobile');
            if (explanationEl) {
                explanationEl.classList.add('hidden');
            }
            if (explanationElMobile) {
                explanationElMobile.classList.add('hidden');
            }
        }
    })
    .catch(error => {
        console.error('[AUTO-CHECK-EXAM] Error:', error);
        showAutoCheckExamStatus(mode, 'error', '❌ Network error - Please check your connection');
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
    const statusContainerMobile = document.getElementById('autoCheckStatusExam' + suffix + 'Mobile');
    const aiPanel = document.getElementById('aiAssistantExam' + suffix);
    const aiPanelMobile = document.getElementById('aiAssistantExam' + suffix + 'Mobile');
    const emptyState = document.getElementById('aiEmptyStateExam' + suffix);
    const emptyStateMobile = document.getElementById('aiEmptyStateExam' + suffix + 'Mobile');
    
    // Hide empty state when showing status
    if (emptyState) {
        emptyState.classList.add('hidden');
    }
    if (emptyStateMobile) {
        emptyStateMobile.classList.add('hidden');
    }
    
    // Show AI panel for conflicts/recommendations
    if (type === 'success' || type === 'error') {
        if (aiPanel) aiPanel.classList.remove('hidden');
        if (aiPanelMobile) aiPanelMobile.classList.remove('hidden');
    }
    
    // Create status message element
    let statusClass = 'p-4 rounded-lg border-l-4 mb-4 ';
    let statusClassMobile = 'p-2 rounded-lg border-l-4 mb-3 ';
    let icon = '';
    let iconMobile = '';
    
    switch(type) {
        case 'checking':
            statusClass += 'bg-blue-50 border-blue-500 text-blue-800';
            statusClassMobile += 'bg-blue-50 border-blue-500 text-blue-800';
            icon = '<svg class="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
            iconMobile = '<svg class="w-4 h-4 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>';
            break;
        case 'success':
            statusClass += 'bg-green-50 border-green-500 text-green-800';
            statusClassMobile += 'bg-green-50 border-green-500 text-green-800';
            icon = '<svg class="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
            iconMobile = '<svg class="w-4 h-4 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
            break;
        case 'error':
            statusClass += 'bg-red-50 border-red-500 text-red-800';
            statusClassMobile += 'bg-red-50 border-red-500 text-red-800';
            icon = '<svg class="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
            iconMobile = '<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>';
            break;
        case 'warning':
            statusClass += 'bg-yellow-50 border-yellow-500 text-yellow-800';
            statusClassMobile += 'bg-yellow-50 border-yellow-500 text-yellow-800';
            icon = '<svg class="w-5 h-5 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
            iconMobile = '<svg class="w-4 h-4 text-yellow-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path></svg>';
            break;
    }
    
    // Desktop version
    if (statusContainer) {
        statusContainer.innerHTML = `
            <div class="${statusClass}">
                <div class="flex items-center space-x-3">
                    ${icon}
                    <p class="text-sm font-medium">${message}</p>
                </div>
            </div>
        `;
    }
    
    // Mobile version (more compact)
    if (statusContainerMobile) {
        statusContainerMobile.innerHTML = `
            <div class="${statusClassMobile}">
                <div class="flex items-center space-x-2">
                    ${iconMobile}
                    <p class="text-[10px] font-medium">${message}</p>
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
    
    // Get submit button form
    const submitForm = document.getElementById(mode === 'add' ? 'addExamScheduleForm' : 'editExamScheduleForm');
    const submitButton = submitForm?.querySelector('button[type="submit"]');
    
    if (!submitButton) return;
    
    // Update button state
    if (hasConflicts && !allowSubmit) {
        // Conflicts exist - DISABLE button
        submitButton.disabled = true;
        submitButton.className = 'px-2 py-1.5 sm:px-4 sm:py-2.5 md:px-6 md:py-3 text-[11px] sm:text-sm font-semibold text-white bg-gray-400 rounded-lg cursor-not-allowed transition-all shadow-lg';
        submitButton.title = 'Resolve conflicts before submitting';
        submitButton.innerHTML = `
            <svg class="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
            </svg>
            Resolve Conflicts to ${mode === 'add' ? 'Add' : 'Update'}
        `;
        console.log(`[AUTO-CHECK-EXAM] Submit button DISABLED for ${mode} modal`);
    } else if (allowSubmit) {
        // Incomplete form - DISABLE button with appropriate message
        submitButton.disabled = true;
        submitButton.className = 'px-2 py-1.5 sm:px-4 sm:py-2.5 md:px-6 md:py-3 text-[11px] sm:text-sm font-semibold text-white bg-gray-400 rounded-lg cursor-not-allowed transition-all shadow-lg';
        submitButton.title = 'Fill in all required fields';
        submitButton.innerHTML = `
            <svg class="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
            </svg>
            Fill in Required Fields
        `;
        console.log(`[AUTO-CHECK-EXAM] Submit button DISABLED (incomplete) for ${mode} modal`);
    } else {
        // No conflicts - ENABLE button
        submitButton.disabled = false;
        submitButton.className = 'px-2 py-1.5 sm:px-4 sm:py-2.5 md:px-6 md:py-3 text-[11px] sm:text-sm font-semibold text-white bg-red-600 rounded-lg hover:bg-red-700 transition-all flex items-center shadow-lg hover:shadow-xl';
        submitButton.title = '';
        submitButton.innerHTML = `
            <svg class="w-3 h-3 sm:w-4 sm:h-4 mr-1 sm:mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="${mode === 'add' ? 'M12 4v16m8-8H4' : 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z'}"></path>
            </svg>
            ${mode === 'add' ? 'Add Exam Schedule' : 'Update Exam Schedule'}
        `;
        console.log(`[AUTO-CHECK-EXAM] Submit button ENABLED for ${mode} modal`);
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
    
    // Hide AI panel and show empty state
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const aiPanel = document.getElementById('aiAssistantExam' + suffix);
    const aiPanelMobile = document.getElementById('aiAssistantExam' + suffix + 'Mobile');
    const emptyState = document.getElementById('aiEmptyStateExam' + suffix);
    const emptyStateMobile = document.getElementById('aiEmptyStateExam' + suffix + 'Mobile');
    const statusContainer = document.getElementById('autoCheckStatusExam' + suffix);
    const statusContainerMobile = document.getElementById('autoCheckStatusExam' + suffix + 'Mobile');
    
    if (aiPanel) aiPanel.classList.add('hidden');
    if (aiPanelMobile) aiPanelMobile.classList.add('hidden');
    
    if (emptyState) emptyState.classList.remove('hidden');
    if (emptyStateMobile) emptyStateMobile.classList.remove('hidden');
    
    if (statusContainer) statusContainer.innerHTML = '';
    if (statusContainerMobile) statusContainerMobile.innerHTML = '';
    
    // Hide conflict/recommendation sections
    const conflictsSection = document.getElementById('aiConflictsExam' + suffix);
    const conflictsSectionMobile = document.getElementById('aiConflictsExam' + suffix + 'Mobile');
    const recommendationsSection = document.getElementById('aiRecommendationsExam' + suffix);
    const recommendationsSectionMobile = document.getElementById('aiRecommendationsExam' + suffix + 'Mobile');
    const explanationSection = document.getElementById('aiExplanationExam' + suffix);
    const explanationSectionMobile = document.getElementById('aiExplanationExam' + suffix + 'Mobile');
    
    if (conflictsSection) conflictsSection.classList.add('hidden');
    if (conflictsSectionMobile) conflictsSectionMobile.classList.add('hidden');
    if (recommendationsSection) recommendationsSection.classList.add('hidden');
    if (recommendationsSectionMobile) recommendationsSectionMobile.classList.add('hidden');
    if (explanationSection) explanationSection.classList.add('hidden');
    if (explanationSectionMobile) explanationSectionMobile.classList.add('hidden');
    
    console.log(`[AUTO-CHECK-EXAM] State reset for ${mode} exam modal`);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[AUTO-CHECK-EXAM] DOM loaded, waiting for exam modals...');
    
    // Wait a bit for modals to be in DOM, then initialize
    setTimeout(() => {
        initAutoConflictDetectionExam();
    }, 500);
});

// Export functions for use in other scripts
window.initAutoConflictDetectionExam = initAutoConflictDetectionExam;
window.resetAutoCheckExamState = resetAutoCheckExamState;
window.performAutoExamConflictCheck = performAutoExamConflictCheck;
