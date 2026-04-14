// ============================================================================
// Scroll State Management - Save scroll position for left panels
// ============================================================================

// CRITICAL FIX: Move all modals to body level on page load to prevent stacking context issues
document.addEventListener('DOMContentLoaded', function() {
    const modalIds = [
        'addScheduleModal',
        'editScheduleModal', 
        'addExamScheduleModal',
        'editExamScheduleModal'
    ];
    
    modalIds.forEach(modalId => {
        const modal = document.getElementById(modalId);
        if (modal && modal.parentElement !== document.body) {
            document.body.appendChild(modal);
        }
    });
});

/**
 * Toggle export dropdown menu
 * @param {string} dropdownId - ID of the dropdown element to toggle
 */
function toggleExportDropdown(dropdownId) {
    const dropdown = document.getElementById(dropdownId);
    if (dropdown) {
        dropdown.classList.toggle('hidden');
    }
    
    // Close dropdown when clicking outside
    if (!dropdown.classList.contains('hidden')) {
        const closeDropdown = (e) => {
            if (!e.target.closest(`#${dropdownId}`) && !e.target.closest('button[onclick*="toggleExportDropdown"]')) {
                dropdown.classList.add('hidden');
                document.removeEventListener('click', closeDropdown);
            }
        };
        setTimeout(() => document.addEventListener('click', closeDropdown), 0);
    }
}

/**
 * Save scroll position for a specific list
 * @param {string} listId - ID of the scrollable list element
 * @param {string} storageKey - localStorage key to store position
 */
function saveScrollPosition(listId, storageKey) {
    const listElement = document.getElementById(listId);
    if (listElement) {
        const scrollPos = listElement.scrollTop;
        localStorage.setItem(storageKey, scrollPos.toString());
    }
}

/**
 * Restore scroll position for a specific list
 * @param {string} listId - ID of the scrollable list element
 * @param {string} storageKey - localStorage key to retrieve position
 */
function restoreScrollPosition(listId, storageKey) {
    const listElement = document.getElementById(listId);
    if (listElement) {
        const savedScroll = localStorage.getItem(storageKey);
        if (savedScroll !== null) {
            listElement.scrollTop = parseInt(savedScroll, 10);
        }
    }
}

/**
 * Initialize scroll state listeners for all left panels
 */
function initScrollStateManagement() {
    // Section List (Class Schedules)
    const sectionList = document.getElementById('sectionList');
    if (sectionList) {
        sectionList.addEventListener('scroll', function() {
            saveScrollPosition('sectionList', 'scheduleScrollPos_sectionList');
        });
    }
    
    // Faculty List
    const facultyList = document.getElementById('facultyList');
    if (facultyList) {
        facultyList.addEventListener('scroll', function() {
            saveScrollPosition('facultyList', 'scheduleScrollPos_facultyList');
        });
    }
    
    // Room List
    const roomList = document.getElementById('roomList');
    if (roomList) {
        roomList.addEventListener('scroll', function() {
            saveScrollPosition('roomList', 'scheduleScrollPos_roomList');
        });
    }
    
    // Exam Section List
    const examSectionList = document.getElementById('examSectionList');
    if (examSectionList) {
        examSectionList.addEventListener('scroll', function() {
            saveScrollPosition('examSectionList', 'scheduleScrollPos_examSectionList');
        });
    }
}

function syncWeekCalendarHeaderAlignment() {
    document.querySelectorAll('.week-calendar-container').forEach(container => {
        const calendarBody = container.querySelector('.week-calendar-body');
        if (!calendarBody) {
            return;
        }

        const scrollbarOffset = Math.max(0, calendarBody.offsetWidth - calendarBody.clientWidth);
        container.style.setProperty('--week-calendar-scrollbar-offset', `${scrollbarOffset}px`);
    });
}

function queueWeekCalendarHeaderAlignmentSync() {
    if (typeof window.requestAnimationFrame === 'function') {
        window.requestAnimationFrame(syncWeekCalendarHeaderAlignment);
        return;
    }

    setTimeout(syncWeekCalendarHeaderAlignment, 0);
}

// ============================================================================
// Schedule View Switching Function (Table vs Calendar)
// ============================================================================
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
        
        // Initialize week calendar (overlap detection, current-day highlighting)
        if (typeof initializeWeekCalendar === 'function') initializeWeekCalendar();
    }
    
    // Store preference in localStorage
    localStorage.setItem('scheduleViewPreference', viewType);
}

function applySavedViewForTab(tabName) {
    const viewPreference = localStorage.getItem('scheduleViewPreference') || 'table';

    if (tabName === 'class' && typeof switchScheduleView === 'function') {
        switchScheduleView(viewPreference);
    } else if (tabName === 'faculty' && typeof switchFacultyView === 'function') {
        switchFacultyView(viewPreference);
    } else if (tabName === 'room' && typeof switchRoomView === 'function') {
        switchRoomView(viewPreference);
    } else if (tabName === 'exam' && typeof switchExamView === 'function') {
        switchExamView(viewPreference);
    }

    if (typeof syncScheduleViewportState === 'function') {
        syncScheduleViewportState();
    }

    queueWeekCalendarHeaderAlignmentSync();
}

// Tab Switching Function
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Deactivate all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const contentId = 'content-' + tabName;
    const selectedContent = document.getElementById(contentId);
    
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Activate selected tab button
    const buttonId = 'tab-' + tabName;
    const selectedButton = document.getElementById(buttonId);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
    
    // Store active tab in localStorage
    localStorage.setItem('activeScheduleTab', tabName);

    // Re-apply saved view mode and responsive master/detail state for the active tab.
    applySavedViewForTab(tabName);
}

// Window export
window.switchTab = switchTab;


// Restore active tab on page load
document.addEventListener('DOMContentLoaded', function() {
    // On standalone pages (faculty, room, exam), force-activate the correct tab
    if (window.SCHEDULE_PAGE && window.SCHEDULE_PAGE !== 'class') {
        // Standalone page — just ensure the right tab content is active
        const pageName = window.SCHEDULE_PAGE;
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        const targetContent = document.getElementById('content-' + pageName);
        if (targetContent) {
            targetContent.classList.add('active');
        }
    } else {
        // Combined schedule page or class standalone — use URL params / localStorage
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        const urlParams = new URLSearchParams(window.location.search);
        let activeTab = 'class'; // Default to class tab
        
        if (urlParams.has('section_id')) {
            activeTab = 'class';
        } else if (urlParams.has('faculty_id')) {
            activeTab = 'faculty';
        } else if (urlParams.has('room_id')) {
            activeTab = 'room';
        } else if (urlParams.has('exam_section_id')) {
            activeTab = 'exam';
        } else {
            activeTab = localStorage.getItem('activeScheduleTab') || 'class';
        }
        
        switchTab(activeTab);
    }
    
    // Restore schedule view preference (table or calendar)
    const viewPreference = localStorage.getItem('scheduleViewPreference') || 'table';
    if (typeof switchScheduleView === 'function') switchScheduleView(viewPreference);
    if (typeof switchExamView === 'function') switchExamView(viewPreference);
    if (typeof switchFacultyView === 'function') switchFacultyView(viewPreference);
    if (typeof switchRoomView === 'function') switchRoomView(viewPreference);

    queueWeekCalendarHeaderAlignmentSync();
    
    // Initialize scroll state management
    initScrollStateManagement();
    
    // Restore scroll positions for all left panels
    restoreScrollPosition('sectionList', 'scheduleScrollPos_sectionList');
    restoreScrollPosition('facultyList', 'scheduleScrollPos_facultyList');
    restoreScrollPosition('roomList', 'scheduleScrollPos_roomList');
    restoreScrollPosition('examSectionList', 'scheduleScrollPos_examSectionList');
});

// Toast Notification System
function showToast(message, type = 'success') {
    if (window.__iswToastManager && typeof window.__iswToastManager.show === 'function') {
        return window.__iswToastManager.show(message, type);
    }
}

// NOTE: Flash message toast initialization is handled in schedule.html
// Do not duplicate DOMContentLoaded listener here to avoid showing toasts multiple times
// NOTE: Flash message toast initialization is handled in schedule.html
// Do not duplicate DOMContentLoaded listener here to avoid showing toasts multiple times

