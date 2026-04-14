/**
 * Curriculum Selector Module for Schedule Management
 * Handles curriculum selection and subject loading based on selected curriculum
 */

// Make functions available globally
window.loadCurriculaForSection = loadCurriculaForSection;
window.loadSubjectsForCurriculum = loadSubjectsForCurriculum;
window.loadCurriculaForEdit = loadCurriculaForEdit;
window.loadSubjectsForEditWithCurriculum = loadSubjectsForEditWithCurriculum;

const _curriculaToastState = { message: '', at: 0 };
const _curriculumYearPrefState = {
    storageKey: 'ischedwise_curriculum_by_year',
    cache: null
};

function _getCurriculumScope(mode = 'add') {
    return String(mode || '').startsWith('exam') ? 'exam' : 'class';
}

function _getSectionSwitcher(mode = 'add') {
    return String(mode || '').startsWith('exam')
        ? document.getElementById('examModalSectionSwitcher')
        : document.getElementById('modalSectionSwitcher');
}

function _getSectionOptionById(sectionId, mode = 'add') {
    if (!sectionId) return null;

    const primary = _getSectionSwitcher(mode);
    const sectionIdStr = String(sectionId);
    const primaryMatch = primary
        ? Array.from(primary.options || []).find((option) => String(option.value) === sectionIdStr)
        : null;
    if (primaryMatch) return primaryMatch;

    const alternate = String(mode || '').startsWith('exam')
        ? document.getElementById('modalSectionSwitcher')
        : document.getElementById('examModalSectionSwitcher');
    if (!alternate) return null;

    return Array.from(alternate.options || []).find((option) => String(option.value) === sectionIdStr) || null;
}

function _getYearLevelPreferenceKey(sectionId, mode = 'add') {
    const option = _getSectionOptionById(sectionId, mode);
    if (!option) return null;

    const yearLevel = String(option.dataset.yearLevel || '').trim();
    if (!yearLevel) return null;

    const programId = String(option.dataset.programId || '').trim() || '0';
    const scope = _getCurriculumScope(mode);
    return `${scope}:${programId}:${yearLevel}`;
}

function _readCurriculumYearPreferences() {
    if (_curriculumYearPrefState.cache) {
        return _curriculumYearPrefState.cache;
    }

    try {
        const raw = sessionStorage.getItem(_curriculumYearPrefState.storageKey);
        const parsed = raw ? JSON.parse(raw) : {};
        _curriculumYearPrefState.cache = parsed && typeof parsed === 'object' ? parsed : {};
    } catch (error) {
        _curriculumYearPrefState.cache = {};
    }

    return _curriculumYearPrefState.cache;
}

function _writeCurriculumYearPreferences(preferences) {
    _curriculumYearPrefState.cache = preferences;

    try {
        sessionStorage.setItem(_curriculumYearPrefState.storageKey, JSON.stringify(preferences));
    } catch (error) {
        // Ignore storage failures and keep behavior functional.
    }
}

function _rememberCurriculumForYear(sectionId, curriculumId, mode = 'add') {
    if (!sectionId || !curriculumId) return;

    const key = _getYearLevelPreferenceKey(sectionId, mode);
    if (!key) return;

    const preferences = _readCurriculumYearPreferences();
    preferences[key] = String(curriculumId);
    _writeCurriculumYearPreferences(preferences);
}

function _getRememberedCurriculumForYear(sectionId, mode = 'add') {
    const key = _getYearLevelPreferenceKey(sectionId, mode);
    if (!key) return '';

    const preferences = _readCurriculumYearPreferences();
    return String(preferences[key] || '');
}

