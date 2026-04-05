/**
 * Custom Time Picker Component for iSchedWise V4
 * ─────────────────────────────────────────────────
 * Replaces native <input type="time"> with a styled dropdown picker
 * that only allows :00 and :30 minute intervals.
 *
 * Usage (HTML):
 *   <div class="custom-time-picker" data-time-picker
 *        data-name="start_time" data-id="start_time_add"
 *        data-value="07:00" data-required="true"
 *        data-onchange="calculateEndTime('add')">
 *   </div>
 *
 * The component creates:
 *   - A hidden <input> for form submission (HH:MM, 24-hour)
 *   - A styled trigger button showing time in 12-hour AM/PM format
 *   - A dropdown with Hour / Minute / AM|PM columns
 */

(function () {
    'use strict';

    // ── Helpers ──────────────────────────────────────────────────────────

    /** Convert 24-hour value to 12-hour display parts */
    function to12Hour(h24) {
        const period = h24 < 12 ? 'AM' : 'PM';
        let h12 = h24 % 12;
        if (h12 === 0) h12 = 12;
        return { hour12: h12, period };
    }

    /** Convert 12-hour + period to 24-hour */
    function to24Hour(h12, period) {
        if (period === 'AM') {
            return h12 === 12 ? 0 : h12;
        }
        return h12 === 12 ? 12 : h12 + 12;
    }

    /** Pad to 2 digits */
    function pad(n) { return String(n).padStart(2, '0'); }

    /** Format HH:MM (24h) → "7:00 AM" */
    function formatDisplay(value) {
        if (!value) return '--:-- --';
        const [hStr, mStr] = value.split(':');
        const h24 = parseInt(hStr, 10);
        const m = parseInt(mStr, 10);
        const { hour12, period } = to12Hour(h24);
        return `${hour12}:${pad(m)} ${period}`;
    }

    // ── Build one picker instance ────────────────────────────────────────

    function buildPicker(container) {
        // Already initialised?
        if (container._timePicker) return;

        // Fixed hour range: 12 AM (0) to 11 PM (23) — full day
        const minHour = 0;
        const maxHour = 23;
        const name = container.dataset.name || '';
        const id = container.dataset.id || '';
        const value = container.dataset.value || '';
        const required = container.dataset.required === 'true';
        const onchangeAttr = container.dataset.onchange || '';
        const hiddenField = container.dataset.hiddenField || '';
        const extraClasses = container.dataset.inputClass || '';

        // ── Hidden input for form submission ───────────────────────────
        const hiddenInput = document.createElement('input');
        hiddenInput.type = 'hidden';
        hiddenInput.name = name;
        if (id) hiddenInput.id = id;
        if (hiddenField) hiddenInput.setAttribute('data-field', hiddenField);
        if (required) hiddenInput.required = true;
        hiddenInput.value = value;
        hiddenInput.classList.add('time-picker-hidden-input');
        container.appendChild(hiddenInput);

        // ── Trigger button ─────────────────────────────────────────────
        const trigger = document.createElement('button');
        trigger.type = 'button';
        trigger.className = `time-picker-trigger ${extraClasses}`.trim();
        trigger.setAttribute('aria-haspopup', 'listbox');
        trigger.setAttribute('aria-expanded', 'false');
        trigger.innerHTML = `
            <span class="tp-display-text">${formatDisplay(value)}</span>
            <svg class="tp-clock-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>
        `;
        container.appendChild(trigger);

        // ── Dropdown panel ─────────────────────────────────────────────
        const dropdown = document.createElement('div');
        dropdown.className = 'time-picker-dropdown hidden';
        dropdown.setAttribute('role', 'listbox');

        // Build hour range — convert to 12-hour buckets
        // We need hours from minHour..maxHour in both AM and PM
        const amHours = [];   // 12-hour values that fall in AM
        const pmHours = [];   // 12-hour values that fall in PM

        for (let h = minHour; h <= maxHour; h++) {
            const { hour12, period } = to12Hour(h);
            if (period === 'AM') {
                if (!amHours.includes(hour12)) amHours.push(hour12);
            } else {
                if (!pmHours.includes(hour12)) pmHours.push(hour12);
            }
        }

        // We'll show hours dynamically based on selected period
        const allHoursByPeriod = { AM: amHours, PM: pmHours };

        // ── Hour column ────────────────────────────────────────────────
        const hourCol = document.createElement('div');
        hourCol.className = 'tp-column tp-column-hour';
        hourCol.innerHTML = '<div class="tp-column-label">Hr</div><div class="tp-column-options"></div>';

        // ── Minute column ──────────────────────────────────────────────
        const minCol = document.createElement('div');
        minCol.className = 'tp-column tp-column-minute';
        minCol.innerHTML = '<div class="tp-column-label">Min</div><div class="tp-column-options"></div>';
        const minOptions = minCol.querySelector('.tp-column-options');
        ['00', '30'].forEach(m => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'tp-option';
            btn.dataset.value = m;
            btn.textContent = m;
            minOptions.appendChild(btn);
        });

        // ── Period (AM/PM) column ──────────────────────────────────────
        const periodCol = document.createElement('div');
        periodCol.className = 'tp-column tp-column-period';
        periodCol.innerHTML = '<div class="tp-column-label"></div><div class="tp-column-options"></div>';
        const periodOptions = periodCol.querySelector('.tp-column-options');
        const availablePeriods = [];
        if (amHours.length > 0) availablePeriods.push('AM');
        if (pmHours.length > 0) availablePeriods.push('PM');
        availablePeriods.forEach(p => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'tp-option tp-option-period';
            btn.dataset.value = p;
            btn.textContent = p;
            periodOptions.appendChild(btn);
        });

        dropdown.appendChild(hourCol);
        dropdown.appendChild(minCol);
        dropdown.appendChild(periodCol);
        container.appendChild(dropdown);

        // ── State ──────────────────────────────────────────────────────
        const state = { hour12: null, minute: null, period: null, open: false };

        // Parse initial value
        if (value) {
            const [hStr, mStr] = value.split(':');
            const h24 = parseInt(hStr, 10);
            const m = parseInt(mStr, 10);
            const info = to12Hour(h24);
            state.hour12 = info.hour12;
            state.minute = pad(m === 30 ? 30 : 0);
            state.period = info.period;
        } else {
            // Default to first available period
            state.period = availablePeriods[0] || 'AM';
            state.minute = '00';
        }

        // ── Render functions ───────────────────────────────────────────

        function renderHours() {
            const hourOptions = hourCol.querySelector('.tp-column-options');
            hourOptions.innerHTML = '';
            const hours = allHoursByPeriod[state.period] || [];
            // Sort properly: 1-11, then 12 last
            const sorted = [...hours].sort((a, b) => {
                if (a === 12) return 1;
                if (b === 12) return -1;
                return a - b;
            });
            sorted.forEach(h => {
                const btn = document.createElement('button');
                btn.type = 'button';
                btn.className = 'tp-option';
                btn.dataset.value = String(h);
                btn.textContent = String(h);
                if (state.hour12 === h) btn.classList.add('selected');
                hourOptions.appendChild(btn);
            });
        }

        function renderSelection() {
            // Highlight selected minute
            minOptions.querySelectorAll('.tp-option').forEach(btn => {
                btn.classList.toggle('selected', btn.dataset.value === state.minute);
            });
            // Highlight selected period
            periodOptions.querySelectorAll('.tp-option').forEach(btn => {
                btn.classList.toggle('selected', btn.dataset.value === state.period);
            });
            // Highlight selected hour
            hourCol.querySelector('.tp-column-options').querySelectorAll('.tp-option').forEach(btn => {
                btn.classList.toggle('selected', state.hour12 !== null && parseInt(btn.dataset.value, 10) === state.hour12);
            });
        }

        function updateValue() {
            if (state.hour12 === null || state.minute === null || state.period === null) return;
            const h24 = to24Hour(state.hour12, state.period);
            const newVal = `${pad(h24)}:${state.minute}`;
            const oldVal = hiddenInput.value;
            hiddenInput.value = newVal;
            trigger.querySelector('.tp-display-text').textContent = formatDisplay(newVal);
            container.dataset.value = newVal;

            if (newVal !== oldVal) {
                // Fire native events so existing onchange handlers work
                hiddenInput.dispatchEvent(new Event('change', { bubbles: true }));
                hiddenInput.dispatchEvent(new Event('input', { bubbles: true }));
                // Execute inline onchange if specified
                if (onchangeAttr) {
                    try { new Function('input', onchangeAttr)(hiddenInput); } catch (e) { console.warn('TimePicker onchange error:', e); }
                }
            }
        }

        function scrollToSelected(colEl) {
            const selected = colEl.querySelector('.tp-option.selected');
            if (selected) {
                const optionsContainer = colEl.querySelector('.tp-column-options');
                // Scroll so the selected item is centered
                const containerH = optionsContainer.clientHeight;
                const itemTop = selected.offsetTop;
                const itemH = selected.offsetHeight;
                optionsContainer.scrollTop = itemTop - (containerH / 2) + (itemH / 2);
            }
        }

        // ── Event handlers ─────────────────────────────────────────────

        function openDropdown() {
            dropdown.classList.remove('hidden');
            trigger.setAttribute('aria-expanded', 'true');
            trigger.classList.add('tp-active');
            state.open = true;
            renderHours();
            renderSelection();
            // Position dropdown
            positionDropdown();
            // Scroll to selected items
            requestAnimationFrame(() => {
                scrollToSelected(hourCol);
                scrollToSelected(minCol);
                scrollToSelected(periodCol);
            });
        }

        function closeDropdown() {
            dropdown.classList.add('hidden');
            trigger.setAttribute('aria-expanded', 'false');
            trigger.classList.remove('tp-active');
            state.open = false;
        }

        function positionDropdown() {
            const triggerRect = trigger.getBoundingClientRect();
            const dropH = dropdown.offsetHeight || 220;
            const spaceBelow = window.innerHeight - triggerRect.bottom;
            const spaceAbove = triggerRect.top;
            const viewportPad = 8;
            const availableWidth = Math.max(160, window.innerWidth - (viewportPad * 2));
            const width = Math.min(220, Math.max(176, triggerRect.width), availableWidth);
            const left = Math.min(
                Math.max(viewportPad, triggerRect.left),
                Math.max(viewportPad, window.innerWidth - width - viewportPad)
            );

            dropdown.style.position = 'fixed';
            dropdown.style.zIndex = '99999';
            dropdown.style.left = left + 'px';
            dropdown.style.width = width + 'px';
            dropdown.style.minWidth = width + 'px';
            dropdown.style.right = 'auto';

            if (spaceBelow < dropH && spaceAbove > spaceBelow) {
                // Open upward
                dropdown.style.top = 'auto';
                dropdown.style.bottom = (window.innerHeight - triggerRect.top + 4) + 'px';
            } else {
                // Open downward (default)
                dropdown.style.top = (triggerRect.bottom + 4) + 'px';
                dropdown.style.bottom = 'auto';
            }
        }

        // Reposition on scroll / resize while open
        function onScrollOrResize() {
            if (state.open) positionDropdown();
        }
        window.addEventListener('scroll', onScrollOrResize, true);
        window.addEventListener('resize', onScrollOrResize);
        window.addEventListener('orientationchange', onScrollOrResize);

        // Toggle on trigger click
        trigger.addEventListener('click', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (state.open) {
                closeDropdown();
            } else {
                // Close any other open pickers first
                document.querySelectorAll('.time-picker-dropdown:not(.hidden)').forEach(d => {
                    if (d !== dropdown) {
                        d.classList.add('hidden');
                        const p = d.closest('[data-time-picker]');
                        if (p && p._timePicker) p._timePicker.close();
                    }
                });
                openDropdown();
            }
        });

        // Prevent dropdown clicks from closing it
        dropdown.addEventListener('click', (e) => {
            e.stopPropagation();
        });

        // Hour selection
        hourCol.addEventListener('click', (e) => {
            const btn = e.target.closest('.tp-option');
            if (!btn) return;
            state.hour12 = parseInt(btn.dataset.value, 10);
            renderSelection();
            updateValue();
        });

        // Minute selection
        minOptions.addEventListener('click', (e) => {
            const btn = e.target.closest('.tp-option');
            if (!btn) return;
            state.minute = btn.dataset.value;
            renderSelection();
            updateValue();
        });

        // Period selection
        periodOptions.addEventListener('click', (e) => {
            const btn = e.target.closest('.tp-option');
            if (!btn) return;
            const newPeriod = btn.dataset.value;
            if (newPeriod !== state.period) {
                state.period = newPeriod;
                // Check if current hour exists in new period's available hours
                const availableHours = allHoursByPeriod[state.period] || [];
                if (state.hour12 !== null && !availableHours.includes(state.hour12)) {
                    // Select the first available hour in the new period
                    const sorted = [...availableHours].sort((a, b) => {
                        if (a === 12) return 1;
                        if (b === 12) return -1;
                        return a - b;
                    });
                    state.hour12 = sorted[0] || null;
                }
                renderHours();
                renderSelection();
                updateValue();
            }
        });

        // Close on outside click
        function handleOutsideClick(e) {
            if (state.open && !container.contains(e.target)) {
                closeDropdown();
            }
        }
        document.addEventListener('click', handleOutsideClick, true);

        // Close on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape' && state.open) {
                closeDropdown();
            }
        });

        // ── Public API (stored on container) ───────────────────────────
        container._timePicker = {
            open: openDropdown,
            close: closeDropdown,
            getValue: () => hiddenInput.value,
            setValue: (val) => {
                hiddenInput.value = val || '';
            },
            getInput: () => hiddenInput,
            destroy: () => {
                document.removeEventListener('click', handleOutsideClick, true);
                window.removeEventListener('scroll', onScrollOrResize, true);
                window.removeEventListener('resize', onScrollOrResize);
                window.removeEventListener('orientationchange', onScrollOrResize);
                container._timePicker = null;
            }
        };

        // Intercept .value property on hidden input so programmatic sets
        // also update the display (for calculateEndTime etc.)
        const origDescriptor = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value');
        Object.defineProperty(hiddenInput, 'value', {
            get() {
                return origDescriptor.get.call(this);
            },
            set(val) {
                origDescriptor.set.call(this, val);
                // Update the picker UI to match
                if (val && val.includes(':')) {
                    const [hStr, mStr] = val.split(':');
                    const h24 = parseInt(hStr, 10);
                    const m = parseInt(mStr, 10);
                    const info = to12Hour(h24);
                    state.hour12 = info.hour12;
                    state.minute = pad(m);
                    state.period = info.period;
                    trigger.querySelector('.tp-display-text').textContent = formatDisplay(val);
                    container.dataset.value = val;
                    if (state.open) {
                        renderHours();
                        renderSelection();
                    }
                } else if (!val) {
                    trigger.querySelector('.tp-display-text').textContent = '--:-- --';
                    container.dataset.value = '';
                    state.hour12 = null;
                    state.minute = '00';
                    state.period = availablePeriods[0] || 'AM';
                }
            },
            configurable: true
        });

        // Initial render
        renderHours();
        renderSelection();
    }

    // ── Init all pickers on the page ─────────────────────────────────────

    function initAllTimePickers() {
        document.querySelectorAll('[data-time-picker]:not([data-tp-init])').forEach(el => {
            buildPicker(el);
            el.setAttribute('data-tp-init', 'true');
        });
    }

    // Auto-init on DOMContentLoaded
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initAllTimePickers);
    } else {
        initAllTimePickers();
    }

    // Observe DOM for dynamically added pickers (modals, etc.)
    const observer = new MutationObserver((mutations) => {
        let hasNewPickers = false;
        for (const mut of mutations) {
            for (const node of mut.addedNodes) {
                if (node.nodeType === 1) {
                    if (node.matches && node.matches('[data-time-picker]:not([data-tp-init])')) {
                        hasNewPickers = true;
                        break;
                    }
                    if (node.querySelector && node.querySelector('[data-time-picker]:not([data-tp-init])')) {
                        hasNewPickers = true;
                        break;
                    }
                }
            }
            if (hasNewPickers) break;
        }
        if (hasNewPickers) initAllTimePickers();
    });
    observer.observe(document.body || document.documentElement, { childList: true, subtree: true });

    // ── Global API ───────────────────────────────────────────────────────
    window.TimePicker = {
        init: initAllTimePickers,
        build: buildPicker,
        formatDisplay,

        /** Helper: set a time picker value by input ID */
        setValueById(inputId, value) {
            const input = document.getElementById(inputId);
            if (input) {
                input.value = value;  // Triggers the property setter above
            }
        },

        /** Helper: get a time picker value by input ID */
        getValueById(inputId) {
            const input = document.getElementById(inputId);
            return input ? input.value : '';
        },

        /** Re-initialize a specific container (useful after modal open) */
        reinit(container) {
            if (!container._timePicker) {
                buildPicker(container);
                container.setAttribute('data-tp-init', 'true');
            }
        }
    };

})();
