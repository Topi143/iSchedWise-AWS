# C1 — Replace Stat Cards with Mini Sparklines

> **Category:** Part C — Visual Analytics  
> **Priority:** 11  
> **Effort:** Medium  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★☆☆ Medium — Adds context without adding clutter  

---

## Problem Statement

Dashboard stat cards show big numbers like "148 Class Schedules" and "45 Faculty Members." These are point-in-time snapshots with no context. The user can't tell if 148 is more or fewer than last week, whether faculty count is growing, or if scheduling pace is on track.

**Numbers without trends are just data. Trends are information.**

---

## Current Stat Cards

### File: [app/templates/dashboard.html](../../app/templates/dashboard.html) (lines 326-460)

**Primary Stats (4 cards):**
| Card | Variable | Subtitle |
|------|----------|----------|
| Class Schedules | `schedule_count` | "This semester" |
| Faculty Members | `faculty_count` | "Active instructors" |
| Sections | `section_count` | "All programs" |
| Rooms Available | `room_count` | "In N building(s)" |

**Secondary Stats (4 cards):**
| Card | Variable | Subtitle |
|------|----------|----------|
| Today's Classes | `todays_schedules` | — |
| Exam Schedules | `exam_schedule_count` | — |
| Curriculum | `curriculum_count` | — |
| Subjects | `subject_count` | — |

---

## Proposed Solution

### Add Tiny Trend Indicators Below Each Number

Instead of complex sparkline charts, use a simpler and more practical approach — a **trend arrow with percentage change** compared to the previous semester:

```
┌─────────────────────────┐
│  📅 Class Schedules      │
│                          │
│     148                  │
│     ↑ 12% from last sem  │  ← NEW: trend indicator
│     This semester         │
└─────────────────────────┘
```

### Alternate: Mini Bar Chart (7 Dots)

For metrics that change within a semester (like daily schedule creation activity), show a **7-day activity sparkline** using simple colored dots:

```
┌─────────────────────────┐
│  📅 Class Schedules      │
│                          │
│     148                  │
│     ● ● ● ◐ ○ ○ ○       │  ← Activity dots (last 7 days)
│     This semester         │
└─────────────────────────┘
```

---

## Trend Data Calculation

### Backend: Semester Comparison

```python
def get_stat_trends(current_year, current_semester, user_department_ids=None):
    """Calculate trend data for dashboard stat cards.
    
    Compares current semester to previous semester.
    
    Returns:
        dict: {
            'schedule_trend': {'direction': 'up', 'pct': 12, 'previous': 132},
            'faculty_trend': {'direction': 'same', 'pct': 0, 'previous': 45},
            'section_trend': {'direction': 'down', 'pct': -5, 'previous': 32},
            ...
        }
    """
    # Determine previous semester
    if current_semester == '2nd Semester':
        prev_semester = '1st Semester'
        prev_year = current_year
    elif current_semester == '1st Semester':
        prev_semester = '2nd Semester'
        # Parse year: "2025-2026" → "2024-2025"
        years = current_year.split('-')
        prev_year = f"{int(years[0])-1}-{int(years[1])-1}"
    else:  # Summer
        prev_semester = '2nd Semester'
        prev_year = current_year
    
    # Count for previous semester
    prev_schedules = Schedule.query.filter_by(
        academic_year=prev_year, semester=prev_semester, is_archived=False
    ).count() if prev_year else 0
    
    prev_exams = ExamSchedule.query.filter_by(
        academic_year=prev_year, semester=prev_semester, is_archived=False
    ).count() if prev_year else 0
    
    def calc_trend(current, previous):
        if previous == 0:
            return {'direction': 'new', 'pct': 0, 'previous': 0}
        pct = round(((current - previous) / previous) * 100)
        if pct > 0:
            return {'direction': 'up', 'pct': pct, 'previous': previous}
        elif pct < 0:
            return {'direction': 'down', 'pct': pct, 'previous': previous}
        else:
            return {'direction': 'same', 'pct': 0, 'previous': previous}
    
    return {
        'schedule_trend': calc_trend(current_schedule_count, prev_schedules),
        'exam_trend': calc_trend(current_exam_count, prev_exams),
        # Faculty/section/room trends are cross-semester (counted differently)
    }
```

