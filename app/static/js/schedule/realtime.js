/**
 * Real-time Schedule Updates via Socket.IO
 * Enables multi-user concurrent scheduling with live updates
 */

// Socket.IO connection state
let socket = null;
let isConnected = false;
let currentRoom = null;
let heartbeatInterval = null;
let currentEditLock = null;

// Lock timeout in milliseconds (should match server-side SCHEDULE_LOCK_TIMEOUT_MINUTES)
const LOCK_HEARTBEAT_INTERVAL = 60000; // 1 minute

/**
 * Initialize Socket.IO connection
 */
function initializeSocketIO() {
    // Check if Socket.IO is available
    if (typeof io === 'undefined') {
        console.warn('Socket.IO not loaded. Real-time updates disabled.');
        return;
    }

    // Ensure only one active Socket.IO client exists per page.
    if (socket) {
        try {
            socket.disconnect();
        } catch (error) {
            console.warn('Socket cleanup before re-init failed:', error);
        }
        socket = null;
    }
    
    // Connect to Socket.IO server
    socket = io({
        // Keep polling-only in current deployment to avoid websocket upgrade errors.
        transports: ['polling'],
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
        closeOnBeforeunload: true
    });
    
    // Connection established
    socket.on('connect', function() {
        isConnected = true;
        
        // Join the schedule room for current academic period
        joinScheduleRoom();
    });
    
    // Connection lost
    socket.on('disconnect', function() {
        isConnected = false;
        stopHeartbeat();
        currentRoom = null;
    });
    
    // Connection error
    socket.on('connect_error', function(error) {
        console.error('Connection error:', error);
    });
    
    // User joined the room
    socket.on('user_joined', function(data) {
    });
    
    // User left the room
    socket.on('user_left', function(data) {
    });
    
    // Schedule was changed by another user
    socket.on('schedule_changed', function(data) {
        handleScheduleChange(data);
    });
    
    // Schedule was locked by another user
    socket.on('schedule_locked', function(data) {
        handleScheduleLocked(data);
    });
    
    // Schedule was unlocked
    socket.on('schedule_unlocked', function(data) {
        handleScheduleUnlocked(data);
    });
    
    // Lock denied (someone else has it)
    socket.on('lock_denied', function(data) {
        showToast(`This schedule is being edited by ${data.locked_by}`, 'error');
    });
    
    // Lock acquired successfully
    socket.on('lock_acquired', function(data) {
        currentEditLock = data;
        startHeartbeat(data.schedule_id, data.type);
    });
    
    // Heartbeat acknowledged
    socket.on('heartbeat_ack', function(data) {
    });
    
    // Locks released (user disconnected)
    socket.on('locks_released', function(data) {
        // Refresh any locked indicators
        refreshLockIndicators();
    });
    
    // Conflict alert from another user's schedule change
    socket.on('conflict_alert', function(data) {
        handleConflictAlert(data);
    });
    
    // Recheck confirmation
    socket.on('recheck_confirmed', function(data) {
    });
}

/**
 * Join the schedule room for real-time updates
 */
function joinScheduleRoom() {
    if (!socket || !isConnected) return;
    
    // Get current academic settings from the page
    const academicYear = window.currentAcademicYear || '';
    const semester = window.currentSemester || '';
    
    currentRoom = { academic_year: academicYear, semester: semester };
    
    socket.emit('join_schedule_room', currentRoom);
}

/**
 * Leave the schedule room
 */
function leaveScheduleRoom() {
    if (!socket || !isConnected || !currentRoom) return;
    
    socket.emit('leave_schedule_room', currentRoom);
}

/**
 * Acquire edit lock on a schedule
 */
function acquireScheduleLock(scheduleId, scheduleType = 'class') {
    if (!socket || !isConnected) {
        console.warn('Not connected. Cannot acquire lock.');
        return Promise.resolve(false);
    }
    
    return new Promise((resolve) => {
        socket.emit('acquire_schedule_lock', {
            schedule_id: scheduleId,
            type: scheduleType
        });
        
        // Listen for response (one-time)
        const handleAcquired = (data) => {
            if (data.schedule_id === scheduleId) {
                socket.off('lock_acquired', handleAcquired);
                socket.off('lock_denied', handleDenied);
                resolve(true);
            }
        };
        
        const handleDenied = (data) => {
            if (data.schedule_id === scheduleId) {
                socket.off('lock_acquired', handleAcquired);
                socket.off('lock_denied', handleDenied);
                resolve(false);
            }
        };
        
        socket.on('lock_acquired', handleAcquired);
        socket.on('lock_denied', handleDenied);
        
        // Timeout after 5 seconds
        setTimeout(() => {
            socket.off('lock_acquired', handleAcquired);
            socket.off('lock_denied', handleDenied);
            resolve(false);
        }, 5000);
    });
}

