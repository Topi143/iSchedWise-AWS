/**
 * Curriculum Selector Module for Schedule Management
 * Handles curriculum selection and subject loading based on selected curriculum
 */

// Make functions available globally
window.loadCurriculaForSection = loadCurriculaForSection;
window.loadSubjectsForCurriculum = loadSubjectsForCurriculum;
window.loadCurriculaForEdit = loadCurriculaForEdit;
window.loadSubjectsForEditWithCurriculum = loadSubjectsForEditWithCurriculum;

/**
 * Load curricula for a section
 * @param {number} sectionId - The section ID
 * @param {string} mode - Either 'add', 'edit', 'exam_add', or 'exam_edit'
 */
function loadCurriculaForSection(sectionId, mode = 'add') {
    const curriculumSelect = document.getElementById(`curriculum_id_${mode}`);
    const subjectSelect = document.getElementById(`subject_id_${mode}`);
    
    // Show loading state
    curriculumSelect.innerHTML = '<option value="">Loading curricula...</option>';
    curriculumSelect.disabled = true;
    subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
    subjectSelect.disabled = true;
    
    // Fetch curricula for this section
    fetch(`/schedule/get-curricula/${sectionId}`)
        .then(response => response.json())
        .then(data => {
            curriculumSelect.innerHTML = '<option value="">Select a curriculum...</option>';
            
            if (data.curricula && data.curricula.length > 0) {
                data.curricula.forEach(curriculum => {
                    const option = document.createElement('option');
                    option.value = curriculum.id;
                    option.textContent = curriculum.display;
                    curriculumSelect.appendChild(option);
                });
                
                // Auto-select if only one curriculum
                if (data.curricula.length === 1) {
                    curriculumSelect.value = data.curricula[0].id;
                    loadSubjectsForCurriculum(mode);
                }
            } else {
                curriculumSelect.innerHTML = '<option value="">No curricula available</option>';
            }
            
            curriculumSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading curricula:', error);
            curriculumSelect.innerHTML = '<option value="">Error loading curricula</option>';
            curriculumSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Error loading curricula. Please try again.', 'error');
            }
        });
}

/**
 * Load subjects based on selected curriculum
 * @param {string} mode - Either 'add', 'edit', 'exam_add', or 'exam_edit'
 */
function loadSubjectsForCurriculum(mode = 'add') {
    const curriculumId = document.getElementById(`curriculum_id_${mode}`).value;
    const sectionId = document.getElementById(`section_id_${mode}`).value;
    const subjectSelect = document.getElementById(`subject_id_${mode}`);
    
    if (!curriculumId) {
        subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
        subjectSelect.disabled = true;
        return;
    }
    
    // Show loading state
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // Fetch subjects for this curriculum
    fetch(`/schedule/get-subjects/${sectionId}?curriculum_id=${curriculumId}`)
        .then(response => response.json())
        .then(data => {
            subjectSelect.innerHTML = '<option value="">Select a subject...</option>';
            
            if (data.subjects && data.subjects.length > 0) {
                data.subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.id;
                    option.textContent = subject.display;
                    
                    // Add data attributes for smart scheduling (only for class schedules, not exam)
                    if (!mode.startsWith('exam_')) {
                        option.dataset.code = subject.subject_code;
                        option.dataset.description = subject.course_description;
                        option.dataset.lecUnits = subject.lec_units;
                        option.dataset.labUnits = subject.lab_units;
                        option.dataset.totalUnits = subject.total_units;
                    }
                    
                    subjectSelect.appendChild(option);
                });
            } else {
                subjectSelect.innerHTML = '<option value="">No subjects available for this curriculum</option>';
            }
            
            subjectSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading subjects:', error);
            subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
            subjectSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Error loading subjects. Please try again.', 'error');
            }
        });
}

/**
 * Load curricula for edit modal with schedule data
 * @param {number} sectionId - The section ID
 * @param {object} scheduleData - The schedule data object
 * @param {string} mode - Either 'edit' or 'exam_edit' (default: 'edit')
 */
