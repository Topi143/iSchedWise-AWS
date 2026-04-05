# C2 — Reports: Extended Chart Visualizations

> **Category:** Part C — Visual Analytics  
> **Priority:** 11 (same batch as C1)  
> **Effort:** Medium  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★☆☆ Medium — Visual charts are easier to interpret than tables  

---

## Problem Statement

The Reports Overview already has 4 Chart.js charts (Type Distribution doughnut, Weekly Distribution bar, Faculty Workload top-10 horizontal bar, Room Utilization top-10 horizontal bar). These are good but limited. Key DSS visualizations are missing:

1. **Room Heatmap** — No way to see which rooms are busy at which times
2. **Faculty Workload by Department** — Can't compare workload distribution across departments
3. **Semester Trend Lines** — Comparison page shows numbers but no visual trend
4. **SQI Radar Chart** — Covered in B1, but listed here for completeness

---

## Existing Charts

### File: [app/templates/reports/overview.html](../../app/templates/reports/overview.html)

| Chart | Type | Data Source | Location |
|-------|------|-------------|----------|
| Type Distribution | Doughnut | `lecture_count`, `lab_count` | Reports Overview |
| Weekly Distribution | Bar | `schedule_by_day` dict | Reports Overview |
| Faculty Workload (Top 10) | Horizontal Bar | `faculty_workloads` | Reports Overview |
| Room Utilization (Top 10) | Horizontal Bar | `room_utilizations` | Reports Overview |

**Chart.js is already loaded** — no additional library needed.

---

## New Charts to Add

### 1. Room Utilization Heatmap (Day × Time Grid)

**What:** A grid showing room utilization intensity across day-of-week × time-of-day, helping users identify scheduling bottlenecks and underused time slots.

**Location:** Reports → Room Utilization section (new widget)

```
         7AM  8AM  9AM  10AM  11AM  12PM  1PM  2PM  3PM  4PM  5PM
Monday   [  ] [██] [██] [███] [███] [░░] [██] [██] [░░] [  ] [  ]
Tuesday  [  ] [██] [███][███] [██ ] [░░] [██] [░░] [  ] [  ] [  ]
Wednesday[  ] [██] [██] [██ ] [██ ] [░░] [░░] [  ] [  ] [  ] [  ]
Thursday [  ] [███][███][██ ] [██ ] [░░] [██] [██] [░░] [  ] [  ]
Friday   [  ] [██] [░░] [░░] [░░] [░░] [  ] [  ] [  ] [  ] [  ]
Saturday [  ] [░░] [░░] [  ] [  ] [  ] [  ] [  ] [  ] [  ] [  ]

Legend: [  ] 0%   [░░] 1-25%   [██] 26-75%   [███] 76-100%
```

**Backend Data:**

```python
def get_room_heatmap_data(academic_year, semester, user_department_ids=None):
    """Generate room occupancy heatmap data (day × hour grid).
    
    Returns:
        list[dict]: [
            {'day': 'Monday', 'hour': 8, 'occupancy_pct': 75, 'count': 15, 'total_rooms': 20},
            ...
        ]
    """
    schedules = Schedule.query.filter_by(
        academic_year=academic_year, semester=semester, is_archived=False
    ).all()
    
    total_rooms = Room.query.filter_by(is_archived=False).count()
    
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    hours = list(range(7, 21))  # 7AM to 8PM
    
    heatmap = []
    for day in days:
        for hour in hours:
            # Count rooms occupied during this hour on this day
            occupied = sum(1 for s in schedules 
                         if s.day_of_week == day 
                         and s.start_time.hour <= hour < s.end_time.hour)
            
            pct = round((occupied / total_rooms) * 100) if total_rooms > 0 else 0
            heatmap.append({
                'day': day,
                'hour': hour,
                'occupancy_pct': pct,
                'count': occupied,
                'total_rooms': total_rooms
            })
    
    return heatmap
```