// Section Selection Function
function selectSection(id, name) {
    // Save scroll position before navigation
    saveScrollPosition('sectionList', 'scheduleScrollPos_sectionList');
    
    // Update URL without page refresh
    const url = new URL(window.location.href);
    url.searchParams.set('section_id', id);
    window.history.pushState({}, '', url);
    if (typeof window.syncScheduleHeaderActions === 'function') {
        window.syncScheduleHeaderActions();
    }
    
    // Show detail view on mobile
    if (typeof showClassDetail === 'function') {
        showClassDetail();
    }
    
    // Update UI: highlight selected item
    document.querySelectorAll('.section-list-item').forEach(item => {
        item.classList.remove('selected');
    });
    // Find and highlight the clicked item by matching the onclick content with exact ID
    const sectionItems = document.querySelectorAll('.section-list-item');
    sectionItems.forEach(item => {
        const onclick = item.getAttribute('onclick');
        // Use regex to match exact ID (not partial match like ID 1 matching 10, 11, etc.)
        if (onclick && onclick.match(new RegExp(`selectSection\\(${id}\\s*,`))) {
            item.classList.add('selected');
        }
    });
    
    // Show loading state
    const rightPanel = document.querySelector('#content-class #class-detail');
    let contentArea = null; // Declare outside to be accessible in catch block
    
    if (rightPanel) {
        // Find the content area (the scrollable div after the header)
        contentArea = rightPanel.querySelector('.flex-1.overflow-y-auto');
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p class="text-gray-600">Loading schedules...</p>
                    </div>
                </div>
            `;
        }
    }
    
    // Fetch schedules for selected section via AJAX
    fetch(`/schedule/class?section_id=${id}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        // Parse the response and extract the schedule content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the right panel content from the response
        const newRightPanel = doc.querySelector('#content-class #class-detail');
        if (newRightPanel && rightPanel) {
            rightPanel.innerHTML = newRightPanel.innerHTML;
            applySavedViewForTab('class');
        }
    })
    .catch(error => {
        console.error('Error loading schedules:', error);
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center text-red-600">
                        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p>Error loading schedules. Please try again.</p>
                    </div>
                </div>
            `;
        }
    });
}

// Filter by Program Function
function filterByDepartment(departmentId) {
    const url = new URL(window.location.href);
    if (departmentId) {
        url.searchParams.set('program_id', departmentId);
    } else {
        url.searchParams.delete('program_id');
    }
    window.history.replaceState({}, '', url);
    
    const yearLevelFilter = document.getElementById('yearLevelFilter');
    const yearLevel = yearLevelFilter ? yearLevelFilter.value : '';
    
    // Handle program groups
    const programGroups = document.querySelectorAll('#sectionList .program-group');
    const sectionItems = document.querySelectorAll('#sectionList .section-list-item');
    let visibleCount = 0;
    
    // First, filter program groups by program
    programGroups.forEach(group => {
        const groupDeptId = group.getAttribute('data-program-id');
        const deptMatch = departmentId === '' || departmentId === groupDeptId;
        
        if (deptMatch) {
            group.style.display = '';
        } else {
            group.style.display = 'none';
        }
    });
    
    // Then, filter individual sections within visible groups
    sectionItems.forEach(item => {
        const itemDeptId = item.getAttribute('data-program-id');
        const itemYearLevel = item.getAttribute('data-year-level') || '';
        
        // Check program filter
        const deptMatch = departmentId === '' || departmentId === itemDeptId;
        
        // Check year level filter
        const yearLevelFilterMatch = yearLevel === '' || itemYearLevel === yearLevel;
        
        // Show only if both filters match
        const shouldShow = deptMatch && yearLevelFilterMatch;
        
        if (shouldShow) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Hide program groups that have no visible sections
    programGroups.forEach(group => {
        const visibleSections = group.querySelectorAll('.section-list-item:not([style*="display: none"])');
        if (visibleSections.length === 0) {
            group.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('section-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Filter Exam by Program Function
function filterExamByDepartment(departmentId) {
    const url = new URL(window.location.href);
    if (departmentId) {
        url.searchParams.set('exam_department_id', departmentId);
    } else {
        url.searchParams.delete('exam_department_id');
    }
    window.history.replaceState({}, '', url);
    
    const yearLevelFilter = document.getElementById('examYearLevelFilter');
    const yearLevel = yearLevelFilter ? yearLevelFilter.value : '';
    
    // Handle program groups
    const programGroups = document.querySelectorAll('#examSectionList .program-group');
    const sectionItems = document.querySelectorAll('#examSectionList .section-list-item');
    let visibleCount = 0;
    
    // First, filter program groups by program
    programGroups.forEach(group => {
        const groupDeptId = group.getAttribute('data-program-id');
        const deptMatch = departmentId === '' || departmentId === groupDeptId;
        
        if (deptMatch) {
            group.style.display = '';
        } else {
            group.style.display = 'none';
        }
    });
    
    // Then, filter individual sections within visible groups
    sectionItems.forEach(item => {
        const itemDeptId = item.getAttribute('data-program-id');
        const itemYearLevel = item.getAttribute('data-year-level') || '';
        
        // Check program filter
        const deptMatch = departmentId === '' || departmentId === itemDeptId;
        
        // Check year level filter
        const yearLevelFilterMatch = yearLevel === '' || itemYearLevel === yearLevel;
        
        // Show only if both filters match
        const shouldShow = deptMatch && yearLevelFilterMatch;
        
        if (shouldShow) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Hide program groups that have no visible sections
    programGroups.forEach(group => {
        const visibleSections = group.querySelectorAll('.section-list-item:not([style*="display: none"])');
        if (visibleSections.length === 0) {
            group.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('exam-section-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Filter by Year Level Function (for Class tab)
function filterByYearLevel(yearLevel) {
    const url = new URL(window.location.href);
    if (yearLevel) {
        url.searchParams.set('year_level', yearLevel);
    } else {
        url.searchParams.delete('year_level');
    }
    window.history.replaceState({}, '', url);
    
    const departmentFilter = document.getElementById('departmentFilter');
    const departmentId = departmentFilter ? departmentFilter.value : '';
    
    // Handle program groups and sections
    const programGroups = document.querySelectorAll('#sectionList .program-group');
    const sectionItems = document.querySelectorAll('#sectionList .section-list-item');
    let visibleCount = 0;
    
    // First, show all program groups (they'll be hidden later if empty)
    programGroups.forEach(group => {
        const groupDeptId = group.getAttribute('data-program-id');
        const deptMatch = departmentId === '' || departmentId === groupDeptId;
        group.style.display = deptMatch ? '' : 'none';
    });
    
    // Filter individual sections
    sectionItems.forEach(item => {
        const itemDeptId = item.getAttribute('data-program-id');
        const itemYearLevel = item.getAttribute('data-year-level') || '';
        
        // Check program filter
        const deptMatch = departmentId === '' || departmentId === itemDeptId;
        
        // Check year level filter
        const yearLevelFilterMatch = yearLevel === '' || itemYearLevel === yearLevel;
        
        // Show only if both filters match
        const shouldShow = deptMatch && yearLevelFilterMatch;
        
        if (shouldShow) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Hide program groups that have no visible sections
    programGroups.forEach(group => {
        const visibleSections = group.querySelectorAll('.section-list-item:not([style*="display: none"])');
        if (visibleSections.length === 0) {
            group.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('section-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Filter by Year Level Function (for Exam tab)
function filterExamByYearLevel(yearLevel) {
    const url = new URL(window.location.href);
    if (yearLevel) {
        url.searchParams.set('exam_year_level', yearLevel);
    } else {
        url.searchParams.delete('exam_year_level');
    }
    window.history.replaceState({}, '', url);
    
    const departmentFilter = document.getElementById('examDepartmentFilter');
    const departmentId = departmentFilter ? departmentFilter.value : '';
    
    // Handle program groups and sections
    const programGroups = document.querySelectorAll('#examSectionList .program-group');
    const sectionItems = document.querySelectorAll('#examSectionList .section-list-item');
    let visibleCount = 0;
    
    // First, show all program groups (they'll be hidden later if empty)
    programGroups.forEach(group => {
        const groupDeptId = group.getAttribute('data-program-id');
        const deptMatch = departmentId === '' || departmentId === groupDeptId;
        group.style.display = deptMatch ? '' : 'none';
    });
    
    // Filter individual sections
    sectionItems.forEach(item => {
        const itemDeptId = item.getAttribute('data-program-id');
        const itemYearLevel = item.getAttribute('data-year-level') || '';
        
        // Check program filter
        const deptMatch = departmentId === '' || departmentId === itemDeptId;
        
        // Check year level filter
        const yearLevelFilterMatch = yearLevel === '' || itemYearLevel === yearLevel;
        
        // Show only if both filters match
        const shouldShow = deptMatch && yearLevelFilterMatch;
        
        if (shouldShow) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Hide program groups that have no visible sections
    programGroups.forEach(group => {
        const visibleSections = group.querySelectorAll('.section-list-item:not([style*="display: none"])');
        if (visibleSections.length === 0) {
            group.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('exam-section-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Search Faculty by Name
function searchFaculty(searchTerm) {
    const facultyItems = document.querySelectorAll('#facultyList .faculty-list-item');
    const facultyGroups = document.querySelectorAll('#facultyList .faculty-group');
    const searchLower = searchTerm.toLowerCase().trim();
    let visibleCount = 0;
    
    facultyItems.forEach(item => {
        // Use data attribute for search or fall back to text content
        const facultyName = item.dataset.facultyName || item.querySelector('.text-sm.font-semibold')?.textContent.toLowerCase() || '';
        
        if (searchLower === '' || facultyName.includes(searchLower)) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Show/hide program groups based on visible items
    facultyGroups.forEach(group => {
        const visibleItems = group.querySelectorAll('.faculty-list-item:not([style*="display: none"])');
        if (visibleItems.length === 0 && searchLower !== '') {
            group.style.display = 'none';
        } else {
            group.style.display = '';
        }
    });
    
    // Update the count badge
    const badge = document.getElementById('faculty-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Search Room by Number or Building
function searchRoom(searchTerm) {
    const roomItems = document.querySelectorAll('#roomList .room-list-item');
    const roomGroups = document.querySelectorAll('#roomList .room-group');
    const searchLower = searchTerm.toLowerCase().trim();
    let visibleCount = 0;
    
    roomItems.forEach(item => {
        // Use data attribute for search or fall back to text content
        const roomName = item.dataset.roomName || item.querySelector('.text-sm.font-semibold')?.textContent.toLowerCase() || '';
        
        if (searchLower === '' || roomName.includes(searchLower)) {
            item.style.display = '';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    // Show/hide building groups based on visible items
    roomGroups.forEach(group => {
        const visibleItems = group.querySelectorAll('.room-list-item:not([style*="display: none"])');
        if (visibleItems.length === 0 && searchLower !== '') {
            group.style.display = 'none';
        } else {
            group.style.display = '';
        }
    });
    
    // Update the count badge
    const badge = document.getElementById('room-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// ============================================================================
// Room Search and Select for Modals
// ============================================================================

function showRoomDropdownModal(mode) {
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    if (dropdown) {
        dropdown.classList.remove('hidden');
    }
    
    // Close dropdown when clicking outside
    document.addEventListener('click', function closeDropdown(e) {
        const searchInput = document.getElementById(`room_search_${mode}`);
        const dropdown = document.getElementById(`room_dropdown_${mode}`);
        if (dropdown && searchInput && !dropdown.contains(e.target) && e.target !== searchInput) {
            dropdown.classList.add('hidden');
            document.removeEventListener('click', closeDropdown);
        }
    });
}

function filterRoomsModal(mode, searchTerm) {
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    const options = dropdown.querySelectorAll('.room-option');
    const searchLower = searchTerm.toLowerCase().trim();
    
    if (!dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
    }
    
    let visibleCount = 0;
    options.forEach(option => {
        const roomNumber = option.dataset.roomNumber.toLowerCase();
        const building = option.dataset.building.toLowerCase();
        
        if (searchLower === '' || roomNumber.includes(searchLower) || building.includes(searchLower)) {
            option.style.display = '';
            visibleCount++;
        } else {
            option.style.display = 'none';
        }
    });
    
    // Show "No results" message if no rooms match
    if (visibleCount === 0 && !dropdown.querySelector('.no-results-message')) {
        const noResults = document.createElement('div');
        noResults.className = 'no-results-message px-3 py-4 text-center text-xs sm:text-sm text-gray-500';
        noResults.textContent = 'No rooms found';
        dropdown.appendChild(noResults);
    } else if (visibleCount > 0) {
        const noResults = dropdown.querySelector('.no-results-message');
        if (noResults) {
            noResults.remove();
        }
    }
}

function selectRoomModal(mode, roomId, roomNumber, building) {
    const searchInput = document.getElementById(`room_search_${mode}`);
    const hiddenInput = document.getElementById(`room_id_${mode}`);
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    
    // Update the display text
    searchInput.value = building ? `${roomNumber} - ${building}` : roomNumber;
    
    // Update the hidden input value
    hiddenInput.value = roomId;
    
    // Hide dropdown
    dropdown.classList.add('hidden');
    
    // Trigger auto-check if available
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

/**
 * Check if a subject is PE (Physical Education) based on code and description.
 * Mirrors Python _is_pe_subject() logic in auto_scheduler.py.
 */
function _isPeSubject(code, description) {
    if (!code && !description) return false;
    const c = (code || '').trim();
    const d = (description || '').trim().toLowerCase();
    // Match PE codes: pe1, pe 2, pe, pathfit, p.e.
    if (/^pe[\d\s]|^pe$/i.test(c) || /^pathfit|^p\.e\./i.test(c)) return true;
    // Match PE keywords in description
    return ['physical education', 'sports', 'fitness'].some(kw => d.includes(kw));
}

/**
 * Keep room options visible regardless of subject type or schedule type.
 * This function is intentionally a compatibility no-op for existing call sites.
 * @param {string} dropdownId - The ID of the room dropdown container
 * @param {boolean} isPe - Whether the current subject is PE
 * @param {string} [scheduleType] - 'lecture', 'lab', 'both', or '' (no filter)
 */
function _filterRoomsBySubjectType(dropdownId, isPe, scheduleType) {
    const dropdown = document.getElementById(dropdownId);
    if (!dropdown) return;
    const options = dropdown.querySelectorAll('.room-option');
    options.forEach(option => {
        delete option.dataset.peHidden;
        delete option.dataset.typeHidden;
        option.style.display = '';
        option.classList.remove('hidden');
    });
}

/**
 * Suggest rooms based on subject type and availability
 * @param {string} mode - 'add' or 'edit'
 */
function suggestRooms(mode) {
    const subjectId = document.getElementById(`subject_id_${mode}`).value;
    const dayOfWeek = document.getElementById(`day_of_week_${mode}`).value;
    const startTime = document.getElementById(`start_time_${mode}`).value;
    const endTime = document.getElementById(`end_time_${mode}`).value;
    const scheduleId = mode === 'edit'
        ? (document.getElementById('schedule_id_edit')?.value || document.getElementById('schedule_id')?.value || null)
        : null;
    
    if (!subjectId || !dayOfWeek || !startTime || !endTime) {
        showToast('Please select Subject, Day, Start Time, and End Time first.', 'warning');
        return;
    }
    
    const button = document.querySelector(`button[onclick="suggestRooms('${mode}')"]`);
    const originalText = button.innerHTML;
    button.innerHTML = '<svg class="animate-spin h-3 w-3 mr-1" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Suggesting...';
    button.disabled = true;
    
    fetch('/schedule/suggest-rooms', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('input[name="csrf_token"]').value
        },
        body: JSON.stringify({
            subject_id: subjectId,
            day: dayOfWeek,
            start_time: startTime,
            end_time: endTime,
            schedule_id: scheduleId ? parseInt(scheduleId, 10) : null
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.suggestions && data.suggestions.length > 0) {
            const dropdown = document.getElementById(`room_dropdown_${mode}`);
            const options = Array.from(dropdown.querySelectorAll('.room-option'));
            
            // Reset all options
            options.forEach(opt => {
                opt.style.display = '';
                opt.classList.remove('bg-green-50', 'border-green-200');
                const badge = opt.querySelector('.suggestion-badge');
                if (badge) badge.remove();
            });
            
            // Highlight suggestions and move to top
            const suggestedIds = data.suggestions.map(s => s.room_id);
            const suggestionMap = {};
            data.suggestions.forEach(s => suggestionMap[s.room_id] = s);
            
            // Create a fragment to reorder
            const fragment = document.createDocumentFragment();
            const suggestedElements = [];
            const otherElements = [];
            
            options.forEach(opt => {
                const roomId = parseInt(opt.dataset.roomId);
                if (suggestedIds.includes(roomId)) {
                    opt.classList.add('bg-green-50', 'border-green-200');
                    
                    // Add badge if not exists
                    if (!opt.querySelector('.suggestion-badge')) {
                        const badge = document.createElement('span');
                        badge.className = 'suggestion-badge ml-2 text-[10px] bg-green-100 text-green-800 px-1.5 py-0.5 rounded-full font-medium';
                        badge.textContent = `Score: ${suggestionMap[roomId].score}`;
                        opt.querySelector('.font-semibold').appendChild(badge);
                    }
                    
                    suggestedElements.push({ el: opt, score: suggestionMap[roomId].score });
                } else {
                    otherElements.push(opt);
                }
            });
            
            // Sort suggested by score desc
            suggestedElements.sort((a, b) => b.score - a.score);
            
            suggestedElements.forEach(item => fragment.appendChild(item.el));
            otherElements.forEach(el => fragment.appendChild(el));
            
            dropdown.innerHTML = '';
            dropdown.appendChild(fragment);
            
            // Clear search and show dropdown
            document.getElementById(`room_search_${mode}`).value = '';
            dropdown.classList.remove('hidden');
            document.getElementById(`room_search_${mode}`).focus();
            
        } else {
            showToast('No suitable rooms found for this time slot.', 'warning');
        }
    })
    .catch(error => {
        console.error('Error fetching suggestions:', error);
        showToast('Failed to get suggestions. Please try again.', 'error');
    })
    .finally(() => {
        button.innerHTML = originalText;
        button.disabled = false;
    });
}

// ============================================================================
// Faculty and Room Search for Exam Modals
// ============================================================================

function showFacultyDropdownModalExam(mode) {
    const dropdown = document.getElementById(`faculty_dropdown_${mode}`);
    if (dropdown) {
        dropdown.classList.remove('hidden');
        // Add outside click listener
        setTimeout(() => {
            document.addEventListener('click', function closeFacultyDropdown(e) {
                const searchInput = document.getElementById(`faculty_search_${mode}`);
                if (dropdown && !dropdown.contains(e.target) && e.target !== searchInput) {
                    dropdown.classList.add('hidden');
                    document.removeEventListener('click', closeFacultyDropdown);
                }
            });
        }, 100);
    }
}

function filterFacultyModalExam(mode, searchTerm) {
    const dropdown = document.getElementById(`faculty_dropdown_${mode}`);
    if (!dropdown) return;
    
    const options = dropdown.querySelectorAll('.faculty-option');
    const lowerSearch = searchTerm.toLowerCase();
    let visibleCount = 0;
    
    options.forEach(option => {
        const facultyName = option.dataset.facultyName.toLowerCase();
        if (facultyName.includes(lowerSearch)) {
            option.classList.remove('hidden');
            visibleCount++;
        } else {
            option.classList.add('hidden');
        }
    });
    
    // Show "no results" message if needed
    let noResultsMsg = dropdown.querySelector('.no-results-message');
    if (visibleCount === 0) {
        if (!noResultsMsg) {
            noResultsMsg = document.createElement('div');
            noResultsMsg.className = 'no-results-message px-3 py-4 text-center text-xs text-gray-500';
            noResultsMsg.textContent = 'No faculty found';
            dropdown.appendChild(noResultsMsg);
        }
    } else if (noResultsMsg) {
        noResultsMsg.remove();
    }
}

function selectFacultyModalExam(mode, facultyId, facultyName) {
    const searchField = document.getElementById(`faculty_search_${mode}`);
    const idField = document.getElementById(`faculty_id_${mode}`);
    const dropdown = document.getElementById(`faculty_dropdown_${mode}`);
    if (searchField) searchField.value = facultyName;
    if (idField) {
        idField.value = facultyId;
    }
    if (dropdown) dropdown.classList.add('hidden');
    
    // Check proctor availability when selecting faculty
    const modeClean = mode.replace('exam_', '');
    if (typeof checkSelectedProctorAvailability === 'function') {
        checkSelectedProctorAvailability(facultyId, modeClean);
    }
    
    // Trigger auto-check for exam conflicts with a small delay to ensure value is set
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        // Use setTimeout to ensure the DOM is updated before validation
        setTimeout(() => {
            scheduleAutoExamConflictCheck(modeClean);
        }, 50); // 50ms delay
    } else {
        console.warn('[SELECT FACULTY EXAM] scheduleAutoExamConflictCheck function not found!');
    }
}

function showRoomDropdownModalExam(mode) {
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    if (dropdown) {
        dropdown.classList.remove('hidden');
        // Add outside click listener
        setTimeout(() => {
            document.addEventListener('click', function closeRoomDropdown(e) {
                const searchInput = document.getElementById(`room_search_${mode}`);
                if (dropdown && !dropdown.contains(e.target) && e.target !== searchInput) {
                    dropdown.classList.add('hidden');
                    document.removeEventListener('click', closeRoomDropdown);
                }
            });
        }, 100);
    }
}

function filterRoomsModalExam(mode, searchTerm) {
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    if (!dropdown) return;
    
    const options = dropdown.querySelectorAll('.room-option');
    const lowerSearch = searchTerm.toLowerCase();
    let visibleCount = 0;
    
    options.forEach(option => {
        const roomNumber = option.dataset.roomNumber.toLowerCase();
        const building = option.dataset.building ? option.dataset.building.toLowerCase() : '';
        if (roomNumber.includes(lowerSearch) || building.includes(lowerSearch)) {
            option.classList.remove('hidden');
            visibleCount++;
        } else {
            option.classList.add('hidden');
        }
    });
    
    // Show "no results" message if needed
    let noResultsMsg = dropdown.querySelector('.no-results-message');
    if (visibleCount === 0) {
        if (!noResultsMsg) {
            noResultsMsg = document.createElement('div');
            noResultsMsg.className = 'no-results-message px-3 py-4 text-center text-xs text-gray-500';
            noResultsMsg.textContent = 'No rooms found';
            dropdown.appendChild(noResultsMsg);
        }
    } else if (noResultsMsg) {
        noResultsMsg.remove();
    }
}

function selectRoomModalExam(mode, roomId, roomNumber, building) {
    const displayText = building ? `${roomNumber} - ${building}` : roomNumber;
    const searchField = document.getElementById(`room_search_${mode}`);
    const idField = document.getElementById(`room_id_${mode}`);
    const dropdown = document.getElementById(`room_dropdown_${mode}`);
    if (searchField) searchField.value = displayText;
    if (idField) {
        idField.value = roomId;
    }
    if (dropdown) dropdown.classList.add('hidden');
    
    // Trigger auto-check for exam conflicts with a small delay to ensure value is set
    if (typeof scheduleAutoExamConflictCheck === 'function') {
        const modeClean = mode.replace('exam_', '');
        // Use setTimeout to ensure the DOM is updated before validation
        setTimeout(() => {
            scheduleAutoExamConflictCheck(modeClean);
        }, 50); // 50ms delay
    } else {
        console.warn('[SELECT ROOM EXAM] scheduleAutoExamConflictCheck function not found!');
    }
}

// ============================================================================
// Proctor Availability Functions for Exam Scheduling
// ============================================================================

/**
 * Store for cached proctor availability data
 */
window.proctorAvailabilityCache = {};

/**
 * Check and display proctor availability when exam date/time changes
 * @param {string} mode - 'add' or 'edit'
 */
function checkProctorAvailability(mode) {
    const examDate = document.getElementById(`exam_date_${mode}`)?.value;
    const startTime = document.getElementById(`start_time_exam_${mode}`)?.value;
    const endTime = document.getElementById(`end_time_exam_${mode}`)?.value;
    
    // Only proceed if we have date and both times
    if (!examDate || !startTime || !endTime) {
        // Reset availability badges to default (no availability info)
        resetProctorAvailabilityBadges(mode);
        return;
    }
    
    // Create cache key
    const cacheKey = `${examDate}_${startTime}_${endTime}`;
    
    // Check cache first
    if (window.proctorAvailabilityCache[cacheKey]) {
        applyProctorAvailabilityBadges(mode, window.proctorAvailabilityCache[cacheKey]);
        return;
    }
    
    // Fetch availability from server
    fetch('/faculty/api/available-proctors', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
        },
        body: JSON.stringify({
            exam_date: examDate,
            start_time: startTime,
            end_time: endTime
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Cache the result
            window.proctorAvailabilityCache[cacheKey] = data.proctors;
            // Apply badges
            applyProctorAvailabilityBadges(mode, data.proctors);
        }
    })
    .catch(error => {
        console.error('Error fetching proctor availability:', error);
    });
}

/**
 * Apply availability badges to faculty options in the dropdown
 * @param {string} mode - 'add' or 'edit'
 * @param {Array} proctors - Array of proctor availability data
 */
function applyProctorAvailabilityBadges(mode, proctors) {
    const dropdown = document.getElementById(`faculty_dropdown_exam_${mode}`);
    if (!dropdown) return;
    
    const facultyOptions = dropdown.querySelectorAll('.faculty-option');
    
    // Create a map of faculty ID to availability
    const availabilityMap = {};
    proctors.forEach(p => {
        availabilityMap[p.id] = {
            status: p.availability_status,
            reason: p.availability_reason
        };
    });
    
    facultyOptions.forEach(option => {
        const facultyId = parseInt(option.dataset.facultyId);
        const availability = availabilityMap[facultyId];
        
        // Remove existing badges
        const existingBadge = option.querySelector('.availability-badge');
        if (existingBadge) existingBadge.remove();
        
        // Add new badge
        if (availability) {
            const badge = createAvailabilityBadge(availability.status, availability.reason);
            const nameDiv = option.querySelector('.font-semibold');
            if (nameDiv) {
                nameDiv.insertAdjacentElement('afterend', badge);
            }
            
            // Update option styling based on availability
            option.classList.remove('bg-green-50', 'bg-yellow-50', 'bg-red-50');
            if (availability.status === 'preferred') {
                option.classList.add('bg-green-50');
            } else if (availability.status === 'unavailable') {
                option.classList.add('bg-red-50');
            }
        }
    });
}

/**
 * Create an availability badge element
 * @param {string} status - 'available', 'unavailable', 'preferred', or 'no_data'
 * @param {string} reason - Optional reason text
 * @returns {HTMLElement}
 */
function createAvailabilityBadge(status, reason) {
    const badge = document.createElement('span');
    badge.className = 'availability-badge inline-flex items-center text-[10px] px-1.5 py-0.5 rounded-full ml-2';
    
    switch(status) {
        case 'preferred':
            badge.className += ' bg-green-100 text-green-700';
            badge.innerHTML = '<svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd"></path></svg>Preferred';
            break;
        case 'available':
            badge.className += ' bg-blue-100 text-blue-700';
            badge.innerHTML = '<svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-11a1 1 0 10-2 0v3.586L7.707 9.293a1 1 0 00-1.414 1.414l3 3a1 1 0 001.414 0l3-3a1 1 0 00-1.414-1.414L11 10.586V7z" clip-rule="evenodd"></path></svg>Available';
            break;
        case 'unavailable':
            badge.className += ' bg-red-100 text-red-700';
            badge.innerHTML = '<svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>Unavailable';
            if (reason) {
                badge.title = reason;
            }
            break;
        default:
            badge.className += ' bg-gray-100 text-gray-600';
            badge.innerHTML = '<svg class="w-3 h-3 mr-0.5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-8-3a1 1 0 00-.867.5 1 1 0 11-1.731-1A3 3 0 0113 8a3.001 3.001 0 01-2 2.83V11a1 1 0 11-2 0v-1a1 1 0 011-1 1 1 0 100-2zm0 8a1 1 0 100-2 1 1 0 000 2z" clip-rule="evenodd"></path></svg>No Info';
    }
    
    return badge;
}

/**
 * Reset availability badges to default (no availability info)
 * @param {string} mode - 'add' or 'edit'
 */
function resetProctorAvailabilityBadges(mode) {
    const dropdown = document.getElementById(`faculty_dropdown_exam_${mode}`);
    if (!dropdown) return;
    
    // Remove all existing badges and styling
    dropdown.querySelectorAll('.availability-badge').forEach(badge => badge.remove());
    dropdown.querySelectorAll('.faculty-option').forEach(option => {
        option.classList.remove('bg-green-50', 'bg-yellow-50', 'bg-red-50');
    });
}

/**
 * Show warning when selecting an unavailable proctor
 * @param {number} facultyId - Faculty ID
 * @param {string} mode - 'add' or 'edit'
 */
function checkSelectedProctorAvailability(facultyId, mode) {
    const examDate = document.getElementById(`exam_date_${mode}`)?.value;
    const startTime = document.getElementById(`start_time_exam_${mode}`)?.value;
    const endTime = document.getElementById(`end_time_exam_${mode}`)?.value;
    
    // Get the warning container
    const warningContainer = document.getElementById(`proctor_warning_exam_${mode}`);
    const examWarningContainer = document.getElementById(`examFacultyAvailabilityWarning${mode === 'add' ? 'Add' : 'Edit'}`);
    
    // Clear warnings if no date/time set
    if (!examDate || !startTime || !endTime) {
        if (warningContainer) {
            warningContainer.classList.add('hidden');
            warningContainer.innerHTML = '';
        }
        if (examWarningContainer) {
            examWarningContainer.classList.add('hidden');
            examWarningContainer.innerHTML = '';
        }
        return;
    }
    
    const cacheKey = `${examDate}_${startTime}_${endTime}`;
    const cachedData = window.proctorAvailabilityCache[cacheKey];
    
    // Function to display warning based on proctor data
    const displayProctorWarning = (proctorData) => {
        if (proctorData && proctorData.availability_status === 'unavailable') {
            const reasonText = proctorData.availability_reason ? `: ${proctorData.availability_reason}` : '';
            if (warningContainer) {
                warningContainer.innerHTML = `
                    <div class="flex items-start gap-2 p-2 bg-red-50 border border-red-200 rounded-lg text-xs text-red-700">
                        <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                        </svg>
                        <span><strong>Unavailable:</strong> This proctor has marked themselves as unavailable for this time slot${reasonText}</span>
                    </div>
                `;
                warningContainer.classList.remove('hidden');
            }
        } else if (proctorData && proctorData.availability_status === 'not_in_schedule') {
            // Faculty didn't set availability for this day - soft warning
            if (warningContainer) {
                warningContainer.innerHTML = `
                    <div class="flex items-start gap-2 p-2 bg-amber-50 border border-amber-200 rounded-lg text-xs text-amber-700">
                        <svg class="w-4 h-4 flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                            <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path>
                        </svg>
                        <span><strong>Note:</strong> This proctor has not set their availability for this day. You may still proceed.</span>
                    </div>
                `;
                warningContainer.classList.remove('hidden');
            }
        } else {
            // Available or preferred - hide warning
            if (warningContainer) {
                warningContainer.classList.add('hidden');
                warningContainer.innerHTML = '';
            }
        }
    };
    
    if (cachedData) {
        // Use cached data
        const proctorData = cachedData.find(p => p.id === parseInt(facultyId));
        displayProctorWarning(proctorData);
    } else {
        // No cached data - fetch from server immediately
        fetch('/faculty/api/available-proctors', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.querySelector('meta[name="csrf-token"]')?.content || ''
            },
            body: JSON.stringify({
                exam_date: examDate,
                start_time: startTime,
                end_time: endTime
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Cache the result
                window.proctorAvailabilityCache[cacheKey] = data.proctors;
                // Apply badges to dropdown
                applyProctorAvailabilityBadges(mode, data.proctors);
                // Check the selected proctor
                const proctorData = data.proctors.find(p => p.id === parseInt(facultyId));
                displayProctorWarning(proctorData);
            }
        })
        .catch(error => {
            console.error('Error fetching proctor availability:', error);
        });
    }
}

/**
 * Setup event listeners for proctor availability checking
 */
function setupProctorAvailabilityListeners() {
    ['add', 'edit'].forEach(mode => {
        // Listen for date changes
        const dateInput = document.getElementById(`exam_date_${mode}`);
        if (dateInput) {
            dateInput.addEventListener('change', () => checkProctorAvailability(mode));
        }
        
        // Listen for time changes
        const startTime = document.getElementById(`start_time_exam_${mode}`);
        const endTime = document.getElementById(`end_time_exam_${mode}`);
        if (startTime) {
            startTime.addEventListener('change', () => checkProctorAvailability(mode));
        }
        if (endTime) {
            endTime.addEventListener('change', () => checkProctorAvailability(mode));
        }
    });
}

// Initialize proctor availability listeners when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    setupProctorAvailabilityListeners();
});

// ========================================
// UNIFIED SCHEDULE MODAL (Add/Edit)
// ========================================

// Track current modal mode: 'add' or 'edit'
window.scheduleModalMode = 'add';
window.currentEditScheduleId = null;

/**
 * Set the modal UI based on mode (add or edit)
 */
function setScheduleModalMode(mode) {
    window.scheduleModalMode = mode;
    
    const titleEl = document.getElementById('scheduleModalTitle');
    const subtitleEl = document.getElementById('scheduleModalSubtitle');
    const iconAdd = document.getElementById('scheduleModalIconAdd');
    const iconEdit = document.getElementById('scheduleModalIconEdit');
    const submitBtn = document.getElementById('submitScheduleBtn');
    const submitBtnText = document.getElementById('submitScheduleBtnText');
    const backToAddBtn = document.getElementById('backToAddScheduleBtn');
    const deleteBtn = document.getElementById('deleteScheduleBtn');
    const form = document.getElementById('addScheduleForm');
    
    // Unified form page elements
    const unifiedTitle = document.getElementById('unifiedPageTitle');
    const unifiedIconAdd = document.getElementById('unifiedIconAdd');
    const unifiedIconEdit = document.getElementById('unifiedIconEdit');
    
    if (mode === 'edit') {
        // Edit mode UI
        if (titleEl) titleEl.textContent = 'Edit Schedule';
        if (subtitleEl) subtitleEl.textContent = 'Update the schedule details below';
        if (iconAdd) iconAdd.classList.add('hidden');
        if (iconEdit) iconEdit.classList.remove('hidden');
        if (backToAddBtn) backToAddBtn.classList.remove('hidden');
        if (backToAddBtn) backToAddBtn.style.display = 'flex';
        if (deleteBtn) { deleteBtn.classList.remove('hidden'); deleteBtn.style.display = 'flex'; }
        if (form) form.action = '/schedule/edit';
        // Unified page header
        if (unifiedTitle) unifiedTitle.textContent = 'Edit Schedule';
        if (unifiedIconAdd) unifiedIconAdd.classList.add('hidden');
        if (unifiedIconEdit) unifiedIconEdit.classList.remove('hidden');
        // Hide auto-generate in edit mode
        const autoGenBtn = document.getElementById('autoGenBtn');
        if (autoGenBtn) autoGenBtn.style.display = 'none';
    } else {
        // Add mode UI
        if (titleEl) titleEl.textContent = 'Add New Schedule';
        if (subtitleEl) subtitleEl.textContent = 'Fill in the details below to create a schedule';
        if (iconAdd) iconAdd.classList.remove('hidden');
        if (iconEdit) iconEdit.classList.add('hidden');
        if (backToAddBtn) backToAddBtn.classList.add('hidden');
        if (backToAddBtn) backToAddBtn.style.display = '';
        if (deleteBtn) { deleteBtn.classList.add('hidden'); deleteBtn.style.display = 'none'; }
        if (form) form.action = '/schedule/add';
        // Unified page header
        if (unifiedTitle) unifiedTitle.textContent = 'Create Schedule';
        if (unifiedIconAdd) unifiedIconAdd.classList.remove('hidden');
        if (unifiedIconEdit) unifiedIconEdit.classList.add('hidden');
        // Show auto-generate if section selected
        const autoGenBtn = document.getElementById('autoGenBtn');
        if (autoGenBtn && window.FORM_SECTION_ID) autoGenBtn.style.display = 'flex';
    }
}

// Open Schedule Modal for Adding
function openAddScheduleModal(sectionId, sectionName = '') {
    // On view pages, navigate to the unified create page instead of opening modal
    if (!window.SCHEDULE_FORM_MODE) {
        window.location.href = '/schedule/create?type=class&section_id=' + sectionId;
        return;
    }
    // Set to add mode
    setScheduleModalMode('add');
    window.currentEditScheduleId = null;
    
    // Clear edit-specific fields
    document.getElementById('schedule_id').value = '';
    document.getElementById('schedule_version').value = '';
    
    document.getElementById('section_id_add').value = sectionId;
    // On inline form pages, content is already visible - skip modal show/hide
    if (!window.INLINE_FORM_PAGE) {
        document.getElementById('addScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }
    
    // Set the section dropdown to the current section
    const sectionSwitcher = document.getElementById('modalSectionSwitcher');
    if (sectionSwitcher) {
        sectionSwitcher.value = sectionId;
    }
    
    // Reset schedule type dropdown to default state
    const scheduleTypeSelect = document.getElementById('schedule_type_add');
    if (scheduleTypeSelect) {
        scheduleTypeSelect.value = '';
        // Reset all options to default text
        document.getElementById('lectureOption_add').textContent = 'Lecture (0 units)';
        document.getElementById('labOption_add').textContent = 'Lab (0 units)';
        // Disable all options initially
        document.getElementById('lectureOption_add').disabled = true;
        document.getElementById('labOption_add').disabled = true;
    }
    
    // Reset auto-check state to initial (no spinner, button disabled with message)
    if (typeof resetAutoCheckState === 'function') {
        resetAutoCheckState('add');
    }
    
    // Clear time pickers for fresh add form
    if (typeof TimePicker !== 'undefined' && TimePicker.clearById) {
        TimePicker.clearById('start_time_add');
        TimePicker.clearById('end_time_add');
    }
    
    // Load curricula for this section (which will then load subjects)
    loadCurriculaForSection(sectionId, 'add');
    
    // Render modal calendar with section's existing schedules
    if (typeof renderModalCalendar === 'function') {
        // Small delay to ensure modal is visible for proper height calculation
        setTimeout(() => {
            renderModalCalendar(sectionId, sectionName);
        }, 100);
    }
}

/**
 * Open Schedule Modal for Editing
 */
function openEditScheduleModalUnified(scheduleData) {
    // Set to edit mode
    setScheduleModalMode('edit');
    window.currentEditScheduleId = scheduleData.id;
    
    // Set edit-specific fields
    document.getElementById('schedule_id').value = scheduleData.id;
    document.getElementById('schedule_version').value = scheduleData.version || '';
    document.getElementById('section_id_add').value = scheduleData.section_id;
    
    // On inline form pages, content is already visible - skip modal show/hide
    if (!window.INLINE_FORM_PAGE) {
        document.getElementById('addScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }
    
    // Set section dropdown
    const sectionSwitcher = document.getElementById('modalSectionSwitcher');
    if (sectionSwitcher) {
        sectionSwitcher.value = scheduleData.section_id;
    }
    
    // Reset schedule type dropdown to default state (will be set after subject loads)
    const scheduleTypeSelect = document.getElementById('schedule_type_add');
    if (scheduleTypeSelect) {
        scheduleTypeSelect.value = '';
        document.getElementById('lectureOption_add').textContent = 'Lecture (0 units)';
        document.getElementById('labOption_add').textContent = 'Lab (0 units)';
        document.getElementById('lectureOption_add').disabled = true;
        document.getElementById('labOption_add').disabled = true;
    }
    
    // Reset auto-check state
    if (typeof resetAutoCheckState === 'function') {
        resetAutoCheckState('add');
    }
    
    // Store schedule data for later use after curricula/subjects load
    window.pendingEditScheduleData = scheduleData;
    
    // Load curricula for this section, then populate form fields
    loadCurriculaForSectionEdit(scheduleData.section_id, scheduleData, 'add');
    
    // Set other fields immediately
    document.getElementById('day_of_week_add').value = scheduleData.day_of_week || '';
    document.getElementById('start_time_add').value = scheduleData.start_time || '';
    document.getElementById('end_time_add').value = scheduleData.end_time || '';
    
    // Set room
    document.getElementById('room_id_add').value = scheduleData.room_id || '';
    const roomSearch = document.getElementById('room_search_add');
    if (roomSearch) {
        if (scheduleData.room_number && scheduleData.building_name) {
            roomSearch.value = `${scheduleData.room_number} - ${scheduleData.building_name}`;
        } else if (scheduleData.room_number) {
            roomSearch.value = scheduleData.room_number;
        } else {
            roomSearch.value = '';
        }
    }
    
    // Render modal calendar
    if (typeof renderModalCalendar === 'function') {
        setTimeout(() => {
            renderModalCalendar(scheduleData.section_id, scheduleData.section_name || '');
        }, 100);
    }
}

// Unified close function
function closeScheduleModal() {
    // On inline form pages, navigate back instead of hiding modal
    if (window.INLINE_FORM_PAGE) {
        const sectionId = document.getElementById('section_id_add')?.value;
        window.location.href = sectionId ? '/schedule/class?section_id=' + sectionId : '/schedule/class';
        return;
    }
    document.getElementById('addScheduleModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    document.getElementById('addScheduleForm').reset();
    
    // Clear edit fields
    document.getElementById('schedule_id').value = '';
    document.getElementById('schedule_version').value = '';
    window.currentEditScheduleId = null;
    window.pendingEditScheduleData = null;
    
    // Reset to add mode for next open
    setScheduleModalMode('add');
    
    // Reset faculty picker display
    resetFacultyPicker('add');
    
    // Reset auto-check state
    if (typeof resetAutoCheckState === 'function') {
        resetAutoCheckState('add');
    }
    
    // Clear modal calendar and table
    if (typeof clearModalCalendar === 'function') {
        clearModalCalendar();
    }
    
    // Reset modal view to calendar (default) with proper button styling
    const tableBtn = document.getElementById('modalViewToggleTable');
    const calendarBtn = document.getElementById('modalViewToggleCalendar');
    const tableView = document.getElementById('modalTableView');
    const calendarContainer = document.getElementById('modalCalendarContainer');
    
    // Reset to calendar view as default - hide both views
    if (tableView) {
        tableView.classList.add('hidden');
        tableView.style.display = 'none';
    }
    if (calendarContainer) {
        calendarContainer.classList.add('hidden');
        calendarContainer.style.display = 'none';
    }
    
    // Reset button states to calendar selected
    if (calendarBtn) {
        calendarBtn.classList.add('bg-white', 'text-blue-600', 'shadow-sm');
        calendarBtn.classList.remove('text-gray-600', 'hover:text-gray-900');
    }
    if (tableBtn) {
        tableBtn.classList.remove('bg-white', 'text-blue-600', 'shadow-sm');
        tableBtn.classList.add('text-gray-600', 'hover:text-gray-900');
    }
    
    // Reset modal view preference to calendar
    window.modalViewPreference = 'calendar';
}

/**
 * Switch back from Edit mode to Add mode without closing the modal
 * This is called when user clicks "New" button while in edit mode
 */
function switchBackToAddMode() {
    // Get current section ID to preserve it
    const sectionId = document.getElementById('section_id_add')?.value;
    const sectionSwitcher = document.getElementById('modalSectionSwitcher');
    const sectionName = sectionSwitcher?.options[sectionSwitcher.selectedIndex]?.text || '';
    
    // Reset to add mode
    setScheduleModalMode('add');
    window.currentEditScheduleId = null;
    window.pendingEditScheduleData = null;
    
    // Clear edit-specific hidden fields
    const scheduleIdField = document.getElementById('schedule_id');
    const versionField = document.getElementById('schedule_version');
    if (scheduleIdField) scheduleIdField.value = '';
    if (versionField) versionField.value = '';
    
    // Reset form fields but keep section selected
    const form = document.getElementById('addScheduleForm');
    if (form) form.reset();
    
    // Restore section ID after form reset
    if (sectionId) {
        document.getElementById('section_id_add').value = sectionId;
        if (sectionSwitcher) sectionSwitcher.value = sectionId;
    }
    
    // Reset schedule type dropdown
    const scheduleTypeSelect = document.getElementById('schedule_type_add');
    if (scheduleTypeSelect) {
        scheduleTypeSelect.value = '';
        const lectureOption = document.getElementById('lectureOption_add');
        const labOption = document.getElementById('labOption_add');
        if (lectureOption) {
            lectureOption.textContent = 'Lecture (0 units)';
            lectureOption.disabled = true;
        }
        if (labOption) {
            labOption.textContent = 'Lab (0 units)';
            labOption.disabled = true;
        }
    }
    
    // Reset faculty picker
    resetFacultyPicker('add');
    
    // Reset auto-check state
    if (typeof resetAutoCheckState === 'function') {
        resetAutoCheckState('add');
    }
    
    // Remove highlight from any selected schedule in calendar/table
    document.querySelectorAll('.modal-events-container .week-event.ring-2.ring-green-500').forEach(el => {
        el.classList.remove('ring-2', 'ring-green-500');
    });
    document.querySelectorAll('#modalTableBody tr.bg-green-50').forEach(el => {
        el.classList.remove('bg-green-50');
    });
    
    // Reload curricula for the section (to reset dropdowns)
    if (sectionId && typeof loadCurriculaForSection === 'function') {
        loadCurriculaForSection(sectionId, 'add');
    }
}

// Expose globally
window.switchBackToAddMode = switchBackToAddMode;

// Keep old function name for backward compatibility
function closeAddScheduleModal() {
    closeScheduleModal();
}

// Reset faculty picker to initial state
function resetFacultyPicker(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const facultyDisplay = document.getElementById(`facultyDisplay${suffix}`);
    const facultyList = document.getElementById(`facultyList${suffix}`);
    const facultySearch = document.getElementById(`facultySearch${suffix}`);
    const facultyDropdown = document.getElementById(`facultyDropdown${suffix}`);
    const facultyChevron = document.getElementById(`facultyChevron${suffix}`);
    
    // Reset display
    if (facultyDisplay) {
        facultyDisplay.innerHTML = '<span class="text-gray-400">Select a faculty...</span>';
    }
    
    // Reset list
    if (facultyList) {
        facultyList.innerHTML = `
            <div class="p-4 text-center text-gray-500 text-sm">
                <svg class="w-8 h-8 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                </svg>
                Select a subject first to load faculty
            </div>
        `;
    }
    
    // Reset search
    if (facultySearch) {
        facultySearch.value = '';
    }
    
    // Close dropdown
    if (facultyDropdown) {
        facultyDropdown.classList.add('hidden');
    }
    if (facultyChevron) {
        facultyChevron.classList.remove('rotate-180');
    }
    
    // Clear cache
    window.facultyDataCache[mode] = [];
}

// Note: loadCurriculaForSection and loadSubjectsForCurriculum are now in curriculum_selector.js

// Load subjects dynamically based on section (DEPRECATED - use loadCurriculaForSection instead)
function loadSubjectsForSection(sectionId) {
    // For backward compatibility, redirect to curriculum-based loading
    loadCurriculaForSection(sectionId, 'add');
}

// Load faculty for a specific subject with enhanced UI
// Stores faculty data for the enhanced picker
window.facultyDataCache = { add: [], edit: [] };

function loadFacultyForSubject(subjectId, mode = 'add', selectedFacultyId = null) {
    const facultySelect = document.getElementById(`faculty_id_${mode}`);
    const facultyList = document.getElementById(`facultyList${mode === 'add' ? 'Add' : 'Edit'}`);
    const facultyDisplay = document.getElementById(`facultyDisplay${mode === 'add' ? 'Add' : 'Edit'}`);
    if (!subjectId) {
        // Reset when no subject selected
        facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
        facultySelect.value = '';
        window.facultyDataCache[mode] = [];
        if (facultyList) {
            facultyList.innerHTML = `
                <div class="p-4 text-center text-gray-500 text-sm">
                    <svg class="w-8 h-8 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path>
                    </svg>
                    Select a subject first to load faculty
                </div>
            `;
        }
        if (facultyDisplay) {
            facultyDisplay.innerHTML = '<span class="text-gray-400">Select a faculty...</span>';
        }
        return;
    }
    
    // Show loading state
    if (facultyList) {
        facultyList.innerHTML = `
            <div class="p-4 text-center text-gray-500 text-sm">
                <svg class="w-6 h-6 mx-auto mb-2 animate-spin text-green-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"></path>
                </svg>
                Loading faculty...
            </div>
        `;
    }
    
    // Fetch faculty for this subject
    fetch(`/schedule/get-faculty/${subjectId}`)
        .then(response => response.json())
        .then(data => {
            facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
            window.facultyDataCache[mode] = data.faculty || [];
            if (data.faculty && data.faculty.length > 0) {
                // Populate hidden select for form submission
                data.faculty.forEach(faculty => {
                    const option = document.createElement('option');
                    option.value = faculty.id;
                    option.textContent = faculty.display;
                    option.dataset.facultyData = JSON.stringify(faculty);
                    
                    if (selectedFacultyId && faculty.id == selectedFacultyId) {
                        option.selected = true;
                    }
                    
                    facultySelect.appendChild(option);
                });
                
                // Render enhanced faculty list
                renderFacultyList(mode, data.faculty, selectedFacultyId);
                
                // If a faculty was pre-selected, update display
                if (selectedFacultyId) {
                    const selectedFaculty = data.faculty.find(f => f.id == selectedFacultyId);
                    if (selectedFaculty) {
                        updateFacultyDisplay(mode, selectedFaculty);
                    }
                } else {
                    // Hybrid subject-change behavior: auto-select only when exactly one assigned faculty exists.
                    // Otherwise, keep faculty unset so users select explicitly.
                    const assignedFaculty = data.faculty.filter(f => f.is_assigned);
                    if (assignedFaculty.length === 1) {
                        selectFacultyFromDropdown(mode, assignedFaculty[0].id, { silent: true });
                    } else {
                        clearFacultySelection(mode);
                    }
                }
                
                // Trigger conflict check after faculty is loaded (for edit mode)
                if (window.scheduleModalMode === 'edit' && typeof scheduleAutoConflictCheck === 'function') {
                    setTimeout(() => scheduleAutoConflictCheck('add'), 200);
                }
            } else {
                if (facultyList) {
                    facultyList.innerHTML = `
                        <div class="p-4 text-center text-gray-500 text-sm">
                            <svg class="w-8 h-8 mx-auto mb-2 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path>
                            </svg>
                            No faculty available
                        </div>
                    `;
                }
            }
        })
        .catch(error => {
            console.error('[FACULTY] Error loading faculty:', error);
            facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
            window.facultyDataCache[mode] = [];
            if (facultyList) {
                facultyList.innerHTML = `
                    <div class="p-4 text-center text-red-500 text-sm">
                        <svg class="w-8 h-8 mx-auto mb-2 text-red-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        Error loading faculty
                    </div>
                `;
            }
            showToast('Error loading faculty. Please try again.', 'error');
        });
}

function clearFacultySelection(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const facultySelect = document.getElementById(`faculty_id_${mode}`);
    const facultyDisplay = document.getElementById(`facultyDisplay${suffix}`);

    if (facultySelect) {
        facultySelect.value = '';
    }

    if (facultyDisplay) {
        facultyDisplay.innerHTML = '<span class="text-gray-400">Select a faculty...</span>';
    }
}

// Render enhanced faculty list with cards
function renderFacultyList(mode, facultyData, selectedId = null) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const facultyList = document.getElementById(`facultyList${suffix}`);
    if (!facultyList) return;
    
    if (!facultyData || facultyData.length === 0) {
        facultyList.innerHTML = '<div class="p-4 text-center text-gray-500 text-sm">No faculty available</div>';
        return;
    }
    
    let html = '';
    
    // Render all faculty in a single list
    facultyData.forEach(faculty => {
        html += renderFacultyCard(faculty, mode, selectedId);
    });
    
    facultyList.innerHTML = html;
}

// Render individual faculty card
function renderFacultyCard(faculty, mode, selectedId) {
    const isSelected = selectedId && faculty.id == selectedId;
    const availabilityConfig = getAvailabilityConfig(faculty.availability);
    
    // Build available days display
    let availableDaysHtml = '';
    if (faculty.available_days && faculty.available_days.length > 0) {
        availableDaysHtml = `
            <div class="flex items-center gap-1 mt-1">
                <svg class="w-3 h-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path>
                </svg>
                <span class="text-[10px] text-emerald-600 font-medium">${faculty.available_days.join(', ')}</span>
            </div>
        `;
    }
    
    return `
        <div class="faculty-card px-3 py-2.5 hover:bg-gray-50 cursor-pointer border-b border-gray-100 transition-colors ${isSelected ? 'bg-green-50 border-l-4 border-l-green-500' : ''}"
             onclick="selectFacultyFromDropdown('${mode}', ${faculty.id})"
             data-faculty-id="${faculty.id}"
             data-faculty-name="${faculty.full_name.toLowerCase()}"
             data-program="${(faculty.department_code || '').toLowerCase()}"
             data-available-days="${faculty.available_days ? faculty.available_days.join(',') : ''}">
            <div class="flex items-center space-x-3">
                <!-- Avatar -->
                <div class="w-9 h-9 rounded-full ${availabilityConfig.bgClass} flex items-center justify-center flex-shrink-0">
                    <span class="${availabilityConfig.textClass} text-xs font-bold">${faculty.initials}</span>
                </div>
                
                <!-- Info -->
                <div class="flex-1 min-w-0">
                    <div class="flex items-center space-x-2">
                        <span class="text-sm font-medium text-gray-900 truncate">${faculty.full_name}</span>
                    </div>
                    <div class="flex items-center space-x-2 text-xs text-gray-500">
                        <span>${faculty.department_code || 'No Dept'}</span>
                    </div>
                    ${availableDaysHtml}
                </div>
                
                <!-- Availability Indicator -->
                <div class="flex-shrink-0">
                    <span class="${availabilityConfig.dotClass} w-2.5 h-2.5 rounded-full inline-block" title="${availabilityConfig.label}"></span>
                </div>
            </div>
        </div>
    `;
}

// Get availability styling config
function getAvailabilityConfig(availability) {
    const configs = {
        available: {
            label: 'Available',
            bgClass: 'bg-green-100',
            textClass: 'text-green-700',
            badgeClass: 'bg-green-100 text-green-700',
            dotClass: 'bg-green-500'
        },
        moderate: {
            label: 'Moderate Load',
            bgClass: 'bg-blue-100',
            textClass: 'text-blue-700',
            badgeClass: 'bg-blue-100 text-blue-700',
            dotClass: 'bg-blue-500'
        },
        high_load: {
            label: 'High Load',
            bgClass: 'bg-yellow-100',
            textClass: 'text-yellow-700',
            badgeClass: 'bg-yellow-100 text-yellow-700',
            dotClass: 'bg-yellow-500'
        },
        overloaded: {
            label: 'Overloaded',
            bgClass: 'bg-red-100',
            textClass: 'text-red-700',
            badgeClass: 'bg-red-100 text-red-700',
            dotClass: 'bg-red-500'
        }
    };
    return configs[availability] || configs.available;
}

// Toggle faculty dropdown
window.toggleFacultyDropdown = function(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const dropdown = document.getElementById(`facultyDropdown${suffix}`);
    const chevron = document.getElementById(`facultyChevron${suffix}`);
    const searchInput = document.getElementById(`facultySearch${suffix}`);
    
    if (dropdown.classList.contains('hidden')) {
        dropdown.classList.remove('hidden');
        chevron.classList.add('rotate-180');
        if (searchInput) {
            setTimeout(() => searchInput.focus(), 100);
        }
        
        // Close on click outside
        setTimeout(() => {
            document.addEventListener('click', function closeDropdown(e) {
                const picker = document.getElementById(`facultyPicker${suffix}`);
                if (!picker.contains(e.target)) {
                    dropdown.classList.add('hidden');
                    chevron.classList.remove('rotate-180');
                    document.removeEventListener('click', closeDropdown);
                }
            });
        }, 10);
    } else {
        dropdown.classList.add('hidden');
        chevron.classList.remove('rotate-180');
    }
};

// Filter faculty list based on search
window.filterFacultyList = function(mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const searchInput = document.getElementById(`facultySearch${suffix}`);
    const searchTerm = searchInput.value.toLowerCase().trim();
    const cards = document.querySelectorAll(`#facultyList${suffix} .faculty-card`);
    
    cards.forEach(card => {
        const name = card.dataset.facultyName || '';
        const dept = card.dataset.program || '';
        const matches = name.includes(searchTerm) || dept.includes(searchTerm);
        card.style.display = matches ? '' : 'none';
    });
};

// Select a faculty from the modal dropdown (for add/edit schedule forms)
window.selectFacultyFromDropdown = function(mode, facultyId, options = {}) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const facultySelect = document.getElementById(`faculty_id_${mode}`);
    const dropdown = document.getElementById(`facultyDropdown${suffix}`);
    const chevron = document.getElementById(`facultyChevron${suffix}`);
    const silent = Boolean(options && options.silent);

    if (!facultySelect) {
        return;
    }
    
    // Update hidden select
    facultySelect.value = facultyId;
    
    // Find faculty data
    const facultyCache = Array.isArray(window.facultyDataCache[mode]) ? window.facultyDataCache[mode] : [];
    const faculty = facultyCache.find(f => f.id == facultyId);
    if (faculty) {
        updateFacultyDisplay(mode, faculty);
    }
    
    // Close dropdown
    if (dropdown) {
        dropdown.classList.add('hidden');
    }
    if (chevron) {
        chevron.classList.remove('rotate-180');
    }
    
    // Trigger change event for auto-conflict check
    const event = new Event('change', { bubbles: true });
    facultySelect.dispatchEvent(event);
    
    // Trigger auto-conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
    
    if (!silent && faculty && typeof showToast === 'function') {
        showToast(`Selected: ${faculty.full_name}`, 'success');
    }
};

