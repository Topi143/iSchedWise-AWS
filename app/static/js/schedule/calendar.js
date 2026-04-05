// Calendar View Switching Functions

// Schedule View Switching Function (Table vs Calendar)
function switchScheduleView(viewType) {
    const tableView = document.getElementById('scheduleTableView');
    const calendarView = document.getElementById('scheduleCalendarView');
    const tableBtn = document.getElementById('viewToggleTable');
    const calendarBtn = document.getElementById('viewToggleCalendar');
    
    if (viewType === 'table') {
        tableView?.classList.remove('hidden');
        calendarView?.classList.add('hidden');
        
        // Update button styles
        tableBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
    } else {
        tableView?.classList.add('hidden');
        calendarView?.classList.remove('hidden');
        
        // Update button styles
        calendarBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Initialize calendar enhancements when switching to calendar view
        initializeWeekCalendar();
    }
    
    // Store preference in localStorage
    localStorage.setItem('scheduleViewPreference', viewType);
}

// Faculty Schedule View Switching
function switchFacultyView(viewType) {
    const tableView = document.getElementById('facultyTableView');
    const calendarView = document.getElementById('facultyCalendarView');
    const tableBtn = document.getElementById('viewToggleFacultyTable');
    const calendarBtn = document.getElementById('viewToggleFacultyCalendar');
    
    if (viewType === 'table') {
        tableView?.classList.remove('hidden');
        calendarView?.classList.add('hidden');
        tableBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
    } else {
        tableView?.classList.add('hidden');
        calendarView?.classList.remove('hidden');
        calendarBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Initialize calendar enhancements when switching to calendar view
        initializeWeekCalendar();
    }
    
    localStorage.setItem('facultyViewPreference', viewType);
}

// Room Schedule View Switching
function switchRoomView(viewType) {
    const tableView = document.getElementById('roomTableView');
    const calendarView = document.getElementById('roomCalendarView');
    const tableBtn = document.getElementById('viewToggleRoomTable');
    const calendarBtn = document.getElementById('viewToggleRoomCalendar');
    
    if (viewType === 'table') {
        tableView?.classList.remove('hidden');
        calendarView?.classList.add('hidden');
        tableBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
    } else {
        tableView?.classList.add('hidden');
        calendarView?.classList.remove('hidden');
        calendarBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Initialize calendar enhancements when switching to calendar view
        initializeWeekCalendar();
    }
    
    localStorage.setItem('roomViewPreference', viewType);
}

// Exam Schedule View Switching
function switchExamView(viewType) {
    const tableView = document.getElementById('examTableView');
    const calendarView = document.getElementById('examCalendarView');
    const tableBtn = document.getElementById('viewToggleExamTable');
    const calendarBtn = document.getElementById('viewToggleExamCalendar');
    
    if (viewType === 'table') {
        tableView?.classList.remove('hidden');
        calendarView?.classList.add('hidden');
        tableBtn?.classList.add('bg-white', 'text-orange-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-orange-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
    } else {
        tableView?.classList.add('hidden');
        calendarView?.classList.remove('hidden');
        calendarBtn?.classList.add('bg-white', 'text-orange-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-orange-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Initialize calendar enhancements when switching to calendar view
        initializeWeekCalendar();
    }
    
    localStorage.setItem('examViewPreference', viewType);
}

function cacheEmptyStateTemplate(element) {
    if (!element || element.dataset.defaultTemplate) return;
    element.dataset.defaultTemplate = element.innerHTML;
}

function restoreEmptyStateTemplate(element) {
    if (!element) return;
    if (element.dataset.defaultTemplate) {
        element.innerHTML = element.dataset.defaultTemplate;
    }
}

function renderStateLoading(theme, label) {
    const accent = theme === 'orange' ? 'border-orange-500' : 'border-blue-500';
    const text = theme === 'orange' ? 'text-orange-600' : 'text-blue-600';
    return `
        <div class="h-full flex items-center justify-center">
            <div class="text-center">
                <div class="animate-spin rounded-full h-10 w-10 border-b-2 ${accent} mx-auto mb-3"></div>
                <p class="text-sm font-medium ${text}">${label}</p>
            </div>
        </div>
    `;
}

function renderStateError(theme, message, retryFnName) {
    const iconBg = theme === 'orange' ? 'bg-orange-100 dark:bg-orange-900/30' : 'bg-red-100 dark:bg-red-900/30';
    const iconText = theme === 'orange' ? 'text-orange-500 dark:text-orange-300' : 'text-red-500 dark:text-red-300';
    const buttonBg = theme === 'orange' ? 'bg-orange-50 dark:bg-orange-900/30 border-orange-200 dark:border-orange-800 text-orange-700 dark:text-orange-300 hover:bg-orange-100 dark:hover:bg-orange-900/50' : 'bg-blue-50 dark:bg-blue-900/30 border-blue-200 dark:border-blue-800 text-blue-700 dark:text-blue-300 hover:bg-blue-100 dark:hover:bg-blue-900/50';
    return `
        <div class="h-full flex items-center justify-center p-6">
            <div class="text-center max-w-xs">
                <div class="w-14 h-14 ${iconBg} rounded-full flex items-center justify-center mx-auto mb-3">
                    <svg class="w-7 h-7 ${iconText}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>
                </div>
                <p class="text-sm font-medium text-gray-800 dark:text-gray-200 mb-2">Unable to load schedule</p>
                <p class="text-xs text-gray-500 dark:text-gray-400">${message}</p>
                <button type="button" onclick="${retryFnName}()" class="mt-4 inline-flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-all ${buttonBg}">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
                    </svg>
                    Retry
                </button>
            </div>
        </div>
    `;
}

function focusFirstAvailable(ids) {
    for (const id of ids) {
        const element = document.getElementById(id);
        if (!element || element.disabled) continue;
        if (element.matches('input, select, textarea, button')) {
            element.focus();
        } else {
            if (!element.hasAttribute('tabindex')) element.setAttribute('tabindex', '-1');
            element.focus();
        }
        element.scrollIntoView({ block: 'center', behavior: 'smooth' });
        return true;
    }
    return false;
}

window.focusScheduleSectionSelector = function() {
    focusFirstAvailable(['modalSectionSwitcher']);
};

window.focusExamSectionSelector = function() {
    focusFirstAvailable(['examModalSectionSwitcher']);
};

window.focusClassFormStart = function() {
    focusFirstAvailable(['curriculum_id_add', 'subject_id_add', 'schedule_type_add']);
};

window.focusExamFormStart = function() {
    focusFirstAvailable(['curriculum_id_exam_add', 'subject_id_exam_add', 'exam_date_add']);
};

window.focusClassSectionList = function() {
    const firstSection = document.querySelector('#sectionList .section-list-item');
    if (!firstSection) return;
    if (!firstSection.hasAttribute('tabindex')) firstSection.setAttribute('tabindex', '-1');
    firstSection.focus();
    firstSection.scrollIntoView({ block: 'center', behavior: 'smooth' });
};

window.focusExamSectionList = function() {
    const firstSection = document.querySelector('#examSectionList .section-list-item');
    if (!firstSection) return;
    if (!firstSection.hasAttribute('tabindex')) firstSection.setAttribute('tabindex', '-1');
    firstSection.focus();
    firstSection.scrollIntoView({ block: 'center', behavior: 'smooth' });
};

function syncModalCalendarHeaderScrollbarOffset(calendarBodyId, weekCalendarId) {
    const calendarBody = document.getElementById(calendarBodyId);
    const weekCalendar = document.getElementById(weekCalendarId);
    if (!calendarBody || !weekCalendar) return;

    const dayHeaderGrid = weekCalendar.querySelector('.flex.border-b .grid.grid-cols-7');
    if (!dayHeaderGrid) return;

    const scrollbarWidth = Math.max(0, calendarBody.offsetWidth - calendarBody.clientWidth);
    dayHeaderGrid.style.paddingRight = `${scrollbarWidth}px`;
}

function queueModalCalendarHeaderScrollbarOffsetSync(calendarBodyId, weekCalendarId) {
    requestAnimationFrame(() => {
        requestAnimationFrame(() => {
            syncModalCalendarHeaderScrollbarOffset(calendarBodyId, weekCalendarId);
        });
    });
}

// ============================================================================
// MODAL VIEW SWITCHING (Table vs Calendar inside Add/Edit Schedule Modal)
// ============================================================================

// Store current modal view preference
window.modalViewPreference = 'calendar';

/**
 * Switch between Table and Calendar view inside the Schedule Modal
 * @param {string} viewType - 'table' or 'calendar'
 */
function switchModalView(viewType) {
    const tableView = document.getElementById('modalTableView');
    const calendarContainer = document.getElementById('modalCalendarContainer');
    const weekCalendar = document.getElementById('modalWeekCalendar');
    const tableBtn = document.getElementById('modalViewToggleTable');
    const calendarBtn = document.getElementById('modalViewToggleCalendar');
    const emptyState = document.getElementById('modalCalendarEmptyState');
    
    window.modalViewPreference = viewType;
    
    if (viewType === 'table') {
        // Show table, hide calendar - use both class and style for certainty
        if (tableView) {
            tableView.classList.remove('hidden');
            tableView.style.display = 'flex';
        }
        if (calendarContainer) {
            calendarContainer.classList.add('hidden');
            calendarContainer.style.display = 'none';
        }
        
        // Update button styles
        tableBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Re-render table data and hide empty state if we have data
        if (window.modalCalendarData && window.modalCalendarData.schedules) {
            emptyState?.classList.add('hidden');
            renderModalTableView(window.modalCalendarData.schedules);
        }
    } else {
        // Show calendar, hide table - use both class and style for certainty
        if (tableView) {
            tableView.classList.add('hidden');
            tableView.style.display = 'none';
        }
        if (calendarContainer) {
            calendarContainer.classList.remove('hidden');
            calendarContainer.style.display = 'flex';
        }
        
        // Update button styles
        calendarBtn?.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Hide empty state and show calendar grid if we have data
        if (window.modalCalendarData && window.modalCalendarData.schedules) {
            emptyState?.classList.add('hidden');
            weekCalendar?.classList.remove('hidden');
            
            // Re-render calendar
            requestAnimationFrame(() => {
                buildModalCalendarGrid(window.modalCalendarData.startHour, window.modalCalendarData.endHour);
                renderModalCalendarEvents(window.modalCalendarData.schedules, window.modalCalendarData.startHour);
                queueModalCalendarHeaderScrollbarOffsetSync('modalCalendarBody', 'modalWeekCalendar');
            });
        }
    }
    
    localStorage.setItem('modalViewPreference', viewType);
}

/**
 * Render the modal table view with schedule data
 * @param {Array} schedules - Array of schedule objects
 */
function renderModalTableView(schedules) {
    const tableBody = document.getElementById('modalTableBody');
    const tableEmptyState = document.getElementById('modalTableEmptyState');
    
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    if (!schedules || schedules.length === 0) {
        // Show empty state
        tableEmptyState?.classList.remove('hidden');
        return;
    }
    
    // Hide empty state
    tableEmptyState?.classList.add('hidden');
    
    // Day order for sorting
    const dayOrder = { 'Monday': 1, 'Tuesday': 2, 'Wednesday': 3, 'Thursday': 4, 'Friday': 5, 'Saturday': 6, 'Sunday': 7 };
    
    // Sort schedules by day and then by time
    const sortedSchedules = [...schedules].sort((a, b) => {
        const dayDiff = (dayOrder[a.day_of_week] || 8) - (dayOrder[b.day_of_week] || 8);
        if (dayDiff !== 0) return dayDiff;
        return a.start_time.localeCompare(b.start_time);
    });
    
    // Build table rows
    sortedSchedules.forEach((schedule, index) => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-blue-50/80 transition-colors duration-150 cursor-pointer group' + (index % 2 === 0 ? '' : ' bg-gray-50/30');
        row.dataset.scheduleId = schedule.id;
        row.dataset.scheduleData = JSON.stringify(schedule);
        
        // Add click handler to load this schedule for editing
        row.addEventListener('click', function() {
            const scheduleData = JSON.parse(this.dataset.scheduleData);
            if (typeof loadScheduleForEditing === 'function') {
                loadScheduleForEditing(scheduleData);
            }
        });
        
        // Format time
        const startTime = formatTime12Hour(schedule.start_time);
        const endTime = formatTime12Hour(schedule.end_time);
        
        // Schedule type badge color
        let typeBadgeClass = 'bg-blue-100 text-blue-700';
        if (schedule.schedule_type === 'Lab' || schedule.schedule_type === 'lab') {
            typeBadgeClass = 'bg-green-100 text-green-700';
        }
        
        // Day abbreviation and color
        const dayAbbrev = schedule.day_of_week?.substring(0, 3).toUpperCase() || 'N/A';
        let dayBadgeClass = 'bg-gray-100 text-gray-700';
        if (['Monday', 'Wednesday', 'Friday'].includes(schedule.day_of_week)) {
            dayBadgeClass = 'bg-blue-100 text-blue-700 border border-blue-200';
        } else if (['Tuesday', 'Thursday'].includes(schedule.day_of_week)) {
            dayBadgeClass = 'bg-teal-100 text-teal-700 border border-teal-200';
        } else if (['Saturday', 'Sunday'].includes(schedule.day_of_week)) {
            dayBadgeClass = 'bg-orange-100 text-orange-700 border border-orange-200';
        }
        
        row.innerHTML = `
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap">
                <span class="inline-flex items-center justify-center px-2 py-0.5 rounded-md text-[10px] sm:text-xs font-bold ${dayBadgeClass}">
                    ${dayAbbrev}
                </span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap">
                <span class="text-xs font-medium text-gray-700">${startTime}</span>
                <span class="text-[10px] text-gray-400 mx-0.5">-</span>
                <span class="text-xs font-medium text-gray-700">${endTime}</span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5">
                <div class="font-semibold text-gray-900 text-xs sm:text-sm truncate max-w-[100px] sm:max-w-[180px]" title="${schedule.subject_code || ''}">
                    ${schedule.subject_code || 'N/A'}
                </div>
                <div class="text-[10px] text-gray-500 truncate max-w-[100px] sm:max-w-[180px]" title="${schedule.subject_name || ''}">
                    ${schedule.subject_name || ''}
                </div>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap hidden sm:table-cell">
                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[10px] font-semibold ${typeBadgeClass}">
                    ${schedule.schedule_type || 'Lecture'}
                </span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap hidden sm:table-cell">
                <span class="text-xs font-medium text-gray-700">${schedule.room_number || 'TBA'}</span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 hidden lg:table-cell">
                <div class="text-xs text-gray-600 truncate max-w-[120px]" title="${schedule.faculty_name || 'TBA'}">
                    ${schedule.faculty_name || 'TBA'}
                </div>
            </td>
            <td class="px-1.5 sm:px-2 py-2 hidden sm:table-cell">
                <div class="flex items-center justify-center gap-1">
                    <button class="modal-table-delete-btn p-1 rounded hover:bg-red-100 text-red-500 transition-colors" title="Delete">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                </div>
            </td>
        `;

        // Action button handlers (stopPropagation to prevent row click)
        const deleteBtn = row.querySelector('.modal-table-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (typeof deleteSchedule === 'function') deleteSchedule(schedule.id, schedule.subject_code || 'Schedule');
            });
        }

        tableBody.appendChild(row);
    });
}