/**
 * Release edit lock on a schedule
 */
function releaseScheduleLock(scheduleId, scheduleType = 'class') {
    if (!socket || !isConnected) return;
    
    socket.emit('release_schedule_lock', {
        schedule_id: scheduleId,
        type: scheduleType
    });
    
    stopHeartbeat();
    currentEditLock = null;
}

/**
 * Start heartbeat to keep lock alive
 */
function startHeartbeat(scheduleId, scheduleType) {
    stopHeartbeat(); // Clear any existing heartbeat
    
    heartbeatInterval = setInterval(() => {
        if (socket && isConnected) {
            socket.emit('heartbeat', {
                schedule_id: scheduleId,
                type: scheduleType
            });
        }
    }, LOCK_HEARTBEAT_INTERVAL);
}

/**
 * Stop heartbeat
 */
function stopHeartbeat() {
    if (heartbeatInterval) {
        clearInterval(heartbeatInterval);
        heartbeatInterval = null;
    }
}

/**
 * Cleanup socket resources during page navigation/unload.
 */
function cleanupSocketConnection() {
    if (!socket) return;

    if (currentEditLock) {
        releaseScheduleLock(currentEditLock.schedule_id, currentEditLock.type);
    } else {
        stopHeartbeat();
    }

    leaveScheduleRoom();

    if (socket.connected) {
        socket.disconnect();
    }

    isConnected = false;
    currentRoom = null;
}

/**
 * Handle schedule change from another user
 */
function handleScheduleChange(data) {
    const action = data.action;
    const schedule = data.schedule;
    const changedBy = data.changed_by_name;
    
    // Skip reload if this change was made by the current user
    // (the AJAX handler already refreshed the calendar/form)
    if (data.changed_by && data.changed_by === window.CURRENT_USER_ID) {
        return;
    }
    
    // Show notification
    let message = '';
    switch (action) {
        case 'created':
            message = `${changedBy} added a new schedule`;
            break;
        case 'updated':
            message = `${changedBy} updated a schedule`;
            break;
        case 'deleted':
            message = `${changedBy} deleted a schedule`;
            break;
        default:
            message = `Schedule was ${action} by ${changedBy}`;
    }
    
    showToast(message, 'info');
    
    // Auto-refresh the page so data stays current
    setTimeout(() => location.reload(), 1500);
}

/**
 * Handle schedule locked notification
 */
function handleScheduleLocked(data) {
    const scheduleId = data.schedule_id;
    const lockedBy = data.locked_by_name;
    
    // Find and update the schedule card/row with a lock indicator
    const scheduleElement = document.querySelector(`[data-schedule-id="${scheduleId}"]`);
    if (scheduleElement) {
        scheduleElement.classList.add('schedule-locked');
        
        // Add lock badge if not already present
        if (!scheduleElement.querySelector('.lock-badge')) {
            const lockBadge = document.createElement('div');
            lockBadge.className = 'lock-badge absolute top-1 right-1 bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs flex items-center gap-1';
            lockBadge.innerHTML = `
                <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path>
                </svg>
                <span>Editing: ${lockedBy}</span>
            `;
            scheduleElement.style.position = 'relative';
            scheduleElement.appendChild(lockBadge);
        }
    }
}

/**
 * Handle schedule unlocked notification
 */
function handleScheduleUnlocked(data) {
    const scheduleId = data.schedule_id;
    
    // Find and remove the lock indicator
    const scheduleElement = document.querySelector(`[data-schedule-id="${scheduleId}"]`);
    if (scheduleElement) {
        scheduleElement.classList.remove('schedule-locked');
        
        const lockBadge = scheduleElement.querySelector('.lock-badge');
        if (lockBadge) {
            lockBadge.remove();
        }
    }
}

/**
 * Refresh all lock indicators on the page
 */
function refreshLockIndicators() {
    // Remove all lock badges
    document.querySelectorAll('.lock-badge').forEach(badge => badge.remove());
    document.querySelectorAll('.schedule-locked').forEach(el => el.classList.remove('schedule-locked'));
}

/**
 * Show refresh prompt when data has changed
 */