### Activity Dots (Last 7 Days)

```python
def get_weekly_activity():
    """Get schedule creation counts for the last 7 days."""
    from datetime import datetime, timedelta
    
    today = datetime.utcnow().date()
    activity = []
    
    for i in range(6, -1, -1):  # 7 days ago to today
        day = today - timedelta(days=i)
        count = Schedule.query.filter(
            db.func.date(Schedule.created_at) == day,
            Schedule.is_archived == False
        ).count()
        activity.append({
            'date': day.isoformat(),
            'count': count
        })
    
    return activity
```

---

## Template Changes

### Trend Arrow (Simple Approach)

```html
<!-- Add below the count number in each stat card -->
{% if stat_trends.schedule_trend %}
    {% set trend = stat_trends.schedule_trend %}
    <div class="flex items-center gap-1 mt-1">
        {% if trend.direction == 'up' %}
            <svg class="w-3 h-3 text-emerald-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M5.293 9.707a1 1 0 010-1.414l4-4a1 1 0 011.414 0l4 4a1 1 0 01-1.414 1.414L11 7.414V15a1 1 0 11-2 0V7.414L6.707 9.707a1 1 0 01-1.414 0z"/>
            </svg>
            <span class="text-[10px] text-emerald-600">{{ trend.pct }}% from last semester</span>
        {% elif trend.direction == 'down' %}
            <svg class="w-3 h-3 text-red-500" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M14.707 10.293a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 111.414-1.414L9 12.586V5a1 1 0 012 0v7.586l2.293-2.293a1 1 0 011.414 0z"/>
            </svg>
            <span class="text-[10px] text-red-600">{{ trend.pct }}% from last semester</span>
        {% else %}
            <span class="text-[10px] text-gray-400">Same as last semester</span>
        {% endif %}
    </div>
{% endif %}
```

### Activity Dots (Optional Enhancement)

```html
<!-- 7-day activity dots -->
{% if weekly_activity %}
<div class="flex items-center gap-1 mt-2" title="Schedule creation activity (last 7 days)">
    {% for day in weekly_activity %}
        {% set max_count = weekly_activity | map(attribute='count') | max %}
        {% set intensity = (day.count / max_count * 100) if max_count > 0 else 0 %}
        <div class="w-1.5 h-1.5 rounded-full 
            {% if intensity >= 75 %}bg-blue-600
            {% elif intensity >= 50 %}bg-blue-400
            {% elif intensity >= 25 %}bg-blue-200
            {% else %}bg-gray-200{% endif %}"
            title="{{ day.date }}: {{ day.count }} schedules created">
        </div>
    {% endfor %}
</div>
{% endif %}
```

---

## Implementation Steps

### Step 1: Add Trend Calculation to `app/routes/main.py`
1. Add `get_stat_trends()` function
2. Optionally add `get_weekly_activity()` function
3. Call in dashboard route and pass to template

### Step 2: Update Stat Card Templates
1. Add trend arrow/percentage below each stat number
2. Optionally add activity dots row

### Step 3: Handle Edge Cases
1. First semester (no previous data) → "New this semester" label
2. Zero counts → don't show misleading percentages
3. Dean role → trends filtered by department

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/main.py` | **Small addition** | Add trend/activity calculation functions |
| `app/templates/dashboard.html` | **Small edit** | Add trend indicators below stat numbers |

---

## Testing Checklist

- [ ] Trend shows "↑ N%" when current > previous semester
- [ ] Trend shows "↓ N%" when current < previous
- [ ] Trend shows "Same" when equal
- [ ] First semester with no previous data → graceful fallback
- [ ] Activity dots show correct intensity for last 7 days
- [ ] Dark mode: trend colors and dots visible
- [ ] Dean role: trends reflect department-filtered data
- [ ] Performance: trend calculation adds <200ms to dashboard load