/**
 * Format time string to 12-hour format
 * @param {string} time24 - Time in 24-hour format (HH:MM)
 * @returns {string} Time in 12-hour format
 */
function formatTime12Hour(time24) {
    if (!time24) return '';
    const [hours, minutes] = time24.split(':');
    const hour = parseInt(hours, 10);
    const ampm = hour >= 12 ? 'PM' : 'AM';
    const displayHour = hour > 12 ? hour - 12 : (hour === 0 ? 12 : hour);
    return `${displayHour}:${minutes} ${ampm}`;
}

// Restore view preferences on page load
document.addEventListener('DOMContentLoaded', function() {
    // Restore schedule view preference (table or calendar)
    const viewPreference = localStorage.getItem('scheduleViewPreference') || 'table';
    switchScheduleView(viewPreference);
    
    // Restore faculty view preference
    const facultyViewPreference = localStorage.getItem('facultyViewPreference') || 'table';
    if (document.getElementById('facultyTableView')) {
        switchFacultyView(facultyViewPreference);
    }
    
    // Restore room view preference
    const roomViewPreference = localStorage.getItem('roomViewPreference') || 'table';
    if (document.getElementById('roomTableView')) {
        switchRoomView(roomViewPreference);
    }
    
    // Restore exam view preference
    const examViewPreference = localStorage.getItem('examViewPreference') || 'table';
    if (document.getElementById('examTableView')) {
        switchExamView(examViewPreference);
    }
    
    // Initialize week calendar enhancements
    initializeWeekCalendar();
});


// ========================================
// WEEK CALENDAR ENHANCEMENTS
// ========================================

/**
 * Initialize week calendar features:
 * - Current day highlighting
 * - Overlapping event detection and stacking
 */
function initializeWeekCalendar() {
    highlightCurrentDay();
    handleOverlappingEvents();
}

/**
 * Highlight the current day column in the calendar
 */
function highlightCurrentDay() {
    const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
    const today = days[new Date().getDay()];
    
    // Find and highlight day headers
    document.querySelectorAll('.week-day-header').forEach(header => {
        const dayName = header.dataset.day;
        if (dayName === today) {
            header.classList.add('current-day');
        } else {
            header.classList.remove('current-day');
        }
    });
    
    // Find and highlight day columns
    document.querySelectorAll('.week-day-column').forEach(column => {
        const dayName = column.dataset.day;
        if (dayName === today) {
            column.classList.add('current-day');
        } else {
            column.classList.remove('current-day');
        }
    });
}