// Update the faculty display button
function updateFacultyDisplay(mode, faculty) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const facultyDisplay = document.getElementById(`facultyDisplay${suffix}`);
    if (!facultyDisplay || !faculty) return;
    
    const availabilityConfig = getAvailabilityConfig(faculty.availability);
    
    // Build available days display for selected faculty
    let availableDaysHtml = '';
    if (faculty.available_days && faculty.available_days.length > 0) {
        availableDaysHtml = `<span class="text-emerald-600 text-[10px]">• ${faculty.available_days.join(', ')}</span>`;
    }
    
    facultyDisplay.innerHTML = `
        <div class="w-7 h-7 sm:w-8 sm:h-8 rounded-full ${availabilityConfig.bgClass} flex items-center justify-center flex-shrink-0">
            <span class="${availabilityConfig.textClass} text-xs font-bold">${faculty.initials}</span>
        </div>
        <div class="flex-1 min-w-0">
            <div class="text-sm font-medium text-gray-900 truncate">${faculty.full_name}</div>
            <div class="text-xs text-gray-500 flex items-center gap-1">
                <span>${faculty.department_code || 'No Dept'}</span>
                ${availableDaysHtml}
            </div>
        </div>
    `;
}

// Edit Schedule Modal - Now uses unified modal
function openEditScheduleModal() {
    // This function is kept for backward compatibility
    // but the modal is actually opened by openEditScheduleModalUnified
}

