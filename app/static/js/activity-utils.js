(function () {
    const DEFAULT_TIMEZONE = 'Asia/Manila';

    function getSystemTimezone() {
        const configured = (typeof window !== 'undefined' && typeof window.__ISW_SYSTEM_TIMEZONE === 'string')
            ? window.__ISW_SYSTEM_TIMEZONE.trim()
            : '';
        return configured || DEFAULT_TIMEZONE;
    }

    function parseTimestamp(value, options) {
        if (value === null || value === undefined || value === '') return null;
        if (value instanceof Date) {
            return isNaN(value.getTime()) ? null : value;
        }

        const opts = options || {};
        const assumeUtcForNaive = opts.assumeUtcForNaive !== false;
        let text = String(value).trim();
        if (!text) return null;

        if (text.indexOf(' ') !== -1 && text.indexOf('T') === -1) {
            text = text.replace(' ', 'T');
        }

        const hasTimezone = /(?:Z|[+-]\d{2}:\d{2})$/i.test(text);
        const normalized = !hasTimezone && assumeUtcForNaive ? text + 'Z' : text;

        let parsed = new Date(normalized);
        if (isNaN(parsed.getTime()) && normalized !== text) {
            parsed = new Date(text);
        }

        return isNaN(parsed.getTime()) ? null : parsed;
    }

    function escapeHtml(value) {
        if (value === null || value === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(value);
        return div.innerHTML;
    }

    function normalizeAction(action) {
        return String(action || '').toLowerCase();
    }

    function getActionTagClass(action) {
        const normalized = normalizeAction(action);
        if (!normalized) return 'default';
        if (normalized.includes('login')) return 'login';
        if (normalized.includes('logout')) return 'logout';
        if (normalized.includes('created') || normalized.includes('add') || normalized.includes('batch_schedule') || normalized.includes('batch_exam_schedule')) return 'created';
        if (normalized.includes('edited') || normalized.includes('updated') || normalized.includes('modified')) return 'edited';
        if (normalized.includes('deleted') || normalized.includes('removed')) return 'deleted';
        if (normalized.includes('archived') || normalized.includes('unarchived') || normalized.includes('restored')) return 'archived';
        return 'default';
    }

    function getReportActionColorClass(action) {
        const normalized = normalizeAction(action);
        if (normalized.includes('created') || normalized.includes('add')) return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-300 border border-green-200 dark:border-green-800';
        if (normalized.includes('edited') || normalized.includes('updated') || normalized.includes('modified')) return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-300 border border-blue-200 dark:border-blue-800';
        if (normalized.includes('deleted') || normalized.includes('removed')) return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-300 border border-red-200 dark:border-red-800';
        if (normalized.includes('archived')) return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-300 border border-orange-200 dark:border-orange-800';
        if (normalized.includes('unarchived') || normalized.includes('restored')) return 'bg-purple-100 dark:bg-purple-900/30 text-purple-800 dark:text-purple-300 border border-purple-200 dark:border-purple-800';
        return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-300 border border-gray-200 dark:border-gray-600';
    }

    function formatDateTime(iso, fallback) {
        const d = parseTimestamp(iso);
        if (!d) return fallback || '--';
        return d.toLocaleString('en-US', {
            timeZone: getSystemTimezone(),
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
            hour12: true
        });
    }

    function formatDateShort(iso, fallback) {
        const d = parseTimestamp(iso);
        if (!d) return fallback || '--';
        return d.toLocaleDateString('en-US', { timeZone: getSystemTimezone(), month: 'short', day: 'numeric' }) + ' ' +
            d.toLocaleTimeString('en-US', { timeZone: getSystemTimezone(), hour: '2-digit', minute: '2-digit', hour12: true });
    }

    function timeAgo(iso, fallback) {
        const d = parseTimestamp(iso);
        if (!d) return fallback || '';
        const diff = (Date.now() - d.getTime()) / 1000;
        if (diff < 60) return 'just now';
        if (diff < 3600) return Math.floor(diff / 60) + 'm ago';
        if (diff < 86400) return Math.floor(diff / 3600) + 'h ago';
        if (diff < 604800) return Math.floor(diff / 86400) + 'd ago';
        return d.toLocaleDateString('en-US', { timeZone: getSystemTimezone(), month: 'short', day: 'numeric', year: 'numeric' });
    }

    function summarizeDetails(details, maxLen) {
        const limit = maxLen || 80;
        if (details === null || details === undefined) return '';

        let text = '';
        if (typeof details === 'object') {
            const parts = [];
            Object.entries(details).forEach(([key, value]) => {
                if (value === null || value === '') return;
                const readableKey = String(key)
                    .replace(/_/g, ' ')
                    .replace(/\b\w/g, c => c.toUpperCase());
                parts.push(readableKey + ': ' + String(value));
            });
            text = parts.join(' | ');
        } else {
            text = String(details);
        }

        if (!text) return '';
        return text.length > limit ? text.substring(0, limit) : text;
    }

    window.ISWActivityUtils = {
        escapeHtml: escapeHtml,
        normalizeAction: normalizeAction,
        getActionTagClass: getActionTagClass,
        getReportActionColorClass: getReportActionColorClass,
        getSystemTimezone: getSystemTimezone,
        parseTimestamp: parseTimestamp,
        formatDateTime: formatDateTime,
        formatDateShort: formatDateShort,
        timeAgo: timeAgo,
        summarizeDetails: summarizeDetails
    };
})();