function parseScheduleApiJson(response, fallbackMessage) {
    const contentType = (response.headers.get('content-type') || '').toLowerCase();

    if (!response.ok) {
        if (contentType.includes('application/json')) {
            return response.json().then((payload) => {
                const error = payload && payload.error ? payload.error : `Request failed (${response.status})`;
                throw new Error(error);
            });
        }

        return response.text().then((text) => {
            const snippet = (text || '').slice(0, 120).trim();
            throw new Error(snippet || fallbackMessage || `Request failed (${response.status})`);
        });
    }

    if (!contentType.includes('application/json')) {
        return response.text().then((text) => {
            const snippet = (text || '').slice(0, 120).trim();
            throw new Error(snippet || fallbackMessage || 'Invalid server response');
        });
    }

    return response.json();
}

function showCurriculaToastOnce(message) {
    if (typeof showToast !== 'function') return;

    const now = Date.now();
    if (_curriculaToastState.message === message && (now - _curriculaToastState.at) < 1500) {
        return;
    }

    _curriculaToastState.message = message;
    _curriculaToastState.at = now;
    showToast(message, 'error');
}

/**
 * Load curricula for a section
 * @param {number} sectionId - The section ID
 * @param {string} mode - Either 'add', 'edit', 'exam_add', or 'exam_edit'
 */
