(function () {
    'use strict';

    function normalizeType(type) {
        var normalized = (type || 'success').toString().toLowerCase();
        if (normalized === 'danger') return 'error';
        if (normalized !== 'success' && normalized !== 'error' && normalized !== 'warning' && normalized !== 'info') {
            return 'success';
        }
        return normalized;
    }

    function inferType(type) {
        if (type !== undefined && type !== null && type !== '') {
            return type;
        }

        // Some legacy page-local wrappers delegate with `arguments`, which can
        // drop default parameter values (e.g. showNotification's default `info`).
        // Infer intended default from call stack when possible.
        try {
            var stack = (new Error()).stack || '';
            if (stack.indexOf('showNotification') !== -1) return 'info';
            if (stack.indexOf('showToast') !== -1) return 'success';
        } catch (e) {
            // Ignore stack access issues and fall back to success.
        }

        return 'success';
    }

    function createIcon(type) {
        var pathByType = {
            success: 'M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z',
            error: 'M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
            warning: 'M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z',
            info: 'M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z'
        };

        var colorByType = {
            success: '#16a34a',
            error: '#dc2626',
            warning: '#d97706',
            info: '#2563eb'
        };

        var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
        svg.setAttribute('class', 'toast-icon');
        svg.setAttribute('fill', 'none');
        svg.setAttribute('stroke', 'currentColor');
        svg.setAttribute('viewBox', '0 0 24 24');
        svg.style.color = colorByType[type] || colorByType.success;

        var path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
        path.setAttribute('stroke-linecap', 'round');
        path.setAttribute('stroke-linejoin', 'round');
        path.setAttribute('stroke-width', '2');
        path.setAttribute('d', pathByType[type] || pathByType.success);
        svg.appendChild(path);

        return svg;
    }

    function ToastManager() {
        this.defaultDuration = 5000;
    }

    ToastManager.prototype.getContainer = function () {
        var container = document.getElementById('toastContainer') || document.getElementById('globalToastContainer');
        if (container) return container;

        container = document.createElement('div');
        container.id = 'globalToastContainer';
        container.className = 'toast-container';
        document.body.appendChild(container);
        return container;
    };

    ToastManager.prototype.remove = function (toast) {
        if (!toast || toast.classList.contains('is-removing')) return;
        toast.classList.add('is-removing');
        window.setTimeout(function () {
            if (toast && toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 220);
    };

    ToastManager.prototype.show = function (message, type, options) {
        var container = this.getContainer();
        var normalizedType = normalizeType(inferType(type));
        var duration = options && typeof options.duration === 'number' ? options.duration : this.defaultDuration;

        var toast = document.createElement('div');
        toast.className = 'toast toast-' + normalizedType;
        toast.setAttribute('role', 'status');
        toast.setAttribute('aria-live', normalizedType === 'error' ? 'assertive' : 'polite');

        var icon = createIcon(normalizedType);
        var text = document.createElement('p');
        text.textContent = message || '';

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'toast-close';
        closeBtn.setAttribute('aria-label', 'Dismiss notification');
        closeBtn.innerHTML = '✕';

        var self = this;
        closeBtn.addEventListener('click', function () {
            self.remove(toast);
        });

        toast.appendChild(icon);
        toast.appendChild(text);
        toast.appendChild(closeBtn);
        container.appendChild(toast);

        window.setTimeout(function () {
            self.remove(toast);
        }, duration);

        return toast;
    };

    var manager = new ToastManager();

    function bindGlobalToastApi() {
        window.__iswToastManager = manager;
        window.showToast = function (message, type, options) {
            return manager.show(message, type, options);
        };
        window.showNotification = function (message, type, options) {
            return manager.show(message, type || 'info', options);
        };
        window.removeToast = function (toast) {
            return manager.remove(toast);
        };
    }

    // Bind immediately, then re-bind after page scripts to override local duplicates.
    bindGlobalToastApi();
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindGlobalToastApi);
    }
    window.addEventListener('load', bindGlobalToastApi);
    window.setTimeout(bindGlobalToastApi, 0);
})();