**Chart.js Matrix Plugin** — For a true heatmap, use `chartjs-chart-matrix` plugin (CDN, ~15KB). Alternatively, render as a simple HTML grid with Tailwind background colors:

```html
<!-- Pure HTML/CSS Heatmap (no extra library) -->
<div class="grid gap-px" style="grid-template-columns: 80px repeat(14, 1fr);">
    <!-- Header row -->
    <div class="text-[9px] text-gray-400"></div>
    {% for hour in range(7, 21) %}
    <div class="text-[9px] text-gray-400 text-center">{{ hour }}:00</div>
    {% endfor %}
    
    <!-- Data rows -->
    {% for day in ['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday'] %}
    <div class="text-[9px] text-gray-600 font-medium py-1">{{ day[:3] }}</div>
    {% for hour in range(7, 21) %}
        {% set cell = heatmap_data | selectattr('day', 'eq', day) | selectattr('hour', 'eq', hour) | first %}
        {% set pct = cell.occupancy_pct if cell else 0 %}
        <div class="h-6 rounded-sm cursor-pointer transition-colors
            {% if pct >= 76 %}bg-red-400 hover:bg-red-500
            {% elif pct >= 51 %}bg-orange-300 hover:bg-orange-400
            {% elif pct >= 26 %}bg-blue-300 hover:bg-blue-400
            {% elif pct >= 1 %}bg-blue-100 hover:bg-blue-200
            {% else %}bg-gray-50 hover:bg-gray-100
            {% endif %}"
            title="{{ day }} {{ hour }}:00 — {{ pct }}% rooms occupied ({{ cell.count if cell else 0 }}/{{ cell.total_rooms if cell else 0 }})">
        </div>
    {% endfor %}
    {% endfor %}
</div>

<!-- Legend -->
<div class="flex items-center gap-3 mt-2 text-[10px] text-gray-500">
    <span class="flex items-center gap-1"><div class="w-3 h-3 rounded-sm bg-gray-50 border"></div> Empty</span>
    <span class="flex items-center gap-1"><div class="w-3 h-3 rounded-sm bg-blue-100"></div> Low</span>
    <span class="flex items-center gap-1"><div class="w-3 h-3 rounded-sm bg-blue-300"></div> Medium</span>
    <span class="flex items-center gap-1"><div class="w-3 h-3 rounded-sm bg-orange-300"></div> High</span>
    <span class="flex items-center gap-1"><div class="w-3 h-3 rounded-sm bg-red-400"></div> Full</span>
</div>
```

### DSS Value
- Users instantly see **when rooms are scarce** (red zones)
- Users see **when rooms are available** (gray/light zones)  
- Informs scheduling decisions: "Don't schedule MWF 9-10 AM — all rooms taken"

---

### 2. Faculty Workload Distribution by Department (Grouped Bar)

**What:** Compare faculty workload patterns across departments to identify departments with overloaded or underutilized faculty.

**Location:** Reports → Faculty section

```javascript
new Chart(ctx, {
    type: 'bar',
    data: {
        labels: department_names,  // ['CCS', 'CBA', 'CTE', ...]
        datasets: [
            {
                label: 'Normal (<75%)',
                data: normal_counts,
                backgroundColor: 'rgba(16, 185, 129, 0.7)'  // emerald
            },
            {
                label: 'Warning (75-100%)',
                data: warning_counts,
                backgroundColor: 'rgba(245, 158, 11, 0.7)'  // amber
            },
            {
                label: 'Exceeded (>100%)',
                data: exceeded_counts,
                backgroundColor: 'rgba(239, 68, 68, 0.7)'   // red
            }
        ]
    },
    options: {
        scales: { x: { stacked: true }, y: { stacked: true } },
        plugins: { legend: { position: 'bottom' } }
    }
});
```

### Backend Data

