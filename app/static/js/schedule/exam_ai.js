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
    console.log('[AI CHECK EXAM] Element check:', {
        sectionId: sectionIdEl ? 'FOUND' : 'MISSING',
        subjectId: subjectIdEl ? 'FOUND' : 'MISSING',
        facultyId: facultyIdEl ? 'FOUND' : 'MISSING',
        roomId: roomIdEl ? 'FOUND' : 'MISSING',
        examDate: examDateEl ? 'FOUND' : 'MISSING',
        startTime: startTimeEl ? 'FOUND' : 'MISSING',
        endTime: endTimeEl ? 'FOUND' : 'MISSING'
    });
    
    const sectionId = sectionIdEl?.value;
    const subjectId = subjectIdEl?.value || null;
    const facultyId = facultyIdEl?.value || null;
    const roomId = roomIdEl?.value || null;
    const examDate = examDateEl?.value;
    const startTime = startTimeEl?.value;
    const endTime = endTimeEl?.value;
    const examScheduleId = mode === 'edit' ? document.getElementById('exam_schedule_id_edit')?.value : null;
    
    // Debug logging
    console.log('[AI CHECK EXAM] Form data:', {
        sectionId, subjectId, facultyId, roomId, 
        examDate, startTime, endTime, examScheduleId
    });
    
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
    const aiPanelMobile = document.getElementById('aiAssistantExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    const loadingDiv = document.getElementById('aiLoadingExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const loadingDivMobile = document.getElementById('aiLoadingExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    
    if (aiPanel) aiPanel.classList.remove('hidden');
    if (aiPanelMobile) aiPanelMobile.classList.remove('hidden');
    if (loadingDiv) loadingDiv.classList.remove('hidden');
    if (loadingDivMobile) loadingDivMobile.classList.remove('hidden');
    
    // Hide previous results
    const conflictsContainer = document.getElementById('aiConflictsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const conflictsContainerMobile = document.getElementById('aiConflictsExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    const recommendationsContainer = document.getElementById('aiRecommendationsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const recommendationsContainerMobile = document.getElementById('aiRecommendationsExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    const explanationDiv = document.getElementById('aiExplanationExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const explanationDivMobile = document.getElementById('aiExplanationExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    
    if (conflictsContainer) conflictsContainer.classList.add('hidden');
    if (conflictsContainerMobile) conflictsContainerMobile.classList.add('hidden');
    if (recommendationsContainer) recommendationsContainer.classList.add('hidden');
    if (recommendationsContainerMobile) recommendationsContainerMobile.classList.add('hidden');
    if (explanationDiv) explanationDiv.classList.add('hidden');
    if (explanationDivMobile) explanationDivMobile.classList.add('hidden');
    
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
        console.log('[AI CHECK EXAM] Response status:', response.status, response.statusText);
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
        if (loadingDivMobile) loadingDivMobile.classList.add('hidden');
        
        console.log('[AI CHECK EXAM] Response:', data);
        
        if (!data.ai_enabled) {
            if (aiPanel) aiPanel.classList.add('hidden');
            if (aiPanelMobile) aiPanelMobile.classList.add('hidden');
            showToast('AI features are not enabled', 'info');
            return;
        }
        
        // Display conflicts
        if (data.has_conflicts && data.conflicts && data.conflicts.length > 0) {
            displayExamConflicts(data.conflicts, mode);
        } else {
            if (conflictsContainer) {
                conflictsContainer.classList.remove('hidden');
                conflictsContainer.innerHTML = `
                    <div class="p-4 bg-green-50 border border-green-200 rounded-lg">
                        <div class="flex items-start">
                            <svg class="w-5 h-5 text-green-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            <div>
                                <h5 class="text-sm font-semibold text-green-800">No Conflicts Detected</h5>
                                <p class="text-xs text-green-700 mt-1">This exam schedule looks good! You can proceed with scheduling.</p>
                            </div>
                        </div>
                    </div>
                `;
            }
            
            if (conflictsContainerMobile) {
                conflictsContainerMobile.classList.remove('hidden');
                conflictsContainerMobile.innerHTML = `
                    <div class="p-3 bg-green-50 border border-green-200 rounded-lg">
                        <div class="flex items-start">
                            <svg class="w-4 h-4 text-green-600 mr-2 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                            <div>
                                <h5 class="text-[10px] font-semibold text-green-800">No Conflicts</h5>
                                <p class="text-[9px] text-green-700 mt-0.5">Exam schedule is clear!</p>
                            </div>
                        </div>
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
        if (loadingDivMobile) loadingDivMobile.classList.add('hidden');
        
        if (conflictsContainer) {
            conflictsContainer.classList.remove('hidden');
            conflictsContainer.innerHTML = `
                <div class="p-4 bg-red-50 border border-red-200 rounded-lg">
                    <div class="flex items-start">
                        <svg class="w-5 h-5 text-red-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <div>
                            <h5 class="text-sm font-semibold text-red-800">❌ Network error - Please check your connection</h5>
                            <p class="text-xs text-red-700 mt-1">${error.message}</p>
                        </div>
                    </div>
                </div>
            `;
        }
    });
}

/**
 * Display exam conflicts in the UI
 * @param {Array} conflicts - Array of conflict objects
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamConflicts(conflicts, mode) {
    const conflictsContainer = document.getElementById('aiConflictsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const conflictsContainerMobile = document.getElementById('aiConflictsExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    
    if (!conflictsContainer && !conflictsContainerMobile) return;
    
    // Clear containers
    if (conflictsContainer) conflictsContainer.innerHTML = '';
    if (conflictsContainerMobile) conflictsContainerMobile.innerHTML = '';
    
    conflicts.forEach(conflict => {
        // Desktop version - use createElement for proper Tailwind classes
        if (conflictsContainer) {
            const conflictDiv = document.createElement('div');
            conflictDiv.className = 'p-2 bg-red-50 border border-red-200 rounded-lg text-sm';
            conflictDiv.innerHTML = `
                <div class="flex items-start space-x-2">
                    <span class="text-red-600 font-semibold">${conflict.type.toUpperCase()}:</span>
                    <div class="flex-1">
                        <p class="text-red-800">${conflict.message}</p>
                        ${conflict.details ? `
                            <p class="text-red-600 text-xs mt-1">
                                ${conflict.details.subject || ''} • ${conflict.details.date || ''} ${conflict.details.time || ''}
                            </p>
                        ` : ''}
                    </div>
                </div>
            `;
            conflictsContainer.appendChild(conflictDiv);
        }
        
        // Mobile version (more compact)
        if (conflictsContainerMobile) {
            const conflictDivMobile = document.createElement('div');
            conflictDivMobile.className = 'p-2 bg-red-50 border border-red-200 rounded-lg';
            conflictDivMobile.innerHTML = `
                <div class="flex items-start space-x-1.5">
                    <span class="text-red-600 font-semibold text-[10px]">${conflict.type.toUpperCase()}:</span>
                    <div class="flex-1">
                        <p class="text-red-800 text-[10px]">${conflict.message}</p>
                        ${conflict.details ? `
                            <p class="text-red-600 text-[9px] mt-0.5">
                                ${conflict.details.subject || ''} • ${conflict.details.date || ''} ${conflict.details.time || ''}
                            </p>
                        ` : ''}
                    </div>
                </div>
            `;
            conflictsContainerMobile.appendChild(conflictDivMobile);
        }
    });
    
    if (conflictsContainer) conflictsContainer.classList.remove('hidden');
    if (conflictsContainerMobile) conflictsContainerMobile.classList.remove('hidden');
}

/**
 * Display AI recommendations for exam scheduling
 * @param {Array} recommendations - Array of recommendation objects
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamRecommendations(recommendations, mode) {
    const recommendationsContainer = document.getElementById('aiRecommendationsExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const recommendationsContainerMobile = document.getElementById('aiRecommendationsExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    
    if (!recommendationsContainer && !recommendationsContainerMobile) return;
    
    const recommendationsList = document.createElement('div');
    recommendationsList.className = 'space-y-3';
    
    const recommendationsListMobile = document.createElement('div');
    recommendationsListMobile.className = 'space-y-2';
    
    recommendations.forEach(rec => {
        // Desktop version
        if (recommendationsContainer) {
            const recDiv = document.createElement('div');
            recDiv.className = 'p-3 bg-blue-50 border border-blue-200 rounded-lg';
            
            let optionsHTML = '';
            
            if (rec.type === 'time') {
                optionsHTML = rec.options.map(opt => 
                    `<button type="button" onclick="applyExamTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" 
                            class="px-3 py-1 text-sm bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'date') {
                optionsHTML = rec.options.map(opt => 
                    `<button type="button" onclick="applyExamDate('${opt.exam_date}', '${mode}')" 
                            class="px-3 py-1 text-sm bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'room') {
                optionsHTML = rec.options.map(opt => 
                    `<button type="button" onclick="applyExamRoom('${opt.room_id}', '${mode}')" 
                            class="px-3 py-1 text-sm bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'faculty') {
                optionsHTML = rec.options.map(opt => 
                    `<button type="button" onclick="applyExamFaculty('${opt.faculty_id}', '${mode}')" 
                            class="px-3 py-1 text-sm bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            }
            
            recDiv.innerHTML = `
                <h6 class="text-sm font-semibold text-blue-800 mb-2">${rec.message}</h6>
                <div class="flex flex-wrap gap-2">
                    ${optionsHTML}
                </div>
            `;
            
            recommendationsList.appendChild(recDiv);
        }
        
        // Mobile version
        if (recommendationsContainerMobile) {
            const recDivMobile = document.createElement('div');
            recDivMobile.className = 'p-2 bg-blue-50 border border-blue-200 rounded-lg';
            
            let optionsHTMLMobile = '';
            
            if (rec.type === 'time') {
                optionsHTMLMobile = rec.options.slice(0, 2).map(opt => 
                    `<button type="button" onclick="applyExamTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" 
                            class="px-2 py-1 text-[10px] bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'date') {
                optionsHTMLMobile = rec.options.slice(0, 2).map(opt => 
                    `<button type="button" onclick="applyExamDate('${opt.exam_date}', '${mode}')" 
                            class="px-2 py-1 text-[10px] bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'room') {
                optionsHTMLMobile = rec.options.slice(0, 2).map(opt => 
                    `<button type="button" onclick="applyExamRoom('${opt.room_id}', '${mode}')" 
                            class="px-2 py-1 text-[10px] bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            } else if (rec.type === 'faculty') {
                optionsHTMLMobile = rec.options.slice(0, 2).map(opt => 
                    `<button type="button" onclick="applyExamFaculty('${opt.faculty_id}', '${mode}')" 
                            class="px-2 py-1 text-[10px] bg-white border border-blue-300 rounded hover:bg-blue-100 transition-colors">
                        ${opt.display}
                    </button>`
                ).join('');
            }
            
            recDivMobile.innerHTML = `
                <h6 class="text-[10px] font-semibold text-blue-800 mb-1.5">${rec.message}</h6>
                <div class="flex flex-wrap gap-1.5">
                    ${optionsHTMLMobile}
                </div>
            `;
            
            recommendationsListMobile.appendChild(recDivMobile);
        }
    });
    
    if (recommendationsContainer) {
        recommendationsContainer.innerHTML = '';
        recommendationsContainer.appendChild(recommendationsList);
        recommendationsContainer.classList.remove('hidden');
    }
    
    if (recommendationsContainerMobile) {
        recommendationsContainerMobile.innerHTML = '';
        recommendationsContainerMobile.appendChild(recommendationsListMobile);
        recommendationsContainerMobile.classList.remove('hidden');
    }
}

/**
 * Display AI explanation
 * @param {string} explanation - AI-generated explanation text
 * @param {string} mode - 'add' or 'edit'
 */
function displayExamAIExplanation(explanation, mode) {
    const explanationDiv = document.getElementById('aiExplanationExam' + (mode === 'add' ? 'Add' : 'Edit'));
    const explanationDivMobile = document.getElementById('aiExplanationExam' + (mode === 'add' ? 'Add' : 'Edit') + 'Mobile');
    
    if (explanationDiv) {
        explanationDiv.innerHTML = `
            <div class="p-4 bg-purple-50 border border-purple-200 rounded-lg">
                <div class="flex items-start">
                    <svg class="w-5 h-5 text-purple-600 mr-3 flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                    </svg>
                    <div>
                        <h5 class="text-sm font-semibold text-purple-800">AI Analysis</h5>
                        <p class="text-xs text-purple-700 mt-1 whitespace-pre-wrap">${explanation}</p>
                    </div>
                </div>
            </div>
        `;
        explanationDiv.classList.remove('hidden');
    }
    
    if (explanationDivMobile) {
        explanationDivMobile.innerHTML = `
            <div class="p-3 bg-purple-50 border border-purple-200 rounded-lg">
                <h5 class="text-[10px] font-semibold text-purple-800 mb-1">AI Analysis</h5>
                <p class="text-[9px] text-purple-700 whitespace-pre-wrap">${explanation}</p>
            </div>
        `;
        explanationDivMobile.classList.remove('hidden');
    }
}

// ============================================================================
// Apply AI Recommendations for Exam Schedules
// ============================================================================

function applyExamTimeSlot(startTime, endTime, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    document.getElementById('start_time_exam' + suffix).value = startTime;
    document.getElementById('end_time_exam' + suffix).value = endTime;
    showToast('Time slot applied! Auto-rechecking conflicts...', 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamDate(examDate, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    document.getElementById('exam_date' + suffix).value = examDate;
    showToast('Exam date applied! Auto-rechecking conflicts...', 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamRoom(roomId, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    document.getElementById('room_id_exam' + suffix).value = roomId;
    showToast('Room applied! Auto-rechecking conflicts...', 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}

function applyExamFaculty(facultyId, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    document.getElementById('faculty_id_exam' + suffix).value = facultyId;
    showToast('Faculty applied! Auto-rechecking conflicts...', 'success');
    
    // Trigger auto-recheck
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        scheduleAutoExamConflictCheck(mode);
    }
}
