/**
 * Modal AI Overlay Controller
 * Handles collapsible desktop AI panels for class/exam add/edit modals.
 */

(function () {
    'use strict';

    var VIEWPORTS = {
        md: 768,
        xl: 1280
    };

    var PANEL_CONFIGS = [
        {
            key: 'schedule_modal_ai_add_class_open',
            modalId: 'addScheduleModal',
            panelId: 'aiPanelAddScheduleDesktop',
            openButtonId: 'aiPanelAddScheduleOpenBtn',
            minViewport: VIEWPORTS.xl
        },
        {
            key: 'schedule_modal_ai_edit_class_open',
            modalId: 'editScheduleModal',
            panelId: 'aiPanelEditScheduleDesktop',
            openButtonId: 'aiPanelEditScheduleOpenBtn',
            minViewport: VIEWPORTS.md
        },
        {
            key: 'schedule_modal_ai_add_exam_open',
            modalId: 'addExamScheduleModal',
            panelId: 'aiPanelAddExamDesktop',
            openButtonId: 'aiPanelAddExamOpenBtn',
            minViewport: VIEWPORTS.xl
        },
        {
            key: 'schedule_modal_ai_edit_exam_open',
            modalId: 'editExamScheduleModal',
            panelId: 'aiPanelEditExamDesktop',
            openButtonId: 'aiPanelEditExamOpenBtn',
            minViewport: VIEWPORTS.md
        }
    ];

    function isModalVisible(modal) {
        return !!modal && !modal.classList.contains('hidden');
    }

    function inViewport(minViewport) {
        return window.innerWidth >= minViewport;
    }

    function isAIAssistantBatchLocked() {
        return typeof window.isAIAssistantBatchLocked === 'function' && window.isAIAssistantBatchLocked();
    }

    function loadState(config) {
        try {
            return localStorage.getItem(config.key) === 'true';
        } catch (error) {
            return false;
        }
    }

    function saveState(config, open) {
        try {
            localStorage.setItem(config.key, open ? 'true' : 'false');
        } catch (error) {
            // Ignore localStorage write errors.
        }
    }

    function showPanel(config) {
        if (isAIAssistantBatchLocked()) {
            applyConfig(config);
            return;
        }

        config.open = true;
        saveState(config, true);
        applyConfig(config);
    }

    function hidePanel(config) {
        config.open = false;
        saveState(config, false);
        applyConfig(config);
    }

    function applyConfig(config) {
        if (!config.panel || !config.openButton) return;

        if (isAIAssistantBatchLocked()) {
            config.panel.classList.remove('translate-x-0', 'opacity-100', 'pointer-events-auto');
            config.panel.classList.add('translate-x-full', 'opacity-0', 'pointer-events-none');
            config.openButton.classList.add('hidden');
            return;
        }

        var canRenderPanel = inViewport(config.minViewport);
        var shouldShowPanel = canRenderPanel && isModalVisible(config.modal) && config.open;

        if (shouldShowPanel) {
            config.panel.classList.remove('translate-x-full', 'opacity-0', 'pointer-events-none');
            config.panel.classList.add('translate-x-0', 'opacity-100', 'pointer-events-auto');
            config.openButton.classList.add('hidden');
            return;
        }

        config.panel.classList.remove('translate-x-0', 'opacity-100', 'pointer-events-auto');
        config.panel.classList.add('translate-x-full', 'opacity-0', 'pointer-events-none');

        if (canRenderPanel && isModalVisible(config.modal)) {
            config.openButton.classList.remove('hidden');
        } else {
            config.openButton.classList.add('hidden');
        }
    }

    function syncAll() {
        PANEL_CONFIGS.forEach(applyConfig);
    }

    function debounce(fn, delay) {
        var timeoutId;
        return function () {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(fn, delay || 100);
        };
    }

    function attachModalObserver(config) {
        if (!config.modal || typeof MutationObserver === 'undefined') return;

        var observer = new MutationObserver(function () {
            applyConfig(config);
        });

        observer.observe(config.modal, {
            attributes: true,
            attributeFilter: ['class']
        });
    }

    document.addEventListener('DOMContentLoaded', function () {
        PANEL_CONFIGS.forEach(function (config) {
            config.modal = document.getElementById(config.modalId);
            config.panel = document.getElementById(config.panelId);
            config.openButton = document.getElementById(config.openButtonId);
            config.open = loadState(config);

            if (config.openButton) {
                config.openButton.addEventListener('click', function () {
                    showPanel(config);
                });
            }

            if (config.panel) {
                var closeButton = config.panel.querySelector('[data-modal-ai-close="' + config.panelId + '"]');
                if (closeButton) {
                    closeButton.addEventListener('click', function () {
                        hidePanel(config);
                    });
                }
            }

            attachModalObserver(config);
        });

        window.addEventListener('resize', debounce(syncAll, 120));
        window.addEventListener('orientationchange', debounce(syncAll, 120));
        window.addEventListener('aiAssistantBatchLockChanged', syncAll);

        syncAll();
    });
})();
