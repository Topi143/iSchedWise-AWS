// ============================================================================
// AI Decision Support for Exam Schedules
// ============================================================================

/**
 * Check exam schedule for conflicts using AI
 * @param {string} mode - 'add' or 'edit'
 */
function checkExamScheduleWithAI(mode) {
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
    
    // Debug logging
    // Validate ALL required fields (including subject, faculty, and room)
    if (!sectionId || !subjectId || !facultyId || !roomId || !examDate || !startTime || !endTime) {
        const missing = [];
        if (!sectionId) missing.push('Section');
        if (!subjectId) missing.push('Subject');
        if (!facultyId) missing.push('Faculty');
        if (!roomId) missing.push('Room');
        if (!examDate) missing.push('Exam Date');
        if (!startTime) missing.push('Start Time');
        if (!endTime) missing.push('End Time');
        showToast(`Please fill in: ${missing.join(', ')}`, 'error');
        return;
    }
    
    // Validate exam date is not in the past
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    const selectedDate = new Date(examDate);
    selectedDate.setHours(0, 0, 0, 0);
    
    if (selectedDate < today) {
        showToast('Cannot schedule exams in the past. Please select a future date.', 'error');
        return;
    }
    
    // Show loading state
    const aiPanel = document.getElementById('aiAssistantExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const loadingDiv = document.getElementById('aiLoadingExam' + (mode === 'add' ? 'Add' : 'Edit'));
    
    if (aiPanel) aiPanel.classList.remove('hidden');
    if (loadingDiv) loadingDiv.classList.remove('hidden');
    
    // Hide previous results
    const conflictsContainer = document.getElementById('aiConflictsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const recommendationsContainer = document.getElementById('aiRecommendationsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const explanationDiv = document.getElementById('aiExplanationExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const explanationWrapper = document.getElementById('aiExplanationWrapperExam' + (mode === 'add' ? 'Add' : 'Edit'));
    
    if (conflictsContainer) conflictsContainer.classList.add('hidden');
    if (recommendationsContainer) recommendationsContainer.classList.add('hidden');
    if (explanationDiv) explanationDiv.classList.add('hidden');
    if (explanationWrapper) explanationWrapper.classList.add('hidden');
    
    // Call AI API
    fetch('/exam-schedule/ai-check-conflicts', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            section_id: parseInt(sectionId),
            subject_id: subjectId ? parseInt(subjectId) : null,
            faculty_id: facultyId ? parseInt(facultyId) : null,
            room_id: roomId ? parseInt(roomId) : null,
            exam_date: examDate,
            start_time: startTime,
            end_time: endTime,
            exam_schedule_id: examScheduleId ? parseInt(examScheduleId) : null
        })
    })
    .then(response => {
        if (!response.ok) {
            return response.json().catch(() => {
                throw new Error(`Server error (${response.status}: ${response.statusText})`);
            }).then(errorData => {
                throw new Error(`Server error (${response.status}): ${errorData.error || response.statusText}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // Hide loading
        if (loadingDiv) loadingDiv.classList.add('hidden');
        if (!data.ai_enabled) {
            if (aiPanel) aiPanel.classList.add('hidden');
            showToast('AI features are not enabled', 'info');
            return;
        }
        
        // Handle schedule hours warning (non-blocking)
        if (data.schedule_hours_warning) {
            displayExamScheduleHoursWarning(mode, data.schedule_hours_warning);
        } else {
            displayExamScheduleHoursWarning(mode, null);
        }
        
        // Display conflicts
        if (data.has_conflicts && data.conflicts && data.conflicts.length > 0) {
            displayExamConflicts(data.conflicts, mode);
        } else {
            if (conflictsContainer) {
                conflictsContainer.classList.remove('hidden');
                conflictsContainer.innerHTML = `
                    <div class="flex items-center gap-2 py-2">
                        <span class="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0"></span>
                        <p class="text-xs font-medium text-gray-600">No conflicts detected — you can proceed.</p>
                    </div>
                `;
            }
        }
        
        // Display recommendations
        if (data.recommendations && data.recommendations.length > 0) {
            displayExamRecommendations(data.recommendations, mode);
        }
        
        // Display AI explanation
        if (data.ai_explanation) {
            displayExamAIExplanation(data.ai_explanation, mode);
        }
    })
    .catch(error => {
        console.error('[AI CHECK EXAM] Error:', error);
        console.error('[AI CHECK EXAM] Error details:', {
            message: error.message,
            stack: error.stack,
            type: error.constructor.name
        });
        if (loadingDiv) loadingDiv.classList.add('hidden');
        
        if (conflictsContainer) {
            conflictsContainer.classList.remove('hidden');
            conflictsContainer.innerHTML = `
                <div class="flex items-center gap-2 py-2">
                    <span class="w-2 h-2 rounded-full bg-red-400 flex-shrink-0"></span>
                    <p class="text-xs font-medium text-red-700 dark:text-red-300">Network error — ${error.message}</p>
                </div>
            `;
        }
    });
}

/**
 * Display exam conflicts in the UI - Enhanced design matching class modal
 * @param {Array} conflicts - Array of conflict objects
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamConflicts(conflicts, mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const conflictsContainer = document.getElementById('aiConflictsExam' + suffix);
    const conflictsList = document.getElementById('aiConflictsListExam' + suffix);
    const isDetailedMode = typeof isDetailedAssistantMode === 'function'
        ? isDetailedAssistantMode()
        : (typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : false);
    
    if (!conflictsList) return;
    
    // Clear list
    if (conflictsList) conflictsList.innerHTML = '';
    
    // Render conflicts with clearer hierarchy and cleaner spacing
    if (conflictsList) {
        conflicts.forEach((conflict, index) => {
            const severity = conflict.severity || 'high';
            const severityConfig = getExamSeverityConfig(severity);
            const details = conflict.details || {};
            const type = conflict.type || 'section';
            const icon = getExamConflictTypeIcon(type);
            const label = type.replace('_batch', ' (batch)').replace(/_/g, ' ');
            
            // Build detail fragments separated by ·
            const detailParts = [];
            if (details.subject) detailParts.push(details.subject);
            if (details.date) detailParts.push(details.date);
            if (details.time) detailParts.push(details.time);
            const detailTextClass = isDetailedMode
                ? 'text-[11px] text-gray-500 dark:text-gray-400 mt-1'
                : 'text-[10px] text-gray-500 dark:text-gray-400 mt-0.5';
            const detailHtml = detailParts.length > 0
                ? `<p class="${detailTextClass}">${detailParts.join(' · ')}</p>` : '';

            const messageClass = isDetailedMode
                ? `${severityConfig.messageClass} leading-normal`
                : 'text-gray-800 dark:text-gray-200 leading-snug';

            const metaHtml = isDetailedMode
                ? `
                    <div class="mb-0.5">
                        <span class="text-[10px] font-medium text-gray-500 dark:text-gray-400 capitalize tracking-wide">${examEscapeHtml(label)}</span>
                    </div>
                `
                : '';
            
            const conflictDiv = document.createElement('div');
            conflictDiv.className = isDetailedMode
                ? `p-3 rounded-xl ${severityConfig.cardClass} mb-2.5 last:mb-0 bg-white dark:bg-gray-900/35 shadow-sm`
                : 'p-2.5 rounded-lg border border-gray-200/90 dark:border-gray-700 mb-2 last:mb-0 bg-white dark:bg-gray-900/25';
            conflictDiv.innerHTML = `
                <div class="flex items-start gap-2.5">
                    <span class="mt-0.5 ${severityConfig.iconClass}">${icon}</span>
                    <div class="min-w-0 flex-1">
                        ${metaHtml}
                        <p class="text-xs font-semibold ${messageClass}">${conflict.message}</p>
                        ${detailHtml}
                    </div>
                </div>
            `;
            conflictsList.appendChild(conflictDiv);
        });
    }
    
    if (conflictsContainer) conflictsContainer.classList.remove('hidden');
}

/**
 * Get icon SVG based on exam conflict type
 */
function getExamConflictTypeIcon(type) {
    const icons = {
        section: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
        faculty: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
        proctor: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
        room: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>',
        duplicate: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>',
        time_invalid: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        proctor_unavailable: '<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>'
    };
    return icons[type] || icons.section;
}

/**
 * Get styling configuration based on exam conflict severity
 */
function getExamSeverityConfig(severity) {
    const configs = {
        critical: {
            messageClass: 'text-red-700 dark:text-red-300',
            iconClass: 'text-red-500 dark:text-red-400',
            cardClass: 'bg-red-50/90 dark:bg-red-900/20 border border-red-200 dark:border-red-900/50',
            badgeClass: 'text-[9px] font-semibold bg-red-100 dark:bg-red-900/40 text-red-700 dark:text-red-300'
        },
        high: {
            messageClass: 'text-orange-700 dark:text-orange-300',
            iconClass: 'text-orange-500 dark:text-orange-400',
            cardClass: 'bg-orange-50/90 dark:bg-orange-900/20 border border-orange-200 dark:border-orange-900/50',
            badgeClass: 'text-[9px] font-semibold bg-orange-100 dark:bg-orange-900/40 text-orange-700 dark:text-orange-300'
        },
        medium: {
            messageClass: 'text-amber-700 dark:text-amber-300',
            iconClass: 'text-amber-500 dark:text-amber-400',
            cardClass: 'bg-amber-50/90 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-900/50',
            badgeClass: 'text-[9px] font-semibold bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300'
        },
        low: {
            messageClass: 'text-blue-700 dark:text-blue-300',
            iconClass: 'text-blue-500 dark:text-blue-400',
            cardClass: 'bg-blue-50/90 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-900/50',
            badgeClass: 'text-[9px] font-semibold bg-blue-100 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300'
        }
    };
    return configs[severity] || configs.high;
}

/**
 * Display AI recommendations for exam scheduling - Enhanced design matching class modal
 * @param {Array} recommendations - Array of recommendation objects
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamRecommendations(recommendations, mode, readOnly) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const recommendationsContainer = document.getElementById('aiRecommendationsExam' + suffix);
    const recommendationsList = document.getElementById('aiRecommendationsListExam' + suffix);
    const basicHint = document.getElementById('aiBasicModeHintExam' + suffix);
    const recsHeader = document.getElementById('aiRecommendationsHeaderExam' + suffix);
    const isDetailedMode = typeof isDetailedAssistantMode === 'function'
        ? isDetailedAssistantMode()
        : (typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : false);
    
    if (!recommendationsList) return;
    
    // Clear list
    if (recommendationsList) recommendationsList.innerHTML = '';
    
    if (recommendations.length === 0) {
        if (recommendationsContainer) recommendationsContainer.classList.add('hidden');
        return;
    }
    
    // Lightweight type config: thin border + emoji label
    const typeConfig = {
        time: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-emerald-50/70 dark:hover:bg-emerald-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Available Time Slots'
        },
        time_slot: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-emerald-50/70 dark:hover:bg-emerald-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Available Time Slots'
        },
        date: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-indigo-50/70 dark:hover:bg-indigo-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Alternative Dates'
        },
        room: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-amber-50/70 dark:hover:bg-amber-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-amber-300 dark:hover:border-amber-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Available Rooms'
        },
        faculty: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-green-50/70 dark:hover:bg-green-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-green-300 dark:hover:border-green-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Available Proctors'
        }
    };
    
    // Generate unique IDs for collapsible sections
    const sectionId = `exam_rec_${mode}_${Date.now()}`;
    
    recommendations.forEach((rec, recIndex) => {
        // Skip recommendations with no options
        if (!rec.options || rec.options.length === 0) {
            return;
        }
        
        const config = typeConfig[rec.type] || typeConfig.room;
        const uniqueId = `${sectionId}_${recIndex}`;
        const isExpanded = recIndex === 0; // First section expanded by default
        const maxVisibleOptions = 3; // Show first 3 options, rest in "show more"
        const cardClass = isDetailedMode
            ? `bg-white dark:bg-gray-900/35 border ${config.border} rounded-xl overflow-hidden mb-2.5 last:mb-0 shadow-sm`
            : `bg-white dark:bg-gray-900/25 border ${config.border} rounded-lg overflow-hidden mb-2 last:mb-0`;
        const sectionButtonClass = isDetailedMode
            ? 'w-full px-3.5 py-3 flex items-center justify-between hover:bg-purple-50/40 dark:hover:bg-purple-900/15 transition-colors'
            : 'w-full px-3 py-2.5 flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-800/60 transition-colors';
        const sectionBodyClass = isDetailedMode ? 'px-3.5 pb-3.5' : 'px-3 pb-3';
        const showMoreClass = isDetailedMode
            ? `mt-2 text-xs ${config.btnText} hover:underline flex items-center gap-1 mx-auto`
            : 'mt-1.5 text-[11px] text-gray-500 dark:text-gray-400 hover:underline flex items-center gap-1 mx-auto';
        
        // Desktop version - Enhanced collapsible cards with quick actions
        if (recommendationsList) {
            const recDiv = document.createElement('div');
            recDiv.className = cardClass;
            
            // Generate options HTML with improved design
            const generateOptionsHTML = (options, type) => {
                const visibleOptions = options.slice(0, maxVisibleOptions);
                const hiddenOptions = options.slice(maxVisibleOptions);
                
                let html = '<div class="grid grid-cols-1 gap-1.5">';
                
                visibleOptions.forEach((opt, idx) => {
                    html += generateExamOptionButton(opt, idx, type, config, mode, false, isDetailedMode);
                });
                
                html += '</div>';
                
                // Add "show more" section if there are hidden options
                if (hiddenOptions.length > 0) {
                    html += `
                        <div id="moreExamOptions_${uniqueId}" class="hidden mt-2">
                            <div class="grid grid-cols-1 gap-1.5">
                                ${hiddenOptions.map((opt, idx) => generateExamOptionButton(opt, idx + maxVisibleOptions, type, config, mode, false, isDetailedMode)).join('')}
                            </div>
                        </div>
                        <button type="button" onclick="toggleExamMoreOptions('${uniqueId}', this)" data-more-count="${hiddenOptions.length}"
                                class="${showMoreClass}">
                            <span class="toggle-text">Show ${hiddenOptions.length} more</span>
                            <svg class="w-3 h-3 transition-transform toggle-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                            </svg>
                        </button>
                    `;
                }
                
                return html;
            };
            
            recDiv.innerHTML = `
                <button type="button" onclick="toggleExamRecommendationSection('${uniqueId}')" 
                        class="${sectionButtonClass}">
                    <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">${config.label}</span>
                    <div class="flex items-center gap-1.5">
                        <span class="text-[10px] font-semibold ${config.badgeBg} ${config.badgeText} px-1.5 py-0.5 rounded-full">${rec.options.length}</span>
                        <svg id="examChevron_${uniqueId}" class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </div>
                </button>
                <div id="examContent_${uniqueId}" class="${sectionBodyClass} ${isExpanded ? '' : 'hidden'}">
                    ${generateOptionsHTML(rec.options, rec.type)}
                </div>
            `;
            
            recommendationsList.appendChild(recDiv);
        }
    });
    
    if (recommendationsContainer) recommendationsContainer.classList.remove('hidden');

    if (basicHint) {
        basicHint.classList.toggle('hidden', isDetailedMode);
    }

    if (recsHeader) {
        const subtitle = recsHeader.querySelector('p');
        if (subtitle) {
            subtitle.textContent = isDetailedMode
                ? 'Apply actions with richer context and supporting rationale.'
                : 'Apply actions directly with concise guidance.';
        }
    }
}

/**
 * Get confidence badge class based on score
 */
function getExamConfidenceBadgeClass(confidence) {
    if (confidence >= 80) return 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300';
    if (confidence >= 60) return 'bg-blue-100 text-blue-700 ring-1 ring-blue-300';
    if (confidence >= 40) return 'bg-amber-100 text-amber-700 ring-1 ring-amber-300';
    return 'bg-red-100 text-red-700 ring-1 ring-red-300';
}

/**
 * Generate exam option button HTML based on type
 */
function generateExamOptionButton(opt, idx, type, config, mode, readOnly, detailedMode = false) {
    const baseClasses = detailedMode
        ? `group flex items-start gap-2.5 px-3 py-2.5 text-xs ${config.btnBg} border ${config.btnBorder} rounded-lg transition-all cursor-pointer`
        : `group flex items-center gap-2 px-2.5 py-1.5 text-[11px] ${config.btnBg} border ${config.btnBorder} rounded-md transition-all cursor-pointer`;
    const labelClasses = detailedMode ? `font-semibold ${config.btnText}` : `font-medium ${config.btnText}`;
    const reasonHtml = opt.reason
        ? (detailedMode
            ? `<span class="block text-[10px] text-gray-500 dark:text-gray-400 mt-0.5">${opt.reason}</span>`
            : `<span class="text-[10px] text-gray-500 dark:text-gray-400 truncate"> · ${opt.reason}</span>`)
        : '';
    const buildTextContent = (text) => detailedMode
        ? `<span class="min-w-0 flex-1"><span class="${labelClasses}">${text}</span>${reasonHtml}</span>`
        : `<span class="${labelClasses}">${text}</span>${reasonHtml}`;
    
    // Handle both 'time' and 'time_slot' types (backend uses 'time_slot')
    if (type === 'time' || type === 'time_slot') {
        return `<button type="button" onclick="applyExamTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" class="${baseClasses}">
            ${buildTextContent(opt.display)}
        </button>`;
    } else if (type === 'date') {
        return `<button type="button" onclick="applyExamDate('${opt.exam_date}', '${mode}', '${opt.display}')" class="${baseClasses}">
            ${buildTextContent(opt.display)}
        </button>`;
    } else if (type === 'room') {
        return `<button type="button" onclick="applyExamRoom(${opt.room_id}, '${mode}', '${opt.display.replace(/'/g, "\\'")}')" class="${baseClasses} text-left">
            ${buildTextContent(opt.display)}
        </button>`;
    } else if (type === 'faculty') {
        return `<button type="button" onclick="applyExamFaculty(${opt.faculty_id}, '${mode}', '${opt.display.replace(/'/g, "\\'")}')" class="${baseClasses} text-left">
            ${buildTextContent(opt.display)}
        </button>`;
    }
    return '';
}

/**
 * Toggle exam recommendation section visibility
 */
function toggleExamRecommendationSection(id) {
    const content = document.getElementById('examContent_' + id);
    const chevron = document.getElementById('examChevron_' + id);
    
    if (content && chevron) {
        content.classList.toggle('hidden');
        chevron.classList.toggle('rotate-180');
    }
}

/**
 * Toggle exam more options visibility
 */
function toggleExamMoreOptions(id, btn) {
    const moreOptions = document.getElementById('moreExamOptions_' + id);
    if (moreOptions && btn) {
        moreOptions.classList.toggle('hidden');
        const textSpan = btn.querySelector('.toggle-text');
        const icon = btn.querySelector('.toggle-icon');
        const moreCount = btn.dataset.moreCount || moreOptions.querySelectorAll('button').length;
        
        if (moreOptions.classList.contains('hidden')) {
            textSpan.textContent = `Show ${moreCount} more`;
            icon.classList.remove('rotate-180');
        } else {
            textSpan.textContent = 'Show less';
            icon.classList.add('rotate-180');
        }
    }
}

/**
 * Display AI explanation
 * @param {string} explanation - AI-generated explanation text
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamAIExplanation(explanation, mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const explanationDiv = document.getElementById('aiExplanationExam' + suffix);
    const explanationWrapper = document.getElementById('aiExplanationWrapperExam' + suffix);
    const isDetailedMode = typeof isDetailedAssistantMode === 'function'
        ? isDetailedAssistantMode()
        : (typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : false);
    const heading = isDetailedMode ? 'Detailed Analysis' : 'Quick Check';
    const bodyClass = isDetailedMode
        ? 'text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line'
        : 'text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-line';

    if (explanationWrapper) {
        explanationWrapper.className = isDetailedMode
            ? 'mb-3 rounded-xl border border-purple-300/90 dark:border-purple-700 bg-gradient-to-br from-purple-50/90 to-indigo-50/70 dark:from-purple-900/25 dark:to-indigo-900/20 px-3.5 py-3 shadow-sm'
            : 'mb-2.5 rounded-lg border border-gray-200/90 dark:border-gray-700 bg-white dark:bg-gray-900/25 px-3 py-2';
        explanationWrapper.innerHTML = `
            <p class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">${heading}</p>
            <div id="aiExplanationExam${suffix}" class="${bodyClass}">${explanation}</div>
        `;
        explanationWrapper.classList.remove('hidden');
        return;
    }
    
    if (explanationDiv) {
        explanationDiv.innerHTML = `
            <p class="text-[10px] font-semibold text-gray-400 uppercase tracking-wider mb-1">${heading}</p>
            <p class="${bodyClass}">${explanation}</p>
        `;
        explanationDiv.classList.remove('hidden');
    }
}

// ============================================================================
// Apply AI Recommendations for Exam Schedules
// ============================================================================

// Helper function for visual feedback when applying AI suggestions
function highlightExamField(elementId, duration = 2000) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // Add highlight classes
    element.classList.add('ring-2', 'ring-green-500', 'ring-offset-1', 'bg-green-50');
    element.style.transition = 'all 0.3s ease';
    
    // Remove highlight after duration
    setTimeout(() => {
        element.classList.remove('ring-2', 'ring-green-500', 'ring-offset-1', 'bg-green-50');
    }, duration);
}

function applyExamTimeSlot(startTime, endTime, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const startField = document.getElementById('start_time_exam' + suffix);
    const endField = document.getElementById('end_time_exam' + suffix);
    
    if (startField) startField.value = startTime;
    if (endField) endField.value = endTime;
    
    // Visual feedback
    highlightExamField('start_time_exam' + suffix);
    highlightExamField('end_time_exam' + suffix);
    
    // Format display time for toast
    const formatTime = (t) => {
        const [h, m] = t.split(':');
        const hour = parseInt(h);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const hour12 = hour % 12 || 12;
        return `${hour12}:${m} ${ampm}`;
    };
    showToast(`Time applied: ${formatTime(startTime)} - ${formatTime(endTime)}`, 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamDate(examDate, mode, displayText = '') {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const dateField = document.getElementById('exam_date' + suffix);
    
    if (dateField) dateField.value = examDate;
    
    // Visual feedback
    highlightExamField('exam_date' + suffix);
    
    showToast(`Date applied: ${displayText || examDate}`, 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamRoom(roomId, mode, displayText = '') {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const hiddenInput = document.getElementById('room_id_exam' + suffix);
    const searchInput = document.getElementById('room_search_exam' + suffix);
    
    // Update hidden input value
    if (hiddenInput) hiddenInput.value = roomId;
    
    // Update visible search input with display text
    if (searchInput && displayText) {
        searchInput.value = displayText;
    }
    
    // Visual feedback
    highlightExamField('room_search_exam' + suffix);
    
    showToast(`Room applied: ${displayText || 'Selected'}`, 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamFaculty(facultyId, mode, displayText = '') {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const suffixCap = mode === 'add' ? 'Add' : 'Edit';
    const hiddenSelect = document.getElementById('faculty_id_exam' + suffix);
    const facultyTrigger = document.getElementById('facultyTriggerExam' + suffixCap);
    const facultyDisplay = document.getElementById('facultyDisplayExam' + suffixCap);
    
    // Update hidden select value
    if (hiddenSelect) hiddenSelect.value = facultyId;
    
    // Update visible faculty display
    if (facultyDisplay && displayText) {
        const nameParts = displayText.split(' ');
        const initials = nameParts.length >= 2 
            ? (nameParts[0][0] + nameParts[nameParts.length - 1][0]).toUpperCase()
            : displayText.substring(0, 2).toUpperCase();
        
        facultyDisplay.innerHTML = `
            <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-full bg-green-100 flex items-center justify-center flex-shrink-0">
                <span class="text-green-700 text-xs font-bold">${initials}</span>
            </div>
            <div class="flex-1 min-w-0">
                <div class="text-sm font-medium text-gray-900 truncate">${displayText}</div>
                <div class="text-xs text-gray-500">Applied from assistant suggestion</div>
            </div>
        `;
    }
    
    // Visual feedback
    highlightExamField('facultyTriggerExam' + suffixCap);
    
    showToast(`Faculty applied: ${displayText || 'Selected'}`, 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
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
