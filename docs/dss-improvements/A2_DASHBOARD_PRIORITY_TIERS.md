# A2 — Dashboard: Priority Tiers Instead of Flat Grid

> **Category:** Part A — Simplify What Exists  
> **Priority:** 7  
> **Effort:** Medium  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★★★ HIGH — First impression goes from 12 widgets to 3 focused areas  

---

## Problem Statement

The current dashboard displays **12 widgets** with **~50+ discrete data points** in a flat grid with equal visual weight. On a 1080p display, roughly 4-5 widgets are visible without scrolling — the remaining 7-8 require scrolling to discover. There's no hierarchy telling users what matters most.

**Key issues:**
1. **No priority ordering** — "Class Schedules: 148" and "Recent Activity" get the same visual prominence
2. **Numbers without context** — "148 Class Schedules" means nothing without knowing if that's good or bad
3. **Below-the-fold content easily missed** — Faculty Load Summary, Upcoming Exams, System Overview are hidden below scroll
4. **Static Quick Actions** — Generic "New Schedule", "Faculty", "Buildings", "Reports" links don't adapt to system state

---

## Current Architecture

### File
| File | Lines | Purpose |
|------|-------|---------|
| [app/templates/dashboard.html](../../app/templates/dashboard.html) | 832 | Dashboard template with 12 widgets |
| [app/routes/main.py](../../app/routes/main.py) | ~260 | Dashboard route passing 20+ template variables |

### Current Widget Layout (Flat Grid)

```
┌─────────────────────────────────────────────────────────────────────┐
│ Greeting + Academic Year + Semester + Dept Filter                    │ ← Header
├─────────────────────────────────────────────────────────────────────┤
│ [Schedules: 148] [Faculty: 45] [Sections: 30] [Rooms: 25]         │ ← 4 stat cards
├─────────────────────────────────────────────────────────────────────┤
│ [Today: 12]  [Exams: 8]  [Curriculum: 5]  [Subjects: 120]         │ ← 4 secondary cards
├─────────────────────────────────────────────────────────────────────┤
│ Quick Actions: [New Schedule] [Faculty] [Buildings] [Reports]       │ ← Static buttons
├──────────────────────────────────┬──────────────────────────────────┤
│ Department Overview              │ Schedule Progress Ring            │ ← FOLD LINE (~1080p)
│ (5 departments × 3 metrics)     │ (SVG circle, NN%)                │
│ ...                              │ Faculty Load Summary             │
│                                  │ (top 5 avatars + hours)          │
├──────────────────────────────────┤                                  │
│ Recent Schedules (last 5)        ├──────────────────────────────────┤
│                                  │ Upcoming Exams (next 7 days)     │
├──────────────────────────────────┤                                  │
│ Recent Activity (last 8)         │ System Overview (admin only)     │
└──────────────────────────────────┴──────────────────────────────────┘

Total visible without scroll: ~4-5 widgets
Total with scroll: 12 widgets, ~50+ data points
```

### Current Template Variables (from `main.py`)
```python
return render_template('dashboard.html',
    user=current_user,
    curriculum_count=curriculum_count,
    department_count=department_count,
    faculty_count=faculty_count,
    building_count=building_count,
    section_count=section_count,
    room_count=room_count,
    subject_count=subject_count,
    schedule_count=schedule_count,
    exam_schedule_count=exam_schedule_count,
    recent_schedules=recent_schedules,
    departments_overview=departments_overview,
    faculty_workload=faculty_workload,
    current_settings=current_settings,
    available_departments=available_departments,
    selected_department_id=selected_department_id,
    recent_activities=recent_activities,
    user_count=user_count,
    schedule_completion_rate=schedule_completion_rate,
    todays_schedules=todays_schedules,
    upcoming_exams=upcoming_exams
)
```

---

## Proposed Solution

### Tiered Layout: Health Banner → Primary Row → Expandable Details

