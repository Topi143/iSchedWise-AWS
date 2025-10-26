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
        }
        
        // Store preference in localStorage
        localStorage.setItem('scheduleViewPreference', viewType);
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
        const selectedContent = document.getElementById('content-' + tabName);
        if (selectedContent) {
            selectedContent.classList.add('active');
        }
        
        // Activate selected tab button
        const selectedButton = document.getElementById('tab-' + tabName);
        if (selectedButton) {
            selectedButton.classList.add('active');
        }
        
        // Store active tab in localStorage
        localStorage.setItem('activeScheduleTab', tabName);
    }
    
    // Restore active tab on page load
    document.addEventListener('DOMContentLoaded', function() {
        // Ensure all tabs are hidden first
        document.querySelectorAll('.tab-content').forEach(content => {
            content.classList.remove('active');
        });
        document.querySelectorAll('.tab-button').forEach(button => {
            button.classList.remove('active');
        });
        
        // Determine which tab to show based on URL parameters
        const urlParams = new URLSearchParams(window.location.search);
        let activeTab = 'class'; // Default to class tab
        
        // If URL has specific selection parameters, show the corresponding tab
        if (urlParams.has('section_id')) {
            activeTab = 'class';
        } else if (urlParams.has('faculty_id')) {
            activeTab = 'faculty';
        } else if (urlParams.has('room_id')) {
            activeTab = 'room';
        } else if (urlParams.has('exam_section_id')) {
            activeTab = 'exam';
        } else {
            // Only restore from localStorage if no URL parameters
            activeTab = localStorage.getItem('activeScheduleTab') || 'class';
        }
        
        switchTab(activeTab);
        
        // Restore schedule view preference (table or calendar)
        const viewPreference = localStorage.getItem('scheduleViewPreference') || 'table';
        switchScheduleView(viewPreference);
        
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
        const container = document.getElementById('toastContainer');
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = {
            success: `<svg class="w-5 h-5 text-green-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>`,
            error: `<svg class="w-5 h-5 text-red-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>`,
            info: `<svg class="w-5 h-5 text-blue-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                    </svg>`
        };
        
        toast.innerHTML = `
            ${icons[type] || icons.info}
            <span class="flex-1 text-sm font-medium text-gray-900">${message}</span>
            <button onclick="this.parentElement.remove()" class="ml-3 text-gray-400 hover:text-gray-600">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        `;
        
        container.appendChild(toast);
        
        // Auto remove after 5 seconds
        setTimeout(() => toast.remove(), 5000);
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
        const rightPanel = document.querySelector('#content-class .flex-1.bg-white.rounded-xl');
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
        fetch(`/schedule?section_id=${id}`, {
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
            const newRightPanel = doc.querySelector('#content-class .flex-1.bg-white.rounded-xl');
            if (newRightPanel && rightPanel) {
                rightPanel.innerHTML = newRightPanel.innerHTML;
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

    // Filter by Department Function
    function filterByDepartment(departmentId) {
        const url = new URL(window.location.href);
        if (departmentId) {
            url.searchParams.set('department_id', departmentId);
        } else {
            url.searchParams.delete('department_id');
        }
        window.history.replaceState({}, '', url);
        
        const sectionItems = document.querySelectorAll('.section-list-item');
        const sectionList = document.getElementById('sectionList');
        let visibleCount = 0;
        
        sectionItems.forEach(item => {
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
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
            }
        });
        
        const badge = document.getElementById('section-count-badge');
        if (badge) {
            badge.textContent = visibleCount;
        }
    }

    // Filter Faculty by Department Function
    function filterFacultyByDepartment(departmentId) {
        const url = new URL(window.location.href);
        if (departmentId) {
            url.searchParams.set('faculty_department_id', departmentId);
        } else {
            url.searchParams.delete('faculty_department_id');
        }
        // Reload page with new filter
        window.location.href = url.toString();
    }

    // Filter Exam by Department Function
    function filterExamByDepartment(departmentId) {
        const url = new URL(window.location.href);
        if (departmentId) {
            url.searchParams.set('exam_department_id', departmentId);
        } else {
            url.searchParams.delete('exam_department_id');
        }
        window.history.replaceState({}, '', url);
        
        const sectionItems = document.querySelectorAll('#examSectionList .section-list-item');
        const sectionList = document.getElementById('examSectionList');
        let visibleCount = 0;
        
        sectionItems.forEach(item => {
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
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
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
        const searchLower = searchTerm.toLowerCase().trim();
        let visibleCount = 0;
        
        facultyItems.forEach(item => {
            const facultyName = item.querySelector('h4').textContent.toLowerCase();
            const departmentName = item.querySelector('p')?.textContent.toLowerCase() || '';
            
            if (searchLower === '' || facultyName.includes(searchLower) || departmentName.includes(searchLower)) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
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
        const searchLower = searchTerm.toLowerCase().trim();
        let visibleCount = 0;
        
        roomItems.forEach(item => {
            const roomNumber = item.querySelector('h4').textContent.toLowerCase();
            const buildingName = item.querySelector('p')?.textContent.toLowerCase() || '';
            
            if (searchLower === '' || roomNumber.includes(searchLower) || buildingName.includes(searchLower)) {
                item.style.display = '';
                visibleCount++;
            } else {
                item.style.display = 'none';
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
        if (typeof triggerAutoCheck === 'function') {
            triggerAutoCheck(mode);
        }
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
        console.log('[SELECT FACULTY EXAM] Called with mode:', mode, 'facultyId:', facultyId);
        
        const searchField = document.getElementById(`faculty_search_${mode}`);
        const idField = document.getElementById(`faculty_id_${mode}`);
        const dropdown = document.getElementById(`faculty_dropdown_${mode}`);
        
        console.log('[SELECT FACULTY EXAM] Elements found:', {
            searchField: searchField ? 'YES' : 'NO',
            idField: idField ? 'YES' : 'NO',
            dropdown: dropdown ? 'YES' : 'NO'
        });
        
        if (searchField) searchField.value = facultyName;
        if (idField) {
            idField.value = facultyId;
            console.log('[SELECT FACULTY EXAM] Set faculty_id_' + mode + ' to:', facultyId, '(actual value:', idField.value, ')');
        }
        if (dropdown) dropdown.classList.add('hidden');
        
        // Trigger auto-check for exam conflicts with a small delay to ensure value is set
        if (typeof scheduleAutoExamConflictCheck === 'function') {
            const modeClean = mode.replace('exam_', '');
            console.log('[SELECT FACULTY EXAM] Scheduling auto-check with mode:', modeClean);
            // Use setTimeout to ensure the DOM is updated before validation
            setTimeout(() => {
                console.log('[SELECT FACULTY EXAM] Now triggering auto-check');
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
        console.log('[SELECT ROOM EXAM] Called with mode:', mode, 'roomId:', roomId);
        
        const displayText = building ? `${roomNumber} - ${building}` : roomNumber;
        const searchField = document.getElementById(`room_search_${mode}`);
        const idField = document.getElementById(`room_id_${mode}`);
        const dropdown = document.getElementById(`room_dropdown_${mode}`);
        
        console.log('[SELECT ROOM EXAM] Elements found:', {
            searchField: searchField ? 'YES' : 'NO',
            idField: idField ? 'YES' : 'NO',
            dropdown: dropdown ? 'YES' : 'NO'
        });
        
        if (searchField) searchField.value = displayText;
        if (idField) {
            idField.value = roomId;
            console.log('[SELECT ROOM EXAM] Set room_id_' + mode + ' to:', roomId, '(actual value:', idField.value, ')');
        }
        if (dropdown) dropdown.classList.add('hidden');
        
        // Trigger auto-check for exam conflicts with a small delay to ensure value is set
        if (typeof scheduleAutoExamConflictCheck === 'function') {
            const modeClean = mode.replace('exam_', '');
            console.log('[SELECT ROOM EXAM] Scheduling auto-check with mode:', modeClean);
            // Use setTimeout to ensure the DOM is updated before validation
            setTimeout(() => {
                console.log('[SELECT ROOM EXAM] Now triggering auto-check');
                scheduleAutoExamConflictCheck(modeClean);
            }, 50); // 50ms delay
        } else {
            console.warn('[SELECT ROOM EXAM] scheduleAutoExamConflictCheck function not found!');
        }
    }

    // Add Schedule Modal
    function openAddScheduleModal(sectionId) {
        // Close edit modal if it's open
        const editModal = document.getElementById('editScheduleModal');
        if (editModal && !editModal.classList.contains('hidden')) {
            closeEditScheduleModal();
        }
        
        document.getElementById('section_id_add').value = sectionId;
        document.getElementById('addScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Reset schedule type dropdown to default state
        const scheduleTypeSelect = document.getElementById('schedule_type_add');
        if (scheduleTypeSelect) {
            scheduleTypeSelect.value = '';
            // Reset all options to default text
            document.getElementById('lectureOption_add').textContent = 'Lecture (0 units)';
            document.getElementById('labOption_add').textContent = 'Lab (0 units)';
            document.getElementById('bothOption_add').textContent = 'Both Lecture & Lab (0 units)';
            // Disable all options initially
            document.getElementById('lectureOption_add').disabled = true;
            document.getElementById('labOption_add').disabled = true;
            document.getElementById('bothOption_add').disabled = true;
        }
        
        // Reset auto-check state to initial (no spinner, button disabled with message)
        if (typeof resetAutoCheckState === 'function') {
            resetAutoCheckState('add');
        }
        
        // Load curricula for this section (which will then load subjects)
        loadCurriculaForSection(sectionId, 'add');
    }

    function closeAddScheduleModal() {
        document.getElementById('addScheduleModal').classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        document.getElementById('addScheduleForm').reset();
        
        // Reset auto-check state
        if (typeof resetAutoCheckState === 'function') {
            resetAutoCheckState('add');
        }
    }
    
    // Note: loadCurriculaForSection and loadSubjectsForCurriculum are now in curriculum_selector.js
    
    // Load subjects dynamically based on section (DEPRECATED - use loadCurriculaForSection instead)
    function loadSubjectsForSection(sectionId) {
        // For backward compatibility, redirect to curriculum-based loading
        loadCurriculaForSection(sectionId, 'add');
    }

    // Load faculty assigned to a specific subject
    function loadFacultyForSubject(subjectId, mode = 'add', selectedFacultyId = null) {
        const facultySelect = document.getElementById(`faculty_id_${mode}`);
        
        console.log(`[FACULTY] Loading faculty for subject ${subjectId}, mode: ${mode}, pre-select: ${selectedFacultyId}`);
        
        if (!subjectId) {
            // Reset when no subject selected
            facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
            facultySelect.disabled = false;
            return;
        }
        
        // Show loading state
        facultySelect.innerHTML = '<option value="">Loading faculty...</option>';
        facultySelect.disabled = true;
        
        // Fetch faculty for this subject
        fetch(`/schedule/get-faculty/${subjectId}`)
            .then(response => response.json())
            .then(data => {
                facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
                
                let facultyFound = false;
                
                console.log(`[FACULTY] Received ${data.faculty ? data.faculty.length : 0} faculty members`);
                
                if (data.faculty && data.faculty.length > 0) {
                    data.faculty.forEach(faculty => {
                        const option = document.createElement('option');
                        option.value = faculty.id;
                        option.textContent = faculty.display;
                        
                        // Pre-select the faculty if specified
                        if (selectedFacultyId && faculty.id == selectedFacultyId) {
                            option.selected = true;
                            facultyFound = true;
                            console.log(`[FACULTY] Found and selected faculty: ${faculty.id}`);
                        }
                        
                        facultySelect.appendChild(option);
                    });
                } else {
                    // If no faculty assigned, show message
                    const option = document.createElement('option');
                    option.value = "";
                    option.textContent = "No faculty assigned to this subject";
                    option.disabled = true;
                    facultySelect.appendChild(option);
                }
                
                // If selected faculty wasn't in the subject-specific list, 
                // we need to fetch ALL faculties and add the selected one
                if (selectedFacultyId && !facultyFound && mode === 'edit') {
                    console.log(`[FACULTY] Faculty ${selectedFacultyId} not found in subject list, fetching all faculties`);
                    // For edit mode, if the faculty isn't in the subject list,
                    // we need to preserve it by fetching all faculties
                    fetch('/schedule/get-all-faculties')
                        .then(response => response.json())
                        .then(allData => {
                            if (allData.faculties && allData.faculties.length > 0) {
                                const selectedFaculty = allData.faculties.find(f => f.id == selectedFacultyId);
                                if (selectedFaculty) {
                                    console.log(`[FACULTY] Adding currently assigned faculty: ${selectedFaculty.id}`);
                                    // Add the selected faculty to the dropdown with a note
                                    const option = document.createElement('option');
                                    option.value = selectedFaculty.id;
                                    option.textContent = `${selectedFaculty.display} (Currently assigned)`;
                                    option.selected = true;
                                    // Insert after "Select a faculty..." option
                                    facultySelect.insertBefore(option, facultySelect.children[1]);
                                    console.log(`[FACULTY] Faculty dropdown value is now: ${facultySelect.value}`);
                                }
                            }
                        })
                        .catch(error => {
                            console.error('[FACULTY] Error loading all faculties:', error);
                        });
                } else if (facultyFound) {
                    console.log(`[FACULTY] Faculty dropdown value is: ${facultySelect.value}`);
                }
                
                facultySelect.disabled = false;
            })
            .catch(error => {
                console.error('[FACULTY] Error loading faculty:', error);
                facultySelect.innerHTML = '<option value="">Select a faculty...</option>';
                facultySelect.disabled = false;
                showToast('Error loading faculty. Please try again.', 'error');
            });
    }

    // Edit Schedule Modal
    function openEditScheduleModal() {
        // Close add modal if it's open
        const addModal = document.getElementById('addScheduleModal');
        if (addModal && !addModal.classList.contains('hidden')) {
            closeAddScheduleModal();
        }
        
        document.getElementById('editScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Reset auto-check state to initial (no spinner, button disabled with message)
        if (typeof resetAutoCheckState === 'function') {
            resetAutoCheckState('edit');
        }
    }

    function closeEditScheduleModal() {
        document.getElementById('editScheduleModal').classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        document.getElementById('editScheduleForm').reset();
        
        // Reset auto-check state
        if (typeof resetAutoCheckState === 'function') {
            resetAutoCheckState('edit');
        }
    }

    function editSchedule(id, scheduleData) {
        console.log('[EDIT SCHEDULE] Starting edit for schedule ID:', id, 'Data:', scheduleData);
        
        document.getElementById('schedule_id_edit').value = id;
        document.getElementById('section_id_edit').value = scheduleData.section_id;
        
        // Reset schedule type dropdown to default state (like Add modal)
        const scheduleTypeSelect = document.getElementById('schedule_type_edit');
        if (scheduleTypeSelect) {
            scheduleTypeSelect.value = '';
            // Reset all options to default text
            document.getElementById('lectureOption_edit').textContent = 'Lecture (0 units)';
            document.getElementById('labOption_edit').textContent = 'Lab (0 units)';
            document.getElementById('bothOption_edit').textContent = 'Both Lecture & Lab (0 units)';
            // Disable all options initially
            document.getElementById('lectureOption_edit').disabled = true;
            document.getElementById('labOption_edit').disabled = true;
            document.getElementById('bothOption_edit').disabled = true;
        }
        
        // Load curricula and subjects for the schedule's section first (using new curriculum-based approach)
        const sectionId = scheduleData.section_id;
        console.log('[EDIT SCHEDULE] Calling loadCurriculaForEdit with section:', sectionId);
        loadCurriculaForEdit(sectionId, scheduleData);
        
        // Set other fields immediately (except faculty - it will be loaded after subject is selected)
        document.getElementById('day_of_week_edit').value = scheduleData.day_of_week || '';
        document.getElementById('start_time_edit').value = scheduleData.start_time || '';
        document.getElementById('end_time_edit').value = scheduleData.end_time || '';
        
        // Set room (hidden input and search display)
        document.getElementById('room_id_edit').value = scheduleData.room_id || '';
        if (scheduleData.room_number && scheduleData.building_name) {
            document.getElementById('room_search_edit').value = `${scheduleData.room_number} - ${scheduleData.building_name}`;
        } else if (scheduleData.room_number) {
            document.getElementById('room_search_edit').value = scheduleData.room_number;
        } else {
            document.getElementById('room_search_edit').value = '';
        }
        
        // Store the schedule type to set it after subject loads
        window.editScheduleType = scheduleData.schedule_type || 'lecture';
        
        console.log('[EDIT SCHEDULE] Opening modal...');
        openEditScheduleModal();
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
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = '/schedule/delete';  // Fixed: Use direct URL instead of Jinja2 template
        
        // Get CSRF token from meta tag or form in page
        const csrfToken = document.createElement('input');
        csrfToken.type = 'hidden';
        csrfToken.name = 'csrf_token';
        // Get CSRF token from page meta or hidden input
        const tokenMeta = document.querySelector('meta[name="csrf-token"]');
        const tokenInput = document.querySelector('input[name="csrf_token"]');
        csrfToken.value = tokenMeta ? tokenMeta.content : (tokenInput ? tokenInput.value : '');
        
        const scheduleIdInput = document.createElement('input');
        scheduleIdInput.type = 'hidden';
        scheduleIdInput.name = 'schedule_id';
        scheduleIdInput.value = id;
        
        form.appendChild(csrfToken);
        form.appendChild(scheduleIdInput);
        document.body.appendChild(form);
        form.submit();
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
    }
    
    function showScheduleTypeOptions(mode, subjectData) {
        const suffix = mode === 'add' ? '_add' : '_edit';
        const selectElement = document.getElementById('schedule_type' + suffix);
        
        const hasLec = subjectData.lecUnits > 0;
        const hasLab = subjectData.labUnits > 0;
        
        // Update dropdown option text with units
        const lectureOption = document.getElementById('lectureOption' + suffix);
        const labOption = document.getElementById('labOption' + suffix);
        const bothOption = document.getElementById('bothOption' + suffix);
        
        lectureOption.textContent = `Lecture (${subjectData.lecUnits} units)`;
        labOption.textContent = `Lab (${subjectData.labUnits} units)`;
        bothOption.textContent = `Both Lecture & Lab (${subjectData.totalUnits} units)`;
        
        // Enable/disable options based on subject units
        lectureOption.disabled = !hasLec;
        labOption.disabled = !hasLab;
        bothOption.disabled = !(hasLec && hasLab);
        
        // Auto-select appropriate default
        if (hasLec && hasLab) {
            selectElement.value = 'lecture'; // Default to lecture
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
        
        // Store units for auto-calculation based on schedule type
        let units = 0;
        if (scheduleType === 'lecture') {
            units = subjectData.lecUnits;
        } else if (scheduleType === 'lab') {
            units = subjectData.labUnits;
        } else if (scheduleType === 'both') {
            units = subjectData.totalUnits;
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
            } else if (scheduleType === 'both') {
                units = currentSubjectData[mode].totalUnits || 0;
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
        
        // Add duration (units * 60 minutes)
        const durationMinutes = units * 60;
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
        endTimeInput.classList.add('ring-2', 'ring-green-500');
        setTimeout(() => {
            endTimeInput.classList.remove('ring-2', 'ring-green-500');
        }, 1000);
        
        // Show auto-calc badge
        const badge = document.getElementById('autoCalcBadge' + suffix);
        if (badge && units > 0) {
            badge.classList.remove('hidden');
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
        const rightPanel = document.querySelector('#content-faculty .flex-1.bg-white.rounded-xl');
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
        fetch(`/schedule?faculty_id=${id}`, {
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
            const newRightPanel = doc.querySelector('#content-faculty .flex-1.bg-white.rounded-xl');
            if (newRightPanel && rightPanel) {
                rightPanel.innerHTML = newRightPanel.innerHTML;
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
        const rightPanel = document.querySelector('#content-room .flex-1.bg-white.rounded-xl');
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
        fetch(`/schedule?room_id=${id}`, {
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
            const newRightPanel = doc.querySelector('#content-room .flex-1.bg-white.rounded-xl');
            if (newRightPanel && rightPanel) {
                rightPanel.innerHTML = newRightPanel.innerHTML;
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
        
        const roomItems = document.querySelectorAll('#roomList .room-list-item');
        const roomList = document.getElementById('roomList');
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
        
        const facultyItems = document.querySelectorAll('#facultyList .faculty-list-item');
        const facultyList = document.getElementById('facultyList');
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
        url.searchParams.set('exam_section_id', id);
        window.history.pushState({}, '', url);
        
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
        const rightPanel = document.querySelector('#content-exam .flex-1.bg-white.rounded-xl');
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
        fetch(`/schedule?exam_section_id=${id}`, {
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
            const newRightPanel = doc.querySelector('#content-exam .flex-1.bg-white.rounded-xl');
            if (newRightPanel && rightPanel) {
                rightPanel.innerHTML = newRightPanel.innerHTML;
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

    function filterExamByDepartment(departmentId) {
        const url = new URL(window.location.href);
        if (departmentId) {
            url.searchParams.set('exam_department_id', departmentId);
        } else {
            url.searchParams.delete('exam_department_id');
        }
        window.history.replaceState({}, '', url);
        
        const sectionItems = document.querySelectorAll('#examSectionList .section-list-item');
        const sectionList = document.getElementById('examSectionList');
        let visibleCount = 0;
        
        sectionItems.forEach(item => {
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
        
        const badge = document.getElementById('exam-section-count-badge');
        if (badge) {
            badge.textContent = visibleCount;
        }
    }

    // Exam Schedule Modal Functions
    function openAddExamScheduleModal(sectionId) {
        // Close edit modal if open
        const editModal = document.getElementById('editExamScheduleModal');
        if (editModal && !editModal.classList.contains('hidden')) {
            closeEditExamScheduleModal();
        }
        
        document.getElementById('section_id_exam_add').value = sectionId;
        document.getElementById('addExamScheduleModal').classList.remove('hidden');
        document.body.classList.add('overflow-hidden');
        
        // Load curricula for this section (which will then load subjects)
        loadCurriculaForSection(sectionId, 'exam_add');
    }

    function closeAddExamScheduleModal() {
        document.getElementById('addExamScheduleModal').classList.add('hidden');
        document.body.classList.remove('overflow-hidden');
        document.getElementById('addExamScheduleForm').reset();
        
        // Reset auto-check state for exam modal
        if (typeof resetAutoCheckExamState === 'function') {
            resetAutoCheckExamState('add');
        }
    }

    // Edit exam schedule modal
    function editExamSchedule(examScheduleId) {
        // Close add modal if open
        const addModal = document.getElementById('addExamScheduleModal');
        if (addModal && !addModal.classList.contains('hidden')) {
            closeAddExamScheduleModal();
        }
        
        fetch(`/exam-schedule/get/${examScheduleId}`)
            .then(response => response.json())
            .then(data => {
                // Set hidden fields
                document.getElementById('exam_schedule_id_edit').value = data.id;
                document.getElementById('section_id_exam_edit').value = data.section_id;
                
                // Set form fields that don't depend on async data
                document.getElementById('exam_date_edit').value = data.exam_date;
                document.getElementById('start_time_exam_edit').value = data.start_time;
                document.getElementById('end_time_exam_edit').value = data.end_time;
                
                // Set faculty (hidden input and search display)
                document.getElementById('faculty_id_exam_edit').value = data.faculty_id || '';
                if (data.faculty_name) {
                    document.getElementById('faculty_search_exam_edit').value = data.faculty_name;
                } else {
                    document.getElementById('faculty_search_exam_edit').value = '';
                }
                
                // Set room (hidden input and search display)
                document.getElementById('room_id_exam_edit').value = data.room_id || '';
                if (data.room_number && data.building_name) {
                    document.getElementById('room_search_exam_edit').value = `${data.room_number} - ${data.building_name}`;
                } else if (data.room_number) {
                    document.getElementById('room_search_exam_edit').value = data.room_number;
                } else {
                    document.getElementById('room_search_exam_edit').value = '';
                }
                
                // Use curriculum-based loading (same as edit schedule modal)
                if (typeof loadCurriculaForEdit === 'function') {
                    loadCurriculaForEdit(data.section_id, data, 'exam_edit');
                } else {
                    // Fallback to direct subject loading if curriculum selector not available
                    return loadSubjectsForExamSection(data.section_id, 'edit', data);
                }
                
                return Promise.resolve();
            })
            .then(() => {
                // Open modal AFTER all data is loaded
                const modal = document.getElementById('editExamScheduleModal');
                if (modal) {
                    modal.classList.remove('hidden');
                    document.body.classList.add('overflow-hidden');
                }
            })
            .catch(error => {
                console.error('Error loading exam schedule:', error);
                showToast('Error loading exam schedule data', 'error');
            });
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
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = `/exam-schedule/delete`;
        
        const csrfToken = document.querySelector('input[name="csrf_token"]')?.value;
        if (csrfToken) {
            const csrfInput = document.createElement('input');
            csrfInput.type = 'hidden';
            csrfInput.name = 'csrf_token';
            csrfInput.value = csrfToken;
            form.appendChild(csrfInput);
        }
        
        const idInput = document.createElement('input');
        idInput.type = 'hidden';
        idInput.name = 'exam_schedule_id';
        idInput.value = id;
        form.appendChild(idInput);
        
        document.body.appendChild(form);
        form.submit();
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
            .then(response => response.json())
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
        
        return fetch(`/schedule/get-subjects-by-curriculum/${curriculumId}`)
            .then(response => response.json())
            .then(data => {
                subjectSelect.innerHTML = '<option value="">Select a subject</option>';
                
                if (data.subjects && data.subjects.length > 0) {
                    data.subjects.forEach(subject => {
                        const option = document.createElement('option');
                        option.value = subject.id;
                        option.textContent = subject.display;
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
        console.log('[AI CHECK] Form data:', {
            sectionId, subjectId, facultyId, roomId, 
            dayOfWeek, startTime, endTime, scheduleId
        });
        
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
        
        console.log('[AI CHECK] Sending request:', requestData);
        
        // Call AI API
        fetch('/schedule/ai-check-conflicts', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestData)
        })
        .then(response => {
            console.log('[AI CHECK] Response status:', response.status);
            if (!response.ok) {
                return response.text().then(text => {
                    console.error('[AI CHECK] Error response:', text);
                    throw new Error(`Server error (${response.status}): ${text.substring(0, 100)}`);
                });
            }
            return response.json();
        })
        .then(data => {
            console.log('[AI CHECK] Response data:', data);
            
            if (!data.ai_enabled) {
                explanationEl.textContent = 'AI assistance is not enabled. Configure your Gemini API key to use this feature.';
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
        const conflictsContainerMobile = document.getElementById('aiConflicts' + suffix + 'Mobile');
        const conflictsList = document.getElementById('aiConflictsList' + suffix);
        const conflictsListMobile = document.getElementById('aiConflictsList' + suffix + 'Mobile');
        
        // Clear both desktop and mobile lists
        if (conflictsList) conflictsList.innerHTML = '';
        if (conflictsListMobile) conflictsListMobile.innerHTML = '';
        
        conflicts.forEach(conflict => {
            // Desktop version
            if (conflictsList) {
                const conflictDiv = document.createElement('div');
                conflictDiv.className = 'p-2 bg-red-50 border border-red-200 rounded-lg text-sm';
                conflictDiv.innerHTML = `
                    <div class="flex items-start space-x-2">
                        <span class="text-red-600 font-semibold">${conflict.type.toUpperCase()}:</span>
                        <div class="flex-1">
                            <p class="text-red-800">${conflict.message}</p>
                            <p class="text-red-600 text-xs mt-1">
                                ${conflict.details.subject} • ${conflict.details.day} ${conflict.details.time}
                            </p>
                        </div>
                    </div>
                `;
                conflictsList.appendChild(conflictDiv);
            }
            
            // Mobile version (more compact)
            if (conflictsListMobile) {
                const conflictDivMobile = document.createElement('div');
                conflictDivMobile.className = 'p-2 bg-red-50 border border-red-200 rounded-lg';
                conflictDivMobile.innerHTML = `
                    <div class="flex items-start space-x-1.5">
                        <span class="text-red-600 font-semibold text-[10px]">${conflict.type.toUpperCase()}:</span>
                        <div class="flex-1">
                            <p class="text-red-800 text-[10px]">${conflict.message}</p>
                            <p class="text-red-600 text-[9px] mt-0.5">
                                ${conflict.details.subject} • ${conflict.details.day} ${conflict.details.time}
                            </p>
                        </div>
                    </div>
                `;
                conflictsListMobile.appendChild(conflictDivMobile);
            }
        });
        
        if (conflictsContainer) conflictsContainer.classList.remove('hidden');
        if (conflictsContainerMobile) conflictsContainerMobile.classList.remove('hidden');
    }
    
    function displayAIRecommendations(recommendations, mode) {
        const suffix = mode === 'add' ? 'Add' : 'Edit';
        const recommendationsContainer = document.getElementById('aiRecommendations' + suffix);
        const recommendationsContainerMobile = document.getElementById('aiRecommendations' + suffix + 'Mobile');
        const recommendationsList = document.getElementById('aiRecommendationsList' + suffix);
        const recommendationsListMobile = document.getElementById('aiRecommendationsList' + suffix + 'Mobile');
        
        // Clear both lists
        if (recommendationsList) recommendationsList.innerHTML = '';
        if (recommendationsListMobile) recommendationsListMobile.innerHTML = '';
        
        if (recommendations.length === 0) {
            if (recommendationsContainer) recommendationsContainer.classList.add('hidden');
            if (recommendationsContainerMobile) recommendationsContainerMobile.classList.add('hidden');
            return;
        }
        
        recommendations.forEach(rec => {
            // Desktop version
            if (recommendationsList) {
                const recDiv = document.createElement('div');
                recDiv.className = 'p-3 bg-green-50 border border-green-200 rounded-lg';
                
                let optionsHTML = '';
                
                if (rec.type === 'time_slot') {
                    optionsHTML = rec.options.map(opt => 
                        `<button type="button" onclick="applyTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" 
                                class="px-3 py-1 text-sm bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                } else if (rec.type === 'day') {
                    optionsHTML = rec.options.map(opt => 
                        `<button type="button" onclick="applyDay('${opt.day}', '${mode}')" 
                                class="px-3 py-1 text-sm bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.day}
                        </button>`
                    ).join('');
                } else if (rec.type === 'room') {
                    optionsHTML = rec.options.map(opt => 
                        `<button type="button" onclick="applyRoom('${opt.room_id}', '${mode}')" 
                                class="px-3 py-1 text-sm bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                } else if (rec.type === 'faculty') {
                    optionsHTML = rec.options.map(opt => 
                        `<button type="button" onclick="applyFaculty('${opt.faculty_id}', '${mode}')" 
                                class="px-3 py-1 text-sm bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                }
                
                recDiv.innerHTML = `
                    <h6 class="text-sm font-semibold text-green-800 mb-2">${rec.title}</h6>
                    <div class="flex flex-wrap gap-2">
                        ${optionsHTML}
                    </div>
                `;
                
                recommendationsList.appendChild(recDiv);
            }
            
            // Mobile version (more compact)
            if (recommendationsListMobile) {
                const recDivMobile = document.createElement('div');
                recDivMobile.className = 'p-2 bg-green-50 border border-green-200 rounded-lg';
                
                let optionsHTMLMobile = '';
                
                if (rec.type === 'time_slot') {
                    optionsHTMLMobile = rec.options.map(opt => 
                        `<button type="button" onclick="applyTimeSlot('${opt.start_time}', '${opt.end_time}', '${mode}')" 
                                class="px-2 py-1 text-[10px] bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                } else if (rec.type === 'day') {
                    optionsHTMLMobile = rec.options.map(opt => 
                        `<button type="button" onclick="applyDay('${opt.day}', '${mode}')" 
                                class="px-2 py-1 text-[10px] bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.day}
                        </button>`
                    ).join('');
                } else if (rec.type === 'room') {
                    optionsHTMLMobile = rec.options.map(opt => 
                        `<button type="button" onclick="applyRoom('${opt.room_id}', '${mode}')" 
                                class="px-2 py-1 text-[10px] bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                } else if (rec.type === 'faculty') {
                    optionsHTMLMobile = rec.options.map(opt => 
                        `<button type="button" onclick="applyFaculty('${opt.faculty_id}', '${mode}')" 
                                class="px-2 py-1 text-[10px] bg-white border border-green-300 rounded hover:bg-green-100 transition-colors">
                            ${opt.display}
                        </button>`
                    ).join('');
                }
                
                recDivMobile.innerHTML = `
                    <h6 class="text-[10px] font-semibold text-green-800 mb-1.5">${rec.title}</h6>
                    <div class="flex flex-wrap gap-1.5">
                        ${optionsHTMLMobile}
                    </div>
                `;
                
                recommendationsListMobile.appendChild(recDivMobile);
            }
        });
        
        if (recommendationsContainer) recommendationsContainer.classList.remove('hidden');
        if (recommendationsContainerMobile) recommendationsContainerMobile.classList.remove('hidden');
    }
    
    function applyTimeSlot(startTime, endTime, mode) {
        const suffix = mode === 'add' ? '_add' : '_edit';
        document.getElementById('start_time' + suffix).value = startTime;
        document.getElementById('end_time' + suffix).value = endTime;
        showToast('Time slot applied - auto-checking for conflicts...', 'info');
        
        // Trigger automatic conflict check
        if (typeof scheduleAutoConflictCheck === 'function') {
            scheduleAutoConflictCheck(mode);
        }
    }
    
    function applyDay(day, mode) {
        const suffix = mode === 'add' ? '_add' : '_edit';
        document.getElementById('day_of_week' + suffix).value = day;
        showToast('Day changed - auto-checking for conflicts...', 'info');
        
        // Trigger automatic conflict check
        if (typeof scheduleAutoConflictCheck === 'function') {
            scheduleAutoConflictCheck(mode);
        }
    }
    
    function applyRoom(roomId, mode) {
        const suffix = mode === 'add' ? '_add' : '_edit';
        document.getElementById('room_id' + suffix).value = roomId;
        showToast('Room changed - auto-checking for conflicts...', 'info');
        
        // Trigger automatic conflict check
        if (typeof scheduleAutoConflictCheck === 'function') {
            scheduleAutoConflictCheck(mode);
        }
    }
    
    function applyFaculty(facultyId, mode) {
        const suffix = mode === 'add' ? '_add' : '_edit';
        document.getElementById('faculty_id' + suffix).value = facultyId;
        showToast('Faculty changed - auto-checking for conflicts...', 'info');
        
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
        }
        
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
        }
        
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
        }
        
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
    });

    // Export exam schedule functions to global scope for onclick handlers
    // Edit, Add, and Delete operations supported