/**
 * Detect and handle overlapping events by adjusting their widths
 */
function handleOverlappingEvents() {
    // Process each day column
    document.querySelectorAll('.week-events-container').forEach(container => {
        const events = Array.from(container.querySelectorAll('.week-event'));
        
        if (events.length <= 1) return;
        
        // Get event time data
        const eventData = events.map(event => ({
            element: event,
            start: parseInt(event.dataset.start) || 0,
            duration: parseInt(event.dataset.duration) || 60,
            end: (parseInt(event.dataset.start) || 0) + (parseInt(event.dataset.duration) || 60)
        }));
        
        // Sort by start time
        eventData.sort((a, b) => a.start - b.start);
        
        // Find overlapping groups
        const groups = [];
        let currentGroup = [eventData[0]];
        
        for (let i = 1; i < eventData.length; i++) {
            const current = eventData[i];
            const lastInGroup = currentGroup[currentGroup.length - 1];
            
            // Check if current overlaps with any event in the current group
            const overlaps = currentGroup.some(e => 
                current.start < e.end && current.end > e.start
            );
            
            if (overlaps) {
                currentGroup.push(current);
            } else {
                groups.push(currentGroup);
                currentGroup = [current];
            }
        }
        groups.push(currentGroup);
        
        // Apply stacking classes to overlapping events
        groups.forEach(group => {
            if (group.length === 1) {
                // Single event - use full width
                group[0].element.style.left = '2px';
                group[0].element.style.right = '2px';
                return;
            }
            
            // Multiple overlapping events - divide width
            const width = 100 / group.length;
            group.forEach((event, index) => {
                const left = width * index;
                event.element.style.left = `${left}%`;
                event.element.style.right = `${100 - left - width}%`;
                event.element.style.width = `${width - 1}%`;
                event.element.style.marginLeft = index > 0 ? '1px' : '0';
            });
        });
    });
}

/**
 * Refresh calendar view (call after adding/editing events)
 */
function refreshWeekCalendar() {
    initializeWeekCalendar();
}

// ========================================
// MODAL CALENDAR FOR ADD SCHEDULE
// ========================================

// Debounce helper for resize events
let modalCalendarResizeTimeout = null;

/**
 * Handle window resize to recalculate calendar dimensions
 */
function handleModalCalendarResize() {
    if (modalCalendarResizeTimeout) {
        clearTimeout(modalCalendarResizeTimeout);
    }
    
    modalCalendarResizeTimeout = setTimeout(() => {
        const weekCalendar = document.getElementById('modalWeekCalendar');
        const calendarData = window.modalCalendarData;
        const examWeekCalendar = document.getElementById('examModalWeekCalendar');
        const examCalendarData = window.examModalCalendarData;
        
        // Only recalculate if calendar is visible and has data
        if (weekCalendar && !weekCalendar.classList.contains('hidden') && calendarData) {
            buildModalCalendarGrid(calendarData.startHour, calendarData.endHour);
            renderModalCalendarEvents(calendarData.schedules, calendarData.startHour);
            queueModalCalendarHeaderScrollbarOffsetSync('modalCalendarBody', 'modalWeekCalendar');
        }

        if (examWeekCalendar && !examWeekCalendar.classList.contains('hidden') && examCalendarData) {
            buildExamModalCalendarGrid(examCalendarData.startHour, examCalendarData.endHour);
            renderExamModalCalendarEvents(examCalendarData.exams, examCalendarData.startHour);
            queueModalCalendarHeaderScrollbarOffsetSync('examModalCalendarBody', 'examModalWeekCalendar');
        }
    }, 150);
}

// Keep modal calendar dimensions aligned when viewport changes.
window.addEventListener('resize', handleModalCalendarResize);
window.addEventListener('orientationchange', handleModalCalendarResize);

/**
 * Render the modal calendar for a specific section
 * @param {number} sectionId - The section ID to fetch schedules for
 * @param {string} sectionName - The section name to display in header
 */
function renderModalCalendar(sectionId, sectionName) {
    const container = document.getElementById('modalCalendarContainer');
    const emptyState = document.getElementById('modalCalendarEmptyState');
    const weekCalendar = document.getElementById('modalWeekCalendar');
    const tableView = document.getElementById('modalTableView');
    const sectionNameEl = document.getElementById('modalCalendarSectionName');
    const eventCountEl = document.getElementById('modalCalendarEventCount');
    
    window.modalCalendarLastSectionId = sectionId;
    window.modalCalendarLastSectionName = sectionName;
    cacheEmptyStateTemplate(emptyState);

    if (!sectionId) {
        restoreEmptyStateTemplate(emptyState);
        // Show empty state if no section selected
        if (emptyState) emptyState.classList.remove('hidden');
        if (weekCalendar) weekCalendar.classList.add('hidden');
        if (tableView) {
            tableView.classList.add('hidden');
            tableView.style.display = 'none';
        }
        if (container) {
            container.classList.add('hidden');
            container.style.display = 'none';
        }
        if (sectionNameEl) sectionNameEl.textContent = 'Select a section to view schedule';
        if (eventCountEl) eventCountEl.textContent = '0 classes';
        window.modalCalendarData = null;
        return;
    }
    
    // Update section name in header
    if (sectionNameEl && sectionName) {
        sectionNameEl.textContent = sectionName;
    }
    
    // Show loading state
    if (emptyState) {
        emptyState.innerHTML = renderStateLoading('blue', 'Loading class schedule...');
        emptyState.classList.remove('hidden');
    }
    if (weekCalendar) weekCalendar.classList.add('hidden');
    if (tableView) tableView.classList.add('hidden');
    
    // Fetch section schedules
    fetch(`/schedule/api/section-schedules/${sectionId}`)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                showModalCalendarError(data.error);
                return;
            }
            
            const schedules = data.schedules || [];
            const startHour = data.settings?.start_hour || 7;
            const endHour = data.settings?.end_hour || 20;
            
            // Update event count
            if (eventCountEl) {
                eventCountEl.textContent = `${schedules.length} class${schedules.length !== 1 ? 'es' : ''}`;
            }
            
            // Store current data for resize recalculation and table rendering
            window.modalCalendarData = {
                schedules: schedules,
                startHour: startHour,
                endHour: endHour
            };
            
            // Hide empty state and restore baseline markup for future no-section state.
            restoreEmptyStateTemplate(emptyState);
            if (emptyState) emptyState.classList.add('hidden');
            
            // Get current view preference (default to calendar)
            const currentView = window.modalViewPreference || localStorage.getItem('modalViewPreference') || 'calendar';
            
            // Always render both views so switching is instant
            // Render table data
            renderModalTableView(schedules);
            
            // Render based on current view preference - use explicit display styles
            if (currentView === 'table') {
                // Show table view, hide calendar container
                if (tableView) {
                    tableView.classList.remove('hidden');
                    tableView.style.display = 'flex';
                }
                if (container) {
                    container.classList.add('hidden');
                    container.style.display = 'none';
                }
            } else {
                // Show calendar view, hide table
                if (tableView) {
                    tableView.classList.add('hidden');
                    tableView.style.display = 'none';
                }
                if (container) {
                    container.classList.remove('hidden');
                    container.style.display = 'flex';
                }
                if (weekCalendar) weekCalendar.classList.remove('hidden');
                
                // Small delay to ensure DOM has updated with proper dimensions
                requestAnimationFrame(() => {
                    // Build the calendar grid
                    buildModalCalendarGrid(startHour, endHour);
                    
                    // Render events
                    renderModalCalendarEvents(schedules, startHour);
                });
            }
        })
        .catch(error => {
            console.error('Error fetching section schedules:', error);
            showModalCalendarError('Failed to load schedule');
        });
}

/**
 * Show error state in modal calendar
 */
function showModalCalendarError(message) {
    const emptyState = document.getElementById('modalCalendarEmptyState');
    const weekCalendar = document.getElementById('modalWeekCalendar');
    cacheEmptyStateTemplate(emptyState);
    
    if (emptyState) {
        emptyState.innerHTML = renderStateError('blue', message, 'retryModalCalendarLoad');
        emptyState.classList.remove('hidden');
    }
    if (weekCalendar) weekCalendar.classList.add('hidden');
}

function retryModalCalendarLoad() {
    if (!window.modalCalendarLastSectionId) return;
    renderModalCalendar(window.modalCalendarLastSectionId, window.modalCalendarLastSectionName || '');
}

/**
 * Build the modal calendar grid with time labels and day columns
 * Fully responsive: fills available vertical space while showing all hours
 */