```
┌─────────────────────────────────────────────────────────────────────┐
│ Greeting + Academic Year + Dept Filter                              │
├─────────────────────────────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────────────────────────────┐ │
│ │ 🟢 Schedule Health: 82/100  •  3 faculty near overload  •      │ │ ← TIER 1: Health Banner
│ │    2 rooms underutilized  •  All 30 sections scheduled          │ │    (NEW — single line)
│ └─────────────────────────────────────────────────────────────────┘ │
├────────────────┬────────────────────────┬──────────────────────────┤
│ Progress Ring  │  Today's Schedule      │  Smart Quick Actions     │ ← TIER 2: Primary Row
│ (82%, big)     │  (12 classes today)    │  [Resolve 3 Conflicts]   │    (always visible)
│                │  (Next: 10AM Room 301) │  [Schedule 5 Remaining]  │
│                │                        │  [View Reports]          │
├────────────────┴────────────────────────┴──────────────────────────┤
│ ▾ Show Details (collapsed by default)                              │ ← TIER 3: Expandable
│ ┌──────────────────────────────────────────────────────────────── │ │
│ │ [Stat Cards] [Dept Overview] [Faculty Load] [Recent Activity]  │ │
│ │ [Recent Schedules] [Upcoming Exams] [System Overview]          │ │
│ └──────────────────────────────────────────────────────────────── │ │
└─────────────────────────────────────────────────────────────────────┘
```

### Design Principles
1. **Tier 1 (Health Banner):** One glance = system status. Color-coded (green/yellow/red). No clicks needed.
2. **Tier 2 (Primary Row):** What matters RIGHT NOW — schedule progress, today's schedule, next action to take. Always above the fold.
3. **Tier 3 (Details):** All existing widgets preserved — just collapsed behind a toggle. Power users can expand.

---

## Tier 1: Scheduling Health Banner

### Visual Design
```html
<!-- Health Banner — always visible, single line -->
<div class="mb-3 px-4 py-2.5 rounded-xl border flex items-center gap-3 text-sm
     {{ 'bg-emerald-50 border-emerald-200 text-emerald-800' if sqi >= 80 else
        'bg-amber-50 border-amber-200 text-amber-800' if sqi >= 60 else
        'bg-red-50 border-red-200 text-red-800' }}">
    
    <!-- SQI Score Badge -->
    <div class="flex items-center gap-1.5 font-bold flex-shrink-0">
        <span class="w-2.5 h-2.5 rounded-full {{ color_class }}"></span>
        Schedule Health: {{ sqi }}/100
    </div>
    
    <!-- Separator -->
    <span class="text-gray-300">•</span>
    
    <!-- Key Insights (auto-generated, max 3) -->
    <div class="flex-1 truncate">
        {{ health_insights | join(' • ') }}
    </div>
    
    <!-- Expand Button -->
    <button onclick="openSQIDetail()" class="text-xs underline flex-shrink-0">
        Details →
    </button>
</div>
```

### Insight Generation Logic (Backend)
```python
def generate_health_insights(stats):
    """Generate 2-3 short insight strings for the health banner."""
    insights = []
    
    # Faculty insights
    if stats.get('overloaded_faculty_count', 0) > 0:
        insights.append(f"{stats['overloaded_faculty_count']} faculty overloaded")
    elif stats.get('warning_faculty_count', 0) > 0:
        insights.append(f"{stats['warning_faculty_count']} faculty near overload")
    else:
        insights.append("Faculty workloads balanced")
    
    # Room insights
    unused = stats.get('total_rooms', 0) - stats.get('rooms_in_use', 0)
    if unused > 0:
        insights.append(f"{unused} rooms underutilized")
    else:
        insights.append("All rooms in use")
    
    # Completion insights
    rate = stats.get('schedule_completion_rate', 0)
    if rate >= 100:
        insights.append("All sections fully scheduled")
    elif rate >= 80:
        insights.append(f"{100 - rate}% of sections need scheduling")
    else:
        insights.append(f"Only {rate}% sections scheduled")
    
    return insights[:3]
```

### SQI Score Calculation
The SQI (Schedule Quality Index) is defined in detail in [B1_SCHEDULE_QUALITY_INDEX.md](./B1_SCHEDULE_QUALITY_INDEX.md). For the dashboard banner, only the final score (0-100) and color thresholds are needed:
- **80-100:** Green (Excellent)
- **60-79:** Yellow/Amber (Needs Attention)
- **0-59:** Red (Critical Issues)