function closeEditScheduleModal() {
    // Redirect to unified close function
    closeScheduleModal();
}

function editSchedule(id, scheduleData) {
    // On view pages, navigate to the dedicated edit form page
    if (!window.SCHEDULE_FORM_MODE) {
        window.location.href = '/schedule/class/edit/' + id;
        return;
    }
    
    // Add id to scheduleData
    scheduleData.id = id;
    
    // Use the unified modal for editing
    openEditScheduleModalUnified(scheduleData);
}

function parseScheduleFullApiJson(response, fallbackMessage) {
    const contentType = (response.headers.get('content-type') || '').toLowerCase();

    if (!response.ok) {
        if (contentType.includes('application/json')) {
            return response.json().then((payload) => {
                throw new Error(payload.error || payload.message || `Request failed (${response.status})`);
            });
        }

        return response.text().then((text) => {
            throw new Error((text || '').slice(0, 120).trim() || fallbackMessage || `Request failed (${response.status})`);
        });
    }

    if (!contentType.includes('application/json')) {
        return response.text().then((text) => {
            throw new Error((text || '').slice(0, 120).trim() || fallbackMessage || 'Invalid server response');
        });
    }

    return response.json();
}

/**
 * Load curricula for section when editing - populates curriculum dropdown then selects correct one
 * @param {number} sectionId - Section ID
 * @param {Object} scheduleData - Schedule or exam data with subject_id, curriculum_id, etc.
 * @param {string} mode - Mode suffix (e.g., 'add', 'exam_add', 'edit')
 */
function loadCurriculaForSectionEdit(sectionId, scheduleData, mode = 'add') {
    const suffix = mode;
    const curriculumSelect = document.getElementById(`curriculum_id_${suffix}`);
    const subjectSelect = document.getElementById(`subject_id_${suffix}`);
    
    if (!curriculumSelect) {
        console.error(`[loadCurriculaForSectionEdit] curriculum_id_${suffix} not found`);
        return;
    }
    
    // Show loading state
    curriculumSelect.innerHTML = '<option value="">Loading curricula...</option>';
    curriculumSelect.disabled = true;
    subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
    subjectSelect.disabled = true;
    
    // Fetch curricula for this section
    fetch(`/schedule/get-curricula/${sectionId}`)
        .then(response => parseScheduleFullApiJson(response, 'Unable to load curricula'))
        .then(data => {
            curriculumSelect.innerHTML = '<option value="">Select a curriculum...</option>';
            
            if (data.curricula && data.curricula.length > 0) {
                data.curricula.forEach(curriculum => {
                    const option = document.createElement('option');
                    option.value = curriculum.id;
                    option.textContent = curriculum.display;
                    curriculumSelect.appendChild(option);
                });
                
                // If we have schedule data with curriculum_id, select it
                if (scheduleData.curriculum_id) {
                    curriculumSelect.value = scheduleData.curriculum_id;
                    // Load subjects for this curriculum, then set the subject
                    loadSubjectsForCurriculumEdit(scheduleData, mode);
                } else if (data.curricula.length === 1) {
                    // Auto-select if only one curriculum
                    curriculumSelect.value = data.curricula[0].id;
                    loadSubjectsForCurriculumEdit(scheduleData, mode);
                }
            } else {
                curriculumSelect.innerHTML = '<option value="">No curricula available</option>';
            }
            
            curriculumSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading curricula for edit:', error);
            curriculumSelect.innerHTML = '<option value="">Error loading curricula</option>';
            curriculumSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast(error.message || 'Error loading curricula', 'error');
            }
        });
}

/**
 * Load subjects for curriculum when editing
 * @param {Object} scheduleData - Schedule or exam data
 * @param {string} mode - Mode suffix (e.g., 'add', 'exam_add', 'edit')
 */
function loadSubjectsForCurriculumEdit(scheduleData, mode = 'add') {
    const suffix = mode;
    const curriculumId = document.getElementById(`curriculum_id_${suffix}`).value;
    const subjectSelect = document.getElementById(`subject_id_${suffix}`);
    
    if (!curriculumId || !subjectSelect) return;
    
    // Show loading state
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // Use the filtered get-subjects route (filters by section year level + current semester)
    // Fall back to get-subjects-by-curriculum if no section_id available
    const sectionId = scheduleData.section_id || document.getElementById(`section_id_${suffix}`)?.value;
    const url = sectionId
        ? `/schedule/get-subjects/${sectionId}?curriculum_id=${curriculumId}`
        : `/schedule/get-subjects-by-curriculum/${curriculumId}`;
    
    fetch(url)
        .then(response => response.json())
        .then(data => {
            subjectSelect.innerHTML = '<option value="">Select Subject</option>';
            
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
                    
                    // Pre-select the current subject
                    if (subject.id === scheduleData.subject_id) {
                        option.selected = true;
                    }
                    
                    subjectSelect.appendChild(option);
                });
                
                // Trigger subject change if we have a selected subject (only for regular schedules, not exams)
                if (scheduleData.subject_id && !mode.startsWith('exam')) {
                    const selectedOption = subjectSelect.querySelector(`option[value="${scheduleData.subject_id}"]`);
                    if (selectedOption) {
                        const subjectData = {
                            id: selectedOption.value,
                            code: selectedOption.dataset.code,
                            description: selectedOption.dataset.description,
                            lecUnits: parseFloat(selectedOption.dataset.lecUnits) || 0,
                            labUnits: parseFloat(selectedOption.dataset.labUnits) || 0,
                            totalUnits: parseFloat(selectedOption.dataset.totalUnits) || 0
                        };
                        
                        // Store in currentSubjectData
                        currentSubjectData[suffix] = subjectData;
                        
                        // Show schedule type options (only for regular schedules)
                        if (typeof showScheduleTypeOptions === 'function') {
                            showScheduleTypeOptions(suffix, subjectData);
                        }
                        
                        // Set the schedule type after options are populated
                        setTimeout(() => {
                            const scheduleTypeSelect = document.getElementById(`schedule_type_${suffix}`);
                            if (scheduleTypeSelect && scheduleData.schedule_type) {
                                scheduleTypeSelect.value = scheduleData.schedule_type.toLowerCase();
                                handleScheduleTypeChange(suffix);
                            }
                        }, 100);
                        
                        // Load faculty for the selected subject
                        loadFacultyForSubject(scheduleData.subject_id, suffix, scheduleData.faculty_id);
                    }
                } else if (scheduleData.subject_id && mode.startsWith('exam')) {
                    // For exam mode: trigger handleExamSubjectChange and set schedule_type
                    if (typeof handleExamSubjectChange === 'function') {
                        handleExamSubjectChange(suffix);
                    }
                    // Set exam schedule_type after dropdown is populated
                    setTimeout(() => {
                        const examTypeSelect = document.getElementById(`schedule_type_exam_${suffix}`);
                        if (examTypeSelect && scheduleData.schedule_type) {
                            examTypeSelect.value = scheduleData.schedule_type.toLowerCase();
                        }
                    }, 100);
                }
            } else {
                subjectSelect.innerHTML = '<option value="">No subjects available</option>';
            }
            
            subjectSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading subjects for edit:', error);
            subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
            subjectSelect.disabled = false;
        });
}

// Load subjects for edit modal
function loadSubjectsForEdit(sectionId, scheduleData) {
    const subjectSelect = document.getElementById('subject_id_edit');
    
    // Show loading state
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // Fetch subjects for this section
    fetch(`/schedule/get-subjects/${sectionId}`)
        .then(response => response.json())
        .then(data => {
            subjectSelect.innerHTML = '<option value="">Select Subject</option>';
            
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
                    
                    // Pre-select the current subject
                    if (subject.id === scheduleData.subject_id) {
                        option.selected = true;
                    }
                    
                    subjectSelect.appendChild(option);
                });
                
                // Trigger subject change to populate schedule type options
                if (scheduleData.subject_id) {
                    const selectedOption = subjectSelect.options[subjectSelect.selectedIndex];
                    const subjectData = {
                        id: selectedOption.value,
                        code: selectedOption.dataset.code,
                        description: selectedOption.dataset.description,
                        lecUnits: parseFloat(selectedOption.dataset.lecUnits) || 0,
                        labUnits: parseFloat(selectedOption.dataset.labUnits) || 0,
                        totalUnits: parseFloat(selectedOption.dataset.totalUnits) || 0
                    };
                    
                    // Store in currentSubjectData so calculateEndTime can access it
                    currentSubjectData.edit = subjectData;
                    
                    // Show schedule type options
                    showScheduleTypeOptions('edit', subjectData);
                    
                    // Set the schedule type after options are populated
                    setTimeout(() => {
                        document.getElementById('schedule_type_edit').value = window.editScheduleType || 'lecture';
                        // Trigger the schedule type change to store units and show Auto badge
                        handleScheduleTypeChange('edit');
                        
                        // Trigger auto-calculation if start time is already filled
                        // This ensures the end time gets calculated when editing existing schedules
                        const startTimeField = document.getElementById('start_time_edit');
                        if (startTimeField && startTimeField.value) {
                            calculateEndTime('edit');
                        }
                    }, 100);
                    
                    // Load faculty for the selected subject and preserve the selected faculty
                    loadFacultyForSubject(scheduleData.subject_id, 'edit', scheduleData.faculty_id);
                }
            } else {
                subjectSelect.innerHTML = '<option value="">No subjects available for this section</option>';
            }
            
            subjectSelect.disabled = false;
        })
        .catch(error => {
            console.error('Error loading subjects:', error);
            subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
            subjectSelect.disabled = false;
            showToast('Error loading subjects. Please try again.', 'error');
        });
}


