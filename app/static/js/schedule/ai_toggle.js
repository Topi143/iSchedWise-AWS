/**
 * Schedule Assistant Mode Controller
 * Controls Quick vs Detailed presentation modes for the assistant drawer.
 *
 * Both modes keep full conflict handling actions (apply suggestions, generate plan).
 * Quick mode is concise, Detailed mode adds richer context.
 */

(function () {
    'use strict';

    const LEGACY_STORAGE_KEY = 'aiAssistantEnabled';
    const MODE_STORAGE_KEY = 'scheduleAssistantMode';
    const MODE_QUICK = 'quick';
    const MODE_DETAILED = 'detailed';

    const TOGGLE_IDS = ['aiToggleClassDesktop'];

    // Panel element groups affected by the mode toggle
    const CLASS_PANEL_IDS = {
        assistant: 'aiAssistantAdd',
        recommendations: 'aiRecommendationsAdd',
        explanationWrapper: 'aiExplanationWrapperAdd',
        emptyState: 'aiEmptyStateAdd',
        emptyIcon: 'aiEmptyIconAdd',
        workloadSummary: 'aiWorkloadSummaryAdd',
        resolveAll: 'aiResolveAllAdd',
        basicHint: 'aiBasicModeHintAdd',
        recsHeader: 'aiRecommendationsHeaderAdd',
        conflicts: 'aiConflictsAdd',
        conflictsList: 'aiConflictsListAdd',
        recommendationsList: 'aiRecommendationsListAdd',
        autoCheckStatus: 'autoCheckStatusAdd',
        loading: 'aiLoadingAdd'
    };

    const EXAM_PANEL_IDS = {
        assistant: 'aiAssistantExamAdd',
        recommendations: 'aiRecommendationsExamAdd',
        explanationWrapper: 'aiExplanationWrapperExamAdd',
        emptyState: 'aiEmptyStateExamAdd',
        emptyIcon: 'aiEmptyIconExamAdd',
        workloadSummary: null,
        resolveAll: null,
        basicHint: 'aiBasicModeHintExamAdd',
        recsHeader: 'aiRecommendationsHeaderExamAdd',
        conflicts: 'aiConflictsExamAdd',
        conflictsList: 'aiConflictsListExamAdd',
        recommendationsList: 'aiRecommendationsListExamAdd',
        autoCheckStatus: 'autoCheckStatusExamAdd',
        loading: 'aiLoadingExamAdd'
    };

    // SVG icons
    const DETAILED_ICON = '<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>';
    const QUICK_ICON = '<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';

    function normalizeMode(value) {
        return value === MODE_DETAILED ? MODE_DETAILED : MODE_QUICK;
    }

    function resolveInitialMode() {
        const storedMode = localStorage.getItem(MODE_STORAGE_KEY);
        if (storedMode === MODE_QUICK || storedMode === MODE_DETAILED) {
            return storedMode;
        }

        const legacy = localStorage.getItem(LEGACY_STORAGE_KEY);
        if (legacy === 'true') {
            return MODE_DETAILED;
        }
        if (legacy === 'false') {
            return MODE_QUICK;
        }

        return MODE_QUICK;
    }

    function persistMode(mode) {
        const normalizedMode = normalizeMode(mode);
        localStorage.setItem(MODE_STORAGE_KEY, normalizedMode);
        // Keep legacy key for older call-sites and backward compatibility.
        localStorage.setItem(LEGACY_STORAGE_KEY, normalizedMode === MODE_DETAILED ? 'true' : 'false');
    }

    function getModeFromWindow() {
        return normalizeMode(window.scheduleAssistantMode);
    }

    function isDetailedMode() {
        return getModeFromWindow() === MODE_DETAILED;
    }

    function syncCheckboxes(detailed) {
        TOGGLE_IDS.forEach(function (id) {
            var cb = document.getElementById(id);
            if (cb) cb.checked = detailed;
        });
    }

    /** Update the "Quick" / "Detailed" labels next to the toggle switch. */
    function updateToggleLabels(detailed) {
        var quickLabel = document.getElementById('aiToggleLabelBasic');
        var detailedLabel = document.getElementById('aiToggleLabelAI');

        if (quickLabel) {
            quickLabel.className = 'text-[10px] font-medium select-none transition-colors duration-200 ' + (detailed ? 'text-gray-400' : 'text-blue-600 dark:text-blue-300');
        }
        if (detailedLabel) {
            detailedLabel.className = 'text-[10px] font-medium select-none transition-colors duration-200 ' + (detailed ? 'text-purple-600 dark:text-purple-300' : 'text-gray-400');
        }
    }

    /** Update drawer header icon, title, subtitle to match mode. */
    function updateDrawerHeader(detailed) {
        var icon = document.getElementById('aiDrawerHeaderIcon');
        var title = document.getElementById('aiDrawerTitle');
        var subtitle = document.getElementById('aiDrawerSubtitle');
        var modeLabel = document.getElementById('aiDrawerModeLabel');

        if (icon) {
            icon.className = 'w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-200 ' + (detailed ? 'bg-purple-600' : 'bg-blue-600');
            icon.innerHTML = detailed ? DETAILED_ICON : QUICK_ICON;
        }
        if (title) title.textContent = 'Schedule Assistant';
        if (subtitle) {
            subtitle.textContent = detailed
                ? 'Expanded analysis with rationale and workload context'
                : 'Essential conflict checks with direct actions';
        }
        if (modeLabel) modeLabel.textContent = detailed ? 'Detailed mode' : 'Quick mode';
    }

    function updateCapabilityPanel(detailed) {
        var modeBadge = document.getElementById('aiModeBadge');
        var applyCapability = document.getElementById('aiCapabilityApply');
        var explainCapability = document.getElementById('aiCapabilityExplain');

        if (modeBadge) {
            modeBadge.textContent = detailed ? 'Detailed' : 'Quick';
            modeBadge.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ' +
                (detailed
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                    : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300');
        }

        if (applyCapability) {
            applyCapability.className = 'flex items-center justify-between text-gray-600 dark:text-gray-300';
            var applyHint = applyCapability.querySelector('span:last-child');
            if (applyHint) {
                applyHint.textContent = 'Enabled';
                applyHint.className = 'font-semibold text-emerald-600 dark:text-emerald-400';
            }
        }

        if (explainCapability) {
            explainCapability.className = 'flex items-center justify-between text-gray-600 dark:text-gray-300';
            var explainHint = explainCapability.querySelector('span:last-child');
            if (explainHint) {
                explainHint.textContent = detailed ? 'Expanded' : 'Concise';
                explainHint.className = 'font-semibold ' + (detailed ? 'text-purple-600 dark:text-purple-400' : 'text-blue-600 dark:text-blue-400');
            }
        }
    }

    function setAIFallbackNotice(message) {
        var wrapper = document.getElementById('aiFallbackNotice');
        var textEl = document.getElementById('aiFallbackNoticeText');
        if (!wrapper || !textEl) return;

        if (message && String(message).trim()) {
            textEl.textContent = message;
            wrapper.classList.remove('hidden');
            return;
        }

        textEl.textContent = '';
        wrapper.classList.add('hidden');
    }

    /** Update empty-state icon + text based on mode. */
    function updateEmptyStates(detailed) {
        [CLASS_PANEL_IDS, EXAM_PANEL_IDS].forEach(function (g) {
            var emptyEl = document.getElementById(g.emptyState);
            if (!emptyEl) return;

            var pTag = emptyEl.querySelector('p');
            var h5Tag = emptyEl.querySelector('h5');
            var iconContainer = document.getElementById(g.emptyIcon);

            if (h5Tag) {
                h5Tag.textContent = detailed ? 'Detailed Review' : 'Quick Review';
            }

            if (pTag) {
                if (detailed) {
                    pTag.textContent = g === EXAM_PANEL_IDS
                        ? 'Complete exam details to view rationale, trade-offs, and context-rich suggestions.'
                        : 'Complete schedule details to view rationale, trade-offs, and context-rich suggestions.';
                } else {
                    pTag.textContent = g === EXAM_PANEL_IDS
                        ? 'Complete exam details for a clean conflict review and direct next actions.'
                        : 'Complete schedule details for a clean conflict review and direct next actions.';
                }
                pTag.className = 'text-[10px] text-gray-400 dark:text-gray-500 max-w-[180px] leading-relaxed';
            }

            if (iconContainer) {
                var circle = iconContainer.querySelector('.w-12');
                if (circle) {
                    if (detailed) {
                        circle.className = 'w-12 h-12 rounded-full bg-purple-50 dark:bg-purple-900/20 flex items-center justify-center mx-auto';
                        circle.innerHTML = '<svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>';
                    } else {
                        circle.className = 'w-12 h-12 rounded-full bg-blue-50 dark:bg-blue-900/20 flex items-center justify-center mx-auto';
                        circle.innerHTML = '<svg class="w-5 h-5 text-blue-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';
                    }
                }
            }
        });
    }

    /** Show/hide detailed-only info panels and mode hints. */
    function hideAiOnlyPanels(detailed) {
        [CLASS_PANEL_IDS, EXAM_PANEL_IDS].forEach(function (g) {
            if (g.workloadSummary) {
                var wl = document.getElementById(g.workloadSummary);
                if (wl && !detailed) wl.classList.add('hidden');
            }

            var hint = g.basicHint ? document.getElementById(g.basicHint) : null;
            if (hint) {
                hint.classList.toggle('hidden', detailed);
                var hintText = hint.querySelector('p');
                if (hintText) {
                    hintText.textContent = 'Detailed mode includes fuller rationale and workload context.';
                }
            }

            var recsHeader = g.recsHeader ? document.getElementById(g.recsHeader) : null;
            if (recsHeader) {
                var subP = recsHeader.querySelector('p');
                if (subP) {
                    subP.textContent = detailed
                        ? 'Apply actions with richer context and supporting rationale.'
                        : 'Apply actions directly with concise guidance.';
                }
            }
        });
    }

    /**
     * Clear all rendered content in the drawer so a fresh check
     * populates from scratch. Resets both class and exam containers
     * for both Add and Edit suffixes.
     */
    function clearAllContent() {
        var suffixes = ['Add', 'Edit'];
        suffixes.forEach(function (sfx) {
            // Class containers
            var ids = [
                'autoCheckStatus' + sfx,
                'aiConflictsList' + sfx,
                'aiRecommendationsList' + sfx,
                'aiResolveAll' + sfx,
                'aiWorkloadSummary' + sfx,
                // Exam containers
                'autoCheckStatusExam' + sfx,
                'aiConflictsListExam' + sfx,
                'aiRecommendationsListExam' + sfx
            ];
            ids.forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.innerHTML = '';
            });

            // Hide wrapper containers
            var hideIds = [
                'aiAssistant' + sfx,
                'aiConflicts' + sfx,
                'aiRecommendations' + sfx,
                'aiExplanationWrapper' + sfx,
                'aiWorkloadSummary' + sfx,
                'aiResolveAll' + sfx,
                'aiAssistantExam' + sfx,
                'aiConflictsExam' + sfx,
                'aiRecommendationsExam' + sfx,
                'aiExplanationWrapperExam' + sfx
            ];
            hideIds.forEach(function (id) {
                var el = document.getElementById(id);
                if (el) el.classList.add('hidden');
            });
        });

        // Show empty states again
        ['aiEmptyStateAdd', 'aiEmptyStateEdit', 'aiEmptyStateExamAdd', 'aiEmptyStateExamEdit'].forEach(function (id) {
            var el = document.getElementById(id);
            if (el) el.classList.remove('hidden');
        });
    }

    function setAssistantMode(mode) {
        const normalizedMode = normalizeMode(mode);
        const detailed = normalizedMode === MODE_DETAILED;

        window.scheduleAssistantMode = normalizedMode;
        window.aiAssistantEnabled = detailed;
        persistMode(normalizedMode);

        return detailed;
    }

    function isVisibleModal(modalId) {
        var modal = document.getElementById(modalId);
        return Boolean(modal && !modal.classList.contains('hidden'));
    }

    function resolveClassRecheckMode() {
        // Unified schedule workflows (modal + inline form) use *_add field IDs and add-panel IDs,
        // even when editing an existing schedule.
        if (isVisibleModal('editScheduleModal') && !isVisibleModal('addScheduleModal')) {
            return 'edit';
        }

        return 'add';
    }

    function resolveExamRecheckMode() {
        // Unified exam workflows also bind to *_add field IDs and add-panel IDs.
        if (isVisibleModal('editExamScheduleModal') && !isVisibleModal('addExamScheduleModal')) {
            return 'edit';
        }

        return 'add';
    }

    /** Main handler called when the toggle checkbox changes. */
    function onToggleChange(detailed) {
        setAssistantMode(detailed ? MODE_DETAILED : MODE_QUICK);

        syncCheckboxes(detailed);
        updateToggleLabels(detailed);
        updateDrawerHeader(detailed);
        updateCapabilityPanel(detailed);
        setAIFallbackNotice('');
        updateEmptyStates(detailed);
        hideAiOnlyPanels(detailed);

        // Clear all existing content before re-fetching.
        clearAllContent();

        // Reset badge to idle.
        if (typeof updateAIBadge === 'function') updateAIBadge('idle');

        // Re-trigger conflict checks so the server gets the updated use_ai flag.
        if (typeof scheduleAutoConflictCheck === 'function') {
            scheduleAutoConflictCheck(resolveClassRecheckMode());
        }
        if (typeof scheduleAutoExamConflictCheck === 'function') {
            scheduleAutoExamConflictCheck(resolveExamRecheckMode());
        }
    }

    // Initialize mode state with backward-compatible migration.
    const initialMode = resolveInitialMode();
    setAssistantMode(initialMode);

    // Public helper methods used by other schedule scripts.
    window.getScheduleAssistantMode = function () {
        return getModeFromWindow();
    };

    window.isDetailedAssistantMode = function () {
        return isDetailedMode();
    };

    window.isQuickAssistantMode = function () {
        return !isDetailedMode();
    };

    // Keep legacy helper: true means Detailed mode (AI-rich mode).
    window.isAiToggleEnabled = function () {
        return isDetailedMode();
    };

    // ── Initialization ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        const detailed = isDetailedMode();

        syncCheckboxes(detailed);
        updateToggleLabels(detailed);
        updateDrawerHeader(detailed);
        updateCapabilityPanel(detailed);
        setAIFallbackNotice('');
        updateEmptyStates(detailed);
        hideAiOnlyPanels(detailed);

        TOGGLE_IDS.forEach(function (id) {
            var cb = document.getElementById(id);
            if (cb) {
                cb.addEventListener('change', function () {
                    onToggleChange(this.checked);
                });
            }
        });
    });

    window.setAIFallbackNotice = setAIFallbackNotice;
})();