function showRefreshPrompt(action, schedule, changedBy) {
    // Check if prompt already exists
    if (document.getElementById('refreshPrompt')) return;
    
    const prompt = document.createElement('div');
    prompt.id = 'refreshPrompt';
    prompt.className = 'fixed bottom-4 left-1/2 transform -translate-x-1/2 bg-blue-600 text-white px-4 py-3 rounded-lg shadow-lg flex items-center gap-3 z-50 animate-slide-up';
    prompt.innerHTML = `
        <svg class="w-5 h-5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path>
        </svg>
        <span>Schedule data has been updated by ${changedBy}</span>
        <button onclick="location.reload()" class="bg-white text-blue-600 px-3 py-1 rounded font-semibold hover:bg-blue-50 transition-colors">
            Refresh
        </button>
        <button onclick="dismissRefreshPrompt()" class="text-white/80 hover:text-white ml-2">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
            </svg>
        </button>
    `;
    
    document.body.appendChild(prompt);
}

/**
 * Dismiss refresh prompt
 */
function dismissRefreshPrompt() {
    const prompt = document.getElementById('refreshPrompt');
    if (prompt) {
        prompt.classList.add('animate-slide-down');
        setTimeout(() => prompt.remove(), 300);
    }
}



/**
 * Check if a schedule is locked before opening edit modal
 */
async function checkAndOpenEditModal(scheduleId, scheduleType = 'class') {
    // First, try to acquire the lock
    const lockAcquired = await acquireScheduleLock(scheduleId, scheduleType);
    
    if (!lockAcquired) {
        // Lock was denied, modal should not open (toast already shown)
        return false;
    }
    
    // Lock acquired, open the modal
    return true;
}

/**
 * Release lock when edit modal is closed without saving
 */
function onEditModalClosed(scheduleId, scheduleType = 'class') {
    if (currentEditLock && currentEditLock.schedule_id === scheduleId) {
        releaseScheduleLock(scheduleId, scheduleType);
    }
}

/**
 * Handle conflict alert from another user's schedule change
 * Triggers a re-check if user is currently editing a form
 */
function handleConflictAlert(data) {
    // Check if any add/edit modal is currently open
    const addModal = document.getElementById('addScheduleModal');
    const editModal = document.getElementById('editScheduleModal');
    
    const addModalOpen = addModal && !addModal.classList.contains('hidden');
    const editModalOpen = editModal && !editModal.classList.contains('hidden');
    
    if (!addModalOpen && !editModalOpen) {
        // No modal open, skip informational realtime add toast.
        return;
    }
    
    // Modal is open - show conflict alert and trigger recheck
    const alertSeverity = data.severity === 'high' ? 'warning' : 'info';
    showToast(`⚠️ ${data.message}. Please verify your current selections.`, alertSeverity);
    
    // Trigger automatic conflict recheck for the open form
    if (addModalOpen && typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck('add');
    } else if (editModalOpen && typeof scheduleAutoConflictCheck === 'function') {
        scheduleAutoConflictCheck('edit');
    }
    
    // Request recheck confirmation from server
    if (socket && isConnected) {
        socket.emit('request_conflict_recheck', {
            type: data.type,
            timestamp: data.timestamp
        });
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Set current academic settings from page data
    const settingsElement = document.querySelector('[data-academic-year]');
    if (settingsElement) {
        window.currentAcademicYear = settingsElement.dataset.academicYear;
        window.currentSemester = settingsElement.dataset.semester;
    }
    
    // Initialize Socket.IO
    initializeSocketIO();
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', cleanupSocketConnection);
    window.addEventListener('pagehide', cleanupSocketConnection);
    
    // Add animation styles
    const realtimeAnimationStyle = document.createElement('style');
    realtimeAnimationStyle.textContent = `
        @keyframes slide-up {
            from { transform: translateX(-50%) translateY(100%); opacity: 0; }
            to { transform: translateX(-50%) translateY(0); opacity: 1; }
        }
        @keyframes slide-down {
            from { transform: translateX(-50%) translateY(0); opacity: 1; }
            to { transform: translateX(-50%) translateY(100%); opacity: 0; }
        }
        .animate-slide-up { animation: slide-up 0.3s ease-out; }
        .animate-slide-down { animation: slide-down 0.3s ease-out; }
        .schedule-locked { opacity: 0.7; pointer-events: none; }
    `;
    document.head.appendChild(realtimeAnimationStyle);
});
