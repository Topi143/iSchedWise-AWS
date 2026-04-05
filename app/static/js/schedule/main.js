// Toast Notification System
function showToast(message, type = 'success') {
    if (window.__iswToastManager && typeof window.__iswToastManager.show === 'function') {
        return window.__iswToastManager.show(message, type);
    }
}

// NOTE: Flash message toast initialization is handled in schedule.html
// Do not duplicate DOMContentLoaded listener here to avoid showing toasts multiple times

// Restore program filter on page load
document.addEventListener('DOMContentLoaded', function() {
    // Restore program filter from URL
    const urlParams = new URLSearchParams(window.location.search);
    const departmentId = urlParams.get('program_id');
    if (departmentId) {
        const filterSelect = document.getElementById('departmentFilter');
        if (filterSelect) {
            filterSelect.value = departmentId;
        }
    }
});

// Master-Detail Mobile Navigation Functions

const SCHEDULE_MOBILE_BREAKPOINT = 1023;
const SCHEDULE_DESKTOP_BREAKPOINT = 1024;

function isScheduleMobileViewport() {
    return window.innerWidth <= SCHEDULE_MOBILE_BREAKPOINT;
}

function debounceSchedule(fn, wait = 140) {
    let timeout;
    return (...args) => {
        clearTimeout(timeout);
        timeout = setTimeout(() => fn(...args), wait);
    };
}

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
    
    if (master && detail) {
        // Always show detail panel when a section is selected
        detail.classList.remove('hidden');
        detail.classList.add('flex');
        
        // On mobile/tablet, hide the master panel
        if (isScheduleMobileViewport()) {
            master.classList.add('hide-on-mobile');
        }
    }
}

/**
 * Faculty Tab - Show master (faculty list) view on mobile/tablet
 */
function showFacultyMaster() {
    const master = document.getElementById('faculty-master');
    const detail = document.getElementById('faculty-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hide-on-mobile');
    }
}

/**
 * Faculty Tab - Show detail (schedule) view on mobile/tablet
 * Called when a faculty is selected
 */
function showFacultyDetail() {
    const master = document.getElementById('faculty-master');
    const detail = document.getElementById('faculty-detail');
    
    if (master && detail) {
        // Always show detail panel when a faculty is selected
        detail.classList.remove('hide-on-mobile');
        
        // On mobile/tablet, hide the master panel
        if (isScheduleMobileViewport()) {
            master.classList.add('hide-on-mobile');
        }
    }
}

/**
 * Room Tab - Show master (room list) view on mobile/tablet
 */
function showRoomMaster() {
    const master = document.getElementById('room-master');
    const detail = document.getElementById('room-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hide-on-mobile');
    }
}

/**
 * Room Tab - Show detail (schedule) view on mobile/tablet
 * Called when a room is selected
 */
function showRoomDetail() {
    const master = document.getElementById('room-master');
    const detail = document.getElementById('room-detail');
    
    if (master && detail) {
        // Always show detail panel when a room is selected
        detail.classList.remove('hide-on-mobile');
        
        // On mobile/tablet, hide the master panel
        if (isScheduleMobileViewport()) {
            master.classList.add('hide-on-mobile');
        }
    }
}

/**
 * Exam Tab - Show master (section list) view on mobile/tablet
 */
function showExamMaster() {
    const master = document.getElementById('exam-master');
    const detail = document.getElementById('exam-detail');
    
    if (master && detail) {
        master.classList.remove('hide-on-mobile');
        detail.classList.add('hide-on-mobile');
    }
}

/**
 * Exam Tab - Show detail (schedule) view on mobile/tablet
 * Called when an exam section is selected
 */
function showExamDetail() {
    const master = document.getElementById('exam-master');
    const detail = document.getElementById('exam-detail');
    
    if (master && detail) {
        // Always show detail panel when an exam section is selected
        detail.classList.remove('hide-on-mobile');
        
        // On mobile/tablet, hide the master panel
        if (isScheduleMobileViewport()) {
            master.classList.add('hide-on-mobile');
        }
    }
}

function syncScheduleViewportState() {
    if (window.innerWidth >= SCHEDULE_DESKTOP_BREAKPOINT) {
        const classMaster = document.getElementById('class-master');
        const classDetail = document.getElementById('class-detail');
        const facultyMaster = document.getElementById('faculty-master');
        const facultyDetail = document.getElementById('faculty-detail');
        const roomMaster = document.getElementById('room-master');
        const roomDetail = document.getElementById('room-detail');
        const examMaster = document.getElementById('exam-master');
        const examDetail = document.getElementById('exam-detail');

        if (classMaster) classMaster.classList.remove('hide-on-mobile');
        if (classDetail) {
            classDetail.classList.remove('hide-on-mobile', 'hidden');
            classDetail.classList.add('flex');
        }

        if (facultyMaster) facultyMaster.classList.remove('hide-on-mobile');
        if (facultyDetail) facultyDetail.classList.remove('hide-on-mobile', 'hidden');

        if (roomMaster) roomMaster.classList.remove('hide-on-mobile');
        if (roomDetail) roomDetail.classList.remove('hide-on-mobile', 'hidden');

        if (examMaster) examMaster.classList.remove('hide-on-mobile');
        if (examDetail) examDetail.classList.remove('hide-on-mobile', 'hidden');
    }
}

window.addEventListener('resize', debounceSchedule(syncScheduleViewportState, 140));
window.addEventListener('orientationchange', debounceSchedule(syncScheduleViewportState, 120));
