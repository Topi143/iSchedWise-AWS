/**
 * Form State Persistence Module for Schedule Add Page
 * Saves form field values to sessionStorage so they survive page redirects
 * (e.g., after successfully adding a schedule, the page redirects back and
 *  the user can quickly add another one without re-selecting everything).
 *
 * Strategy:
 *  - Save state on every field change (input, change events + polling for hidden fields)
 *  - On page load, detect if saved state exists for the current section
 *  - Wait for async dropdowns (curriculum, subject) to populate, then restore values
 *  - Clear state when section changes or user navigates away from add page
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'ischedwise_form_state';

    // ─── Fields to track ─────────────────────────────────────────────
    const CLASS_FIELDS = [
        { id: 'curriculum_id_add', type: 'select' },
        { id: 'subject_id_add', type: 'select' },
        { id: 'schedule_type_add', type: 'select' },
        { id: 'faculty_id_add', type: 'hidden', displayId: 'facultyDisplayAdd' },
        { id: 'day_of_week_add', type: 'select' },
        { id: 'room_id_add', type: 'hidden', displayId: 'room_search_add' },
        { id: 'start_time_add', type: 'time' },
        { id: 'end_time_add', type: 'time' },
    ];

    // ─── Helpers ─────────────────────────────────────────────────────

    function getSectionId() {
        const el = document.getElementById('section_id_add');
        return el ? el.value : null;
    }

    function getSaved() {
        try {
            const raw = sessionStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch { return null; }
    }

    function setSaved(data) {
        try {
            sessionStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        } catch { /* quota exceeded – ignore */ }
    }

    function clearSaved() {
        sessionStorage.removeItem(STORAGE_KEY);
    }

    // ─── Save current form state ─────────────────────────────────────

    function captureState() {
        if (window._formStateRestoring) return; // Prevent overwriting while async restoring

        const sectionId = getSectionId();
        if (!sectionId) return;

        // Also capture section name from the dropdown
        let sectionName = window.FORM_SECTION_NAME || '';

        const state = { sectionId: sectionId, sectionName: sectionName, ts: Date.now(), fields: {} };

        CLASS_FIELDS.forEach(f => {
            const el = document.getElementById(f.id);
            if (!el) return;
            state.fields[f.id] = el.value || '';

            // For room: also save the display text
            if (f.id === 'room_id_add') {
                const display = document.getElementById('room_search_add');
                if (display) state.fields['_room_display'] = display.value || '';
            }

            // For faculty: save the display HTML & faculty name for quick restore
            if (f.id === 'faculty_id_add') {
                const display = document.getElementById('facultyDisplayAdd');
                if (display) state.fields['_faculty_html'] = display.innerHTML || '';
            }
        });

        setSaved(state);
    }

    // ─── Restore form state ──────────────────────────────────────────

    /**
     * Attempt to restore form state after async data loads.
     * Returns true if there is state to restore (even if not yet complete).
     */
    /**
     * Restore the section selection from saved state.
     * Called before tryRestore when the page loads without a server-side section.
     * Returns true if section was restored, false if no restore needed.
     */
    function restoreSection() {
        const saved = getSaved();
        if (!saved || !saved.sectionId) return false;

        // Check if state is stale (older than 30 minutes)
        if (Date.now() - saved.ts > 30 * 60 * 1000) {
            clearSaved();
            return false;
        }

        // If section is already set server-side, no need to restore
        if (window.FORM_SECTION_ID) return true;

        // Find the section in the dropdown and select it
        const switcher = document.getElementById('modalSectionSwitcher');
        if (!switcher) return false;

        const savedId = String(saved.sectionId);
        for (let i = 0; i < switcher.options.length; i++) {
            if (String(switcher.options[i].value) === savedId) {
                switcher.value = savedId;
                // Trigger the section switch which shows form fields, loads curricula, etc.
                if (typeof switchModalSection === 'function') {
                    switchModalSection(savedId);
                }
                return true;
            }
        }

        // Section not found in dropdown (deleted?), clear state
        clearSaved();
        return false;
    }

    function tryRestore() {
        const saved = getSaved();
        if (!saved || !saved.fields) return false;

        const currentSection = getSectionId();
        if (!currentSection) {
            // Section can be briefly empty while async UI initializes; keep waiting.
            return false;
        }

        if (String(saved.sectionId) !== String(currentSection)) {
            // Different section selected – saved state is no longer applicable.
            clearSaved();
            return false;
        }

        // Check if state is stale (older than 30 minutes)
        if (Date.now() - saved.ts > 30 * 60 * 1000) {
            clearSaved();
            return false;
        }

        const fields = saved.fields;
        let allDone = true;

        // 1. Restore curriculum (must wait for options to be populated)
        const currSel = document.getElementById('curriculum_id_add');
        if (currSel && fields['curriculum_id_add']) {
            if (currSel.options.length <= 1 || currSel.disabled) {
                // Options not loaded yet
                allDone = false;
            } else {
                // Try to set value
                currSel.value = fields['curriculum_id_add'];
                if (currSel.value !== fields['curriculum_id_add']) {
                    // Option doesn't exist (curriculum changed?) – skip restore
                    clearSaved();
                    return false;
                }
                // Trigger subject loading if not already loaded
                const subSel = document.getElementById('subject_id_add');
                if (subSel && (subSel.options.length <= 1 || subSel.disabled)) {
                    // Need to load subjects for this curriculum
                    if (typeof window.loadSubjectsForCurriculum === 'function') {
                        window.loadSubjectsForCurriculum('add');
                    }
                    allDone = false;
                }
            }
        }

        // 2. Restore subject (must wait for subject options)
        const subSel = document.getElementById('subject_id_add');
        if (subSel && fields['subject_id_add']) {
            if (subSel.options.length <= 1 || subSel.disabled) {
                allDone = false;
            } else if (!subSel.value || subSel.value !== fields['subject_id_add']) {
                subSel.value = fields['subject_id_add'];
                if (subSel.value === fields['subject_id_add']) {
                    // Trigger subject change to populate schedule types + faculty
                    if (typeof window.handleSubjectChange === 'function') {
                        window.handleSubjectChange('add');
                    }
                    // Schedule type and faculty will be set on next poll cycle
                    allDone = false;
                }
            }
        }

        // 3. Restore schedule type (available after subject is selected)
        const typeSel = document.getElementById('schedule_type_add');
        if (typeSel && fields['schedule_type_add']) {
            if (typeSel.value !== fields['schedule_type_add']) {
                typeSel.value = fields['schedule_type_add'];
                if (typeSel.value === fields['schedule_type_add']) {
                    if (typeof window.handleScheduleTypeChange === 'function') {
                        window.handleScheduleTypeChange('add');
                    }
                }
            }
        }

        // 4. Restore day of week (static options – always available)
        const daySel = document.getElementById('day_of_week_add');
        if (daySel && fields['day_of_week_add']) {
            daySel.value = fields['day_of_week_add'];
        }

        // 5. Restore room
        const roomHidden = document.getElementById('room_id_add');
        const roomSearch = document.getElementById('room_search_add');
        if (roomHidden && fields['room_id_add']) {
            roomHidden.value = fields['room_id_add'];
            if (roomSearch && fields['_room_display']) {
                roomSearch.value = fields['_room_display'];
            }
        }

        // 6. Restore faculty (hidden value + display)
        const facHidden = document.getElementById('faculty_id_add');
        if (facHidden && fields['faculty_id_add']) {
            facHidden.value = fields['faculty_id_add'];
            const facDisplay = document.getElementById('facultyDisplayAdd');
            if (facDisplay && fields['_faculty_html'] && fields['_faculty_html'].trim()) {
                facDisplay.innerHTML = fields['_faculty_html'];
            }
        }

        // 7. Restore times
        const startTime = document.getElementById('start_time_add');
        const endTime = document.getElementById('end_time_add');
        if (startTime && fields['start_time_add']) startTime.value = fields['start_time_add'];
        if (endTime && fields['end_time_add']) endTime.value = fields['end_time_add'];

        return allDone;
    }

    // ─── Init: bind listeners + attempt restore ──────────────────────

    let _restoreTimer = null;
    let _saveInterval = null;

    function init() {
        // Only run on add mode
        if (window.SCHEDULE_FORM_MODE !== 'add') return;

        // Bind change/input listeners to save state on every interaction
        CLASS_FIELDS.forEach(f => {
            const el = document.getElementById(f.id);
            if (!el) return;
            el.addEventListener('change', captureState);
            el.addEventListener('input', captureState);
        });

        // Also watch the room search display input
        const roomSearch = document.getElementById('room_search_add');
        if (roomSearch) roomSearch.addEventListener('change', captureState);

        // Poll hidden fields (faculty_id, room_id) that change programmatically
        _saveInterval = setInterval(captureState, 1000);

        // Attempt to restore state with polling (async data may take a moment)
        const saved = getSaved();
        if (saved && saved.sectionId) {
            window._formStateRestoring = true;

            // First, restore the section selection (if page loaded without one)
            const sectionRestored = restoreSection();

            if (sectionRestored && saved.fields) {
                // Wait a bit for section switch to trigger curricula loading, then restore fields
                let attempts = 0;
                const maxAttempts = 120; // up to 12 seconds for slower async loads
                _restoreTimer = setInterval(() => {
                    attempts++;
                    const done = tryRestore();
                    if (done || attempts >= maxAttempts) {
                        clearInterval(_restoreTimer);
                        _restoreTimer = null;
                        
                        window._formStateRestoring = false;

                        // Trigger auto-conflict check if fields are populated
                        if (typeof scheduleAutoConflictCheck === 'function') {
                            const facVal = document.getElementById('faculty_id_add');
                            const dayVal = document.getElementById('day_of_week_add');
                            if (facVal && facVal.value && dayVal && dayVal.value) {
                                setTimeout(() => scheduleAutoConflictCheck('add'), 300);
                            }
                        }
                    }
                }, 100);
            } else {
                window._formStateRestoring = false;
            }
        }
    }

    // ─── Public API ──────────────────────────────────────────────────

    // Flag to prevent clearing state during restore
    window._formStateRestoring = false;

    // Clear saved state (called when section changes, form submits, etc.)
    window.clearFormState = function () {
        if (window._formStateRestoring) return; // Don't clear during restore
        clearSaved();
    };

    // Allow manual save trigger
    window.saveFormState = captureState;

    // Initialize on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        // DOM already ready (script loaded at end of body)
        init();
    }

    // Clean up interval on page unload
    window.addEventListener('beforeunload', function () {
        if (_saveInterval) clearInterval(_saveInterval);
        if (_restoreTimer) clearInterval(_restoreTimer);
    });

})();