function deleteSchedule(id, subjectCode) {
    // Check if we're on schedule_form.html (has its own class delete modal with different IDs)
    const formPageModal = document.getElementById('deleteScheduleSubjectInfo');
    if (formPageModal) {
        // Use schedule_form.html's own class delete modal
        formPageModal.textContent = subjectCode || 'this schedule';
        document.getElementById('delete_schedule_id').value = id;
        document.getElementById('deleteScheduleModal').classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        return;
    }
    
    // Use unified _delete_modal.html (schedule_class.html, schedule_room.html, etc.)
    document.getElementById('delete_schedule_id').value = id;
    document.getElementById('delete_schedule_type').value = 'class';
    document.getElementById('delete_schedule_info').textContent = subjectCode;
    document.getElementById('deleteScheduleModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

function closeDeleteScheduleModal() {
    document.getElementById('deleteScheduleModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
}

async function executeDeleteSchedule() {
    const scheduleId = document.getElementById('delete_schedule_id').value;
    const scheduleType = document.getElementById('delete_schedule_type').value;
    const confirmBtn = document.getElementById('confirmDeleteScheduleBtn');
    
    if (!scheduleId) return;
    
    // Disable button to prevent double-click
    const originalHTML = confirmBtn.innerHTML;
    confirmBtn.disabled = true;
    confirmBtn.innerHTML = `
        <span class="flex items-center gap-2">
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            Deleting...
        </span>
    `;
    
    try {
        let url, body;
        if (scheduleType === 'exam') {
            url = '/exam-schedule/delete-ajax';
            body = JSON.stringify({ exam_schedule_id: parseInt(scheduleId) });
        } else {
            url = '/schedule/delete-ajax';
            body = JSON.stringify({ schedule_id: parseInt(scheduleId) });
        }
        
        const response = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: body
        });
        const result = await response.json();
        
        if (result.success) {
            // Close the modal
            closeDeleteScheduleModal();
            
            // Show success toast
            if (typeof showToast === 'function') {
                showToast(result.message || 'Schedule deleted successfully!', 'success');
            }
            
            // Refresh the right panel based on current page
            _refreshCurrentViewPanel();
        } else {
            if (typeof showToast === 'function') {
                showToast(result.error || 'Failed to delete schedule.', 'error');
            }
        }
    } catch (err) {
        console.error('Delete error:', err);
        if (typeof showToast === 'function') {
            showToast('Network error: ' + err.message, 'error');
        }
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.innerHTML = originalHTML;
    }
}

/**
 * Refresh the right detail panel on the current view page after a delete.
 * Determines the page type from window.SCHEDULE_PAGE and the selected entity
 * from URL params, then re-calls the appropriate select* function.
 */
function _refreshCurrentViewPanel() {
    const page = window.SCHEDULE_PAGE;
    const urlParams = new URLSearchParams(window.location.search);
    
    if (page === 'class') {
        const sectionId = urlParams.get('section_id');
        if (sectionId) {
            // Find section name from the highlighted list item
            const selectedItem = document.querySelector('.section-list-item.selected');
            const sectionName = selectedItem ? selectedItem.textContent.trim() : '';
            selectSection(parseInt(sectionId), sectionName);
        }
    } else if (page === 'faculty') {
        const facultyId = urlParams.get('faculty_id');
        if (facultyId) {
            const selectedItem = document.querySelector('.faculty-list-item.selected');
            const facultyName = selectedItem ? selectedItem.textContent.trim() : '';
            selectFaculty(parseInt(facultyId), facultyName);
        }
    } else if (page === 'room') {
        const roomId = urlParams.get('room_id');
        if (roomId) {
            const selectedItem = document.querySelector('.room-list-item.selected');
            const roomNumber = selectedItem ? selectedItem.textContent.trim() : '';
            selectRoom(parseInt(roomId), roomNumber);
        }
    } else if (page === 'exam') {
        const sectionId = urlParams.get('section_id');
        if (sectionId) {
            const selectedItem = document.querySelector('#examSectionList .section-list-item.selected');
            const sectionName = selectedItem ? selectedItem.textContent.trim() : '';
            selectExamSection(parseInt(sectionId), sectionName);
        }
    }
}

// ============================================================================
// Batch Delete: Select and delete multiple schedules at once
// ============================================================================

let _batchDeleteMode = { class: false, exam: false, faculty: false, room: false };

function toggleBatchDeleteMode(type) {
    if (_batchDeleteMode[type]) {
        cancelBatchDeleteMode(type);
    } else {
        enterBatchDeleteMode(type);
    }
}

function enterBatchDeleteMode(type) {
    _batchDeleteMode[type] = true;
    const prefix = type;
    const toolbar = document.getElementById(prefix + 'BatchToolbar');
    const toggleBtn = document.getElementById(prefix + 'BatchDeleteToggle');
    const checkCols = document.querySelectorAll('.' + prefix + 'BatchCheckCol');

    if (toolbar) toolbar.style.display = 'flex';
    if (toggleBtn) {
        toggleBtn.classList.remove('bg-red-50', 'text-red-600', 'border-red-200');
        toggleBtn.classList.add('bg-red-600', 'text-white', 'border-red-600');
    }
    checkCols.forEach(col => col.classList.remove('hidden'));

    // Reset all checkboxes
    const checks = document.querySelectorAll('.' + prefix + 'BatchCheck');
    checks.forEach(c => { c.checked = false; });
    const selectAll = document.getElementById(prefix + 'SelectAll');
    if (selectAll) selectAll.checked = false;
    updateBatchDeleteCount(type);
}

function cancelBatchDeleteMode(type) {
    _batchDeleteMode[type] = false;
    const prefix = type;
    const toolbar = document.getElementById(prefix + 'BatchToolbar');
    const toggleBtn = document.getElementById(prefix + 'BatchDeleteToggle');
    const checkCols = document.querySelectorAll('.' + prefix + 'BatchCheckCol');

    if (toolbar) toolbar.style.display = 'none';
    if (toggleBtn) {
        toggleBtn.classList.remove('bg-red-600', 'text-white', 'border-red-600');
        toggleBtn.classList.add('bg-red-50', 'text-red-600', 'border-red-200');
    }
    checkCols.forEach(col => col.classList.add('hidden'));

    // Uncheck everything
    const checks = document.querySelectorAll('.' + prefix + 'BatchCheck');
    checks.forEach(c => { c.checked = false; });
    const selectAll = document.getElementById(prefix + 'SelectAll');
    if (selectAll) selectAll.checked = false;
}

function toggleSelectAllSchedules(type, checked) {
    const checks = document.querySelectorAll('.' + type + 'BatchCheck');
    checks.forEach(c => { c.checked = checked; });
    updateBatchDeleteCount(type);
}

function onBatchCheckChange(type) {
    const checks = document.querySelectorAll('.' + type + 'BatchCheck');
    const selectAll = document.getElementById(type + 'SelectAll');
    const allChecked = Array.from(checks).every(c => c.checked);
    const someChecked = Array.from(checks).some(c => c.checked);
    if (selectAll) {
        selectAll.checked = allChecked;
        selectAll.indeterminate = someChecked && !allChecked;
    }
    updateBatchDeleteCount(type);
}

function updateBatchDeleteCount(type) {
    const checks = document.querySelectorAll('.' + type + 'BatchCheck:checked');
    const count = checks.length;
    const countEl = document.getElementById(type + 'SelectedCount');
    const deleteBtn = document.getElementById(type + 'DeleteSelectedBtn');
    if (countEl) countEl.textContent = count + ' selected';
    if (deleteBtn) deleteBtn.disabled = (count === 0);
}

function getSelectedScheduleIds(type) {
    const checks = document.querySelectorAll('.' + type + 'BatchCheck:checked');
    return Array.from(checks).map(c => parseInt(c.value));
}

function executeBatchDelete(type) {
    const ids = getSelectedScheduleIds(type);
    if (ids.length === 0) return;

    const label = type === 'exam' ? 'exam schedule' : 'class schedule';
    const plural = ids.length === 1 ? label : label + 's';

    showBatchDeleteConfirmModal(type, ids, plural);
}

function showBatchDeleteConfirmModal(type, ids, plural) {
    const existing = document.getElementById('batchDeleteConfirmModal');
    if (existing) existing.remove();

    const modal = document.createElement('div');
    modal.id = 'batchDeleteConfirmModal';
    modal.className = 'fixed inset-0 z-[80] flex items-center justify-center';
    modal.innerHTML = `
        <div class="fixed inset-0 bg-black/40" onclick="closeBatchDeleteConfirmModal()"></div>
        <div class="relative bg-white rounded-xl shadow-2xl w-full max-w-sm mx-4 overflow-hidden">
            <div class="px-5 py-4 border-b border-gray-100">
                <h3 class="text-sm font-semibold text-gray-900 flex items-center gap-2">
                    <svg class="w-4 h-4 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z"></path>
                    </svg>
                    Batch Delete
                </h3>
            </div>
            <div class="px-5 py-4">
                <p class="text-sm text-gray-600">Are you sure you want to delete <strong>${ids.length} ${plural}</strong>? This action cannot be undone.</p>
            </div>
            <div class="px-5 py-3 border-t border-gray-100 bg-gray-50 flex justify-end gap-2">
                <button onclick="closeBatchDeleteConfirmModal()" class="px-3 py-1.5 text-xs font-medium text-gray-600 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors">Cancel</button>
                <button id="batchDeleteConfirmBtn" class="px-4 py-1.5 text-xs font-medium text-white bg-red-600 hover:bg-red-700 rounded-lg transition-colors">Delete ${ids.length} ${plural}</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);

    document.getElementById('batchDeleteConfirmBtn').addEventListener('click', () => {
        closeBatchDeleteConfirmModal();
        doBatchDelete(type, ids);
    });
}

function closeBatchDeleteConfirmModal() {
    const modal = document.getElementById('batchDeleteConfirmModal');
    if (modal) modal.remove();
}

async function doBatchDelete(type, ids) {
    const deleteBtn = document.getElementById(type + 'DeleteSelectedBtn');
    if (deleteBtn) {
        deleteBtn.disabled = true;
        deleteBtn.innerHTML = '<svg class="w-3.5 h-3.5 mr-1 inline animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg> Deleting...';
    }

    const url = type === 'exam' ? '/exam-schedule/batch-delete' : '/schedule/batch-delete';
    const bodyKey = 'schedule_ids';

    try {
        const resp = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ [bodyKey]: ids })
        });
        const data = await resp.json();

        if (data.success) {
            if (typeof showToast === 'function') showToast(data.message, 'success');

            // Remove deleted rows from the table
            ids.forEach(id => {
                const row = document.querySelector(`tr[data-schedule-id="${id}"]`);
                if (row) {
                    row.style.transition = 'opacity 0.3s, transform 0.3s';
                    row.style.opacity = '0';
                    row.style.transform = 'translateX(-10px)';
                    setTimeout(() => row.remove(), 300);
                }
            });

            // Exit batch mode after short delay
            setTimeout(() => {
                cancelBatchDeleteMode(type);
                // Reload page to update counts
                setTimeout(() => window.location.reload(), 500);
            }, 400);
        } else {
            if (typeof showToast === 'function') showToast(data.error || 'Batch delete failed', 'error');
            if (deleteBtn) {
                deleteBtn.disabled = false;
                deleteBtn.innerHTML = '<svg class="w-3.5 h-3.5 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg> Delete Selected';
            }
        }
    } catch (err) {
        if (typeof showToast === 'function') showToast('Network error — please try again', 'error');
        if (deleteBtn) {
            deleteBtn.disabled = false;
            deleteBtn.innerHTML = '<svg class="w-3.5 h-3.5 mr-1 inline" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg> Delete Selected';
        }
    }
}

// ============================================================================
// Smart Scheduling: Auto-calculate time based on units
// ============================================================================

// Store subject data globally
let currentSubjectData = {
    add: null,
    edit: null
};

function handleSubjectChange(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const subjectSelect = document.getElementById('subject_id' + suffix);
    const selectedOption = subjectSelect.options[subjectSelect.selectedIndex];
    
    if (!selectedOption || !selectedOption.value) {
        // Hide schedule type container if no subject selected
        document.getElementById('scheduleTypeContainer' + suffix).classList.add('hidden');
        currentSubjectData[mode] = null;
        
        // Reset faculty to TBA when no subject selected
        loadFacultyForSubject(null, mode);
        
        // Reset room filtering — show all rooms including Court/Gym
        _filterRoomsBySubjectType(`room_dropdown_${mode}`, true, '');
        return;
    }
    
    // Get subject data from option's data attributes
    const subjectData = {
        id: selectedOption.value,
        code: selectedOption.dataset.code,
        description: selectedOption.dataset.description,
        lecUnits: parseFloat(selectedOption.dataset.lecUnits || 0),
        labUnits: parseFloat(selectedOption.dataset.labUnits || 0),
        totalUnits: parseFloat(selectedOption.dataset.totalUnits || 0)
    };
    
    currentSubjectData[mode] = subjectData;
    
    // Show schedule type options based on units
    showScheduleTypeOptions(mode, subjectData);
    
    // Load faculty assigned to this subject
    loadFacultyForSubject(subjectData.id, mode);
    
    // Keep room dropdown fully inclusive (all room types remain visible)
    const isPe = _isPeSubject(subjectData.code, subjectData.description);
    const schedType = document.getElementById('schedule_type' + (mode === 'add' ? '_add' : '_edit'))?.value || '';
    _filterRoomsBySubjectType(`room_dropdown_${mode}`, isPe, schedType);
}

function showScheduleTypeOptions(mode, subjectData) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const selectElement = document.getElementById('schedule_type' + suffix);
    
    // Show the schedule type container (may have been hidden when no subject was selected)
    const scheduleTypeContainer = document.getElementById('scheduleTypeContainer' + suffix);
    if (scheduleTypeContainer) {
        scheduleTypeContainer.classList.remove('hidden');
    }
    
    const hasLec = subjectData.lecUnits > 0;
    const hasLab = subjectData.labUnits > 0;
    
    // Update dropdown option text with units
    const lectureOption = document.getElementById('lectureOption' + suffix);
    const labOption = document.getElementById('labOption' + suffix);
    
    lectureOption.textContent = `Lecture (${subjectData.lecUnits} units)`;
    labOption.textContent = `Lab (${subjectData.labUnits} units)`;
    
    // Enable/disable options based on subject units
    lectureOption.disabled = !hasLec;
    labOption.disabled = !hasLab;

    // Show/hide the "Both" option and update its label with combined units
    const bothOption = document.getElementById('bothOption' + suffix);
    if (bothOption) {
        bothOption.style.display = (hasLec && hasLab) ? '' : 'none';
        if (hasLec && hasLab) {
            const combinedUnits = subjectData.lecUnits + subjectData.labUnits;
            bothOption.textContent = `Lecture & Lab (${combinedUnits} units)`;
        }
    }

    // Update the lab units tag inside the labScheduleSection
    const labUnitsTag = document.getElementById('labUnitsTag' + suffix);
    if (labUnitsTag && hasLab) {
        labUnitsTag.textContent = `(${subjectData.labUnits} units)`;
    }
    
    // Auto-select only when there's exactly one type; if both exist let user choose
    if (hasLec && hasLab) {
        selectElement.value = ''; // Keep "Select type..." so user must pick
    } else if (hasLec) {
        selectElement.value = 'lecture';
    } else if (hasLab) {
        selectElement.value = 'lab';
    }
    
    // Trigger change to update duration info
    handleScheduleTypeChange(mode);
}

function handleScheduleTypeChange(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const subjectData = currentSubjectData[mode];
    
    if (!subjectData) return;
    
    const scheduleType = document.getElementById('schedule_type' + suffix).value;
    
    if (!scheduleType) {
        return;
    }

    // Show/hide the lab extra fields section (add mode only)
    if (mode === 'add') {
        const labSection = document.getElementById('labScheduleSection_add');
        if (labSection) {
            labSection.classList.toggle('hidden', scheduleType !== 'both');
        }
    }
    
    // Store units for auto-calculation based on schedule type
    let units = 0;
    if (scheduleType === 'lecture') {
        units = subjectData.lecUnits;
    } else if (scheduleType === 'lab') {
        units = subjectData.labUnits;
    } else if (scheduleType === 'both') {
        units = subjectData.lecUnits; // use lecture units for the main (lecture) time block
    }
    
    // Store units in start time input for auto-calculation
    const startTimeInput = document.getElementById('start_time' + suffix);
    if (startTimeInput) {
        startTimeInput.dataset.durationUnits = units;
        
        // Show auto-calc badge
        const badge = document.getElementById('autoCalcBadge' + suffix);
        if (badge && units > 0) {
            badge.classList.remove('hidden');
        }
    }
    
    // Maintain inclusive room dropdown after schedule type changes
    const subData = currentSubjectData[mode];
    if (subData) {
        const isPeSubj = _isPeSubject(subData.code, subData.description);
        _filterRoomsBySubjectType(`room_dropdown_${mode}`, isPeSubj, scheduleType);
    }

    // Trigger automatic conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

function selectScheduleType(mode, type) {
    // Legacy function - now just updates dropdown
    const suffix = mode === 'add' ? '_add' : '_edit';
    const selectElement = document.getElementById('schedule_type' + suffix);
    selectElement.value = type;
    handleScheduleTypeChange(mode);
}

function updateTimeDurationInfo(mode, type, units) {
    // Function kept for compatibility but no longer displays UI panel
    // Units calculation still available if needed by other functions
}

function calculateEndTime(mode) {
    // Skip if this is being triggered by applyTimeSlot (AI recommendation)
    if (window.skipCalculateEndTime) {
        return;
    }
    
    const suffix = mode === 'add' ? '_add' : '_edit';
    const startTimeInput = document.getElementById('start_time' + suffix);
    const endTimeInput = document.getElementById('end_time' + suffix);
    
    const startTime = startTimeInput.value;
    
    // Try to get units from data attribute first, then from currentSubjectData
    let units = parseFloat(startTimeInput.dataset.durationUnits || 0);
    
    // If no units in data attribute, try to get from currentSubjectData
    if (units === 0 && currentSubjectData[mode]) {
        const scheduleType = document.getElementById('schedule_type' + suffix)?.value;
        if (scheduleType === 'lecture') {
            units = currentSubjectData[mode].lecUnits || 0;
        } else if (scheduleType === 'lab') {
            units = currentSubjectData[mode].labUnits || 0;
        }
        
        // Store units in data attribute for next time
        if (units > 0) {
            startTimeInput.dataset.durationUnits = units;
        }
    }
    
    if (!startTime || units === 0) {
        return;
    }
    
    // Parse start time
    const [hours, minutes] = startTime.split(':').map(Number);
    const startDate = new Date();
    startDate.setHours(hours, minutes, 0, 0);
    
    // Calculate duration based on subject type and units
    // Rules:
    //   - LEC+LAB subject: 2 units = 3hrs (180min), 1 unit = 2hrs (120min)
    //   - LEC-only subject (no lab): always 3hrs (180min)
    let durationMinutes;
    const subjectInfo = currentSubjectData[mode];
    const scheduleType = document.getElementById('schedule_type' + suffix)?.value;
    const hasLec = subjectInfo && subjectInfo.lecUnits > 0;
    const hasLab = subjectInfo && subjectInfo.labUnits > 0;
    
    if (hasLec && hasLab) {
        // Subject has both LEC and LAB components
        if (units >= 2) {
            durationMinutes = 180; // 3 hours
        } else {
            durationMinutes = 120; // 2 hours
        }
    } else if (hasLec && !hasLab && scheduleType === 'lecture') {
        // LEC-only subject
        durationMinutes = 180; // always 3 hours
    } else {
        // Fallback: units * 60
        durationMinutes = units * 60;
    }
    startDate.setMinutes(startDate.getMinutes() + durationMinutes);
    
    // Format end time
    const endHours = String(startDate.getHours()).padStart(2, '0');
    const endMinutes = String(startDate.getMinutes()).padStart(2, '0');
    const calculatedEndTime = `${endHours}:${endMinutes}`;
    
    // Set the value for the dropdown/select element
    endTimeInput.value = calculatedEndTime;
    
    // If the calculated time doesn't exist in dropdown options, find nearest match
    if (endTimeInput.tagName === 'SELECT') {
        const options = Array.from(endTimeInput.options);
        const exactMatch = options.find(opt => opt.value === calculatedEndTime);
        
        if (!exactMatch) {
            // Find the closest time option that's >= calculated time
            const calculatedMinutes = hours * 60 + minutes + durationMinutes;
            let closestOption = null;
            let minDiff = Infinity;
            
            options.forEach(opt => {
                if (opt.value) {
                    const [optHours, optMinutes] = opt.value.split(':').map(Number);
                    const optTotalMinutes = optHours * 60 + optMinutes;
                    const diff = Math.abs(optTotalMinutes - calculatedMinutes);
                    
                    if (diff < minDiff) {
                        minDiff = diff;
                        closestOption = opt;
                    }
                }
            });
            
            if (closestOption) {
                endTimeInput.value = closestOption.value;
            }
        }
    }
    
    // Flash green to indicate auto-calculation
    // For custom time pickers, target the visible trigger button
    const flashTarget = getTimePickerVisualTarget(endTimeInput) || endTimeInput;
    flashTarget.classList.add('ring-2', 'ring-green-500');
    setTimeout(() => {
        flashTarget.classList.remove('ring-2', 'ring-green-500');
    }, 1000);
    
    // Show auto-calc badge
    const badge = document.getElementById('autoCalcBadge' + suffix);
    if (badge && units > 0) {
        badge.classList.remove('hidden');
    }

    // Trigger conflict check after auto-calculating end time
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

// Modals will only close when clicking the X button
// Outside click and Escape key closing has been disabled for better user experience

// Faculty Tab Functions
function selectFaculty(id, name) {
    // Save scroll position before navigation
    saveScrollPosition('facultyList', 'scheduleScrollPos_facultyList');
    
    // Update URL without page refresh
    const url = new URL(window.location.href);
    url.searchParams.set('faculty_id', id);
    window.history.pushState({}, '', url);
    
    // Show detail view on mobile
    if (typeof showFacultyDetail === 'function') {
        showFacultyDetail();
    }
    
    // Update UI: highlight selected item
    document.querySelectorAll('.faculty-list-item').forEach(item => {
        item.classList.remove('selected');
    });
    // Find and highlight the clicked item by matching the onclick content with exact ID
    const facultyItems = document.querySelectorAll('.faculty-list-item');
    facultyItems.forEach(item => {
        const onclick = item.getAttribute('onclick');
        // Use regex to match exact ID (not partial match like ID 1 matching 10, 11, etc.)
        if (onclick && onclick.match(new RegExp(`selectFaculty\\(${id}\\s*,`))) {
            item.classList.add('selected');
        }
    });
    
    // Show loading state
    const rightPanel = document.querySelector('#content-faculty #faculty-detail');
    let contentArea = null; // Declare outside to be accessible in catch block
    
    if (rightPanel) {
        // Find the content area (the scrollable div after the header)
        contentArea = rightPanel.querySelector('.flex-1.overflow-y-auto');
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p class="text-gray-600">Loading schedules...</p>
                    </div>
                </div>
            `;
        }
    }
    
    // Fetch schedules for selected faculty via AJAX
    fetch(`/schedule/faculty?faculty_id=${id}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        // Parse the response and extract the schedule content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the right panel content from the response
        const newRightPanel = doc.querySelector('#content-faculty #faculty-detail');
        if (newRightPanel && rightPanel) {
            rightPanel.innerHTML = newRightPanel.innerHTML;
            applySavedViewForTab('faculty');
        }
    })
    .catch(error => {
        console.error('Error loading schedules:', error);
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center text-red-600">
                        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p>Error loading schedules. Please try again.</p>
                    </div>
                </div>
            `;
        }
    });
}

