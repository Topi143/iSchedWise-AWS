# Schedule Refactoring - Quick Start Guide

## 🚀 Implementation Steps

This guide shows you exactly how to refactor the schedule page from a monolithic structure to modular components.

---

## Step 1: Extract Shared Styles (5 minutes)

**Create:** `app/templates/schedule/_styles.html`

**Extract from** `schedule.html` lines 6-319 (all the `<style>` content)

```html
<style>
    /* All CSS styles from schedule.html */
    /* Custom Scrollbar, List Items, Table Styles, Toast, etc. */
</style>
```

---

## Step 2: Extract Modals (10 minutes)

**Create:** `app/templates/schedule/_modals.html`

**Extract from** `schedule.html`:
- Add Schedule Modal (lines ~1684-1889)
- Edit Schedule Modal (lines ~1892-2029)
- Add Exam Schedule Modal (lines ~2032-2116)
- Edit Exam Schedule Modal (lines ~2119-2203)

**Template:**
```html
<!-- Add Schedule Modal -->
<div id="addScheduleModal" class="hidden fixed inset-0 bg-black bg-opacity-60...">
    <!-- Modal content -->
</div>

<!-- Edit Schedule Modal -->
<div id="editScheduleModal" class="hidden fixed inset-0 bg-black bg-opacity-60...">
    <!-- Modal content -->
</div>

<!-- Add Exam Schedule Modal -->
<div id="addExamScheduleModal" class="hidden fixed inset-0 bg-black bg-opacity-60...">
    <!-- Modal content -->
</div>

<!-- Edit Exam Schedule Modal -->
<div id="editExamScheduleModal" class="hidden fixed inset-0 bg-black bg-opacity-60...">
    <!-- Modal content -->
</div>
```

---

## Step 3: Extract Class Tab (15 minutes)

**Create:** `app/templates/schedule/_class_tab.html`

**Extract from** `schedule.html` lines ~379-777 (the entire `<div id="content-class">`)

```html
<!-- Tab Content: Class Schedules -->
<div id="content-class" class="tab-content flex-1 overflow-hidden flex gap-4">
    {% if sections %}
    <!-- Left Panel: Section List -->
    <div class="w-80 flex-shrink-0 bg-white rounded-2xl...">
        <!-- Section list content -->
    </div>

    <!-- Right Panel: Schedule Details -->
    <div class="flex-1 bg-white rounded-2xl...">
        <!-- Table view and calendar view -->
    </div>
    {% else %}
    <!-- Empty State -->
    {% endif %}
</div>
```

---

## Step 4: Extract Faculty Tab (15 minutes)

**Create:** `app/templates/schedule/_faculty_tab.html`

**Extract from** `schedule.html` lines ~780-1057 (the entire `<div id="content-faculty">`)

---

## Step 5: Extract Room Tab (15 minutes)

**Create:** `app/templates/schedule/_room_tab.html`

**Extract from** `schedule.html` lines ~1060-1336 (the entire `<div id="content-room">`)

---

## Step 6: Extract Exam Tab (15 minutes)

**Create:** `app/templates/schedule/_exam_tab.html`

**Extract from** `schedule.html` lines ~1339-1680 (the entire `<div id="content-exam">`)

---

## Step 7: Extract JavaScript Modules (30 minutes)

### Create `app/static/js/schedule/tabs.js`
```javascript
// Tab switching logic
function switchTab(tabName) {
    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    // Deactivate all tab buttons
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Show selected tab content
    const selectedContent = document.getElementById('content-' + tabName);
    if (selectedContent) {
        selectedContent.classList.add('active');
    }
    
    // Activate selected tab button
    const selectedButton = document.getElementById('tab-' + tabName);
    if (selectedButton) {
        selectedButton.classList.add('active');
    }
    
    // Store active tab in localStorage
    localStorage.setItem('activeScheduleTab', tabName);
}

// Restore active tab on page load
document.addEventListener('DOMContentLoaded', function() {
    // Ensure all tabs are hidden first
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.querySelectorAll('.tab-button').forEach(button => {
        button.classList.remove('active');
    });
    
    // Then activate the correct tab
    const activeTab = localStorage.getItem('activeScheduleTab') || 'class';
    switchTab(activeTab);
});
```

### Create `app/static/js/schedule/modals.js`
Extract all modal-related functions from schedule.html

### Create `app/static/js/schedule/filters.js`
Extract all filter-related functions

### Create `app/static/js/schedule/calendar.js`
Extract all calendar view switching functions

### Create `app/static/js/schedule/ai.js`
Extract all AI-related functions

### Create `app/static/js/schedule/forms.js`
Extract all form handling functions

### Create `app/static/js/schedule/main.js`
```javascript
// Toast notification system and utilities
function showToast(message, type = 'success') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icons = {
        success: `<svg class="w-5 h-5 text-green-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                </svg>`,
        error: `<svg class="w-5 h-5 text-red-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>`,
        info: `<svg class="w-5 h-5 text-blue-600 mr-3 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>`
    };
    
    toast.innerHTML = `
        ${icons[type] || icons.info}
        <span class="flex-1 text-sm font-medium text-gray-900">${message}</span>
        <button onclick="this.parentElement.remove()" class="ml-3 text-gray-400 hover:text-gray-600">
            <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path>
            </svg>
        </button>
    `;
    
    container.appendChild(toast);
    
    // Auto remove after 5 seconds
    setTimeout(() => toast.remove(), 5000);
}