function buildModalCalendarGrid(startHour, endHour) {
    const timeLabels = document.getElementById('modalTimeLabels');
    const daysGrid = document.getElementById('modalDaysGrid');
    const calendarBody = document.getElementById('modalCalendarBody');
    
    if (!timeLabels || !daysGrid || !calendarBody) return;
    
    // Include extra hour when end time has :30 minutes
    const endMinute = window.scheduleEndMinute || 0;
    
    // Total hours and pixels (1px per minute)
    const totalMinutes = (endHour * 60 + endMinute) - (startHour * 60);
    const totalGridHeight = totalMinutes;
    const axisOffset = 8;
    const totalAxisHeight = totalGridHeight + axisOffset;
    
    // Store for event positioning
    window.modalCalendarPixelsPerMinute = 1;
    window.modalCalendarStartHour = startHour;
    window.modalCalendarTotalHeight = totalGridHeight;
    
    // Build time labels using shared structure (week-time-slot) — 30-minute intervals
    let timeLabelsHTML = '';
    for (let m = startHour * 60; m < (endHour * 60 + endMinute); m += 30) {
        const h = Math.floor(m / 60);
        const min = m % 60;
        const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const minStr = min === 0 ? '00' : '30';
        
        timeLabelsHTML += `
            <div class="week-time-slot">
                <span class="time-label">${hr12}:${minStr}</span>
                <span class="time-period">${ampm}</span>
            </div>
        `;
    }
    
    // Final boundary label
    const finalEndTotalMins = endHour * 60 + endMinute;
    const finalH = Math.floor(finalEndTotalMins / 60);
    const finalMin = finalEndTotalMins % 60;
    const finalH12 = finalH > 12 ? finalH - 12 : (finalH === 0 ? 12 : finalH);
    const finalAmpm = finalH >= 12 ? 'PM' : 'AM';
    const finalMinStr = finalMin === 0 ? '00' : '30';
    
    // Keep the end boundary inside the same axis flow to avoid footer/grid misalignment.
    timeLabelsHTML += `
        <div class="week-time-slot" style="height: 0; position: relative; overflow: visible;">
            <div style="position: absolute; left: 0; right: 0; top: 0; display: flex; justify-content: flex-end; gap: 2px; padding: 0 8px 0 4px;">
                <span class="time-label">${finalH12}:${finalMinStr}</span>
                <span class="time-period">${finalAmpm}</span>
            </div>
        </div>
    `;
    timeLabels.innerHTML = timeLabelsHTML;
    timeLabels.style.position = '';
    timeLabels.style.height = `${totalAxisHeight}px`;
    
    // Build day columns matching main calendar structure
    // Always render full Mon-Sun columns so grid lines remain complete,
    // even when operation days are restricted.
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    let daysHTML = '';
    
    days.forEach((day) => {
        let hourLines = '';
        for (let m = 0; m < totalGridHeight; m += 30) {
            if (m % 60 === 0) {
                hourLines += `<div class="week-hour-line" style="top: ${m + axisOffset}px;"></div>`;
            } else {
                hourLines += `<div class="week-half-hour-line" style="top: ${m + axisOffset}px;"></div>`;
            }
        }
        hourLines += `<div class="week-hour-line" style="top: ${totalGridHeight + axisOffset}px;"></div>`;
        
        daysHTML += `
            <div class="week-day-column" data-day="${day}" style="position: relative; border-right: 1px solid #e5e7eb; min-height: ${totalAxisHeight}px;">
                ${hourLines}
                <div class="modal-events-container week-events-container" data-day="${day}"></div>
            </div>
        `;
    });
    
    daysGrid.innerHTML = daysHTML;
    daysGrid.style.height = `${totalAxisHeight}px`;
    
    // Make calendar body scrollable
    calendarBody.style.overflowY = 'auto';
    calendarBody.style.overflowX = 'hidden';

    queueModalCalendarHeaderScrollbarOffsetSync('modalCalendarBody', 'modalWeekCalendar');
}

function getClassModalEventContainers() {
    const daysGrid = document.getElementById('modalDaysGrid');
    return daysGrid ? daysGrid.querySelectorAll('.modal-events-container') : [];
}

function getClassModalDayContainer(dayName) {
    const daysGrid = document.getElementById('modalDaysGrid');
    return daysGrid ? daysGrid.querySelector(`.modal-events-container[data-day="${dayName}"]`) : null;
}

/**
 * Render events on the modal calendar
 */
function renderModalCalendarEvents(schedules, startHour) {
    const pixelsPerMinute = window.modalCalendarPixelsPerMinute || 1;
    const startMinutes = startHour * 60;
    
    // Clear existing events
    getClassModalEventContainers().forEach(container => {
        container.innerHTML = '';
    });
    
    schedules.forEach(schedule => {
        const dayName = schedule.day_of_week;
        const container = getClassModalDayContainer(dayName);
        
        if (!container) return;
        
        // Calculate position (1px per minute, consistent with main & batch)
        const eventStartMinutes = schedule.start_minutes;
        const topOffset = ((eventStartMinutes - startMinutes) * pixelsPerMinute) + 8;
        const height = schedule.duration * pixelsPerMinute;
        
        // Use shared CSS classes — same as main class tab & batch
        const isLab = schedule.schedule_type === 'Lab' || schedule.schedule_type === 'lab';
        const typeClass = isLab ? 'event-lab' : 'event-lecture';
        
        const eventEl = document.createElement('div');
        eventEl.className = `week-event ${typeClass}`;
        eventEl.style.top = `${topOffset}px`;
        eventEl.style.height = `${Math.max(height, 20)}px`;
        eventEl.style.cursor = 'pointer';
        
        // Store schedule data for click handler
        eventEl.dataset.scheduleId = schedule.id;
        eventEl.dataset.scheduleData = JSON.stringify(schedule);
        
        // Click to load for editing
        eventEl.addEventListener('click', function(e) {
            e.stopPropagation();
            const scheduleData = JSON.parse(this.dataset.scheduleData);
            if (typeof loadScheduleForEditing === 'function') {
                loadScheduleForEditing(scheduleData);
            }
        });
        
        // Tooltip
        eventEl.title = `${schedule.subject_code} - ${schedule.subject_name || ''}\nFaculty: ${schedule.faculty_name || 'TBA'}\nRoom: ${schedule.room_number || 'TBA'}\nTime: ${schedule.start_time_display || schedule.start_time} - ${schedule.end_time_display || schedule.end_time}\nType: ${schedule.schedule_type || 'Lecture'}`;
        
        // Content using shared CSS classes — thresholds match main class tab (45/60/75)
        eventEl.innerHTML = `
            <div class="event-content">
                <div class="event-subject">${schedule.subject_code || 'N/A'}</div>
                ${height >= 45 ? `<div class="event-room">${schedule.room_number || 'TBA'}</div>` : ''}
                ${height >= 60 ? `<div class="event-faculty">${schedule.faculty_name || 'TBA'}</div>` : ''}
                ${height >= 75 ? `<div class="event-time">${schedule.start_time_display || schedule.start_time} - ${schedule.end_time_display || schedule.end_time}</div>` : ''}
            </div>
            <div class="event-type-badge">${(schedule.schedule_type || 'Lec').substring(0, 3).toUpperCase()}</div>
            <button class="calendar-event-delete-btn" title="Delete">
                <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
        `;

        // Delete button click handler
        const delBtn = eventEl.querySelector('.calendar-event-delete-btn');
        if (delBtn) {
            delBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (typeof deleteSchedule === 'function') deleteSchedule(schedule.id, schedule.subject_code || 'Schedule');
            });
        }

        container.appendChild(eventEl);
    });
    
    // Handle overlapping events in modal calendar
    handleModalOverlappingEvents();
}

/**
 * Handle overlapping events in modal calendar
 */
function handleModalOverlappingEvents() {
    getClassModalEventContainers().forEach(container => {
        const events = Array.from(container.querySelectorAll('.week-event'));
        
        if (events.length <= 1) return;
        
        // Get event positions
        const eventData = events.map(event => ({
            element: event,
            top: parseFloat(event.style.top) || 0,
            height: parseFloat(event.style.height) || 20
        }));
        
        // Sort by top position
        eventData.sort((a, b) => a.top - b.top);
        
        // Find overlapping groups
        const groups = [];
        let currentGroup = [eventData[0]];
        
        for (let i = 1; i < eventData.length; i++) {
            const current = eventData[i];
            
            const overlaps = currentGroup.some(e => 
                current.top < (e.top + e.height) && (current.top + current.height) > e.top
            );
            
            if (overlaps) {
                currentGroup.push(current);
            } else {
                groups.push(currentGroup);
                currentGroup = [current];
            }
        }
        groups.push(currentGroup);
        
        // Apply stacking
        groups.forEach(group => {
            if (group.length === 1) {
                group[0].element.style.left = '2px';
                group[0].element.style.right = '2px';
                group[0].element.style.width = 'auto';
                return;
            }
            
            const width = (100 / group.length) - 1;
            group.forEach((event, index) => {
                const left = (100 / group.length) * index;
                event.element.style.left = `${left}%`;
                event.element.style.width = `${width}%`;
                event.element.style.right = 'auto';
            });
        });
    });
}

/**
 * Clear the modal calendar and show empty state
 */