function loadCurriculaForEdit(sectionId, scheduleData, mode = 'edit') {
    console.log('[LOAD CURRICULA] Starting for section:', sectionId, 'mode:', mode, 'scheduleData:', scheduleData);
    
    const curriculumSelect = document.getElementById(`curriculum_id_${mode}`);
    const subjectSelect = document.getElementById(`subject_id_${mode}`);
    
    if (!curriculumSelect) {
        console.error('[LOAD CURRICULA] Curriculum select not found! ID:', `curriculum_id_${mode}`);
        return;
    }
    
    if (!subjectSelect) {
        console.error('[LOAD CURRICULA] Subject select not found! ID:', `subject_id_${mode}`);
        return;
    }
    
    // Show loading state
    curriculumSelect.innerHTML = '<option value="">Loading curricula...</option>';
    curriculumSelect.disabled = true;
    subjectSelect.innerHTML = '<option value="">Loading...</option>';
    subjectSelect.disabled = true;
    
    // Fetch curricula for this section
    fetch(`/schedule/get-curricula/${sectionId}`)
        .then(response => response.json())
        .then(data => {
            curriculumSelect.innerHTML = '<option value="">Select a curriculum...</option>';
            
            if (data.curricula && data.curricula.length > 0) {
                data.curricula.forEach(curriculum => {
                    const option = document.createElement('option');
                    option.value = curriculum.id;
                    option.textContent = curriculum.display;
                    curriculumSelect.appendChild(option);
                });
                
                // Try to detect which curriculum contains the subject by trying each one
                detectAndSelectCurriculum(sectionId, scheduleData, data.curricula, mode);
            } else {
                curriculumSelect.innerHTML = '<option value="">No curricula available</option>';
                subjectSelect.innerHTML = '<option value="">No subjects available</option>';
            }
            
            curriculumSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading curricula:', error);
            curriculumSelect.innerHTML = '<option value="">Error loading curricula</option>';
            curriculumSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Error loading curricula. Please try again.', 'error');
            }
        });
}

/**
 * Detect which curriculum contains the subject and pre-select it
 * @param {number} sectionId - The section ID
 * @param {object} scheduleData - The schedule data object
 * @param {array} curricula - Array of available curricula
 * @param {string} mode - Either 'edit' or 'exam_edit'
 */
function detectAndSelectCurriculum(sectionId, scheduleData, curricula, mode) {
    const curriculumSelect = document.getElementById(`curriculum_id_${mode}`);
    
    console.log('[DETECT] Detecting curriculum for subject:', scheduleData.subject_id, 'from', curricula.length, 'curricula');
    
    // If only one curriculum, select it
    if (curricula.length === 1) {
        console.log('[DETECT] Only one curriculum, selecting:', curricula[0].id);
        curriculumSelect.value = curricula[0].id;
        loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
        return;
    }
    
    // Try each curriculum to find which one has the subject
    let foundCurriculum = false;
    let attemptCount = 0;
    
    curricula.forEach(curriculum => {
        fetch(`/schedule/get-subjects/${sectionId}?curriculum_id=${curriculum.id}`)
            .then(response => response.json())
            .then(data => {
                attemptCount++;
                
                // Check if this curriculum contains the subject
                if (!foundCurriculum && data.subjects && data.subjects.length > 0) {
                    const hasSubject = data.subjects.some(subject => subject.id === scheduleData.subject_id);
                    
                    if (hasSubject) {
                        foundCurriculum = true;
                        console.log('[DETECT] Found curriculum:', curriculum.id, 'contains subject:', scheduleData.subject_id);
                        curriculumSelect.value = curriculum.id;
                        loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
                    }
                }
                
                // If we've tried all curricula and haven't found it, default to first
                if (attemptCount === curricula.length && !foundCurriculum) {
                    console.log('[DETECT] Subject not found in any curriculum, defaulting to first');
                    curriculumSelect.value = curricula[0].id;
                    loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
                }
            })
            .catch(error => {
                console.error('[DETECT] Error detecting curriculum:', error);
                attemptCount++;
                
                // If all attempts failed, default to first curriculum
                if (attemptCount === curricula.length && !foundCurriculum) {
                    console.log('[DETECT] All detection attempts failed, defaulting to first');
                    curriculumSelect.value = curricula[0].id;
                    loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
                }
            });
    });
}