// Show flash messages as toasts on page load
document.addEventListener('DOMContentLoaded', function() {
    const flashMessages = document.getElementById('flashMessages');
    if (flashMessages) {
        const messages = flashMessages.querySelectorAll('[data-message]');
        messages.forEach((msg, index) => {
            setTimeout(() => {
                showToast(msg.dataset.message, msg.dataset.type || 'info');
            }, index * 100);
        });
    }
});
```

---

## Step 8: Update Main Template (10 minutes)

**Update:** `app/templates/schedule.html`

Replace the entire file with this streamlined version:

```html
{% extends "base.html" %}

{% block title %}Schedule Management - iSchedWise{% endblock %}

{% block extra_css %}
    {% include 'schedule/_styles.html' %}
{% endblock %}

{% block content %}
<!-- Toast Container -->
<div id="toastContainer" class="toast-container"></div>

<div class="bg-gray-50 h-screen overflow-hidden flex flex-col p-4">
    <div class="w-full flex flex-col h-full overflow-hidden">
        <!-- Flash Messages (Hidden - converted to toasts) -->
        <div id="flashMessages" class="hidden">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div data-message="{{ message }}" data-type="{{ category }}"></div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
        </div>

        <!-- Page Header -->
        <div class="mb-3 flex-shrink-0 animate-slide-in">
            <div class="bg-white rounded-2xl shadow-lg border border-gray-200 p-4">
                <div class="flex items-center justify-between">
                    <div class="flex items-center gap-3">
                        <div class="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-purple-600 to-purple-700 text-white shadow-lg">
                            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
                            </svg>
                        </div>
                        <div>
                            <h1 class="text-2xl font-bold text-gray-900">Schedule Management</h1>
                            <p class="text-sm text-gray-600 mt-0.5">
                                {% if current_settings %}
                                    {{ current_settings.academic_year }} - {{ current_settings.semester }}
                                    {% if current_settings.exam_period %}
                                        ({{ current_settings.exam_period }})
                                    {% endif %}
                                {% else %}
                                    <span class="text-amber-600">⚠️ No active academic period set</span>
                                {% endif %}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Tab Navigation -->
        <div class="mb-4 flex-shrink-0">
            <div class="bg-white rounded-2xl shadow-lg border border-gray-100 p-1.5 flex gap-1.5 card-hover">
                <button id="tab-class" class="tab-button flex-1 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200" onclick="switchTab('class')">
                    📚 Class Schedules
                </button>
                <button id="tab-faculty" class="tab-button flex-1 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200" onclick="switchTab('faculty')">
                    👨‍🏫 Faculty
                </button>
                <button id="tab-room" class="tab-button flex-1 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200" onclick="switchTab('room')">
                    🏫 Rooms
                </button>
                <button id="tab-exam" class="tab-button flex-1 px-6 py-3 rounded-xl text-sm font-semibold transition-all duration-200" onclick="switchTab('exam')">
                    📝 Exam Schedules
                </button>
            </div>
        </div>

        <!-- Tab Contents -->
        {% include 'schedule/_class_tab.html' %}
        {% include 'schedule/_faculty_tab.html' %}
        {% include 'schedule/_room_tab.html' %}
        {% include 'schedule/_exam_tab.html' %}
    </div>
</div>

<!-- Modals -->
{% include 'schedule/_modals.html' %}

{% endblock %}

{% block extra_js %}
<script src="{{ url_for('static', filename='js/schedule/main.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/tabs.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/modals.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/filters.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/calendar.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/forms.js') }}"></script>
<script src="{{ url_for('static', filename='js/schedule/ai.js') }}"></script>
{% endblock %}
```

---

## Step 9: Split Route Handlers (Optional - Advanced)

If you want to split the Python routes as well:

### Create `app/routes/schedule/` directory structure:

```
app/routes/schedule/
├── __init__.py           # Blueprint setup
├── views.py              # Main index view
├── class_routes.py       # Class CRUD
├── exam_routes.py        # Exam CRUD
├── export_routes.py      # Excel exports
└── api_routes.py         # AJAX APIs
```

### Update `app/routes/__init__.py` to register schedule sub-blueprints

---

## Testing After Refactoring

1. **Clear browser cache** (Ctrl+Shift+Delete)
2. **Test each tab** - verify they load and switch correctly
3. **Test modals** - open/close add and edit modals
4. **Test filters** - department and building filters
5. **Test calendar** - toggle between table and calendar view
6. **Test forms** - add/edit schedules
7. **Test exports** - download Excel files
8. **Check console** - no JavaScript errors

---

## Benefits After Refactoring

✅ **3,384 lines** → ~8 files of **200-500 lines each**  
✅ **Easy to navigate** - file names tell you what's inside  
✅ **Faster debugging** - isolate issues to specific modules  
✅ **Better performance** - browser caches individual files  
✅ **Easier collaboration** - work on different files without conflicts  
✅ **Maintainable** - add features without breaking existing code  

---

## Quick Reference: Where to Find Things

| What You Need | File Location |
|---------------|---------------|
| CSS styles | `_styles.html` |
| Class tab UI | `_class_tab.html` |
| Faculty tab UI | `_faculty_tab.html` |
| Room tab UI | `_room_tab.html` |
| Exam tab UI | `_exam_tab.html` |
| All modals | `_modals.html` |
| Tab switching | `tabs.js` |
| Modal logic | `modals.js` |
| Filters | `filters.js` |
| Calendar | `calendar.js` |
| AI features | `ai.js` |
| Form handling | `forms.js` |
| Toast notifications | `main.js` |

---

Last Updated: October 19, 2025