```python
def get_dept_workload_distribution():
    """Faculty workload status by department (for stacked bar chart)."""
    departments = Department.query.filter_by(is_archived=False).all()
    
    result = []
    for dept in departments:
        faculty = Faculty.query.filter_by(
            department_id=dept.id, is_archived=False
        ).all()
        
        normal = warning = exceeded = 0
        for f in faculty:
            status = f.get_load_status()[3]  # 'normal', 'warning', 'exceeded'
            if status == 'exceeded': exceeded += 1
            elif status == 'warning': warning += 1
            else: normal += 1
        
        result.append({
            'department': dept.department_code,
            'normal': normal,
            'warning': warning,
            'exceeded': exceeded
        })
    
    return result
```

---

### 3. Semester Trend Line (for Compare Page)

**What:** A line chart showing key metrics across semesters to visualize growth trends.

**Location:** Reports → Compare section

```javascript
new Chart(ctx, {
    type: 'line',
    data: {
        labels: semester_labels,  // ['1st Sem 2024-2025', '2nd Sem 2024-2025', '1st Sem 2025-2026', ...]
        datasets: [
            {
                label: 'Schedules',
                data: schedule_counts,
                borderColor: 'rgb(59, 130, 246)',
                tension: 0.3
            },
            {
                label: 'Faculty',
                data: faculty_counts,
                borderColor: 'rgb(16, 185, 129)',
                tension: 0.3
            },
            {
                label: 'Sections',
                data: section_counts,
                borderColor: 'rgb(245, 158, 11)',
                tension: 0.3
            }
        ]
    },
    options: {
        plugins: { legend: { position: 'bottom' } },
        scales: { y: { beginAtZero: true } }
    }
});
```

### Backend Data

```python
def get_semester_trend_data():
    """Get key metrics across all semesters for trend visualization."""
    # Query distinct academic_year + semester combinations
    semesters = db.session.query(
        Schedule.academic_year, Schedule.semester
    ).distinct().order_by(Schedule.academic_year, Schedule.semester).all()
    
    trend_data = []
    for ay, sem in semesters:
        trend_data.append({
            'label': f"{sem[:3]} {ay}",
            'schedules': Schedule.query.filter_by(academic_year=ay, semester=sem, is_archived=False).count(),
            'exams': ExamSchedule.query.filter_by(academic_year=ay, semester=sem, is_archived=False).count(),
            'faculty': db.session.query(Schedule.faculty_id).filter_by(academic_year=ay, semester=sem).distinct().count(),
        })
    
    return trend_data
```

---

## Implementation Steps

### Step 1: Add Backend Data Functions
1. Add `get_room_heatmap_data()` to reports route
2. Add `get_dept_workload_distribution()` to reports route
3. Add `get_semester_trend_data()` to reports route
4. Pass data to respective templates

### Step 2: Add Heatmap to Room Report
1. Add HTML grid heatmap to room utilization section in reports
2. Use pure CSS (no extra library needed) or Chart.js matrix plugin

### Step 3: Add Stacked Bar to Faculty Report
1. Add Chart.js grouped bar chart canvas
2. Initialize with department workload data

### Step 4: Add Trend Line to Compare Report
1. Add Chart.js line chart canvas
2. Initialize with semester trend data

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/routes/reports.py` | **Medium addition** | 3 new data functions |
| `app/templates/reports/overview.html` | **Medium edit** | Add heatmap grid + department bar chart |
| `app/templates/reports/` compare page | **Medium edit** | Add trend line chart |

---

## Testing Checklist

- [ ] Room heatmap renders with correct colors for occupancy levels
- [ ] Heatmap tooltip shows "Day HH:00 — N% (M/Total rooms)"
- [ ] Department workload bar is stacked correctly (normal + warning + exceeded = total)
- [ ] Semester trend line shows all available semesters
- [ ] Charts handle empty data gracefully (no errors, shows "No data")
- [ ] Dark mode: chart backgrounds, labels, and grid lines adapt
- [ ] Responsive: charts resize properly on mobile/tablet
- [ ] Performance: heatmap calculation completes in <1 second
