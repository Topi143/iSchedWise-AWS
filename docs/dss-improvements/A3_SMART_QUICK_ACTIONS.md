# A3 — Smart Quick Actions (Context-Aware)

> **Category:** Part A — Simplify What Exists  
> **Priority:** 9  
> **Effort:** Low  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★☆☆ Medium — Fewer but more relevant choices  

---

## Problem Statement

The dashboard currently has 4 static Quick Action buttons: **New Schedule**, **Faculty**, **Buildings**, **Reports**. These never change regardless of system state. A Dean logging in to a system with 5 unscheduled sections sees the same buttons as a Dean whose schedules are 100% complete.

**Issues:**
1. **No guidance** — Users must decide what to do themselves
2. **Generic targets** — "Faculty" and "Buildings" are management pages, not action-oriented
3. **Missing urgency signals** — No indication of what needs attention NOW

---

## Current Implementation

### File: [app/templates/dashboard.html](../../app/templates/dashboard.html) (lines 469-509)

```html
<h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">Quick Actions</h2>
<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 quick-actions-grid">
    <a href="{{ url_for('schedule.class_view') }}" class="quick-action ...">
        <!-- Calendar icon --> New Schedule
    </a>
    <a href="{{ url_for('faculty.index') }}" class="quick-action ...">
        <!-- Users icon --> Faculty
    </a>
    <a href="{{ url_for('building.index') }}" class="quick-action ...">
        <!-- Building icon --> Buildings
    </a>
    <a href="{{ url_for('reports.index') }}" class="quick-action ...">
        <!-- Chart icon --> Reports
    </a>
</div>
```

### Route: [app/routes/main.py](../../app/routes/main.py)
No smart action logic currently exists. All Quick Actions are hardcoded in the template.

---

## Proposed Solution

### Dynamic Quick Actions Based on System State

Replace static buttons with up to 4 **context-aware actions** ordered by priority:

| Priority | Condition | Action Button | Color | Icon |
|----------|-----------|---------------|-------|------|
| 1 (Highest) | Overloaded faculty > 0 | "Review N Overloaded Faculty" | Red | ⚠️ |
| 2 | Unscheduled sections > 0 | "Schedule N Remaining Sections" | Amber | 📋 |
| 3 | Upcoming exams need proctors | "Assign N Exam Proctors" | Orange | 📝 |
| 4 | Schedule completion < 100% | "Continue Scheduling (NN%)" | Blue | ▶️ |
| 5 | Exams in 7 days without rooms | "Finalize N Exams" | Purple | 🏫 |
| Default | Nothing urgent | "New Schedule" / "Reports" / "Export" | Green/Gray | Standard |

### Visual Difference

**Before (static):**
```
[New Schedule]  [Faculty]  [Buildings]  [Reports]
  (all blue)     (all blue) (all blue)   (all blue)
```

**After (context-aware):**
```
[⚠️ Review 2 Overloaded]  [📋 Schedule 5 Sections]  [📊 View Reports]
  (red bg, bold)            (amber bg)                 (green bg)
```

---

## Backend Logic

### New function in `app/routes/main.py`

