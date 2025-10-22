/**
 * Automatic Conflict Detection System
 * Automatically checks for schedule conflicts when form fields change
 * and prevents submission until conflicts are resolved
 */

// Debounce timer to prevent excessive API calls
let autoCheckDebounceTimer = null;
const AUTO_CHECK_DEBOUNCE_MS = 800;

// Track current conflict state
let hasConflictsAdd = false;
let hasConflictsEdit = false;

/**
 * Initialize automatic conflict detection for both Add and Edit modals
 */
function initAutoConflictDetection() {
    console.log('[AUTO-CHECK] Initializing automatic conflict detection...');
    
    // Initialize for Add Modal
    setupAutoCheckForModal('add');
    
    // Initialize for Edit Modal
    setupAutoCheckForModal('edit');
}

/**
 * Setup automatic conflict checking for a specific modal
 * @param {string} mode - Either 'add' or 'edit'
 */
function setupAutoCheckForModal(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Get all form fields that should trigger conflict check
    const fields = [
        'subject_id' + suffix,
        'faculty_id' + suffix,
        'room_id' + suffix,
        'day_of_week' + suffix,
        'schedule_type' + suffix,
        'start_time' + suffix,
        'end_time' + suffix
    ];
    
    // Add change listeners to all fields
    fields.forEach(fieldId => {
        const field = document.getElementById(fieldId);
        if (field) {
            field.addEventListener('change', () => {
                console.log(`[AUTO-CHECK] ${fieldId} changed, scheduling check...`);
                scheduleAutoConflictCheck(mode);
            });
            
            // Also check on input for time fields
            if (fieldId.includes('time')) {
                field.addEventListener('input', () => {
                    scheduleAutoConflictCheck(mode);
                });
            }
        }
    });
    
    console.log(`[AUTO-CHECK] Listeners attached for ${mode} modal`);
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
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Get form data
    const sectionId = document.getElementById('section_id' + suffix)?.value;
    const subjectId = document.getElementById('subject_id' + suffix)?.value || null;
    const facultyId = document.getElementById('faculty_id' + suffix)?.value || null;
    const roomId = document.getElementById('room_id' + suffix)?.value || null;
    const dayOfWeek = document.getElementById('day_of_week' + suffix)?.value;
    const scheduleType = document.getElementById('schedule_type' + suffix)?.value || 'lecture';
    const startTime = document.getElementById('start_time' + suffix)?.value;
    const endTime = document.getElementById('end_time' + suffix)?.value;
    const scheduleId = mode === 'edit' ? document.getElementById('schedule_id_edit')?.value : null;
    
    console.log('[AUTO-CHECK] Form data:', {
        sectionId, subjectId, facultyId, roomId, 
        dayOfWeek, scheduleType, startTime, endTime, scheduleId
    });
    
    // Check if we have minimum required fields
    if (!sectionId || !dayOfWeek || !startTime || !endTime) {
        console.log('[AUTO-CHECK] Missing required fields, skipping check');
        // Reset conflict state when fields are incomplete
        updateConflictState(mode, false, true);
        return;
    }
    
    // Validate time range
    if (startTime && endTime && startTime >= endTime) {
        console.log('[AUTO-CHECK] Invalid time range');
        showAutoCheckStatus(mode, 'error', '⚠️ End time must be after start time');
        updateConflictState(mode, true);
        return;
    }
    
    // Show checking status
    showAutoCheckStatus(mode, 'checking', '🔍 Checking for conflicts...');
    
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
        schedule_id: scheduleId ? parseInt(scheduleId) : null
    };
    
    console.log('[AUTO-CHECK] Sending request:', requestData);
    
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
            throw new Error(`Server error (${response.status})`);
        }
        return response.json();
    })
    .then(data => {
        console.log('[AUTO-CHECK] Response:', data);
        
        if (!data.ai_enabled) {
            showAutoCheckStatus(mode, 'warning', 'ℹ️ AI conflict detection not enabled - Manual validation required');
            // Allow submission when AI is disabled (no conflicts detected manually)
            updateConflictState(mode, false, false);
            return;
        }
        
        if (data.error) {
            showAutoCheckStatus(mode, 'error', `❌ ${data.error}`);
            updateConflictState(mode, true);
            return;
        }
        
        if (data.has_conflicts) {
            // Has conflicts - disable submit
            const conflictCount = data.conflicts.length;
            const suffix = mode === 'add' ? 'Add' : 'Edit';
            showAutoCheckStatus(mode, 'error', `⚠️ ${conflictCount} conflict${conflictCount > 1 ? 's' : ''} detected! Adjust schedule and conflicts will auto-recheck.`);
            displayAIConflicts(data.conflicts, mode);
            displayAIRecommendations(data.recommendations, mode);
            updateConflictState(mode, true);
            
            // Show full AI explanation (desktop and mobile)
            const explanationEl = document.getElementById('aiExplanation' + suffix);
            const explanationElMobile = document.getElementById('aiExplanation' + suffix + 'Mobile');
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
            showAutoCheckStatus(mode, 'success', '✅ No conflicts detected!');
            updateConflictState(mode, false);
            
            // Hide conflict/recommendation panels (desktop and mobile)
            document.getElementById('aiConflicts' + suffix)?.classList.add('hidden');
            document.getElementById('aiConflicts' + suffix + 'Mobile')?.classList.add('hidden');
            document.getElementById('aiRecommendations' + suffix)?.classList.add('hidden');
            document.getElementById('aiRecommendations' + suffix + 'Mobile')?.classList.add('hidden');
            
            // Show success explanation (desktop and mobile)
            const explanationEl = document.getElementById('aiExplanation' + suffix);
            const explanationElMobile = document.getElementById('aiExplanation' + suffix + 'Mobile');
            const successText = '✅ No conflicts detected! This schedule looks good.';
            if (explanationEl) {
                explanationEl.textContent = successText;
            }
            if (explanationElMobile) {
                explanationElMobile.textContent = successText;
            }
        }
    })
    .catch(error => {
        console.error('[AUTO-CHECK] Error:', error);
        showAutoCheckStatus(mode, 'error', '❌ Network error - Please check your connection');
        // Allow submission on network errors (don't block user)
        updateConflictState(mode, false, false);
    });
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
    const statusContainerMobile = document.getElementById('autoCheckStatus' + suffix + 'Mobile');
    const aiPanel = document.getElementById('aiAssistant' + suffix);
    const aiPanelMobile = document.getElementById('aiAssistant' + suffix + 'Mobile');
    const emptyState = document.getElementById('aiEmptyState' + suffix);
    const emptyStateMobile = document.getElementById('aiEmptyState' + suffix + 'Mobile');
    
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
    
    // Get submit button and text element
    const submitButton = document.getElementById('submitSchedule' + (mode === 'add' ? 'Add' : 'Edit'));
    const submitButtonText = document.getElementById('submitSchedule' + (mode === 'add' ? 'Add' : 'Edit') + 'Text');
    
    if (!submitButton) return;
    
    // Update button state
    if (hasConflicts && !allowSubmit) {
        // Conflicts exist - DISABLE button
        submitButton.disabled = true;
        submitButton.className = 'px-6 py-3 text-sm font-semibold text-white bg-gray-400 rounded-lg cursor-not-allowed transition-all';
        submitButton.title = 'Resolve conflicts before submitting';
        if (submitButtonText) {
            submitButtonText.innerHTML = `
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"></path>
                </svg>
                ${mode === 'add' ? 'Resolve Conflicts to Add' : 'Resolve Conflicts to Update'}
            `;
        }
        console.log(`[AUTO-CHECK] Submit button DISABLED for ${mode} modal`);
    } else if (allowSubmit) {
        // Incomplete form - DISABLE button with appropriate message
        submitButton.disabled = true;
        submitButton.className = 'px-6 py-3 text-sm font-semibold text-white bg-gray-400 rounded-lg cursor-not-allowed transition-all';
        submitButton.title = 'Fill in all required fields';
        if (submitButtonText) {
            submitButtonText.innerHTML = `
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
                </svg>
                ${mode === 'add' ? 'Fill in Required Fields' : 'Fill in Required Fields'}
            `;
        }
        console.log(`[AUTO-CHECK] Submit button DISABLED (incomplete) for ${mode} modal`);
    } else {
        // No conflicts - ENABLE button
        submitButton.disabled = false;
        submitButton.className = 'px-6 py-3 text-sm font-semibold text-white bg-gradient-to-r from-blue-600 to-blue-700 rounded-lg hover:from-blue-700 hover:to-blue-800 shadow-sm transition-all';
        submitButton.title = '';
        if (submitButtonText) {
            submitButtonText.innerHTML = `
                <svg class="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>
                ${mode === 'add' ? 'Add Schedule' : 'Update Schedule'}
            `;
        }
        console.log(`[AUTO-CHECK] Submit button ENABLED for ${mode} modal`);
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
    
    console.log(`[AUTO-CHECK] State reset for ${mode} modal`);
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    console.log('[AUTO-CHECK] DOM loaded, waiting for modals...');
    
    // Wait a bit for modals to be in DOM, then initialize
    setTimeout(() => {
        initAutoConflictDetection();
    }, 500);
});

// Export functions for use in other scripts
window.initAutoConflictDetection = initAutoConflictDetection;
window.resetAutoCheckState = resetAutoCheckState;
window.performAutoConflictCheck = performAutoConflictCheck;