function loadCurriculaForSection(sectionId, mode = 'add') {
    const curriculumSelect = document.getElementById(`curriculum_id_${mode}`);
    const subjectSelect = document.getElementById(`subject_id_${mode}`);

    if (!curriculumSelect || !subjectSelect) return;

    // Show loading state
    curriculumSelect.innerHTML = '<option value="">Loading curricula...</option>';
    curriculumSelect.disabled = true;
    subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
    subjectSelect.disabled = true;
    
    // Fetch curricula for this section
    fetch(`/schedule/get-curricula/${sectionId}`)
        .then(response => parseScheduleApiJson(response, 'Unable to load curricula'))
        .then(data => {
            curriculumSelect.innerHTML = '<option value="">Select a curriculum...</option>';
            
            if (data.curricula && data.curricula.length > 0) {
                data.curricula.forEach(curriculum => {
                    const option = document.createElement('option');
                    option.value = curriculum.id;
                    option.textContent = curriculum.display;
                    curriculumSelect.appendChild(option);
                });

                const rememberedCurriculumId = _getRememberedCurriculumForYear(sectionId, mode);
                const hasRememberedCurriculum = rememberedCurriculumId
                    && Array.from(curriculumSelect.options).some((option) => String(option.value) === rememberedCurriculumId);

                if (hasRememberedCurriculum) {
                    curriculumSelect.value = rememberedCurriculumId;
                    loadSubjectsForCurriculum(mode);
                }
                
                // Auto-select if only one curriculum
                if (!hasRememberedCurriculum && data.curricula.length === 1) {
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
            showCurriculaToastOnce(error.message || 'Error loading curricula. Please try again.');
        });
}

/**
 * Load subjects based on selected curriculum
 * @param {string} mode - Either 'add', 'edit', 'exam_add', or 'exam_edit'
 */
function loadSubjectsForCurriculum(mode = 'add') {
    const curriculumId = document.getElementById(`curriculum_id_${mode}`).value;
    const sectionIdInput = document.getElementById(`section_id_${mode}`);
    const sectionSwitcher = _getSectionSwitcher(mode);
    const sectionId = (sectionIdInput && sectionIdInput.value)
        || (sectionSwitcher && sectionSwitcher.value)
        || '';
    const subjectSelect = document.getElementById(`subject_id_${mode}`);

    if (!subjectSelect) return;

    if (!curriculumId) {
        subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
        subjectSelect.disabled = true;
        return;
    }

    _rememberCurriculumForYear(sectionId, curriculumId, mode);
    
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
                    
                    // Add data attributes for smart scheduling
                    option.dataset.code = subject.subject_code;
                    option.dataset.description = subject.course_description;
                    option.dataset.lecUnits = subject.lec_units;
                    option.dataset.labUnits = subject.lab_units;
                    option.dataset.totalUnits = subject.total_units;
                    
                    subjectSelect.appendChild(option);
                });
            } else {
                subjectSelect.innerHTML = '<option value="">No subjects available for this curriculum</option>';
            }
            
            subjectSelect.disabled = false;

            // Trigger conflict check after subjects reload
            if (mode === 'add' || mode === 'edit') {
                if (typeof scheduleAutoConflictCheck === 'function') {
                    scheduleAutoConflictCheck(mode);
                }
            } else if (mode === 'exam_add' || mode === 'exam_edit') {
                const examMode = mode.replace('exam_', '');
                if (typeof scheduleAutoExamConflictCheck === 'function') {
                    scheduleAutoExamConflictCheck(examMode);
                }
            }
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
        .then(response => parseScheduleApiJson(response, 'Unable to load curricula'))
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
            showCurriculaToastOnce(error.message || 'Error loading curricula. Please try again.');
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
    // If only one curriculum, select it
    if (curricula.length === 1) {
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
                        curriculumSelect.value = curriculum.id;
                        loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
                    }
                }
                
                // If we've tried all curricula and haven't found it, default to first
                if (attemptCount === curricula.length && !foundCurriculum) {
                    curriculumSelect.value = curricula[0].id;
                    loadSubjectsForEditWithCurriculum(sectionId, scheduleData, mode);
                }
            })
            .catch(error => {
                console.error('[DETECT] Error detecting curriculum:', error);
                attemptCount++;
                
                // If all attempts failed, default to first curriculum
                if (attemptCount === curricula.length && !foundCurriculum) {
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
                    
                    // Add data attributes for subject detection (PE, schedule type)
                    option.dataset.code = subject.subject_code;
                    option.dataset.description = subject.course_description;
                    option.dataset.lecUnits = subject.lec_units;
                    option.dataset.labUnits = subject.lab_units;
                    option.dataset.totalUnits = subject.total_units;
                    
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
                        loadFacultyForSubject(scheduleData.subject_id, 'edit', scheduleData.faculty_id);
                    }
                    
                    // Set the schedule type after options are populated
                    setTimeout(() => {
                        if (scheduleData.schedule_type) {
                            document.getElementById('schedule_type_edit').value = scheduleData.schedule_type;
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
                        
                    }, 100);
                } else if (scheduleData.subject_id && subjectSelect.value && mode === 'exam_edit') {
                    // For exam edit mode, ALWAYS load all faculty (not filtered by subject)
                    fetch('/schedule/get-all-faculty')
                        .then(response => response.json())
                        .then(data => {
                            const facultySelect = document.getElementById('faculty_id_exam_edit');
                            facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
                            
                            if (data.faculty && data.faculty.length > 0) {
                                data.faculty.forEach(faculty => {
                                    const option = document.createElement('option');
                                    option.value = faculty.id;
                                    option.textContent = faculty.full_name;
                                    
                                    // Pre-select if matches
                                    if (scheduleData.faculty_id && faculty.id === scheduleData.faculty_id) {
                                        option.selected = true;
                                    }
                                    
                                    facultySelect.appendChild(option);
                                });
                            }
                        })
                        .catch(error => console.error('Error loading faculty:', error));
                    
                    // Load rooms if room_id exists
                    if (scheduleData.room_id) {
                        fetch('/schedule/get-all-rooms')
                            .then(response => response.json())
                            .then(data => {
                                const roomSelect = document.getElementById('room_id_exam_edit');
                                roomSelect.innerHTML = '<option value="">Select a room...</option>';
                                
                                if (data.rooms && data.rooms.length > 0) {
                                    data.rooms.forEach(room => {
                                        const option = document.createElement('option');
                                        option.value = room.id;
                                        option.textContent = room.display;
                                        
                                        // Pre-select if matches
                                        if (room.id === scheduleData.room_id) {
                                            option.selected = true;
                                        }
                                        
                                        roomSelect.appendChild(option);
                                    });
                                }
                            })
                            .catch(error => console.error('Error loading rooms:', error));
                    }
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