function clearModalCalendar() {
    const emptyState = document.getElementById('modalCalendarEmptyState');
    const weekCalendar = document.getElementById('modalWeekCalendar');
    const tableView = document.getElementById('modalTableView');
    const calendarContainer = document.getElementById('modalCalendarContainer');
    const sectionNameEl = document.getElementById('modalCalendarSectionName');
    const eventCountEl = document.getElementById('modalCalendarEventCount');
    const sectionSwitcher = document.getElementById('modalSectionSwitcher');
    const tableBody = document.getElementById('modalTableBody');
    
    cacheEmptyStateTemplate(emptyState);
    restoreEmptyStateTemplate(emptyState);
    emptyState?.classList.remove('hidden');
    
    // Hide the calendar grid and table views - reset display styles
    if (weekCalendar) weekCalendar.classList.add('hidden');
    if (tableView) {
        tableView.classList.add('hidden');
        tableView.style.display = 'none';
    }
    if (calendarContainer) {
        calendarContainer.classList.add('hidden');
        calendarContainer.style.display = 'none';
    }
    
    // Clear table body
    if (tableBody) tableBody.innerHTML = '';
    
    // Reset header info
    if (sectionNameEl) sectionNameEl.textContent = 'Select a section to view schedule';
    if (eventCountEl) eventCountEl.textContent = '0 classes';
    if (sectionSwitcher) sectionSwitcher.value = '';
    
    // Clear stored data
    window.modalCalendarData = null;
    window.modalCalendarLastSectionId = null;
    window.modalCalendarLastSectionName = '';
}

/**
 * Switch section in the modal calendar
 * Called when user selects a different section from the dropdown
 * @param {string} sectionId - The section ID to switch to
 */
function switchModalSection(sectionId) {
    if (!sectionId) {
        clearModalCalendar();
        // Show no-section overlay, hide form fields
        const overlay = document.getElementById('noSectionOverlay');
        const fieldsContainer = document.getElementById('classFormFieldsContainer');
        if (overlay) overlay.classList.remove('hidden');
        if (fieldsContainer) fieldsContainer.classList.add('hidden');
        // Hide Auto Generate button
        const autoGenBtn = document.getElementById('autoGenBtn');
        if (autoGenBtn) autoGenBtn.style.display = 'none';
        // Clear section globals and form state
        window.FORM_SECTION_ID = null;
        window.FORM_SECTION_NAME = '';
        if (typeof window.clearFormState === 'function') window.clearFormState();
        if (window.scheduleFormSyncHooks && typeof window.scheduleFormSyncHooks.onClassSectionChanged === 'function') {
            window.scheduleFormSyncHooks.onClassSectionChanged();
        }
        return;
    }
    
    // Get section name from the dropdown option
    const switcher = document.getElementById('modalSectionSwitcher');
    const selectedOption = switcher.options[switcher.selectedIndex];
    const sectionName = selectedOption.dataset.name || selectedOption.textContent.trim();
    
    // Update hidden section_id field in the form
    const sectionIdInput = document.getElementById('section_id_add');
    if (sectionIdInput) {
        sectionIdInput.value = sectionId;
    }

    // Update global section references (used by Auto Generate button etc.)
    window.FORM_SECTION_ID = parseInt(sectionId, 10);
    window.FORM_SECTION_NAME = sectionName;
    
    // Update URL so reloads preserve the current section
    try {
        const url = new URL(window.location.href);
        url.searchParams.set('section_id', sectionId);
        history.replaceState(null, '', url.toString());
    } catch(e) { /* ignore */ }
    
    // Clear saved form state when switching sections
    if (typeof window.clearFormState === 'function') window.clearFormState();
    
    // Show form fields, hide no-section overlay
    const overlay = document.getElementById('noSectionOverlay');
    const fieldsContainer = document.getElementById('classFormFieldsContainer');
    if (overlay) overlay.classList.add('hidden');
    if (fieldsContainer) fieldsContainer.classList.remove('hidden');
    // Show Auto Generate button (if on class tab)
    const autoGenBtn = document.getElementById('autoGenBtn');
    if (autoGenBtn && window.SCHEDULE_PAGE === 'class') autoGenBtn.style.display = 'flex';
    
    // Load curricula for the new section
    if (typeof window.loadCurriculaForSection === 'function') {
        window.loadCurriculaForSection(sectionId, 'add');
    }
    
    // Reset auto-check state
    if (typeof window.resetAutoCheckState === 'function') {
        window.resetAutoCheckState('add');
    }
    
    // Render the calendar for the new section
    renderModalCalendar(sectionId, sectionName);

    if (window.scheduleFormSyncHooks && typeof window.scheduleFormSyncHooks.onClassSectionChanged === 'function') {
        window.scheduleFormSyncHooks.onClassSectionChanged();
    }
}

/**
 * Load a schedule for editing from modal calendar/table click
 * @param {Object} scheduleData - Schedule data object
 */
function loadScheduleForEditing(scheduleData) {
    // Set to edit mode
    if (typeof window.setScheduleModalMode === 'function') {
        window.setScheduleModalMode('edit');
    }
    window.scheduleModalMode = 'edit';
    window.currentEditScheduleId = scheduleData.id;
    
    // Set hidden fields for edit
    const scheduleIdField = document.getElementById('schedule_id');
    const versionField = document.getElementById('schedule_version');
    if (scheduleIdField) scheduleIdField.value = scheduleData.id;
    if (versionField) versionField.value = scheduleData.version || '';
    
    // Set section_id (should already be set, but ensure it's correct)
    const sectionIdField = document.getElementById('section_id_add');
    if (sectionIdField) sectionIdField.value = scheduleData.section_id;
    
    // Reset auto-check state first
    if (typeof window.resetAutoCheckState === 'function') {
        window.resetAutoCheckState('add');
    }
    
    // Store pending edit data for loading after dropdowns populate
    window.pendingEditScheduleData = scheduleData;
    
    // Load curriculum and subject, then set values
    if (typeof window.loadCurriculaForSectionEdit === 'function') {
        window.loadCurriculaForSectionEdit(scheduleData.section_id, scheduleData, 'add');
    }
    
    // Set day, time, and room fields immediately
    const dayField = document.getElementById('day_of_week_add');
    const startTimeField = document.getElementById('start_time_add');
    const endTimeField = document.getElementById('end_time_add');
    const roomIdField = document.getElementById('room_id_add');
    const roomSearchField = document.getElementById('room_search_add');
    
    if (dayField) dayField.value = scheduleData.day_of_week || '';
    if (startTimeField) startTimeField.value = scheduleData.start_time || '';
    if (endTimeField) endTimeField.value = scheduleData.end_time || '';
    if (roomIdField) roomIdField.value = scheduleData.room_id || '';
    
    // Set room search display
    if (roomSearchField) {
        if (scheduleData.room_number && scheduleData.building_name) {
            roomSearchField.value = `${scheduleData.room_number} - ${scheduleData.building_name}`;
        } else if (scheduleData.room_number) {
            roomSearchField.value = scheduleData.room_number;
        } else {
            roomSearchField.value = '';
        }
    }
    
    // Visual feedback - highlight the clicked event/row
    highlightActiveSchedule(scheduleData.id);
}

/**
 * Highlight the currently selected schedule in calendar/table
 * @param {number} scheduleId - Schedule ID to highlight
 */
function highlightActiveSchedule(scheduleId) {
    const classDaysGrid = document.getElementById('modalDaysGrid');

    // Remove existing highlights
    classDaysGrid?.querySelectorAll('.modal-events-container .week-event.ring-2.ring-green-500').forEach(el => {
        el.classList.remove('ring-2', 'ring-green-500');
    });
    document.querySelectorAll('#modalTableBody tr.bg-green-50').forEach(el => {
        el.classList.remove('bg-green-50');
    });
    
    // Add highlight to clicked schedule
    const calendarEvent = classDaysGrid?.querySelector(`.modal-events-container .week-event[data-schedule-id="${scheduleId}"]`);
    if (calendarEvent) {
        calendarEvent.classList.add('ring-2', 'ring-green-500');
    }
    
    const tableRow = document.querySelector(`#modalTableBody tr[data-schedule-id="${scheduleId}"]`);
    if (tableRow) {
        tableRow.classList.add('bg-green-50');
    }
}

// Expose loadScheduleForEditing globally
window.loadScheduleForEditing = loadScheduleForEditing;

// ============================================================================
// EXAM MODAL CALENDAR FUNCTIONS (Similar to Schedule Modal)
// ============================================================================

// Store current exam modal view preference and data
window.examModalViewPreference = 'calendar';
window.examModalCalendarData = null;

/**
 * Switch between Table and Calendar view inside the Exam Schedule Modal
 * @param {string} viewType - 'table' or 'calendar'
 */