```python
def generate_smart_actions(schedule_completion_rate, faculty_workload, 
                           upcoming_exams, stats=None):
    """Generate context-aware Quick Action buttons for the dashboard.
    
    Returns list of dicts with: label, url, icon, color_class, priority
    Maximum 4 actions returned, ordered by priority.
    """
    actions = []
    
    # --- Priority 1: Overloaded Faculty ---
    overloaded_count = sum(1 for fw in faculty_workload 
                          if fw.get('load_status') == 'exceeded')
    if overloaded_count > 0:
        actions.append({
            'label': f'Review {overloaded_count} Overloaded Faculty',
            'url': url_for('reports.faculty_report'),
            'icon': '⚠️',
            'color_class': 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200',
            'priority': 1
        })
    
    # --- Priority 2: Incomplete Scheduling ---
    if schedule_completion_rate < 100:
        pct_remaining = 100 - schedule_completion_rate
        actions.append({
            'label': f'Continue Scheduling ({schedule_completion_rate}% done)',
            'url': url_for('schedule.class_view'),
            'icon': '📋',
            'color_class': 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200',
            'priority': 2
        })
    
    # --- Priority 3: Near-capacity Faculty ---
    warning_count = sum(1 for fw in faculty_workload 
                        if fw.get('load_status') == 'warning')
    if warning_count > 0 and overloaded_count == 0:  # Don't show if already showing overloaded
        actions.append({
            'label': f'{warning_count} Faculty Near Capacity',
            'url': url_for('reports.faculty_report'),
            'icon': '👥',
            'color_class': 'bg-yellow-50 text-yellow-700 hover:bg-yellow-100 border border-yellow-200',
            'priority': 3
        })
    
    # --- Priority 4: Upcoming Exams ---
    if upcoming_exams and len(upcoming_exams) > 0:
        actions.append({
            'label': f'{len(upcoming_exams)} Upcoming Exams',
            'url': url_for('schedule.class_view', tab='exam'),
            'icon': '📝',
            'color_class': 'bg-purple-50 text-purple-700 hover:bg-purple-100 border border-purple-200',
            'priority': 4
        })
    
    # --- Fallback defaults ---
    default_actions = [
        {
            'label': 'New Schedule',
            'url': url_for('schedule.class_view'),
            'icon': '➕',
            'color_class': 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200',
            'priority': 10
        },
        {
            'label': 'View Reports',
            'url': url_for('reports.index'),
            'icon': '📊',
            'color_class': 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200',
            'priority': 11
        },
        {
            'label': 'Export Schedules',
            'url': url_for('schedule.class_view'),
            'icon': '📥',
            'color_class': 'bg-gray-50 text-gray-600 hover:bg-gray-100 border border-gray-200',
            'priority': 12
        }
    ]
    
    # Fill remaining slots with defaults (up to 4 total)
    for default in default_actions:
        if len(actions) >= 4:
            break
        actions.append(default)
    
    # Sort by priority and limit to 4
    actions.sort(key=lambda a: a['priority'])
    return actions[:4]
```

### Template Update

```html
<h2 class="text-sm font-semibold text-gray-900 dark:text-white mb-3">
    {{ 'Suggested Actions' if smart_actions|selectattr('priority', 'lt', 10)|list else 'Quick Actions' }}
</h2>
<div class="grid grid-cols-2 sm:grid-cols-4 gap-3 quick-actions-grid">
    {% for action in smart_actions %}
    <a href="{{ action.url }}" class="quick-action flex items-center gap-2 p-3 rounded-lg 
       text-xs font-medium transition-colors {{ action.color_class }}">
        <span>{{ action.icon }}</span>
        <span>{{ action.label }}</span>
    </a>
    {% endfor %}
</div>
```

---

## Implementation Steps

### Step 1: Add `generate_smart_actions()` to `app/routes/main.py`
1. Add function before the dashboard route
2. Compute `faculty_workload` with `load_status` (already computed — check existing data)
3. Return `smart_actions` list

### Step 2: Update Dashboard Route
1. Call `generate_smart_actions()` with available data
2. Pass `smart_actions=smart_actions` to `render_template()`

### Step 3: Update Template
1. Replace static Quick Actions grid with dynamic `{% for action in smart_actions %}`
2. Use action's `color_class` for styling
3. Change header text to "Suggested Actions" when actionable items exist

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/main.py` | **Small addition** | Add `generate_smart_actions()` function + pass to template |
| `app/templates/dashboard.html` | **Small edit** | Replace static Quick Action buttons with `{% for %}` loop |

---

## Testing Checklist

- [ ] When overloaded faculty exist → red "Review N Overloaded Faculty" button appears first
- [ ] When scheduling incomplete → amber "Continue Scheduling (NN%)" button appears
- [ ] When both exist → both show, ordered by priority
- [ ] When nothing urgent → default actions (New Schedule, Reports, Export) show
- [ ] Maximum 4 buttons displayed regardless of conditions
- [ ] All button URLs navigate correctly
- [ ] Dean role: actions reflect department-filtered data
- [ ] Mobile: 2-column grid works for dynamic buttons
- [ ] Dark mode: button colors adapt correctly
