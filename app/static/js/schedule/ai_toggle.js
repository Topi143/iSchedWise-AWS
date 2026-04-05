/**
 * AI Toggle Controller
 * Manages the AI assistant on/off toggle across class and exam forms.
 * Persists preference in localStorage. When OFF, the assistant runs
 * in "Basic Mode" (rule-based conflicts + read-only suggestions).
 * When ON, it runs in "AI-Powered" mode (Gemini explanations,
 * one-click apply, workload analysis, confidence scores, auto-resolve).
 */

(function () {
    'use strict';

    const STORAGE_KEY = 'aiAssistantEnabled';

    const stored = localStorage.getItem(STORAGE_KEY);
    window.aiAssistantEnabled = stored === null ? true : stored === 'true';

    window.isAiToggleEnabled = function () {
        return window.aiAssistantEnabled === true;
    };

    const TOGGLE_IDS = ['aiToggleClassDesktop'];

    // Panel element groups affected by the toggle
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
    const SPARKLE_ICON = '<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>';
    const SHIELD_ICON = '<svg class="w-4 h-4 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';

    function syncCheckboxes(enabled) {
        TOGGLE_IDS.forEach(function (id) {
            var cb = document.getElementById(id);
            if (cb) cb.checked = enabled;
        });
    }

    /** Update the "Basic" / "AI" labels next to the toggle switch. */
    function updateToggleLabels(enabled) {
        var basicLabel = document.getElementById('aiToggleLabelBasic');
        var aiLabel = document.getElementById('aiToggleLabelAI');
        if (basicLabel) {
            basicLabel.className = 'text-[10px] font-medium select-none transition-colors duration-200 ' + (enabled ? 'text-gray-400' : 'text-gray-600');
        }
        if (aiLabel) {
            aiLabel.className = 'text-[10px] font-medium select-none transition-colors duration-200 ' + (enabled ? 'text-purple-600' : 'text-gray-400');
        }
    }

    /** Update drawer header icon, title, subtitle to match mode. */
    function updateDrawerHeader(enabled) {
        var icon = document.getElementById('aiDrawerHeaderIcon');
        var title = document.getElementById('aiDrawerTitle');
        var subtitle = document.getElementById('aiDrawerSubtitle');
        var modeLabel = document.getElementById('aiDrawerModeLabel');

        if (icon) {
            icon.className = 'w-8 h-8 rounded-lg flex items-center justify-center transition-colors duration-200 ' + (enabled ? 'bg-purple-600' : 'bg-gray-500');
            icon.innerHTML = enabled ? SPARKLE_ICON : SHIELD_ICON;
        }
        if (title) title.textContent = 'Schedule Assistant';
        if (subtitle) subtitle.textContent = enabled ? 'AI conflict checks and suggestions' : 'Rule-based conflict checks';
        if (modeLabel) modeLabel.textContent = enabled ? 'AI mode' : 'Basic mode';
    }

    function updateCapabilityPanel(enabled) {
        var modeBadge = document.getElementById('aiModeBadge');
        var applyCapability = document.getElementById('aiCapabilityApply');
        var explainCapability = document.getElementById('aiCapabilityExplain');

        if (modeBadge) {
            modeBadge.textContent = enabled ? 'AI Assist' : 'Manual Assist';
            modeBadge.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ' +
                (enabled
                    ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300'
                    : 'bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300');
        }

        if (applyCapability) {
            applyCapability.className = 'flex items-center justify-between ' +
                (enabled ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500');
            var applyHint = applyCapability.querySelector('span:last-child');
            if (applyHint) {
                applyHint.textContent = enabled ? 'Enabled' : 'AI Only';
                applyHint.className = 'font-semibold ' +
                    (enabled ? 'text-emerald-600 dark:text-emerald-400' : '');
            }
        }

        if (explainCapability) {
            explainCapability.className = 'flex items-center justify-between ' +
                (enabled ? 'text-gray-600 dark:text-gray-300' : 'text-gray-400 dark:text-gray-500');
            var explainHint = explainCapability.querySelector('span:last-child');
            if (explainHint) {
                explainHint.textContent = enabled ? 'Enabled' : 'AI Only';
                explainHint.className = 'font-semibold ' +
                    (enabled ? 'text-emerald-600 dark:text-emerald-400' : '');
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
    function updateEmptyStates(enabled) {
        [CLASS_PANEL_IDS, EXAM_PANEL_IDS].forEach(function (g) {
            var emptyEl = document.getElementById(g.emptyState);
            if (!emptyEl) return;
            var pTag = emptyEl.querySelector('p');
            var h5Tag = emptyEl.querySelector('h5');
            var iconContainer = document.getElementById(g.emptyIcon);

            if (!enabled) {
                if (h5Tag) h5Tag.textContent = 'Basic Mode';
                if (pTag) {
                    pTag.innerHTML = 'Fill in details for conflict detection.<br><span class="text-purple-500 cursor-pointer hover:underline" onclick="document.getElementById(\'aiToggleClassDesktop\').click()">Switch to AI</span> for smart suggestions.';
                    pTag.className = 'text-[10px] text-gray-400 max-w-[180px] leading-relaxed';
                }
                if (iconContainer) {
                    var circle = iconContainer.querySelector('.w-12');
                    if (circle) {
                        circle.className = 'w-12 h-12 rounded-full bg-gray-100 flex items-center justify-center mx-auto';
                        circle.innerHTML = '<svg class="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>';
                    }
                }
            } else {
                if (h5Tag) h5Tag.textContent = 'Waiting for Input';
                if (pTag) {
                    pTag.textContent = g === EXAM_PANEL_IDS
                        ? 'Fill in the exam details to check for conflicts'
                        : 'Fill in the schedule details to check for conflicts';
                    pTag.className = 'text-[10px] text-gray-400 max-w-[180px] leading-relaxed';
                }
                if (iconContainer) {
                    var circle = iconContainer.querySelector('.w-12');
                    if (circle) {
                        circle.className = 'w-12 h-12 rounded-full bg-purple-50 flex items-center justify-center mx-auto';
                        circle.innerHTML = '<svg class="w-5 h-5 text-purple-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M5 3v4M3 5h4M6 17v4m-2-2h4m5-16l2.286 6.857L21 12l-5.714 2.143L13 21l-2.286-6.857L5 12l5.714-2.143L13 3z"></path></svg>';
                    }
                }
            }
        });
    }

    /** Hide AI-only panels when in Basic mode, show basic hint. */
    function hideAiOnlyPanels(enabled) {
        [CLASS_PANEL_IDS, EXAM_PANEL_IDS].forEach(function (g) {
            if (g.workloadSummary) {
                var wl = document.getElementById(g.workloadSummary);
                if (wl && !enabled) wl.classList.add('hidden');
            }
            var hint = g.basicHint ? document.getElementById(g.basicHint) : null;
            if (hint) hint.classList.toggle('hidden', enabled);

            var recsHeader = g.recsHeader ? document.getElementById(g.recsHeader) : null;
            if (recsHeader) {
                var subP = recsHeader.querySelector('p');
                if (subP) subP.textContent = enabled ? 'Click any suggestion to apply it instantly.' : 'View-only suggestions. Enable AI mode for one-click apply.';
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

    /** Main handler called when the toggle checkbox changes. */
    function onToggleChange(enabled) {
        window.aiAssistantEnabled = enabled;
        localStorage.setItem(STORAGE_KEY, enabled ? 'true' : 'false');

        syncCheckboxes(enabled);
        updateToggleLabels(enabled);
        updateDrawerHeader(enabled);
        updateCapabilityPanel(enabled);
        setAIFallbackNotice('');
        updateEmptyStates(enabled);
        hideAiOnlyPanels(enabled);

        // Clear all existing content before re-fetching
        clearAllContent();

        // Reset badge to idle
        if (typeof updateAIBadge === 'function') updateAIBadge('idle');

        // Re-trigger conflict checks so the server gets the updated use_ai flag
        if (typeof scheduleAutoConflictCheck === 'function') {
            var mode = (window.scheduleModalMode === 'edit') ? 'edit' : 'add';
            scheduleAutoConflictCheck(mode);
        }
        if (typeof scheduleAutoExamConflictCheck === 'function') {
            scheduleAutoExamConflictCheck('add');
        }
    }

    // ── Initialization ─────────────────────────────────────────────────
    document.addEventListener('DOMContentLoaded', function () {
        syncCheckboxes(window.aiAssistantEnabled);
        updateToggleLabels(window.aiAssistantEnabled);
        updateDrawerHeader(window.aiAssistantEnabled);
        updateCapabilityPanel(window.aiAssistantEnabled);
        setAIFallbackNotice('');
        updateEmptyStates(window.aiAssistantEnabled);
        hideAiOnlyPanels(window.aiAssistantEnabled);

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
