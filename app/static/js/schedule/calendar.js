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
});