function switchExamModalView(viewType) {
    const tableView = document.getElementById('examModalTableView');
    const calendarContainer = document.getElementById('examModalCalendarContainer');
    const weekCalendar = document.getElementById('examModalWeekCalendar');
    const tableBtn = document.getElementById('examModalViewToggleTable');
    const calendarBtn = document.getElementById('examModalViewToggleCalendar');
    const emptyState = document.getElementById('examModalCalendarEmptyState');
    
    window.examModalViewPreference = viewType;
    
    if (viewType === 'table') {
        // Show table, hide calendar
        if (tableView) {
            tableView.classList.remove('hidden');
            tableView.style.display = 'flex';
        }
        if (calendarContainer) {
            calendarContainer.classList.add('hidden');
            calendarContainer.style.display = 'none';
        }
        
        // Update button styles
        tableBtn?.classList.add('bg-white', 'text-orange-600', 'shadow-sm');
        tableBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        calendarBtn?.classList.remove('bg-white', 'text-orange-600', 'shadow-sm');
        calendarBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Re-render table data and hide empty state if we have data
        if (window.examModalCalendarData && window.examModalCalendarData.exams) {
            emptyState?.classList.add('hidden');
            renderExamModalTableView(window.examModalCalendarData.exams);
        }
    } else {
        // Show calendar, hide table
        if (tableView) {
            tableView.classList.add('hidden');
            tableView.style.display = 'none';
        }
        if (calendarContainer) {
            calendarContainer.classList.remove('hidden');
            calendarContainer.style.display = 'flex';
        }
        
        // Update button styles
        calendarBtn?.classList.add('bg-white', 'text-orange-600', 'shadow-sm');
        calendarBtn?.classList.remove('text-gray-600', 'hover:text-gray-900');
        tableBtn?.classList.remove('bg-white', 'text-orange-600', 'shadow-sm');
        tableBtn?.classList.add('text-gray-600', 'hover:text-gray-900');
        
        // Hide empty state and show calendar grid if we have data
        if (window.examModalCalendarData && window.examModalCalendarData.exams) {
            emptyState?.classList.add('hidden');
            weekCalendar?.classList.remove('hidden');
            
            // Re-render calendar
            requestAnimationFrame(() => {
                buildExamModalCalendarGrid(window.examModalCalendarData.startHour, window.examModalCalendarData.endHour);
                renderExamModalCalendarEvents(window.examModalCalendarData.exams, window.examModalCalendarData.startHour);
                queueModalCalendarHeaderScrollbarOffsetSync('examModalCalendarBody', 'examModalWeekCalendar');
            });
        }
    }
    
    localStorage.setItem('examModalViewPreference', viewType);
}

/**
 * Switch section in the exam modal calendar
 * @param {string} sectionId - The section ID to switch to
 */
function switchExamModalSection(sectionId) {
    if (!sectionId) {
        clearExamModalCalendar();
        // Show no-section overlay, hide form fields
        const overlay = document.getElementById('noSectionOverlayExam');
        const fieldsContainer = document.getElementById('examFormFieldsContainer');
        if (overlay) overlay.classList.remove('hidden');
        if (fieldsContainer) fieldsContainer.classList.add('hidden');
        // Hide Batch Exam button
        const autoGenExamBtn = document.getElementById('autoGenExamBtn');
        if (autoGenExamBtn) autoGenExamBtn.style.display = 'none';
        // Clear section globals and form state
        window.EXAM_FORM_SECTION_ID = null;
        window.EXAM_FORM_SECTION_NAME = '';
        window.EXAM_BATCH_SECTION_ID = null;
        window.EXAM_BATCH_SECTION_NAME = '';
        if (window.scheduleFormSyncHooks && typeof window.scheduleFormSyncHooks.onExamSectionChanged === 'function') {
            window.scheduleFormSyncHooks.onExamSectionChanged();
        }
        return;
    }
    
    // Get section name from the dropdown option
    const switcher = document.getElementById('examModalSectionSwitcher');
    const selectedOption = switcher.options[switcher.selectedIndex];
    const sectionName = selectedOption.dataset.name || selectedOption.textContent.trim();
    
    // Update hidden section_id field in the form
    const sectionIdInput = document.getElementById('section_id_exam_add');
    if (sectionIdInput) {
        sectionIdInput.value = sectionId;
    }
    
    // Update global section references
    window.EXAM_FORM_SECTION_ID = parseInt(sectionId, 10);
    window.EXAM_FORM_SECTION_NAME = sectionName;
    // Also update batch globals so enterExamBatchMode() can find the section
    window.EXAM_BATCH_SECTION_ID = parseInt(sectionId, 10);
    window.EXAM_BATCH_SECTION_NAME = sectionName;
    
    // Update URL so reloads preserve the current section
    try {
        const url = new URL(window.location.href);
        url.searchParams.set('section_id', sectionId);
        history.replaceState(null, '', url.toString());
    } catch(e) { /* ignore */ }
    
    // Show form fields, hide no-section overlay
    const overlay = document.getElementById('noSectionOverlayExam');
    const fieldsContainer = document.getElementById('examFormFieldsContainer');
    if (overlay) overlay.classList.add('hidden');
    if (fieldsContainer) fieldsContainer.classList.remove('hidden');
    // Show Batch Exam button when a section is selected
    const autoGenExamBtn = document.getElementById('autoGenExamBtn');
    if (autoGenExamBtn && window.SCHEDULE_PAGE === 'exam') autoGenExamBtn.style.display = 'flex';
    
    // Load curricula for the new section
    if (typeof window.loadCurriculaForSection === 'function') {
        window.loadCurriculaForSection(sectionId, 'exam_add');
    }
    
    // Reset auto-check state for exam
    if (typeof window.resetAutoCheckExamState === 'function') {
        window.resetAutoCheckExamState('add');
    }
    
    // Render the calendar for the new section
    renderExamModalCalendar(sectionId, sectionName);

    if (window.scheduleFormSyncHooks && typeof window.scheduleFormSyncHooks.onExamSectionChanged === 'function') {
        window.scheduleFormSyncHooks.onExamSectionChanged();
    }
}

/**
 * Clear the exam modal calendar
 */
function clearExamModalCalendar() {
    const emptyState = document.getElementById('examModalCalendarEmptyState');
    const tableView = document.getElementById('examModalTableView');
    const calendarContainer = document.getElementById('examModalCalendarContainer');
    const weekCalendar = document.getElementById('examModalWeekCalendar');
    const eventCount = document.getElementById('examModalCalendarEventCount');
    const timeLabels = document.getElementById('examModalTimeLabels');
    const daysGrid = document.getElementById('examModalDaysGrid');
    
    cacheEmptyStateTemplate(emptyState);
    restoreEmptyStateTemplate(emptyState);
    emptyState?.classList.remove('hidden');
    
    // Hide views
    tableView?.classList.add('hidden');
    calendarContainer?.classList.add('hidden');
    weekCalendar?.classList.add('hidden');

    // Clear stale axis/grid DOM so empty state never shows leftover exam times.
    if (timeLabels) {
        timeLabels.innerHTML = '';
        timeLabels.style.height = '';
    }
    if (daysGrid) {
        daysGrid.innerHTML = '';
        daysGrid.style.height = '';
    }
    
    // Reset event count
    if (eventCount) eventCount.textContent = '0 exams';
    
    // Clear stored data
    window.examModalCalendarData = null;
    window.examModalLastSectionId = null;
    window.examModalLastSectionName = '';
}

/**
 * Render the exam modal calendar with exams for a section
 * @param {number} sectionId - Section ID
 * @param {string} sectionName - Section name for display
 */
function renderExamModalCalendar(sectionId, sectionName) {
    window.examModalLastSectionId = sectionId;
    window.examModalLastSectionName = sectionName;
    const emptyState = document.getElementById('examModalCalendarEmptyState');
    cacheEmptyStateTemplate(emptyState);

    if (emptyState) {
        emptyState.innerHTML = renderStateLoading('orange', 'Loading exam schedule...');
        emptyState.classList.remove('hidden');
    }

    const tableView = document.getElementById('examModalTableView');
    const calendarContainer = document.getElementById('examModalCalendarContainer');
    const weekCalendar = document.getElementById('examModalWeekCalendar');
    if (tableView) {
        tableView.classList.add('hidden');
        tableView.style.display = 'none';
    }
    if (calendarContainer) {
        calendarContainer.classList.add('hidden');
        calendarContainer.style.display = 'none';
    }
    weekCalendar?.classList.add('hidden');

    // Fetch exam schedules for this section
    fetch(`/exam-schedule/section/${sectionId}/exams`)
        .then(response => response.json())
        .then(data => {
            const exams = data.exam_schedules || [];
            const startHour = data.start_hour || 7;
            const endHour = data.end_hour || 20;
            
            // Store data for re-rendering
            window.examModalCalendarData = {
                sectionId: sectionId,
                sectionName: sectionName,
                exams: exams,
                startHour: startHour,
                endHour: endHour
            };
            
            // Update UI
            const eventCount = document.getElementById('examModalCalendarEventCount');
            
            restoreEmptyStateTemplate(emptyState);
            emptyState?.classList.add('hidden');
            if (eventCount) {
                eventCount.textContent = `${exams.length} exam${exams.length !== 1 ? 's' : ''}`;
            }
            
            // Always render table data so switching is instant
            renderExamModalTableView(exams);
            
            // Get current view preference
            const currentView = window.examModalViewPreference || localStorage.getItem('examModalViewPreference') || 'calendar';
            
            // Render based on current view preference
            if (currentView === 'table') {
                const tableView = document.getElementById('examModalTableView');
                const calendarContainer = document.getElementById('examModalCalendarContainer');
                if (tableView) {
                    tableView.classList.remove('hidden');
                    tableView.style.display = 'flex';
                }
                if (calendarContainer) {
                    calendarContainer.classList.add('hidden');
                    calendarContainer.style.display = 'none';
                }
            } else {
                const tableView = document.getElementById('examModalTableView');
                const calendarContainer = document.getElementById('examModalCalendarContainer');
                const weekCalendar = document.getElementById('examModalWeekCalendar');
                if (tableView) {
                    tableView.classList.add('hidden');
                    tableView.style.display = 'none';
                }
                if (calendarContainer) {
                    calendarContainer.classList.remove('hidden');
                    calendarContainer.style.display = 'flex';
                }
                if (weekCalendar) {
                    weekCalendar.classList.remove('hidden');
                    weekCalendar.style.display = 'flex';
                }
                buildExamModalCalendarGrid(startHour, endHour);
                renderExamModalCalendarEvents(exams, startHour);
            }
        })
        .catch(error => {
            console.error('[EXAM MODAL] Error fetching exam schedules:', error);
            showExamModalCalendarError('Failed to load exam schedule');
        });
}

