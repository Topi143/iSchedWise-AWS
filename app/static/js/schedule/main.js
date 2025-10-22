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
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
            </svg>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => toast.remove(), 5000);
}

// NOTE: Flash message toast initialization is handled in schedule.html
// Do not duplicate DOMContentLoaded listener here to avoid showing toasts multiple times

// Restore department filter on page load
document.addEventListener('DOMContentLoaded', function() {
    // Restore department filter from URL
    const urlParams = new URLSearchParams(window.location.search);
    const departmentId = urlParams.get('department_id');
    if (departmentId) {
        const filterSelect = document.getElementById('departmentFilter');
        if (filterSelect) {
            filterSelect.value = departmentId;
        }
    }
});

// Master-Detail Mobile Navigation Functions

/**
 * Class Tab - Show master (section list) view on mobile
 */
function showClassMaster() {
    const master = document.getElementById('class-master');
    const detail = document.getElementById('class-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hidden');
        detail.classList.remove('flex');
    }
}

/**
 * Class Tab - Show detail (schedule) view on mobile
 * Called when a section is selected
 */
function showClassDetail() {
    const master = document.getElementById('class-master');
    const detail = document.getElementById('class-detail');
    
    if (master && detail && window.innerWidth <= 768) {
        master.classList.add('hide-on-mobile');
        detail.classList.remove('hidden');
        detail.classList.add('flex');
    }
}

/**
 * Faculty Tab - Show master (faculty list) view on mobile
 */
function showFacultyMaster() {
    const master = document.getElementById('faculty-master');
    const detail = document.getElementById('faculty-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hidden');
        detail.classList.remove('flex');
    }
}

/**
 * Faculty Tab - Show detail (schedule) view on mobile
 * Called when a faculty is selected
 */
function showFacultyDetail() {
    const master = document.getElementById('faculty-master');
    const detail = document.getElementById('faculty-detail');
    
    if (master && detail && window.innerWidth <= 768) {
        master.classList.add('hide-on-mobile');
        detail.classList.remove('hidden');
        detail.classList.add('flex');
    }
}

/**
 * Room Tab - Show master (room list) view on mobile
 */
function showRoomMaster() {
    const master = document.getElementById('room-master');
    const detail = document.getElementById('room-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hidden');
        detail.classList.remove('flex');
    }
}

/**
 * Room Tab - Show detail (schedule) view on mobile
 * Called when a room is selected
 */
function showRoomDetail() {
    const master = document.getElementById('room-master');
    const detail = document.getElementById('room-detail');
    
    if (master && detail && window.innerWidth <= 768) {
        master.classList.add('hide-on-mobile');
        detail.classList.remove('hidden');
        detail.classList.add('flex');
    }
}

/**
 * Exam Tab - Show master (section list) view on mobile
 */
function showExamMaster() {
    const master = document.getElementById('exam-master');
    const detail = document.getElementById('exam-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hidden');
        detail.classList.remove('flex');
    }
}

/**
 * Exam Tab - Show detail (schedule) view on mobile
 * Called when an exam section is selected
 */
function showExamDetail() {
    const master = document.getElementById('exam-master');
    const detail = document.getElementById('exam-detail');
    
    if (master && detail && window.innerWidth <= 768) {
        master.classList.add('hide-on-mobile');
        detail.classList.remove('hidden');
        detail.classList.add('flex');
    }
}