---

## Tier 2: Primary Row (Always Visible)

### 3-Column Layout
```html
<div class="grid grid-cols-1 md:grid-cols-3 gap-3 mb-3">
    <!-- Column 1: Schedule Progress (kept from existing) -->
    <div class="bg-white rounded-xl border p-4 flex flex-col items-center justify-center">
        <!-- Existing SVG progress ring -->
        <svg class="progress-ring w-28 h-28" viewBox="0 0 120 120">...</svg>
        <span class="text-xl font-bold">{{ schedule_completion_rate }}%</span>
        <p class="text-xs text-gray-500">Sections scheduled</p>
    </div>
    
    <!-- Column 2: Today's Snapshot -->
    <div class="bg-white rounded-xl border p-4">
        <h3 class="text-sm font-semibold mb-2">Today</h3>
        <div class="text-3xl font-bold text-blue-600">{{ todays_schedules }}</div>
        <p class="text-xs text-gray-500 mb-3">classes happening now/today</p>
        <!-- Optional: Next upcoming class -->
        {% if next_class %}
        <div class="text-xs bg-blue-50 rounded-lg p-2">
            Next: {{ next_class.subject }} at {{ next_class.start_time }} in {{ next_class.room }}
        </div>
        {% endif %}
    </div>
    
    <!-- Column 3: Smart Quick Actions -->
    <div class="bg-white rounded-xl border p-4">
        <h3 class="text-sm font-semibold mb-2">Suggested Actions</h3>
        <div class="space-y-2">
            <!-- Dynamic based on system state -->
            {% for action in smart_actions %}
            <a href="{{ action.url }}" class="block px-3 py-2 text-xs font-medium rounded-lg
                {{ action.color_class }}">
                {{ action.icon }} {{ action.label }}
            </a>
            {% endfor %}
        </div>
    </div>
</div>
```

---

## Tier 3: Expandable Details

### Toggle Mechanism
```html
<!-- Expand/Collapse Toggle -->
<button id="detailsToggle" onclick="toggleDashboardDetails()" 
        class="w-full mb-3 py-2 px-4 text-sm text-gray-500 hover:text-gray-700 
               bg-gray-50 rounded-lg border border-dashed border-gray-200 
               flex items-center justify-center gap-2 transition-colors">
    <svg id="detailsChevron" class="w-4 h-4 transition-transform" ...>
        <!-- Chevron down icon -->
    </svg>
    <span id="detailsToggleText">Show detailed statistics</span>
</button>

<!-- Collapsible Content (hidden by default) -->
<div id="dashboardDetails" class="hidden space-y-3">
    <!-- ALL existing widgets go here, in their current grid layout -->
    <!-- Primary stat cards (4) -->
    <!-- Secondary stat cards (4) -->
    <!-- Department Overview + Faculty Load + Recent Schedules + etc. -->
</div>
```

### JavaScript
```javascript
function toggleDashboardDetails() {
    const details = document.getElementById('dashboardDetails');
    const chevron = document.getElementById('detailsChevron');
    const text = document.getElementById('detailsToggleText');
    
    details.classList.toggle('hidden');
    chevron.classList.toggle('rotate-180');
    text.textContent = details.classList.contains('hidden') 
        ? 'Show detailed statistics' 
        : 'Hide detailed statistics';
    
    // Remember preference
    localStorage.setItem('dashboardDetailsExpanded', 
        !details.classList.contains('hidden'));
}

// Restore preference on load
document.addEventListener('DOMContentLoaded', () => {
    if (localStorage.getItem('dashboardDetailsExpanded') === 'true') {
        toggleDashboardDetails();
    }
});
```

---

## Smart Quick Actions Logic (Backend)