// Room Tab Functions
function selectRoom(id, roomNumber) {
    // Save scroll position before navigation
    saveScrollPosition('roomList', 'scheduleScrollPos_roomList');
    
    // Update URL without page refresh
    const url = new URL(window.location.href);
    url.searchParams.set('room_id', id);
    window.history.pushState({}, '', url);
    
    // Show detail view on mobile
    if (typeof showRoomDetail === 'function') {
        showRoomDetail();
    }
    
    // Update UI: highlight selected item
    document.querySelectorAll('.room-list-item').forEach(item => {
        item.classList.remove('selected');
    });
    // Find and highlight the clicked item by matching the onclick content with exact ID
    const roomItems = document.querySelectorAll('.room-list-item');
    roomItems.forEach(item => {
        const onclick = item.getAttribute('onclick');
        // Use regex to match exact ID (not partial match like ID 1 matching 10, 11, etc.)
        if (onclick && onclick.match(new RegExp(`selectRoom\\(${id}\\s*,`))) {
            item.classList.add('selected');
        }
    });
    
    // Show loading state
    const rightPanel = document.querySelector('#content-room #room-detail');
    let contentArea = null; // Declare outside to be accessible in catch block
    
    if (rightPanel) {
        // Find the content area (the scrollable div after the header)
        contentArea = rightPanel.querySelector('.flex-1.overflow-y-auto');
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p class="text-gray-600">Loading schedules...</p>
                    </div>
                </div>
            `;
        }
    }
    
    // Fetch schedules for selected room via AJAX
    fetch(`/schedule/room?room_id=${id}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        // Parse the response and extract the schedule content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the right panel content from the response
        const newRightPanel = doc.querySelector('#content-room #room-detail');
        if (newRightPanel && rightPanel) {
            rightPanel.innerHTML = newRightPanel.innerHTML;
            applySavedViewForTab('room');
        }
    })
    .catch(error => {
        console.error('Error loading schedules:', error);
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center text-red-600">
                        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p>Error loading schedules. Please try again.</p>
                    </div>
                </div>
            `;
        }
    });
}

function filterRoomByBuilding(buildingId) {
    const url = new URL(window.location.href);
    if (buildingId) {
        url.searchParams.set('room_building_id', buildingId);
    } else {
        url.searchParams.delete('room_building_id');
    }
    window.history.replaceState({}, '', url);
    
    // Handle building groups
    const roomGroups = document.querySelectorAll('#roomList .room-group');
    roomGroups.forEach(group => {
        const groupBuildingId = group.getAttribute('data-building-id');
        if (buildingId === '' || groupBuildingId === buildingId) {
            group.style.display = '';
        } else {
            group.style.display = 'none';
        }
    });

    const roomItems = document.querySelectorAll('#roomList .room-list-item');
    let visibleCount = 0;
    
    roomItems.forEach(item => {
        const itemBuildingId = item.getAttribute('data-building-id');
        let shouldShow = false;
        
        if (buildingId === '') {
            shouldShow = true;
        } else if (itemBuildingId === buildingId) {
            shouldShow = true;
        } else if (itemBuildingId === '' && buildingId === 'none') {
            shouldShow = true;
        }
        
        if (shouldShow) {
            item.style.display = 'block';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('room-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

function filterFacultyByDepartment(departmentId) {
    const url = new URL(window.location.href);
    if (departmentId) {
        url.searchParams.set('faculty_department_id', departmentId);
    } else {
        url.searchParams.delete('faculty_department_id');
    }
    window.history.replaceState({}, '', url);
    
    // Handle department groups
    const facultyGroups = document.querySelectorAll('#facultyList .faculty-group');
    facultyGroups.forEach(group => {
        const groupDeptId = group.getAttribute('data-department-id');
        if (departmentId === '' || groupDeptId === departmentId) {
            group.style.display = '';
        } else {
            group.style.display = 'none';
        }
    });

    const facultyItems = document.querySelectorAll('#facultyList .faculty-list-item');
    let visibleCount = 0;
    
    facultyItems.forEach(item => {
        const itemDeptId = item.getAttribute('data-department-id');
        let shouldShow = false;
        
        if (departmentId === '') {
            shouldShow = true;
        } else if (itemDeptId === departmentId) {
            shouldShow = true;
        } else if (itemDeptId === '' && departmentId === 'none') {
            shouldShow = true;
        }
        
        if (shouldShow) {
            item.style.display = 'block';
            visibleCount++;
        } else {
            item.style.display = 'none';
        }
    });
    
    const badge = document.getElementById('faculty-count-badge');
    if (badge) {
        badge.textContent = visibleCount;
    }
}

// Exam Tab Functions
function selectExamSection(id, name) {
    // Save scroll position before navigation
    saveScrollPosition('examSectionList', 'scheduleScrollPos_examSectionList');
    
    // Update URL without page refresh
    const url = new URL(window.location.href);
    url.searchParams.set('section_id', id);
    window.history.pushState({}, '', url);
    if (typeof window.syncScheduleHeaderActions === 'function') {
        window.syncScheduleHeaderActions();
    }
    
    // Show detail view on mobile
    if (typeof showExamDetail === 'function') {
        showExamDetail();
    }
    
    // Update UI: highlight selected item
    document.querySelectorAll('#examSectionList .section-list-item').forEach(item => {
        item.classList.remove('selected');
    });
    // Find and highlight the clicked item by matching the onclick content with exact ID
    const examSectionItems = document.querySelectorAll('#examSectionList .section-list-item');
    examSectionItems.forEach(item => {
        const onclick = item.getAttribute('onclick');
        // Use regex to match exact ID (not partial match like ID 1 matching 10, 11, etc.)
        if (onclick && onclick.match(new RegExp(`selectExamSection\\(${id}\\s*,`))) {
            item.classList.add('selected');
        }
    });
    
    // Show loading state
    const rightPanel = document.querySelector('#content-exam #exam-detail');
    let contentArea = null; // Declare outside to be accessible in catch block
    
    if (rightPanel) {
        // Find the content area (the scrollable div after the header)
        contentArea = rightPanel.querySelector('.flex-1.overflow-y-auto');
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center">
                        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto mb-4"></div>
                        <p class="text-gray-600">Loading exam schedules...</p>
                    </div>
                </div>
            `;
        }
    }
    
    // Fetch exam schedules for selected section via AJAX
    fetch(`/schedule/exam?section_id=${id}`, {
        headers: {
            'X-Requested-With': 'XMLHttpRequest'
        }
    })
    .then(response => response.text())
    .then(html => {
        // Parse the response and extract the schedule content
        const parser = new DOMParser();
        const doc = parser.parseFromString(html, 'text/html');
        
        // Extract the right panel content from the response
        const newRightPanel = doc.querySelector('#content-exam #exam-detail');
        if (newRightPanel && rightPanel) {
            rightPanel.innerHTML = newRightPanel.innerHTML;
            applySavedViewForTab('exam');
        }
    })
    .catch(error => {
        console.error('Error loading exam schedules:', error);
        if (contentArea) {
            contentArea.innerHTML = `
                <div class="flex items-center justify-center h-full">
                    <div class="text-center text-red-600">
                        <svg class="w-12 h-12 mx-auto mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                        </svg>
                        <p>Error loading exam schedules. Please try again.</p>
                    </div>
                </div>
            `;
        }
    });
}

// Exam Schedule Modal Functions

// Track current exam modal mode: 'add' or 'edit'
window.examModalMode = 'add';
window.currentEditExamId = null;

/**
 * Set the exam modal UI based on mode (add or edit)
 */
function setExamModalMode(mode) {
    window.examModalMode = mode;
    
    const titleEl = document.getElementById('examModalTitle');
    const subtitleEl = document.getElementById('examModalSubtitle');
    const iconAdd = document.getElementById('examModalIconAdd');
    const iconEdit = document.getElementById('examModalIconEdit');
    const backToAddBtn = document.getElementById('backToAddExamBtn');
    const deleteBtn = document.getElementById('deleteExamScheduleBtn');
    const form = document.getElementById('addExamScheduleForm');
    const submitBtn = document.getElementById('submitExamScheduleAdd');
    const submitText = document.getElementById('submitExamScheduleAddText');
    
    // Unified page header elements
    const unifiedTitle = document.getElementById('unifiedPageTitle');
    const unifiedIconAdd = document.getElementById('unifiedIconAdd');
    const unifiedIconEdit = document.getElementById('unifiedIconEdit');
    
    if (mode === 'edit') {
        // Edit mode UI
        if (titleEl) titleEl.textContent = 'Edit Exam Schedule';
        if (subtitleEl) subtitleEl.textContent = 'Update the exam schedule details below';
        if (iconAdd) iconAdd.classList.add('hidden');
        if (iconEdit) iconEdit.classList.remove('hidden');
        if (backToAddBtn) { backToAddBtn.classList.remove('hidden'); backToAddBtn.style.display = 'flex'; }
        if (deleteBtn) { deleteBtn.classList.remove('hidden'); deleteBtn.style.display = 'flex'; }
        if (form) form.action = '/exam-schedule/edit';
        // Unified page header
        if (unifiedTitle) unifiedTitle.textContent = 'Edit Exam Schedule';
        if (unifiedIconAdd) unifiedIconAdd.classList.add('hidden');
        if (unifiedIconEdit) unifiedIconEdit.classList.remove('hidden');
        // Hide auto-generate in edit mode
        const autoGenExamBtn = document.getElementById('autoGenExamBtn');
        if (autoGenExamBtn) autoGenExamBtn.style.display = 'none';
        // Update submit button text when enabled
        if (submitText && submitBtn && !submitBtn.disabled) {
            submitText.textContent = 'Update Exam';
        }
    } else {
        // Add mode UI
        if (titleEl) titleEl.textContent = 'Add Exam Schedule';
        if (subtitleEl) subtitleEl.textContent = 'Create a new exam schedule entry';
        if (iconAdd) iconAdd.classList.remove('hidden');
        if (iconEdit) iconEdit.classList.add('hidden');
        if (backToAddBtn) { backToAddBtn.classList.add('hidden'); backToAddBtn.style.display = ''; }
        if (deleteBtn) { deleteBtn.classList.add('hidden'); deleteBtn.style.display = 'none'; }
        if (form) form.action = '/exam-schedule/add';
        // Unified page header
        if (unifiedTitle) unifiedTitle.textContent = 'Create Schedule';
        if (unifiedIconAdd) unifiedIconAdd.classList.remove('hidden');
        if (unifiedIconEdit) unifiedIconEdit.classList.add('hidden');
        // Show auto-generate if section selected
        const autoGenExamBtn = document.getElementById('autoGenExamBtn');
        if (autoGenExamBtn && window.FORM_SECTION_ID) autoGenExamBtn.style.display = 'flex';
        // Update submit button text when enabled
        if (submitText && submitBtn && !submitBtn.disabled) {
            submitText.textContent = 'Save Exam';
        }
    }
}

// Expose globally
window.setExamModalMode = setExamModalMode;