function showExamModalCalendarError(message) {
    const emptyState = document.getElementById('examModalCalendarEmptyState');
    const weekCalendar = document.getElementById('examModalWeekCalendar');
    cacheEmptyStateTemplate(emptyState);

    if (emptyState) {
        emptyState.innerHTML = renderStateError('orange', message, 'retryExamModalCalendarLoad');
        emptyState.classList.remove('hidden');
    }

    weekCalendar?.classList.add('hidden');
}

function retryExamModalCalendarLoad() {
    if (!window.examModalLastSectionId) return;
    renderExamModalCalendar(window.examModalLastSectionId, window.examModalLastSectionName || '');
}

/**
 * Render the exam modal table view with exam data
 * @param {Array} exams - Array of exam schedule objects
 */
function renderExamModalTableView(exams) {
    const tableBody = document.getElementById('examModalTableBody');
    const tableView = document.getElementById('examModalTableView');
    const tableEmptyState = document.getElementById('examModalTableEmptyState');
    
    // Only populate data — do NOT force visibility toggle here.
    // Visibility is controlled by switchExamModalView() and renderExamModalCalendar().
    
    if (!tableBody) return;
    
    // Clear existing rows
    tableBody.innerHTML = '';
    
    if (!exams || exams.length === 0) {
        tableEmptyState?.classList.remove('hidden');
        return;
    }
    
    tableEmptyState?.classList.add('hidden');
    
    // Sort exams by date and then by time
    const sortedExams = [...exams].sort((a, b) => {
        const dateDiff = new Date(a.exam_date) - new Date(b.exam_date);
        if (dateDiff !== 0) return dateDiff;
        return a.start_time.localeCompare(b.start_time);
    });
    
    // Build table rows
    sortedExams.forEach((exam, index) => {
        const row = document.createElement('tr');
        row.className = 'hover:bg-orange-50/80 transition-colors duration-150 cursor-pointer group' + (index % 2 === 0 ? '' : ' bg-gray-50/30');
        row.dataset.examId = exam.id;
        
        // Format date
        const examDate = new Date(exam.exam_date);
        const dateStr = examDate.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        
        // Format time
        const startTime = formatTime12Hour(exam.start_time);
        const endTime = formatTime12Hour(exam.end_time);
        
        row.innerHTML = `
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap">
                <span class="inline-flex items-center justify-center px-2 py-0.5 rounded-md text-[10px] sm:text-xs font-bold bg-orange-100 text-orange-700 border border-orange-200">
                    ${dateStr}
                </span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 whitespace-nowrap">
                <span class="text-xs font-medium text-gray-700">${startTime}</span>
                <span class="text-[10px] text-gray-400 mx-0.5">-</span>
                <span class="text-xs font-medium text-gray-700">${endTime}</span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5">
                <div class="font-semibold text-gray-900 text-xs sm:text-sm truncate max-w-[100px] sm:max-w-[180px]" title="${exam.subject_code || ''}">
                    ${exam.subject_code || 'N/A'}
                </div>
                <div class="text-[10px] text-gray-500 truncate max-w-[100px] sm:max-w-[180px]">${exam.subject_name || ''}</div>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 hidden sm:table-cell">
                <span class="text-xs font-medium text-gray-700">${exam.room_number || 'N/A'}</span>
            </td>
            <td class="px-2.5 sm:px-3 py-2.5 hidden lg:table-cell">
                <div class="text-xs text-gray-600 truncate max-w-[120px]">${exam.faculty_name || 'N/A'}</div>
            </td>
            <td class="px-1.5 sm:px-2 py-2 hidden sm:table-cell">
                <div class="flex items-center justify-center gap-1">
                    <button class="exam-table-delete-btn p-1 rounded hover:bg-red-100 text-red-500 transition-colors" title="Delete">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                    </button>
                </div>
            </td>
        `;

        // Action button handlers (stopPropagation to prevent row click)
        const deleteBtn = row.querySelector('.exam-table-delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                if (typeof deleteExamSchedule === 'function') deleteExamSchedule(exam.id, exam.subject_code || 'Exam');
            });
        }

        // Add click handler to load exam for editing
        row.addEventListener('click', function(e) {
            // Prepare exam data for editing
            const examData = {
                id: exam.id,
                section_id: exam.section_id,
                subject_id: exam.subject_id,
                subject_code: exam.subject_code,
                curriculum_id: exam.curriculum_id,
                exam_date: exam.exam_date,
                start_time: exam.start_time,
                end_time: exam.end_time,
                faculty_id: exam.faculty_id,
                faculty_name: exam.faculty_name,
                room_id: exam.room_id,
                room_number: exam.room_number,
                building_name: exam.building_name,
                version: exam.version
            };
            
            if (typeof window.loadExamForEditing === 'function') {
                window.loadExamForEditing(examData);
            }
        });
        
        tableBody.appendChild(row);
    });
}

/**
 * Build the exam modal calendar grid structure
 * @param {number} startHour - Start hour (e.g., 7)
 * @param {number} endHour - End hour (e.g., 20)
 */
function buildExamModalCalendarGrid(startHour, endHour) {
    const timeLabels = document.getElementById('examModalTimeLabels');
    const daysGrid = document.getElementById('examModalDaysGrid');
    const calendarBody = document.getElementById('examModalCalendarBody');
    const weekCalendar = document.getElementById('examModalWeekCalendar');
    const calendarContainer = document.getElementById('examModalCalendarContainer');
    const tableView = document.getElementById('examModalTableView');
    
    // Show calendar view, hide table
    calendarContainer?.classList.remove('hidden');
    weekCalendar?.classList.remove('hidden');
    tableView?.classList.add('hidden');
    
    if (!timeLabels || !daysGrid || !calendarBody) return;    // Include extra hour when end time has :30 minutes
    const examEndMinute = window.examEndMinute || 0;
    
    // Total hours and pixels (1px per minute)
    const totalMinutes = (endHour * 60 + examEndMinute) - (startHour * 60);
    const totalGridHeight = totalMinutes;
    const axisOffset = 8;
    const totalAxisHeight = totalGridHeight + axisOffset;

    // Fill the available panel height to avoid a dead blank block under the grid.
    const availableBodyHeight = Math.max(
        0,
        Math.floor(calendarBody.clientHeight || calendarBody.getBoundingClientRect().height || 0)
    );
    const renderedAxisHeight = Math.max(totalAxisHeight, availableBodyHeight);
    const renderedGridHeight = Math.max(totalGridHeight, renderedAxisHeight - axisOffset);
    
    // Store for event positioning
    window.examModalCalendarPixelsPerMinute = 1;
    window.examModalCalendarStartHour = startHour;
    window.examModalCalendarTotalHeight = renderedGridHeight;
    
    // Build time labels using shared structure (week-time-slot) — 30-minute intervals
    let timeLabelsHTML = '';
    for (let m = startHour * 60; m < (endHour * 60 + examEndMinute); m += 30) {
        const h = Math.floor(m / 60);
        const min = m % 60;
        const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
        const ampm = h >= 12 ? 'PM' : 'AM';
        const minStr = min === 0 ? '00' : '30';
        
        timeLabelsHTML += `
            <div class="week-time-slot">
                <span class="time-label">${hr12}:${minStr}</span>
                <span class="time-period">${ampm}</span>
            </div>
        `;
    }
    
    // Final boundary label
    const finalEndTotalMins = endHour * 60 + examEndMinute;
    const finalH = Math.floor(finalEndTotalMins / 60);
    const finalMin = finalEndTotalMins % 60;
    const finalH12 = finalH > 12 ? finalH - 12 : (finalH === 0 ? 12 : finalH);
    const finalAmpm = finalH >= 12 ? 'PM' : 'AM';
    const finalMinStr = finalMin === 0 ? '00' : '30';
    
    // Keep the end boundary inside the same axis flow to avoid footer/grid misalignment.
    timeLabelsHTML += `
        <div class="week-time-slot" style="height: 0; position: relative; overflow: visible;">
            <div style="position: absolute; left: 0; right: 0; top: 0; display: flex; justify-content: flex-end; gap: 2px; padding: 0 8px 0 4px;">
                <span class="time-label">${finalH12}:${finalMinStr}</span>
                <span class="time-period">${finalAmpm}</span>
            </div>
        </div>
    `;
    timeLabels.innerHTML = timeLabelsHTML;
    timeLabels.style.position = '';
    timeLabels.style.height = `${renderedAxisHeight}px`;
    
    // Build day columns matching main calendar structure
    const days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
    let daysHTML = '';
    
    days.forEach((day) => {
        let hourLines = '';
        for (let m = 0; m < renderedGridHeight; m += 30) {
            if (m % 60 === 0) {
                hourLines += `<div class="week-hour-line" style="top: ${m + axisOffset}px;"></div>`;
            } else {
                hourLines += `<div class="week-half-hour-line" style="top: ${m + axisOffset}px;"></div>`;
            }
        }
        hourLines += `<div class="week-hour-line" style="top: ${renderedGridHeight + axisOffset}px;"></div>`;
        
        daysHTML += `
            <div class="week-day-column" data-day="${day}" style="position: relative; border-right: 1px solid #e5e7eb; min-height: ${renderedAxisHeight}px;">
                ${hourLines}
                <div class="modal-events-container week-events-container" data-day="${day}"></div>
            </div>
        `;
    }); 
    daysGrid.innerHTML = daysHTML;
    daysGrid.style.height = `${renderedAxisHeight}px`;
    
    // Make calendar body scrollable
    calendarBody.style.overflowY = 'auto';
    calendarBody.style.overflowX = 'hidden';

    queueModalCalendarHeaderScrollbarOffsetSync('examModalCalendarBody', 'examModalWeekCalendar');
}