```python
def generate_smart_actions(stats, current_user):
    """Generate context-aware Quick Action buttons for dashboard."""
    actions = []
    
    # Priority 1: Unresolved conflicts (if we track them)
    # (Requires conflict tracking — see B1)
    
    # Priority 2: Incomplete scheduling
    if stats.get('schedule_completion_rate', 100) < 100:
        remaining = stats.get('unscheduled_sections', 0)
        actions.append({
            'label': f'Schedule {remaining} Remaining Sections',
            'url': url_for('schedule.class_view'),
            'icon': '📋',
            'color_class': 'bg-amber-50 text-amber-700 hover:bg-amber-100 border border-amber-200'
        })
    
    # Priority 3: Overloaded faculty
    if stats.get('overloaded_faculty_count', 0) > 0:
        count = stats['overloaded_faculty_count']
        actions.append({
            'label': f'Review {count} Overloaded Faculty',
            'url': url_for('reports.faculty_report'),
            'icon': '⚠️',
            'color_class': 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
        })
    
    # Priority 4: Upcoming exams needing attention
    if stats.get('unscheduled_exams', 0) > 0:
        actions.append({
            'label': f'Schedule {stats["unscheduled_exams"]} Exams',
            'url': url_for('schedule.class_view', tab='exam'),
            'icon': '📝',
            'color_class': 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
        })
    
    # Default actions (if nothing urgent)
    if not actions:
        actions = [
            {
                'label': 'View Reports',
                'url': url_for('reports.index'),
                'icon': '📊',
                'color_class': 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100 border border-emerald-200'
            },
            {
                'label': 'Export Schedules',
                'url': url_for('schedule.class_view'),
                'icon': '📥',
                'color_class': 'bg-gray-50 text-gray-700 hover:bg-gray-100 border border-gray-200'
            }
        ]
    
    return actions[:3]  # Max 3 actions
```

---

## Implementation Steps

### Step 1: Update `app/routes/main.py`
1. Import and call `calculate_statistics()` from reports (lightweight, with `include={'counts', 'faculty'}`)
2. Compute SQI score (or a simplified version — see B1 doc)
3. Generate `health_insights` list
4. Generate `smart_actions` list
5. Pass new variables: `sqi`, `health_insights`, `smart_actions`

### Step 2: Restructure `app/templates/dashboard.html`
1. Add Health Banner (Tier 1) after the greeting header
2. Restructure Tier 2 as a 3-column grid (Progress Ring | Today | Smart Actions)
3. Wrap all existing widgets (Tier 3) in collapsible container
4. Add toggle button between Tier 2 and Tier 3
5. Add `toggleDashboardDetails()` JavaScript

### Step 3: Style & Polish
1. Dark mode support for Health Banner and new Tier 2 widgets
2. Responsive: On mobile, Tier 2 becomes single-column stack
3. Add smooth expand/collapse animation (`transition-all duration-300`)
4. Persist expanded/collapsed state in localStorage

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/main.py` | **Medium edit** | Add SQI calculation, health insights generation, smart actions |
| `app/templates/dashboard.html` | **Major refactor** | Restructure into 3 tiers |

---

## User Experience Comparison

| Aspect | Before | After |
|--------|--------|-------|
| First impression | 8 stat cards + 4 buttons + ... (12 widgets) | 1 health bar + 3 focused panels |
| Info visible without scroll | ~20 data points across 4-5 widgets | ~8 data points across 4 elements |
| "What should I do next?" | User must interpret numbers and decide | Smart Actions tell you exactly |
| Power user access | All widgets always visible | Toggle "Show details" to reveal all |
| System health at a glance | Compare 8+ numbers mentally | One color-coded score + 3 insights |
| Mobile experience | Scroll through 12 widgets | Health bar + 3 panels, expand if needed |

---

## Testing Checklist

- [ ] Health Banner shows correct SQI score (matches reports calculation)
- [ ] Banner color changes: green (≥80), amber (60-79), red (<60)
- [ ] Health insights update dynamically based on system state
- [ ] Smart Actions change based on: incomplete scheduling, overloaded faculty, exams needed
- [ ] Smart Actions show default (Reports, Export) when nothing urgent
- [ ] Tier 3 toggle expands/collapses correctly
- [ ] Tier 3 state persists via localStorage across page reloads
- [ ] All existing widgets still render correctly inside Tier 3
- [ ] Mobile: single-column responsive layout for all tiers
- [ ] Dark mode: all new elements adapt correctly
- [ ] Dean role: department filtering still works for all tiers
- [ ] Admin role: system overview still shows in Tier 3
- [ ] Performance: calculate_statistics() call doesn't noticeably slow dashboard load
