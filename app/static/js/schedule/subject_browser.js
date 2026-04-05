/**
 * Subject Browser Drawer
 * Slide-in panel for browsing all program subjects across curricula.
 * Shared across: class form (add/edit), exam form (add/edit), batch builder, batch exam builder.
 */
(function () {
    'use strict';

    let _drawerOpen = false;
    let _activeMode = null;       // 'add', 'edit', 'exam_add', 'exam_edit', 'batch', 'exam_batch'
    let _cachedSubjects = [];     // Raw subjects from API
    let _filteredSubjects = [];   // After applying filters
    const SUBJECT_DRAWER_DESKTOP_BREAKPOINT = 768;

    function isSubjectDrawerDesktopViewport() {
        return window.innerWidth >= SUBJECT_DRAWER_DESKTOP_BREAKPOINT;
    }

    function debounceSubjectDrawer(fn, wait = 120) {
        let timeout;
        return (...args) => {
            clearTimeout(timeout);
            timeout = setTimeout(() => fn(...args), wait);
        };
    }

    function syncSubjectDrawerViewportState() {
        const drawer = document.getElementById('subjectDrawer');
        const overlay = document.getElementById('subjectDrawerOverlay');
        if (!drawer) return;

        if (isSubjectDrawerDesktopViewport()) {
            if (_drawerOpen) {
                drawer.classList.remove('translate-x-full', 'translate-y-full');
                drawer.classList.add('translate-x-0');
            } else {
                drawer.classList.remove('translate-x-0', 'translate-y-0');
                drawer.classList.add('translate-x-full');
            }
            if (overlay) {
                overlay.classList.add('hidden');
                overlay.classList.remove('block');
            }
            return;
        }

        if (_drawerOpen) {
            drawer.classList.remove('translate-y-full', 'translate-x-full');
            drawer.classList.add('translate-y-0');
            if (overlay) {
                overlay.classList.remove('hidden');
                overlay.classList.add('block');
            }
        } else {
            drawer.classList.remove('translate-y-0', 'translate-x-0');
            drawer.classList.add('translate-y-full');
            if (overlay) {
                overlay.classList.add('hidden');
                overlay.classList.remove('block');
            }
        }
    }

    // ── Open / Close ───────────────────────────────────────────────

    function openSubjectBrowser(mode) {
        const drawer = document.getElementById('subjectDrawer');
        const overlay = document.getElementById('subjectDrawerOverlay');
        if (!drawer) return;

        _activeMode = mode;
        _drawerOpen = true;

        // Close AI drawer if open (avoid z-index overlap)
        if (typeof closeAIDrawer === 'function') closeAIDrawer();

        // Determine section ID based on mode
        let sectionId = null;
        if (mode === 'add' || mode === 'edit') {
            sectionId = document.getElementById('section_id_add')?.value
                     || document.getElementById('section_id_edit')?.value;
        } else if (mode === 'exam_add' || mode === 'exam_edit') {
            sectionId = document.getElementById('section_id_exam_add')?.value
                     || document.getElementById('section_id_exam_edit')?.value;
        } else if (mode === 'batch') {
            sectionId = window.FORM_SECTION_ID;
        } else if (mode === 'exam_batch') {
            sectionId = window.EXAM_BATCH_SECTION_ID;
        }

        if (!sectionId) {
            if (typeof showToast === 'function') showToast('Select a section first', 'error');
            _drawerOpen = false;
            return;
        }

        // Show drawer with transition
        if (isSubjectDrawerDesktopViewport()) {
            drawer.classList.remove('translate-x-full');
            drawer.classList.add('translate-x-0');
        } else {
            drawer.classList.remove('translate-y-full');
            drawer.classList.add('translate-y-0');
            if (overlay) {
                overlay.classList.remove('hidden');
                overlay.classList.add('block');
            }
        }

        // Reset filters
        const search = document.getElementById('subjectDrawerSearch');
        if (search) search.value = '';
        const yearFilter = document.getElementById('subjectDrawerYearFilter');
        const semFilter = document.getElementById('subjectDrawerSemFilter');
        if (yearFilter) yearFilter.value = '';
        if (semFilter) semFilter.value = '';

        // Show loading state
        _showDrawerState('loading');

        // Choose API endpoint based on mode
        let url;
        if (mode === 'batch') {
            url = `/schedule/batch-all-program-subjects/${sectionId}`;
        } else if (mode === 'exam_batch') {
            url = `/schedule/batch-all-program-subjects/${sectionId}`;
        } else {
            url = `/schedule/get-program-subjects/${sectionId}`;
        }

        fetch(url)
            .then(r => r.json())
            .then(data => {
                _cachedSubjects = data.subjects || [];
                _populateDrawerFilters();
                _filterDrawerSubjects();
            })
            .catch(err => {
                console.error('Error loading subjects for drawer:', err);
                _showDrawerState('empty');
            });
    }

    function closeSubjectBrowser() {
        const drawer = document.getElementById('subjectDrawer');
        const overlay = document.getElementById('subjectDrawerOverlay');
        if (!drawer) return;

        _drawerOpen = false;

        if (isSubjectDrawerDesktopViewport()) {
            drawer.classList.add('translate-x-full');
            drawer.classList.remove('translate-x-0');
        } else {
            drawer.classList.add('translate-y-full');
            drawer.classList.remove('translate-y-0');
            if (overlay) {
                overlay.classList.add('hidden');
                overlay.classList.remove('block');
            }
        }
    }

    // ── Internal Helpers ──────────────────────────────────────────

    function _showDrawerState(state) {
        const loading = document.getElementById('subjectDrawerLoading');
        const empty = document.getElementById('subjectDrawerEmpty');
        const items = document.getElementById('subjectDrawerItems');
        if (loading) loading.classList.toggle('hidden', state !== 'loading');
        if (empty) empty.classList.toggle('hidden', state !== 'empty');
        if (items) items.classList.toggle('hidden', state !== 'items');
    }

    function _populateDrawerFilters() {
        const yearSelect = document.getElementById('subjectDrawerYearFilter');
        const semSelect = document.getElementById('subjectDrawerSemFilter');

        const years = new Set();
        const semesters = new Set();

        _cachedSubjects.forEach(s => {
            if (s.year_level_name) years.add(s.year_level_name);
            if (s.semester_name) semesters.add(s.semester_name);
        });

        if (yearSelect) {
            yearSelect.innerHTML = '<option value="">All Years</option>';
            [...years].sort().forEach(y => {
                const opt = document.createElement('option');
                opt.value = y; opt.textContent = y;
                yearSelect.appendChild(opt);
            });
        }
        if (semSelect) {
            semSelect.innerHTML = '<option value="">All Sems</option>';
            [...semesters].sort().forEach(s => {
                const opt = document.createElement('option');
                opt.value = s; opt.textContent = s;
                semSelect.appendChild(opt);
            });
        }
    }

    function _filterDrawerSubjects() {
        const searchInput = document.getElementById('subjectDrawerSearch');
        const yearSelect = document.getElementById('subjectDrawerYearFilter');
        const semSelect = document.getElementById('subjectDrawerSemFilter');
        const countLabel = document.getElementById('subjectDrawerCount');

        const searchTerm = (searchInput ? searchInput.value : '').toLowerCase().trim();
        const yearFilter = yearSelect ? yearSelect.value : '';
        const semFilter = semSelect ? semSelect.value : '';

        _filteredSubjects = _cachedSubjects.filter(s => {
            if (yearFilter && s.year_level_name !== yearFilter) return false;
            if (semFilter && s.semester_name !== semFilter) return false;
            if (searchTerm) {
                const haystack = `${s.subject_code} ${s.course_description} ${s.group_label || ''}`.toLowerCase();
                if (!haystack.includes(searchTerm)) return false;
            }
            return true;
        });

        if (countLabel) {
            countLabel.textContent = `${_filteredSubjects.length}`;
        }

        _renderDrawerItems();
    }

    function _renderDrawerItems() {
        const container = document.getElementById('subjectDrawerItems');
        if (!container) return;

        if (_filteredSubjects.length === 0) {
            _showDrawerState('empty');
            return;
        }

        _showDrawerState('items');

        // Group by group_label
        const groups = {};
        _filteredSubjects.forEach(s => {
            const key = s.group_label || 'Other';
            if (!groups[key]) groups[key] = [];
            groups[key].push(s);
        });

        let html = '';
        Object.keys(groups).forEach(label => {
            html += `<div class="px-3 py-1.5 bg-gray-50 dark:bg-gray-900/60 border-b border-gray-100 dark:border-gray-700 sticky top-0 z-10">
                <span class="text-[10px] font-bold text-gray-500 dark:text-gray-300 uppercase tracking-wider">${_escapeHtml(label)}</span>
            </div>`;

            groups[label].forEach(s => {
                // For batch modes, subjects have subject_id; for form modes, they have id
                const subjectId = s.subject_id || s.id;
                const schedType = s.schedule_type || '';
                const units = s.total_units != null ? s.total_units : (s.lec_units + s.lab_units);
                const duration = s.duration_minutes ? ` · ${s.duration_minutes}min` : '';
                const typeLabel = schedType ? (schedType === 'lab' ? ' LAB' : ' LEC') : '';

                html += `<button type="button" onclick="_selectDrawerSubject(${subjectId}, '${schedType}')"
                    class="w-full text-left px-4 py-2.5 border-b border-gray-50 dark:border-gray-700 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 transition-colors group flex items-start gap-3">
                    <div class="flex-1 min-w-0">
                        <div class="flex items-center gap-1.5">
                            <span class="text-xs font-bold text-gray-800 dark:text-gray-100 group-hover:text-indigo-700 dark:group-hover:text-indigo-300">${_escapeHtml(s.subject_code)}</span>
                            ${typeLabel ? `<span class="text-[9px] font-semibold px-1 py-0.5 rounded bg-gray-100 dark:bg-gray-700 text-gray-500 dark:text-gray-300">${typeLabel}</span>` : ''}
                        </div>
                        <p class="text-[11px] text-gray-500 dark:text-gray-400 truncate mt-0.5">${_escapeHtml(s.course_description)}</p>
                    </div>
                    <span class="text-[10px] font-semibold text-indigo-500 dark:text-indigo-300 bg-indigo-50 dark:bg-indigo-900/30 px-1.5 py-0.5 rounded-full flex-shrink-0 mt-0.5">${units}u${duration}</span>
                </button>`;
            });
        });

        container.innerHTML = html;
    }

    function _selectDrawerSubject(subjectId, scheduleType) {
        const mode = _activeMode;
        if (!mode) return;

        if (mode === 'batch') {
            _selectForBatch(subjectId, scheduleType);
        } else if (mode === 'exam_batch') {
            _selectForExamBatch(subjectId, scheduleType);
        } else {
            // Form modes: add, edit, exam_add, exam_edit
            _selectForForm(subjectId, mode);
        }

        closeSubjectBrowser();
    }

    /**
     * Select subject for the add/edit form: set the <select> value and trigger change handlers.
     */
    function _selectForForm(subjectId, mode) {
        const subjectSelect = document.getElementById(`subject_id_${mode}`);
        if (!subjectSelect) return;

        // Find the subject in cached data
        const subject = _cachedSubjects.find(s => (s.id || s.subject_id) == subjectId);
        if (!subject) return;

        // Check if the option already exists in the select
        let optionExists = false;
        for (let i = 0; i < subjectSelect.options.length; i++) {
            if (subjectSelect.options[i].value == subjectId) {
                subjectSelect.value = subjectId;
                optionExists = true;
                break;
            }
        }

        // If option doesn't exist, add it (cross-level subject)
        if (!optionExists) {
            const option = document.createElement('option');
            option.value = subject.id || subject.subject_id;
            option.textContent = subject.display || `${subject.subject_code} - ${subject.course_description} (${subject.total_units} units)`;
            option.dataset.code = subject.subject_code;
            option.dataset.description = subject.course_description;
            option.dataset.lecUnits = subject.lec_units;
            option.dataset.labUnits = subject.lab_units;
            option.dataset.totalUnits = subject.total_units;
            subjectSelect.appendChild(option);
            subjectSelect.value = option.value;
        }

        // Trigger the appropriate change handler
        if (mode === 'add' || mode === 'edit') {
            if (typeof handleSubjectChange === 'function') {
                handleSubjectChange(mode);
            }
        } else if (mode === 'exam_add' || mode === 'exam_edit') {
            const examMode = mode.replace('exam_', '');
            if (typeof handleExamSubjectChange === 'function') {
                handleExamSubjectChange(examMode);
            }
        }
    }

    /**
     * Select subject for batch builder: add it as a new row via existing addSelectedSubject().
     */
    function _selectForBatch(subjectId, scheduleType) {
        // Find the subject in batch data
        const subject = _cachedSubjects.find(s =>
            s.subject_id == subjectId && (!scheduleType || s.schedule_type === scheduleType)
        );
        if (!subject) return;

        // Store in _availableSubjects and set batchSubjectSelect for addSelectedSubject()
        if (typeof window._availableSubjects === 'undefined') return;

        // Check if already in _availableSubjects
        let idx = window._availableSubjects.indexOf(subject);
        if (idx === -1) {
            window._availableSubjects.push(subject);
            idx = window._availableSubjects.length - 1;
        }

        const select = document.getElementById('batchSubjectSelect');
        if (select) {
            // Add option temporarily
            const opt = document.createElement('option');
            opt.value = idx;
            opt.textContent = subject.subject_code;
            opt.selected = true;
            select.appendChild(opt);
        }

        // Call the existing add function
        if (typeof addSelectedSubject === 'function') {
            addSelectedSubject();
        }
    }

    /**
     * Select subject for exam batch builder: add it as a new row via existing addExamSelectedSubject().
     */
    function _selectForExamBatch(subjectId, scheduleType) {
        const subject = _cachedSubjects.find(s =>
            s.subject_id == subjectId && (!scheduleType || s.schedule_type === scheduleType)
        );
        if (!subject) return;

        if (typeof window._examAvailableSubjects === 'undefined') return;

        let idx = window._examAvailableSubjects.indexOf(subject);
        if (idx === -1) {
            window._examAvailableSubjects.push(subject);
            idx = window._examAvailableSubjects.length - 1;
        }

        const select = document.getElementById('examBatchSubjectSelect');
        if (select) {
            const opt = document.createElement('option');
            opt.value = idx;
            opt.textContent = subject.subject_code;
            opt.selected = true;
            select.appendChild(opt);
        }

        if (typeof addExamSelectedSubject === 'function') {
            addExamSelectedSubject();
        }
    }

    function _escapeHtml(str) {
        const div = document.createElement('div');
        div.textContent = str || '';
        return div.innerHTML;
    }

    // ── Expose globals ───────────────────────────────────────────

    window.openSubjectBrowser = openSubjectBrowser;
    window.closeSubjectBrowser = closeSubjectBrowser;
    window._filterDrawerSubjects = _filterDrawerSubjects;
    window._selectDrawerSubject = _selectDrawerSubject;

    window.addEventListener('resize', debounceSubjectDrawer(syncSubjectDrawerViewportState, 120));
    window.addEventListener('orientationchange', debounceSubjectDrawer(syncSubjectDrawerViewportState, 120));

    document.addEventListener('DOMContentLoaded', syncSubjectDrawerViewportState);

})();