function getExamModalEventContainers() {
    const daysGrid = document.getElementById('examModalDaysGrid');
    return daysGrid ? daysGrid.querySelectorAll('.modal-events-container') : [];
}

function getExamModalDayContainer(dayName) {
    const daysGrid = document.getElementById('examModalDaysGrid');
    return daysGrid ? daysGrid.querySelector(`.modal-events-container[data-day="${dayName}"]`) : null;
}

/**
 * Render exam events on the calendar grid
 * @param {Array} exams - Array of exam schedule objects
 * @param {number} startHour - Start hour for positioning
 */
function renderExamModalCalendarEvents(exams, startHour) {
    // Clear existing events
    getExamModalEventContainers().forEach(container => {
        container.innerHTML = '';
    });
    
    if (!exams || exams.length === 0) return;
    
    const pixelsPerMinute = window.examModalCalendarPixelsPerMinute || 1;
    const startMinutes = startHour * 60;
    
    // Group events by day for overlap detection
    const eventsByDay = {};
    
    exams.forEach(exam => {
        const examDate = new Date(exam.exam_date);
        if (Number.isNaN(examDate.getTime())) return;
        const dayIndex = examDate.getDay();
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
        const dayOfWeek = days[dayIndex];
        
        if (!eventsByDay[dayOfWeek]) eventsByDay[dayOfWeek] = [];
        
        const [startH, startM] = exam.start_time.split(':').map(Number);
        const [endH, endM] = exam.end_time.split(':').map(Number);
        const dateStr = examDate.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        
        eventsByDay[dayOfWeek].push({
            exam, dayOfWeek, startH, startM, endH, endM, dateStr,
            startTotal: startH * 60 + startM,
            endTotal: endH * 60 + endM
        });
    });
    
    // Render events per day with overlap handling
    Object.keys(eventsByDay).forEach(dayOfWeek => {
        const container = getExamModalDayContainer(dayOfWeek);
        if (!container) return;
        
        const dayEvents = eventsByDay[dayOfWeek];
        
        // Detect overlaps
        const sorted = [...dayEvents].sort((a, b) => a.startTotal - b.startTotal);
        const groups = [];
        let currentGroup = [sorted[0]];
        
        for (let i = 1; i < sorted.length; i++) {
            const prev = currentGroup[currentGroup.length - 1];
            if (sorted[i].startTotal < prev.endTotal) {
                currentGroup.push(sorted[i]);
            } else {
                groups.push(currentGroup);
                currentGroup = [sorted[i]];
            }
        }
        groups.push(currentGroup);
        
        const overlapMap = new Map();
        groups.forEach(g => {
            g.forEach((ev, idx) => {
                overlapMap.set(ev, { index: idx, total: g.length });
            });
        });
        
        dayEvents.forEach(ev => {
            const eventStartMinutes = ev.startH * 60 + ev.startM;
            const topOffset = ((eventStartMinutes - startMinutes) * pixelsPerMinute) + 8;
            const height = Math.max((ev.endTotal - ev.startTotal) * pixelsPerMinute, 20);
            
            const eventEl = document.createElement('div');
            eventEl.className = 'week-event event-exam';
            eventEl.style.top = `${topOffset}px`;
            eventEl.style.height = `${height}px`;
            eventEl.style.cursor = 'pointer';
            eventEl.dataset.examId = ev.exam.id;
            
            // Overlap stacking
            const group = overlapMap.get(ev);
            if (group && group.total > 1) {
                const w = 100 / group.total;
                eventEl.style.left = (w * group.index) + '%';
                eventEl.style.right = (100 - w * (group.index + 1)) + '%';
            }
            
            // Format times
            const stFmt = _examModalFmtTime12(ev.startH, ev.startM);
            const etFmt = _examModalFmtTime12(ev.endH, ev.endM);
            
            // Tooltip
            eventEl.title = `${ev.exam.subject_code || 'Exam'} - ${ev.exam.subject_name || ''}\nDate: ${ev.dateStr}\nProctor: ${ev.exam.faculty_name || 'TBA'}\nRoom: ${ev.exam.room_number || 'TBA'}\nTime: ${stFmt} - ${etFmt}`;
            
            // Content using shared CSS — progressive detail at thresholds matching class modal (45/60/75)
            eventEl.innerHTML = `
                <div class="event-content">
                    <div class="event-subject">${ev.exam.subject_code || 'Exam'}</div>
                    ${height >= 45 ? `<div class="event-room">${ev.exam.room_number || 'TBA'}</div>` : ''}
                    ${height >= 60 ? `<div class="event-faculty">${ev.exam.faculty_name || 'TBA'}</div>` : ''}
                    ${height >= 75 ? `<div class="event-time">${stFmt} - ${etFmt}</div>` : ''}
                </div>
                <div class="event-type-badge">${ev.dateStr}</div>
                <button class="calendar-event-delete-btn" title="Delete">
                    <svg width="12" height="12" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
                </button>
            `;

            // Delete button click handler
            const delBtn = eventEl.querySelector('.calendar-event-delete-btn');
            if (delBtn) {
                delBtn.addEventListener('click', function(e) {
                    e.stopPropagation();
                    if (typeof deleteExamSchedule === 'function') deleteExamSchedule(ev.exam.id, ev.exam.subject_code || 'Exam');
                });
            }

            // Click handler
            eventEl.addEventListener('click', function(e) {
                e.stopPropagation();
                const examData = {
                    id: ev.exam.id,
                    section_id: ev.exam.section_id,
                    subject_id: ev.exam.subject_id,
                    subject_code: ev.exam.subject_code,
                    curriculum_id: ev.exam.curriculum_id,
                    exam_date: ev.exam.exam_date,
                    start_time: ev.exam.start_time,
                    end_time: ev.exam.end_time,
                    faculty_id: ev.exam.faculty_id,
                    faculty_name: ev.exam.faculty_name,
                    room_id: ev.exam.room_id,
                    room_number: ev.exam.room_number,
                    building_name: ev.exam.building_name,
                    version: ev.exam.version
                };
                if (typeof window.loadExamForEditing === 'function') {
                    window.loadExamForEditing(examData);
                }
            });
            
            container.appendChild(eventEl);
        });
    });
}

function _examModalFmtTime12(h, m) {
    const hr12 = h > 12 ? h - 12 : (h === 0 ? 12 : h);
    const ampm = h >= 12 ? 'PM' : 'AM';
    return hr12 + ':' + String(m).padStart(2, '0') + ' ' + ampm;
}

// Expose exam modal functions globally
window.switchExamModalView = switchExamModalView;
window.switchExamModalSection = switchExamModalSection;
window.clearExamModalCalendar = clearExamModalCalendar;
window.renderExamModalCalendar = renderExamModalCalendar;

