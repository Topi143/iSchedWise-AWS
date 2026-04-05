/**
 * AI Assistant Dock Controller
 * Manages the docked assistant panel and mobile collapse state.
 */

(function () {
    'use strict';

    var DESKTOP_BREAKPOINT = 1024;
    var DESKTOP_STATE_KEY = 'schedule_ai_drawer_desktop_open';
    var BATCH_STATE_KEY = 'ischedwise_batch_mode';
    var drawerOpenMobile = false;
    var drawerOpenDesktop = false;
    var drawerAutoOpened = false;
    var activeDrawerTab = 'class';
    var assistantBatchLock = false;
    var assistantBatchMode = '';

    var STATE_CONFIG = {
        idle: { label: 'Idle', pill: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' },
        checking: { label: 'Checking', pill: 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300' },
        clear: { label: 'All Clear', pill: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300' },
        warnings: { label: '{n} Warning{s}', pill: 'bg-amber-100 text-amber-700 dark:bg-amber-900/40 dark:text-amber-300' },
        conflicts: { label: '{n} Conflict{s}', pill: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300' },
        error: { label: 'Check Failed', pill: 'bg-gray-100 text-gray-600 dark:bg-gray-700 dark:text-gray-300' }
    };

    function isDesktopViewport() {
        return window.innerWidth >= DESKTOP_BREAKPOINT;
    }

    function debounce(fn, wait) {
        var timeout;
        return function () {
            var args = arguments;
            clearTimeout(timeout);
            timeout = setTimeout(function () { fn.apply(null, args); }, wait || 120);
        };
    }

    function getElements() {
        return {
            drawer: document.getElementById('aiDrawer'),
            content: document.getElementById('aiDrawerContent'),
            toggleIcon: document.getElementById('aiDrawerToggleIcon'),
            statePill: document.getElementById('aiDrawerStatePill'),
            badge: document.getElementById('aiBadge'),
            badgeText: document.getElementById('aiBadgeText'),
            dockPanel: document.getElementById('aiAssistantDockPanel'),
            desktopOpenButton: document.getElementById('aiDrawerOpenDesktopBtn')
        };
    }

    function isAIAssistantBatchLocked() {
        return assistantBatchLock;
    }

    function getAIAssistantBatchMode() {
        return assistantBatchMode;
    }

    function isCurrentViewportOpen() {
        return isDesktopViewport() ? drawerOpenDesktop : drawerOpenMobile;
    }

    function setCurrentViewportOpen(open) {
        if (isDesktopViewport()) {
            drawerOpenDesktop = !!open;
            try {
                localStorage.setItem(DESKTOP_STATE_KEY, drawerOpenDesktop ? 'true' : 'false');
            } catch (error) {
                // Ignore storage errors (private mode, restricted storage, etc.)
            }
            return;
        }
        drawerOpenMobile = !!open;
    }

    function syncDesktopDockState(elements) {
        if (!elements.dockPanel) return;

        var dockHidden = elements.dockPanel.classList.contains('hidden');
        if (assistantBatchLock) {
            dockHidden = true;
        }
        if (!dockHidden) {
            if (drawerOpenDesktop) {
                elements.dockPanel.classList.remove('translate-x-full', 'opacity-0', 'pointer-events-none');
                elements.dockPanel.classList.add('translate-x-0', 'opacity-100', 'pointer-events-auto');
            } else {
                elements.dockPanel.classList.remove('translate-x-0', 'opacity-100', 'pointer-events-auto');
                elements.dockPanel.classList.add('translate-x-full', 'opacity-0', 'pointer-events-none');
            }
        }

        if (!elements.desktopOpenButton) return;

        if (dockHidden || drawerOpenDesktop) {
            elements.desktopOpenButton.classList.add('hidden', 'lg:hidden');
            elements.desktopOpenButton.classList.remove('lg:inline-flex');
        } else {
            elements.desktopOpenButton.classList.remove('hidden', 'lg:hidden');
            elements.desktopOpenButton.classList.add('lg:inline-flex');
        }
    }

    function syncDrawerLayoutForViewport() {
        var elements = getElements();
        if (!elements.content) return;

        if (assistantBatchLock) {
            elements.content.classList.add('hidden');
            if (elements.toggleIcon) elements.toggleIcon.classList.remove('rotate-180');
            syncDesktopDockState(elements);
            return;
        }

        if (isDesktopViewport()) {
            if (drawerOpenDesktop) {
                elements.content.classList.remove('hidden');
            } else {
                elements.content.classList.add('hidden');
            }
            syncDesktopDockState(elements);
            return;
        }

        if (drawerOpenMobile) {
            elements.content.classList.remove('hidden');
            if (elements.toggleIcon) elements.toggleIcon.classList.add('rotate-180');
        } else {
            elements.content.classList.add('hidden');
            if (elements.toggleIcon) elements.toggleIcon.classList.remove('rotate-180');
        }
    }

    function openAIDrawer() {
        if (assistantBatchLock) return;

        setCurrentViewportOpen(true);
        syncDrawerLayoutForViewport();

        if (!isDesktopViewport()) {
            var drawer = document.getElementById('aiDrawer');
            if (drawer && typeof drawer.scrollIntoView === 'function') {
                drawer.scrollIntoView({ behavior: 'smooth', block: 'start' });
            }
        }
    }

    function closeAIDrawer() {
        setCurrentViewportOpen(false);
        drawerAutoOpened = false;
        syncDrawerLayoutForViewport();
    }

    function toggleAIDrawer() {
        if (isCurrentViewportOpen()) closeAIDrawer();
        else openAIDrawer();
    }

    function autoOpenDrawer() {
        if (assistantBatchLock) return;

        if (!isCurrentViewportOpen() && !drawerAutoOpened) {
            drawerAutoOpened = true;
            openAIDrawer();
        }
    }

    function autoCloseDrawer() {
        if (isCurrentViewportOpen() && drawerAutoOpened) closeAIDrawer();
    }

    function setAIAssistantDockVisible(visible) {
        var elements = getElements();
        if (!elements.dockPanel) return;

        if (visible && !assistantBatchLock) {
            elements.dockPanel.classList.remove('hidden');
            if (elements.desktopOpenButton) {
                elements.desktopOpenButton.classList.remove('lg:hidden');
            }
            syncDrawerLayoutForViewport();
            return;
        }

        elements.dockPanel.classList.add('hidden');
        if (elements.desktopOpenButton) {
            elements.desktopOpenButton.classList.add('hidden', 'lg:hidden');
            elements.desktopOpenButton.classList.remove('lg:inline-flex');
        }
        closeAIDrawer();
    }

    function emitBatchLockEvent() {
        if (typeof window.dispatchEvent !== 'function' || typeof window.CustomEvent !== 'function') return;

        window.dispatchEvent(new CustomEvent('aiAssistantBatchLockChanged', {
            detail: {
                locked: assistantBatchLock,
                mode: assistantBatchMode
            }
        }));
    }

    function applyAIAssistantBatchLock(locked, mode) {
        assistantBatchLock = !!locked;
        assistantBatchMode = assistantBatchLock ? (mode || '') : '';

        if (assistantBatchLock) {
            setAIAssistantDockVisible(false);
        } else {
            setAIAssistantDockVisible(true);
        }

        syncDrawerLayoutForViewport();
        emitBatchLockEvent();
    }

    function formatLabel(label, count) {
        if (!count || count <= 0) {
            return label.replace('{n} ', '').replace('{s}', '');
        }
        return label.replace('{n}', count).replace('{s}', count > 1 ? 's' : '');
    }

    function updateAIBadge(state, count) {
        var elements = getElements();
        var config = STATE_CONFIG[state] || STATE_CONFIG.idle;
        var safeCount = count || 0;
        var label = formatLabel(config.label, safeCount);

        if (elements.statePill) {
            elements.statePill.className = 'inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ' + config.pill;
            elements.statePill.textContent = label;
        }

        // Keep compatibility attributes for scripts that still target the old badge.
        if (elements.badge) {
            elements.badge.classList.add('hidden');
            elements.badge.classList.remove('flex');
            elements.badge.setAttribute('title', label);
            elements.badge.setAttribute('aria-label', label);
        }
        if (elements.badgeText) {
            elements.badgeText.textContent = label;
        }
    }

    function onDrawerTabSwitch(tab) {
        activeDrawerTab = tab;
        var classContent = document.getElementById('aiDrawerClassContent');
        var examContent = document.getElementById('aiDrawerExamContent');

        if (tab === 'class') {
            if (classContent) classContent.classList.remove('hidden');
            if (examContent) examContent.classList.add('hidden');
        } else {
            if (classContent) classContent.classList.add('hidden');
            if (examContent) examContent.classList.remove('hidden');
        }

        drawerAutoOpened = false;
    }

    window.addEventListener('resize', debounce(syncDrawerLayoutForViewport, 120));
    window.addEventListener('orientationchange', debounce(syncDrawerLayoutForViewport, 120));

    window.toggleAIDrawer = toggleAIDrawer;
    window.openAIDrawer = openAIDrawer;
    window.closeAIDrawer = closeAIDrawer;
    window.autoOpenDrawer = autoOpenDrawer;
    window.autoCloseDrawer = autoCloseDrawer;
    window.updateAIBadge = updateAIBadge;
    window.onDrawerTabSwitch = onDrawerTabSwitch;
    window.setAIAssistantDockVisible = setAIAssistantDockVisible;
    window.applyAIAssistantBatchLock = applyAIAssistantBatchLock;
    window.isAIAssistantBatchLocked = isAIAssistantBatchLocked;
    window.getAIAssistantBatchMode = getAIAssistantBatchMode;

    document.addEventListener('DOMContentLoaded', function () {
        // Both mobile and desktop default to collapsed.
        drawerOpenMobile = false;

        try {
            var storedDesktopState = localStorage.getItem(DESKTOP_STATE_KEY);
            drawerOpenDesktop = storedDesktopState === 'true';
        } catch (error) {
            drawerOpenDesktop = false;
        }

        try {
            var storedBatchMode = sessionStorage.getItem(BATCH_STATE_KEY);
            assistantBatchLock = storedBatchMode === 'class' || storedBatchMode === 'exam';
            assistantBatchMode = assistantBatchLock ? storedBatchMode : '';
        } catch (error) {
            assistantBatchLock = false;
            assistantBatchMode = '';
        }

        syncDrawerLayoutForViewport();
        onDrawerTabSwitch(activeDrawerTab);
        updateAIBadge('idle', 0);
        emitBatchLockEvent();
    });
})();