function openAddExamScheduleModal(sectionId) {
    // On view pages, navigate to the unified create page (exam tab)
    if (!window.SCHEDULE_FORM_MODE) {
        window.location.href = '/schedule/create?type=exam&section_id=' + sectionId;
        return;
    }
    // Set to add mode
    setExamModalMode('add');
    window.currentEditExamId = null;
    
    // Clear edit-specific fields
    document.getElementById('exam_schedule_id_add').value = '';
    document.getElementById('exam_schedule_version_add').value = '';
    
    // Close edit modal if open
    const editModal = document.getElementById('editExamScheduleModal');
    if (editModal && !editModal.classList.contains('hidden')) {
        closeEditExamScheduleModal();
    }
    
    document.getElementById('section_id_exam_add').value = sectionId;
    // On inline form pages, content is already visible - skip modal show/hide
    if (!window.INLINE_FORM_PAGE) {
        document.getElementById('addExamScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
    }
    
    // Load curricula for this section (which will then load subjects)
    loadCurriculaForSection(sectionId, 'exam_add');
    
    // Initialize the exam modal calendar
    initializeExamModalCalendar(sectionId);
}

/**
 * Initialize the exam modal calendar when opening the modal
 * @param {number} sectionId - Section ID to load exams for
 */
function initializeExamModalCalendar(sectionId) {
    // Set the section in the dropdown
    const switcher = document.getElementById('examModalSectionSwitcher');
    if (switcher) {
        switcher.value = sectionId;
    }
    
    // Get section name from the dropdown
    let sectionName = '';
    if (switcher && switcher.selectedIndex >= 0) {
        const selectedOption = switcher.options[switcher.selectedIndex];
        sectionName = selectedOption.dataset.name || selectedOption.textContent.trim();
    }
    
    // Render the calendar for this section
    if (typeof window.renderExamModalCalendar === 'function') {
        window.renderExamModalCalendar(sectionId, sectionName);
    }
}

function closeAddExamScheduleModal() {
    closeExamModal();
}

// Unified close function for exam modal
function closeExamModal() {
    // On inline form pages, navigate back instead of hiding modal
    if (window.INLINE_FORM_PAGE) {
        const sectionId = document.getElementById('section_id_exam_add')?.value;
        window.location.href = sectionId ? '/schedule/exam?section_id=' + sectionId : '/schedule/exam';
        return;
    }
    document.getElementById('addExamScheduleModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    document.getElementById('addExamScheduleForm').reset();
    
    // Clear edit fields
    document.getElementById('exam_schedule_id_add').value = '';
    document.getElementById('exam_schedule_version_add').value = '';
    window.currentEditExamId = null;
    
    // Reset to add mode for next open
    setExamModalMode('add');
    
    // Reset auto-check state for exam modal
    if (typeof resetAutoCheckExamState === 'function') {
        resetAutoCheckExamState('add');
    }
    
    // Clear exam modal calendar
    if (typeof window.clearExamModalCalendar === 'function') {
        window.clearExamModalCalendar();
    }
}

/**
 * Switch back from Edit mode to Add mode without closing the exam modal
 */
function switchBackToAddExamMode() {
    // Get current section ID to preserve it
    const sectionId = document.getElementById('section_id_exam_add')?.value;
    const sectionSwitcher = document.getElementById('examModalSectionSwitcher');
    const sectionName = sectionSwitcher?.options[sectionSwitcher.selectedIndex]?.text || '';
    
    // Reset to add mode
    setExamModalMode('add');
    window.currentEditExamId = null;
    
    // Clear edit-specific hidden fields
    const examIdField = document.getElementById('exam_schedule_id_add');
    const versionField = document.getElementById('exam_schedule_version_add');
    if (examIdField) examIdField.value = '';
    if (versionField) versionField.value = '';
    
    // Reset form fields but keep section selected
    const form = document.getElementById('addExamScheduleForm');
    if (form) form.reset();
    
    // Restore section ID after form reset
    if (sectionId) {
        document.getElementById('section_id_exam_add').value = sectionId;
        if (sectionSwitcher) sectionSwitcher.value = sectionId;
    }
    
    // Reset auto-check state
    if (typeof resetAutoCheckExamState === 'function') {
        resetAutoCheckExamState('add');
    }
    
    // Remove highlight from any selected exam in calendar/table
    document.querySelectorAll('.exam-modal-calendar-event.ring-2.ring-orange-500').forEach(el => {
        el.classList.remove('ring-2', 'ring-orange-500');
    });
    document.querySelectorAll('#examModalTableBody tr.bg-orange-50').forEach(el => {
        el.classList.remove('bg-orange-50');
    });
    
    // Reload curricula for the section (to reset dropdowns)
    if (sectionId && typeof loadCurriculaForSection === 'function') {
        loadCurriculaForSection(sectionId, 'exam_add');
    }
}

// Expose globally
window.closeExamModal = closeExamModal;
window.switchBackToAddExamMode = switchBackToAddExamMode;

/**
 * Load exam schedule for editing in the modal (called when clicking an exam event in the calendar)
 * @param {Object} examData - Exam schedule data object
 */
function loadExamForEditing(examData) {
    // Set to edit mode
    setExamModalMode('edit');
    window.currentEditExamId = examData.id;
    
    // Set hidden fields for edit
    const examIdField = document.getElementById('exam_schedule_id_add');
    const versionField = document.getElementById('exam_schedule_version_add');
    if (examIdField) examIdField.value = examData.id;
    if (versionField) versionField.value = examData.version || '';
    
    // Set section_id
    const sectionIdField = document.getElementById('section_id_exam_add');
    if (sectionIdField) sectionIdField.value = examData.section_id;
    
    // Set date, time fields immediately
    const examDateField = document.getElementById('exam_date_add');
    const startTimeField = document.getElementById('start_time_exam_add');
    const endTimeField = document.getElementById('end_time_exam_add');
    
    if (examDateField) examDateField.value = examData.exam_date || '';
    if (startTimeField) startTimeField.value = examData.start_time || '';
    if (endTimeField) endTimeField.value = examData.end_time || '';
    
    // Set faculty
    const facultyIdField = document.getElementById('faculty_id_exam_add');
    const facultySearchField = document.getElementById('faculty_search_exam_add');
    if (facultyIdField) facultyIdField.value = examData.faculty_id || '';
    if (facultySearchField) {
        facultySearchField.value = examData.faculty_name || '';
    }
    
    // Set room
    const roomIdField = document.getElementById('room_id_exam_add');
    const roomSearchField = document.getElementById('room_search_exam_add');
    if (roomIdField) roomIdField.value = examData.room_id || '';
    if (roomSearchField) {
        if (examData.room_number && examData.building_name) {
            roomSearchField.value = `${examData.room_number} - ${examData.building_name}`;
        } else if (examData.room_number) {
            roomSearchField.value = examData.room_number;
        } else {
            roomSearchField.value = '';
        }
    }
    
    // Load curriculum and subject
    if (typeof loadCurriculaForSectionEdit === 'function') {
        loadCurriculaForSectionEdit(examData.section_id, examData, 'exam_add');
    }
    
    // Highlight the clicked exam event
    highlightActiveExam(examData.id);
}

/**
 * Highlight the currently selected exam in calendar/table
 * @param {number} examId - Exam ID to highlight
 */
function highlightActiveExam(examId) {
    // Remove existing highlights
    document.querySelectorAll('.exam-modal-calendar-event.ring-2.ring-orange-500').forEach(el => {
        el.classList.remove('ring-2', 'ring-orange-500');
    });
    document.querySelectorAll('#examModalTableBody tr.bg-orange-50').forEach(el => {
        el.classList.remove('bg-orange-50');
    });
    
    // Add highlight to clicked exam
    const calendarEvent = document.querySelector(`.exam-modal-calendar-event[data-exam-id="${examId}"]`);
    if (calendarEvent) {
        calendarEvent.classList.add('ring-2', 'ring-orange-500');
    }
    
    const tableRow = document.querySelector(`#examModalTableBody tr[data-exam-id="${examId}"]`);
    if (tableRow) {
        tableRow.classList.add('bg-orange-50');
    }
}

// Expose globally
window.loadExamForEditing = loadExamForEditing;

// Edit exam schedule - uses unified modal (same as schedule)
function editExamSchedule(examScheduleId, examDataFromTemplate = null) {
    // On view pages, navigate to the dedicated exam edit form page
    if (!window.SCHEDULE_FORM_MODE) {
        window.location.href = '/schedule/exam/edit/' + examScheduleId;
        return;
    }
    
    // Helper function to process exam data and open modal
    const processExamData = (data) => {
        // Prepare exam data object matching loadExamForEditing expected format
        const examData = {
            id: data.id,
            section_id: data.section_id,
            subject_id: data.subject_id,
            curriculum_id: data.curriculum_id,
            faculty_id: data.faculty_id,
            faculty_name: data.faculty_name,
            room_id: data.room_id,
            room_number: data.room_number,
            building_name: data.building_name,
            exam_date: data.exam_date,
            start_time: data.start_time,
            end_time: data.end_time,
            version: data.version,
            schedule_type: data.schedule_type || 'lecture'
        };
        
        // Open the unified exam modal first (if not already open)
        if (!window.INLINE_FORM_PAGE) {
            const modal = document.getElementById('addExamScheduleModal');
            if (modal && modal.classList.contains('hidden')) {
                modal.classList.remove('hidden');
                document.body.classList.add('overflow-hidden');
            }
        }
        
        // Set section in section switcher
        const sectionSwitcher = document.getElementById('examModalSectionSwitcher');
        if (sectionSwitcher) {
            sectionSwitcher.value = data.section_id;
        }
        
        // Use the unified loadExamForEditing function
        loadExamForEditing(examData);
        
        // Render the modal calendar after a short delay
        if (typeof renderExamModalCalendar === 'function') {
            setTimeout(() => {
                const selectedOption = sectionSwitcher?.options[sectionSwitcher?.selectedIndex];
                const sectionName = selectedOption?.dataset?.name || selectedOption?.textContent?.trim() || '';
                renderExamModalCalendar(data.section_id, sectionName);
            }, 100);
        }
    };
    
    // If exam data is passed directly from template, use it immediately (faster)
    if (examDataFromTemplate) {
        processExamData(examDataFromTemplate);
    } else {
        // Otherwise, fetch from API
        fetch(`/exam-schedule/get/${examScheduleId}`)
            .then(response => response.json())
            .then(data => {
                processExamData(data);
            })
            .catch(error => {
                console.error('[EXAM EDIT] Error loading exam schedule:', error);
                if (typeof showToast === 'function') {
                    showToast('Error loading exam schedule data', 'error');
                }
            });
    }
}

function closeEditExamScheduleModal() {
    document.getElementById('editExamScheduleModal').classList.add('hidden');
    document.body.classList.remove('overflow-hidden');
    document.getElementById('editExamScheduleForm').reset();
    
    // Reset auto-check state for exam edit modal
    if (typeof resetAutoCheckExamState === 'function') {
        resetAutoCheckExamState('edit');
    }
}

function deleteExamSchedule(id, subjectCode) {
    // Check if we're on schedule_form.html (has its own exam delete modal)
    const formPageExamModal = document.getElementById('deleteExamScheduleModal');
    if (formPageExamModal) {
        // Use schedule_form.html's own exam delete modal
        const subjectInfo = document.getElementById('deleteExamSubjectInfo');
        if (subjectInfo) {
            subjectInfo.textContent = subjectCode || 'this exam schedule';
        }
        document.getElementById('delete_exam_schedule_id').value = id;
        formPageExamModal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
        return;
    }
    
    // Use unified _delete_modal.html (schedule_exam.html, schedule_class.html, etc.)
    document.getElementById('delete_schedule_id').value = id;
    document.getElementById('delete_schedule_type').value = 'exam';
    document.getElementById('delete_schedule_info').textContent = subjectCode + ' (Exam)';
    
    // Update modal title for exam
    const modalTitle = document.querySelector('#deleteScheduleModal h3');
    if (modalTitle) {
        modalTitle.textContent = 'Delete Exam Schedule';
    }
    
    // Update warning message for exam
    const warningText = document.querySelector('#deleteScheduleModal .text-xs.text-red-700');
    if (warningText) {
        warningText.textContent = 'This action cannot be undone. The exam schedule will be permanently removed.';
    }
    
    // Update button text for exam
    const btnText = document.querySelector('#confirmDeleteScheduleBtn span');
    if (btnText) {
        btnText.innerHTML = `
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path>
            </svg>
            Delete Exam
        `;
    }
    
    document.getElementById('deleteScheduleModal').classList.remove('hidden');
    document.body.classList.add('overflow-hidden');
}

// Load subjects for exam section
function loadSubjectsForExamSection(sectionId, mode, examData = null) {
    const suffix = mode === 'add' ? '_exam_add' : '_exam_edit';
    const subjectSelect = document.getElementById('subject_id' + suffix);
    const facultySelect = document.getElementById('faculty_id' + suffix);
    const roomSelect = document.getElementById('room_id' + suffix);
    const curriculumSelect = document.getElementById('curriculum_id' + suffix);
    
    if (!subjectSelect || !facultySelect || !roomSelect || !curriculumSelect) {
        console.error('Missing dropdown elements for exam modal');
        return Promise.reject('Missing dropdown elements');
    }
    
    // Show loading state
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // First load curricula for the section
    return fetch(`/schedule/get-curricula/${sectionId}`)
        .then(response => parseScheduleFullApiJson(response, 'Unable to load curricula'))
        .then(data => {
            curriculumSelect.innerHTML = '<option value="">Select Curriculum...</option>';
            
            if (data.curricula && data.curricula.length > 0) {
                data.curricula.forEach(curriculum => {
                    const option = document.createElement('option');
                    option.value = curriculum.id;
                    option.textContent = `${curriculum.curriculum_code} - ${curriculum.curriculum_name}`;
                    curriculumSelect.appendChild(option);
                });
                
                // If editing, we need to find which curriculum contains the subject
                if (examData && examData.subject_id) {
                    // Fetch subject details to get curriculum_id
                    return fetch(`/schedule/get-subject-details/${examData.subject_id}`)
                        .then(r => {
                            if (!r.ok) throw new Error('Subject not found');
                            return r.json();
                        })
                        .then(subjectData => {
                            if (subjectData && subjectData.curriculum_id) {
                                curriculumSelect.value = subjectData.curriculum_id;
                                // Now load subjects for that curriculum and select the subject
                                return loadSubjectsForExamCurriculum(mode, examData.subject_id);
                            } else {
                                subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
                                subjectSelect.disabled = true;
                                return Promise.resolve();
                            }
                        })
                        .catch(error => {
                            console.error('Error fetching subject details:', error);
                            subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
                            subjectSelect.disabled = true;
                            return Promise.resolve();
                        });
                } else {
                    // Add mode - wait for user to select curriculum
                    subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
                    subjectSelect.disabled = true;
                    return Promise.resolve();
                }
            } else {
                subjectSelect.innerHTML = '<option value="">No curricula available</option>';
                subjectSelect.disabled = true;
                return Promise.resolve();
            }
        })
        .then(() => {
            // Load faculty and rooms
            return Promise.all([
                fetch('/schedule/get-all-faculty').then(r => r.json()),
                fetch('/schedule/get-all-rooms').then(r => r.json())
            ]);
        })
        .then(([facultyData, roomData]) => {
            // Populate faculty dropdown
            facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
            if (facultyData.faculty && facultyData.faculty.length > 0) {
                facultyData.faculty.forEach(fac => {
                    const option = document.createElement('option');
                    option.value = fac.id;
                    option.textContent = fac.full_name;
                    facultySelect.appendChild(option);
                });
                
                // If editing, select the current faculty
                if (examData && examData.faculty_id) {
                    facultySelect.value = examData.faculty_id;
                }
            }
            
            // Populate room dropdown
            roomSelect.innerHTML = '<option value="">Select a room...</option>';
            if (roomData.rooms && roomData.rooms.length > 0) {
                roomData.rooms.forEach(room => {
                    const option = document.createElement('option');
                    option.value = room.id;
                    option.textContent = room.display || room.room_number;
                    roomSelect.appendChild(option);
                });
                
                // If editing, select the current room
                if (examData && examData.room_id) {
                    roomSelect.value = examData.room_id;
                }
            }
        })
        .catch(error => {
            console.error('Error loading exam data:', error);
            subjectSelect.innerHTML = '<option value="">Error loading subjects</option>';
            subjectSelect.disabled = false;
            if (typeof showToast === 'function') {
                showToast(error.message || 'Error loading curricula', 'error');
            }
            throw error;
        });
}

// Load subjects when curriculum is selected in exam modal
function loadSubjectsForExamCurriculum(mode, selectedSubjectId = null) {
    const suffix = mode === 'add' ? '_exam_add' : '_exam_edit';
    const curriculumId = document.getElementById('curriculum_id' + suffix).value;
    const subjectSelect = document.getElementById('subject_id' + suffix);
    
    if (!curriculumId) {
        subjectSelect.innerHTML = '<option value="">Select curriculum first...</option>';
        subjectSelect.disabled = true;
        return Promise.resolve();
    }
    
    subjectSelect.innerHTML = '<option value="">Loading subjects...</option>';
    subjectSelect.disabled = true;
    
    // Use filtered get-subjects route when section is available (filters by year level + semester)
    const sectionId = document.getElementById('section_id_exam_add')?.value
                   || document.getElementById('section_id' + suffix)?.value;
    const url = sectionId
        ? `/schedule/get-subjects/${sectionId}?curriculum_id=${curriculumId}`
        : `/schedule/get-subjects-by-curriculum/${curriculumId}`;
    
    return fetch(url)
        .then(response => response.json())
        .then(data => {
            subjectSelect.innerHTML = '<option value="">Select a subject</option>';
            
            if (data.subjects && data.subjects.length > 0) {
                data.subjects.forEach(subject => {
                    const option = document.createElement('option');
                    option.value = subject.id;
                    option.textContent = subject.display;
                    // Set data attributes for PE detection and schedule type
                    option.dataset.code = subject.subject_code;
                    option.dataset.description = subject.course_description;
                    option.dataset.lecUnits = subject.lec_units;
                    option.dataset.labUnits = subject.lab_units;
                    option.dataset.totalUnits = subject.total_units;
                    subjectSelect.appendChild(option);
                });
                
                // If we have a selected subject ID (edit mode), set it
                if (selectedSubjectId) {
                    subjectSelect.value = selectedSubjectId;
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
        });
}

// Modals will only close when clicking the X button (exam modals)
// Outside click closing has been disabled for better user experience

// ============================================================================
// AI Decision Support System
// ============================================================================

function checkScheduleWithAI(mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    
    // Get form data
    const sectionId = document.getElementById('section_id' + suffix).value;
    const subjectId = document.getElementById('subject_id' + suffix).value || null;
    const facultyId = document.getElementById('faculty_id' + suffix).value || null;
    const roomId = document.getElementById('room_id' + suffix).value || null;
    const dayOfWeek = document.getElementById('day_of_week' + suffix).value;
    const startTime = document.getElementById('start_time' + suffix).value;
    const endTime = document.getElementById('end_time' + suffix).value;
    const scheduleId = mode === 'edit' ? document.getElementById('schedule_id_edit').value : null;
    
    // Debug logging
    // Validate required fields
    if (!sectionId || !dayOfWeek || !startTime || !endTime) {
        const missing = [];
        if (!sectionId) missing.push('Section');
        if (!dayOfWeek) missing.push('Day');
        if (!startTime) missing.push('Start Time');
        if (!endTime) missing.push('End Time');
        showToast(`Please fill in: ${missing.join(', ')}`, 'error');
        return;
    }
    
    // Show loading state
    const aiPanel = document.getElementById('aiAssistant' + (mode === 'add' ? 'Add' : 'Edit'));
    const explanationEl = document.getElementById('aiExplanation' + (mode === 'add' ? 'Add' : 'Edit'));
    
    aiPanel.classList.remove('hidden');
    explanationEl.textContent = '🤔 Analyzing schedule with AI...';
    
    // Hide conflicts and recommendations
    document.getElementById('aiConflicts' + (mode === 'add' ? 'Add' : 'Edit')).classList.add('hidden');
    document.getElementById('aiRecommendations' + (mode === 'add' ? 'Add' : 'Edit')).classList.add('hidden');
    
    // Prepare request data
    const requestData = {
        section_id: parseInt(sectionId),
        subject_id: subjectId ? parseInt(subjectId) : null,
        faculty_id: facultyId ? parseInt(facultyId) : null,
        room_id: roomId ? parseInt(roomId) : null,
        day_of_week: dayOfWeek,
        start_time: startTime,
        end_time: endTime,
        schedule_id: scheduleId ? parseInt(scheduleId) : null
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
                console.error('[AI CHECK] Error response:', text);
                throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`);
            });
        }
        return response.json();
    })
    .then(data => {
        if (!data.ai_enabled) {
            explanationEl.textContent = 'Detailed insights are not enabled. Configure your Gemini API key to use this feature.';
            return;
        }
        
        if (data.error) {
            explanationEl.textContent = `❌ Error: ${data.error}`;
            showToast(data.error, 'error');
            return;
        }
        
        if (data.has_conflicts) {
            displayAIConflicts(data.conflicts, mode);
            displayAIRecommendations(data.recommendations, mode);
            explanationEl.textContent = data.ai_explanation || 'Conflicts detected. See recommendations below.';
        } else {
            explanationEl.textContent = '✅ No conflicts detected! This schedule looks good.';
            showToast('No conflicts found - schedule is clear!', 'success');
        }
    })
    .catch(error => {
        console.error('[AI CHECK] Error:', error);
        explanationEl.textContent = `❌ ${error.message}`;
        showToast('Error checking with AI', 'error');
    });
}

function displayAIConflicts(conflicts, mode) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const conflictsContainer = document.getElementById('aiConflicts' + suffix);
    const conflictsList = document.getElementById('aiConflictsList' + suffix);
    const isDetailedMode = typeof isDetailedAssistantMode === 'function'
        ? isDetailedAssistantMode()
        : (typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : false);
    
    // Clear list
    if (conflictsList) conflictsList.innerHTML = '';
    
    // Render conflicts with stronger hierarchy and calmer spacing
    if (conflictsList) {
        conflicts.forEach((conflict, index) => {
            const severity = conflict.severity || 'high';
            const severityConfig = getSeverityConfig(severity);
            const details = conflict.details || {};
            const conflictType = (conflict.type || 'conflict').replace(/_/g, ' ');
            
            // Build detail fragments separated by ·
            const detailParts = [];
            if (details.subject) detailParts.push(details.subject);
            if (details.day) detailParts.push(details.day);
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
                    <div class="mb-1">
                        <span class="text-[10px] font-medium text-gray-500 dark:text-gray-400 capitalize tracking-wide">${conflictType}</span>
                    </div>
                `
                : '';
            
            const conflictDiv = document.createElement('div');
            conflictDiv.className = isDetailedMode
                ? `mb-2.5 last:mb-0 rounded-xl border ${severityConfig.cardClass} bg-white dark:bg-gray-900/35 p-3 shadow-sm`
                : 'mb-2 last:mb-0 rounded-lg border border-gray-200/90 dark:border-gray-700 bg-white dark:bg-gray-900/25 p-2.5';
            conflictDiv.innerHTML = `
                <div class="flex items-start gap-2.5">
                    <span class="mt-1 w-2 h-2 rounded-full ${severityConfig.dotClass} flex-shrink-0"></span>
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
 * Get icon SVG based on conflict type
 */
function getConflictTypeIcon(type) {
    const icons = {
        section: '<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"></path></svg>',
        faculty: '<svg class="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>',
        room: '<svg class="w-4 h-4 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>',
        duplicate: '<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"></path></svg>',
        time_invalid: '<svg class="w-4 h-4 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>',
        proctor_unavailable: '<svg class="w-4 h-4 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>'
    };
    return icons[type] || icons.section;
}

/**
 * Get styling configuration based on conflict severity
 */
function getSeverityConfig(severity) {
    const configs = {
        critical: {
            cardClass: 'border-red-200 bg-red-50/90 dark:border-red-900/50 dark:bg-red-900/20',
            messageClass: 'text-red-800 dark:text-red-300',
            dotClass: 'bg-red-500 dark:bg-red-400',
            badgeClass: 'text-red-700 dark:text-red-300'
        },
        high: {
            cardClass: 'border-orange-200 bg-orange-50/90 dark:border-orange-900/50 dark:bg-orange-900/20',
            messageClass: 'text-orange-800 dark:text-orange-300',
            dotClass: 'bg-orange-500 dark:bg-orange-400',
            badgeClass: 'text-orange-700 dark:text-orange-300'
        },
        medium: {
            cardClass: 'border-amber-200 bg-amber-50/90 dark:border-amber-900/50 dark:bg-amber-900/20',
            messageClass: 'text-amber-800 dark:text-amber-300',
            dotClass: 'bg-amber-500 dark:bg-amber-400',
            badgeClass: 'text-amber-700 dark:text-amber-300'
        },
        low: {
            cardClass: 'border-blue-200 bg-blue-50/90 dark:border-blue-900/50 dark:bg-blue-900/20',
            messageClass: 'text-blue-800 dark:text-blue-300',
            dotClass: 'bg-blue-500 dark:bg-blue-400',
            badgeClass: 'text-blue-700 dark:text-blue-300'
        }
    };
    return configs[severity] || configs.high;
}

function displayAIRecommendations(recommendations, mode, readOnly) {
    const suffix = mode === 'add' ? 'Add' : 'Edit';
    const recommendationsContainer = document.getElementById('aiRecommendations' + suffix);
    const recommendationsList = document.getElementById('aiRecommendationsList' + suffix);
    const basicHint = document.getElementById('aiBasicModeHint' + suffix);
    const recsHeader = document.getElementById('aiRecommendationsHeader' + suffix);
    const isDetailedMode = typeof isDetailedAssistantMode === 'function'
        ? isDetailedAssistantMode()
        : (typeof isAiToggleEnabled === 'function' ? isAiToggleEnabled() : false);
    
    // Clear list
    if (recommendationsList) recommendationsList.innerHTML = '';
    
    if (recommendations.length === 0) {
        if (recommendationsContainer) recommendationsContainer.classList.add('hidden');
        return;
    }
    
    // Lightweight type config: thin border + emoji label
    const typeConfig = {
        time_slot: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-emerald-50/70 dark:hover:bg-emerald-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-emerald-300 dark:hover:border-emerald-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Best Time Options'
        },
        day: {
            border: 'border-gray-200 dark:border-gray-700',
            btnBg: 'bg-white dark:bg-gray-800 hover:bg-indigo-50/70 dark:hover:bg-indigo-900/20',
            btnBorder: 'border-gray-200 dark:border-gray-700 hover:border-indigo-300 dark:hover:border-indigo-600/60',
            btnText: 'text-gray-700 dark:text-gray-200',
            badgeBg: 'bg-gray-100 dark:bg-gray-700', badgeText: 'text-gray-600 dark:text-gray-300',
            label: 'Alternative Days'
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
            label: 'Available Faculty'
        }
    };
    
    // Generate unique IDs for collapsible sections
    const sectionId = `rec_${mode}_${Date.now()}`;
    
    recommendations.forEach((rec, recIndex) => {
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
                    html += generateOptionButton(opt, idx, type, config, mode, false, isDetailedMode);
                });
                
                html += '</div>';
                
                // Add "show more" section if there are hidden options
                if (hiddenOptions.length > 0) {
                    html += `
                        <div id="moreOptions_${uniqueId}" class="hidden mt-2">
                            <div class="grid grid-cols-1 gap-1.5">
                                ${hiddenOptions.map((opt, idx) => generateOptionButton(opt, idx + maxVisibleOptions, type, config, mode, false, isDetailedMode)).join('')}
                            </div>
                        </div>
                        <button type="button" onclick="toggleMoreOptions('${uniqueId}', this)" data-more-count="${hiddenOptions.length}"
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
                <button type="button" onclick="toggleRecommendationSection('${uniqueId}')" 
                        class="${sectionButtonClass}">
                    <span class="text-xs font-semibold text-gray-700 dark:text-gray-200">${config.label}</span>
                    <div class="flex items-center gap-1.5">
                        <span class="text-[10px] font-semibold ${config.badgeBg} ${config.badgeText} px-1.5 py-0.5 rounded-full">${rec.options.length}</span>
                        <svg id="chevron_${uniqueId}" class="w-3.5 h-3.5 text-gray-400 dark:text-gray-500 transition-transform ${isExpanded ? 'rotate-180' : ''}" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7"></path>
                        </svg>
                    </div>
                </button>
                <div id="content_${uniqueId}" class="${sectionBodyClass} ${isExpanded ? '' : 'hidden'}">
                    ${generateOptionsHTML(rec.options, rec.type)}
                </div>
            `;
            
            recommendationsList.appendChild(recDiv);
        }
    });
    
    if (recommendationsContainer) recommendationsContainer.classList.remove('hidden');

    // Show/hide Quick mode hint
    if (basicHint) {
        basicHint.classList.toggle('hidden', isDetailedMode);
    }

    // Update recommendations header subtitle based on mode
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
function getConfidenceBadgeClass(confidence) {
    if (confidence >= 80) return 'bg-emerald-100 text-emerald-700 ring-1 ring-emerald-300';
    if (confidence >= 60) return 'bg-blue-100 text-blue-700 ring-1 ring-blue-300';
    if (confidence >= 40) return 'bg-amber-100 text-amber-700 ring-1 ring-amber-300';
    return 'bg-red-100 text-red-700 ring-1 ring-red-300';
}

/**
 * Generate option button HTML based on type
 */
function generateOptionButton(opt, idx, type, config, mode, readOnly, detailedMode = false) {
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
    
    if (type === 'time_slot') {
        return `<button type="button" onclick="applyTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" class="${baseClasses}">
            ${buildTextContent(opt.display)}
        </button>`;
    } else if (type === 'day') {
        return `<button type="button" onclick="applyDay('${opt.day}', '${mode}')" class="${baseClasses}">
            ${buildTextContent(opt.day)}
        </button>`;
    } else if (type === 'room') {
        const roomName = opt.display.split(' (')[0];
        const building = opt.display.includes('(') ? ' (' + opt.display.split('(')[1] : '';
        return `<button type="button" onclick="applyRoom(${opt.room_id}, '${mode}', '${opt.display.replace(/'/g, "\\'")}')" class="${baseClasses} text-left">
            ${buildTextContent(roomName + building)}
        </button>`;
    } else if (type === 'faculty') {
        return `<button type="button" onclick="applyFaculty(${opt.faculty_id}, '${mode}', '${opt.display.replace(/'/g, "\\'")}')" class="${baseClasses}">
            ${buildTextContent(opt.display)}
        </button>`;
    }
    return '';
}

/**
 * Toggle recommendation section visibility
 */
function toggleRecommendationSection(uniqueId) {
    const content = document.getElementById('content_' + uniqueId);
    const chevron = document.getElementById('chevron_' + uniqueId);
    
    if (content && chevron) {
        content.classList.toggle('hidden');
        chevron.classList.toggle('rotate-180');
    }
}

/**
 * Toggle "show more" options
 */
function toggleMoreOptions(uniqueId, button) {
    const moreOptions = document.getElementById('moreOptions_' + uniqueId);
    const toggleText = button.querySelector('.toggle-text');
    const toggleIcon = button.querySelector('.toggle-icon');
    
    if (moreOptions) {
        const isHidden = moreOptions.classList.contains('hidden');
        moreOptions.classList.toggle('hidden');
        
        if (toggleText) {
            const moreCount = button.dataset.moreCount || '';
            toggleText.textContent = isHidden ? 'Show less' : `Show ${moreCount} more`;
        }
        if (toggleIcon) {
            toggleIcon.classList.toggle('rotate-180');
        }
    }
}

// Helper function to display AI explanation in the drawer
function displayExplanation(suffix, text, isAiPowered) {
    const wrapperId = 'aiExplanationWrapper' + suffix;
    const textId = 'aiExplanation' + suffix;
    const wrapper = document.getElementById(wrapperId);
    const textEl = document.getElementById(textId);
    if (!wrapper || !textEl) return;

    if (!text) {
        wrapper.classList.add('hidden');
        return;
    }

    const detailedMode = typeof isDetailedAssistantMode === 'function' ? isDetailedAssistantMode() : Boolean(isAiPowered);
    const heading = detailedMode ? 'Detailed Analysis' : 'Quick Check';
    const bodyClass = detailedMode
        ? 'text-xs text-gray-700 dark:text-gray-300 leading-relaxed whitespace-pre-line'
        : 'text-[11px] text-gray-600 dark:text-gray-300 leading-relaxed whitespace-pre-line';

    wrapper.className = detailedMode
        ? 'mb-3 rounded-xl border border-purple-300/90 dark:border-purple-700 bg-gradient-to-br from-purple-50/90 to-indigo-50/70 dark:from-purple-900/25 dark:to-indigo-900/20 px-3.5 py-3 shadow-sm'
        : 'mb-2.5 rounded-lg border border-gray-200/90 dark:border-gray-700 bg-white dark:bg-gray-900/25 px-3 py-2';
    wrapper.innerHTML = `
        <p class="text-[10px] font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wide mb-1">${heading}</p>
        <div id="${textId}" class="${bodyClass}">${text}</div>
    `;
    wrapper.classList.remove('hidden');
}

// Helper function to display workload summary in the drawer (Detailed mode only)
function displayWorkloadSummary(suffix, workloadData) {
    const elId = 'aiWorkloadSummary' + suffix;
    const el = document.getElementById(elId);
    if (!el) return;

    if (!workloadData || !workloadData.faculty_name) {
        el.classList.add('hidden');
        return;
    }

    const hours = workloadData.weekly_hours || 0;
    const maxHours = workloadData.max_hours || 21;
    const pct = Math.min(Math.round((hours / maxHours) * 100), 100);
    const status = workloadData.status || 'balanced';
    const barColor = status === 'at_limit' ? 'bg-red-400' : status === 'heavy' ? 'bg-amber-400' : 'bg-emerald-400';
    const statusLabel = status === 'at_limit' ? 'At limit' : status === 'heavy' ? 'Heavy load' : 'Balanced';
    const statusTone = status === 'at_limit'
        ? 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300'
        : status === 'heavy'
            ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300'
            : 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300';

    el.innerHTML = `
        <div class="rounded-xl border border-purple-200/80 dark:border-purple-800 bg-purple-50/40 dark:bg-purple-900/15 p-3 shadow-sm">
            <div class="flex items-center justify-between mb-2">
                <p class="text-[10px] font-semibold text-purple-700 dark:text-purple-300 uppercase tracking-wide">Workload Context</p>
                <span class="px-1.5 py-0.5 rounded text-[9px] font-semibold ${statusTone}">${statusLabel}</span>
            </div>
            <div class="flex items-center gap-2">
                <span class="text-[10px] font-medium text-gray-600 dark:text-gray-300 truncate max-w-[110px]">${workloadData.faculty_name}</span>
                <div class="flex-1 h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
                    <div class="h-full ${barColor} rounded-full transition-all" style="width:${pct}%"></div>
                </div>
                <span class="text-[10px] font-medium text-gray-500 dark:text-gray-400 whitespace-nowrap">${hours}/${maxHours}h</span>
            </div>
            <p class="mt-2 text-[10px] text-gray-500 dark:text-gray-400">${pct}% of weekly capacity in current plan.</p>
        </div>
    `;
    el.classList.remove('hidden');
}

// Helper function for visual feedback when applying AI suggestions
function highlightAppliedField(elementId, duration = 2000) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    // For custom time pickers, highlight the visible trigger button instead of hidden input
    const target = getTimePickerVisualTarget(element) || element;
    
    // Add highlight classes
    target.classList.add('ring-2', 'ring-green-500', 'ring-offset-1', 'bg-green-50');
    target.style.transition = 'all 0.3s ease';
    
    // Remove highlight after duration
    setTimeout(() => {
        target.classList.remove('ring-2', 'ring-green-500', 'ring-offset-1', 'bg-green-50');
    }, duration);
}

/**
 * Get the visible trigger button for a custom time picker input,
 * or return null if the element is not inside a custom time picker.
 */
function getTimePickerVisualTarget(element) {
    const picker = element.closest('[data-time-picker]');
    if (picker) {
        return picker.querySelector('.time-picker-trigger') || null;
    }
    return null;
}

function applyTimeSlot(startTime, endTime, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const startField = document.getElementById('start_time' + suffix);
    const endField = document.getElementById('end_time' + suffix);
    
    // Set flag to prevent calculateEndTime from overriding our end time
    window.skipCalculateEndTime = true;
    
    // Update values
    if (startField) startField.value = startTime;
    if (endField) endField.value = endTime;
    
    // Reset flag after a brief delay to allow change event to process
    setTimeout(() => {
        window.skipCalculateEndTime = false;
    }, 100);
    
    // Visual feedback - highlight both time fields
    highlightAppliedField('start_time' + suffix);
    highlightAppliedField('end_time' + suffix);
    
    // Format display time for toast
    const formatTime = (t) => {
        const [h, m] = t.split(':');
        const hour = parseInt(h);
        const ampm = hour >= 12 ? 'PM' : 'AM';
        const hour12 = hour % 12 || 12;
        return `${hour12}:${m} ${ampm}`;
    };
    showToast(`Time applied: ${formatTime(startTime)} - ${formatTime(endTime)}`, 'success');
    
    // Trigger automatic conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

function applyDay(day, mode) {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const dayField = document.getElementById('day_of_week' + suffix);
    
    // Update value
    if (dayField) dayField.value = day;
    
    // Visual feedback
    highlightAppliedField('day_of_week' + suffix);
    
    showToast(`Day applied: ${day}`, 'success');
    
    // Trigger automatic conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

function applyRoom(roomId, mode, displayText = '') {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const hiddenInput = document.getElementById('room_id' + suffix);
    const searchInput = document.getElementById('room_search' + suffix);
    
    // Update hidden input value
    if (hiddenInput) hiddenInput.value = roomId;
    
    // Update visible search input with display text
    if (searchInput && displayText) {
        searchInput.value = displayText;
    }
    
    // Visual feedback on the search input
    highlightAppliedField('room_search' + suffix);
    
    showToast(`Room applied: ${displayText || 'Selected'}`, 'success');
    
    // Trigger automatic conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

function applyFaculty(facultyId, mode, displayText = '') {
    const suffix = mode === 'add' ? '_add' : '_edit';
    const suffixCap = mode === 'add' ? 'Add' : 'Edit';
    const hiddenSelect = document.getElementById('faculty_id' + suffix);
    const facultyTrigger = document.getElementById('facultyTrigger' + suffixCap);
    const facultyDisplay = document.getElementById('facultyDisplay' + suffixCap);
    
    // Update hidden select value
    if (hiddenSelect) hiddenSelect.value = facultyId;
    
    // Update visible faculty display
    if (facultyDisplay && displayText) {
        // Get initials from name
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
    
    // Visual feedback on the faculty trigger button
    highlightAppliedField('facultyTrigger' + suffixCap);
    
    showToast(`Faculty applied: ${displayText || 'Selected'}`, 'success');
    
    // Trigger automatic conflict check
    if (typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck(mode);
    }
}

// ============================================================================
// Faculty Schedule View Switching (Table vs Calendar)
// ============================================================================
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
        
        // Initialize week calendar (overlap detection, current-day highlighting)
        if (typeof initializeWeekCalendar === 'function') initializeWeekCalendar();
    }

    queueWeekCalendarHeaderAlignmentSync();
    
    localStorage.setItem('facultyViewPreference', viewType);
}

// ============================================================================
// Room Schedule View Switching (Table vs Calendar)
// ============================================================================
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
        
        // Initialize week calendar (overlap detection, current-day highlighting)
        if (typeof initializeWeekCalendar === 'function') initializeWeekCalendar();
    }

    queueWeekCalendarHeaderAlignmentSync();
    
    localStorage.setItem('roomViewPreference', viewType);
}

// ============================================================================
// Exam Schedule View Switching (Table vs Calendar)
// ============================================================================
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
        
        // Initialize week calendar (overlap detection, current-day highlighting)
        if (typeof initializeWeekCalendar === 'function') initializeWeekCalendar();
    }

    queueWeekCalendarHeaderAlignmentSync();
    
    localStorage.setItem('examViewPreference', viewType);
}

// Restore view preferences on page load
document.addEventListener('DOMContentLoaded', function() {
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
    
    // Restore year level filters from URL parameters
    const urlParams = new URLSearchParams(window.location.search);
    
    // Restore class tab year level filter
    const yearLevel = urlParams.get('year_level');
    if (yearLevel) {
        const yearLevelFilter = document.getElementById('yearLevelFilter');
        if (yearLevelFilter) {
            yearLevelFilter.value = yearLevel;
        }
    }
    
    // Restore exam tab year level filter
    const examYearLevel = urlParams.get('exam_year_level');
    if (examYearLevel) {
        const examYearLevelFilter = document.getElementById('examYearLevelFilter');
        if (examYearLevelFilter) {
            examYearLevelFilter.value = examYearLevel;
        }
    }

    queueWeekCalendarHeaderAlignmentSync();
});

window.addEventListener('resize', queueWeekCalendarHeaderAlignmentSync);

// Export schedule functions to global scope for onclick handlers
window.editSchedule = editSchedule;
window.openEditScheduleModal = openEditScheduleModal;
window.closeEditScheduleModal = closeEditScheduleModal;
window.openAddScheduleModal = openAddScheduleModal;
window.closeScheduleModal = closeScheduleModal;
window.openEditScheduleModalUnified = openEditScheduleModalUnified;
window.setScheduleModalMode = setScheduleModalMode;
window.handleSubjectChange = handleSubjectChange;
window.handleScheduleTypeChange = handleScheduleTypeChange;
window.calculateEndTime = calculateEndTime;
window.loadFacultyForSubject = loadFacultyForSubject;
window.loadCurriculaForSectionEdit = loadCurriculaForSectionEdit;

// Export tab selection functions to global scope for onclick handlers
window.selectSection = selectSection;
window.selectFaculty = selectFaculty;
window.selectRoom = selectRoom;
window.selectExamSection = selectExamSection;

// Export tab switching function to global scope for onclick handlers
window.switchTab = switchTab;

// Export search functions to global scope for oninput handlers
window.searchFaculty = searchFaculty;
window.searchRoom = searchRoom;

// Export view switching functions to global scope for onclick handlers
window.switchFacultyView = switchFacultyView;
window.switchRoomView = switchRoomView;
window.switchExamView = switchExamView;
window.toggleExportDropdown = toggleExportDropdown;

// Export filter functions to global scope for onchange handlers
window.filterByDepartment = filterByDepartment;
window.filterByYearLevel = filterByYearLevel;
window.filterExamByDepartment = filterExamByDepartment;
window.filterExamByYearLevel = filterExamByYearLevel;
window.filterFacultyByDepartment = filterFacultyByDepartment;
window.filterRoomByBuilding = filterRoomByBuilding;

// Export exam schedule functions to global scope for onclick handlers
// Edit, Add, and Delete operations supported