/**
 * Load subjects for edit modal with curriculum selection
 * @param {number} sectionId - The section ID
 * @param {object} scheduleData - The schedule data object
 * @param {string} mode - Either 'edit' or 'exam_edit' (default: 'edit')
 */
function loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode = 'edit') {
    const curriculumSelect = document.getElementById(`curriculum_id_${mode}`);
    const curriculumId = curriculumSelect.value;
    const subjectSelect = document.getElementById(`subject_id_${mode}`);
    
    // Show loading state
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // Build URL with curriculum_id if available
    let url = `/schedule/get-subjects/${sectionId}`;
    if (curriculumId) {
        url += `?curriculum_id=${curriculumId}`;
    }
    
    // Fetch subjects
    fetch(url)
        .then(response => response.json())
        .then(data => {
            subjectSelect.innerHTML = '<option value="">Select a subject...</option>';
            
            if (data.subjects && data.subjects.length > 0) {
                data.subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.id;
                    option.textContent = subject.display;
                    
                    // Add data attributes only for class schedules (not exam)
                    if (mode === 'edit') {
                        option.dataset.code = subject.subject_code;
                        option.dataset.description = subject.course_description;
                        option.dataset.lecUnits = subject.lec_units;
                        option.dataset.labUnits = subject.lab_units;
                        option.dataset.totalUnits = subject.total_units;
                    }
                    
                    // Pre-select the current subject
                    if (subject.id === scheduleData.subject_id) {
                        option.selected = true;
                    }
                    
                    subjectSelect.appendChild(option);
                });
                
                // Trigger subject change handler if subject was found (only for class schedules)
                if (scheduleData.subject_id && subjectSelect.value && mode === 'edit') {
                    // Get the selected option data
                    const selectedOption = subjectSelect.options[subjectSelect.selectedIndex];
                    const subjectData = {
                        id: selectedOption.value,
                        code: selectedOption.dataset.code,
                        description: selectedOption.dataset.description,
                        lecUnits: parseFloat(selectedOption.dataset.lecUnits) || 0,
                        labUnits: parseFloat(selectedOption.dataset.labUnits) || 0,
                        totalUnits: parseFloat(selectedOption.dataset.totalUnits) || 0
                    };
                    
                    // Store in currentSubjectData for calculateEndTime
                    if (typeof currentSubjectData !== 'undefined') {
                        currentSubjectData.edit = subjectData;
                    }
                    
                    // Show schedule type options if the function exists
                    if (typeof showScheduleTypeOptions === 'function') {
                        showScheduleTypeOptions('edit', subjectData);
                    }
                    
                    // Load faculty for the selected subject and preserve the selected faculty
                    if (typeof loadFacultyForSubject === 'function') {
                        console.log('[EDIT] Loading faculty for subject:', scheduleData.subject_id, 'pre-selecting:', scheduleData.faculty_id);
                        loadFacultyForSubject(scheduleData.subject_id, 'edit', scheduleData.faculty_id);
                    }
                    
                    // Set the schedule type after options are populated
                    setTimeout(() => {
                        if (scheduleData.schedule_type) {
                            document.getElementById('schedule_type_edit').value = scheduleData.schedule_type;
                            console.log('[EDIT] Set schedule type:', scheduleData.schedule_type);
                        }
                        
                        // Trigger the schedule type change handler
                        if (typeof handleScheduleTypeChange === 'function') {
                            handleScheduleTypeChange('edit');
                        }
                        
                        // Trigger auto-calculation if start time is already filled
                        const startTimeField = document.getElementById('start_time_edit');
                        if (startTimeField && startTimeField.value && typeof calculateEndTime === 'function') {
                            calculateEndTime('edit');
                        }
                        
                        // Log final form values for debugging
                        console.log('[EDIT] Final form values:', {
                            curriculum_id: document.getElementById('curriculum_id_edit').value,
                            subject_id: document.getElementById('subject_id_edit').value,
                            faculty_id: document.getElementById('faculty_id_edit').value,
                            schedule_type: document.getElementById('schedule_type_edit').value
                        });
                    }, 100);
                }
            } else {
                subjectSelect.innerHTML = '<option value="">No subjects available</option>';
            }
            
            subjectSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading subjects:', error);
            subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
            subjectSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast('Error loading subjects. Please try again.', 'error');
            }
        });
}
