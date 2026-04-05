# B1 — Schedule Quality Index (SQI)

> **Category:** Part B — Add DSS Power Behind Simple Surfaces  
> **Priority:** 6  
> **Effort:** Medium  
> **DSS Impact:** ★★★★★ HIGH — The centerpiece metric of the entire DSS  
> **Simplicity Impact:** ★★★★★ HIGH — One number replaces scattered metrics  

---

## Problem Statement

The system currently has no single measure of "schedule quality." Reports show raw counts (148 schedules, 45 faculty, 25 rooms) and individual metrics (completion rate, faculty utilization) but users must mentally aggregate these to assess whether the schedule is *good*. 

A Decision Support System needs a **composite quality metric** that:
1. Quantifies schedule health in one number
2. Identifies which dimensions are strong/weak
3. Enables before/after comparison when making changes
4. Drives the Health Banner on the dashboard (see A2)

---

## What Is SQI?

The **Schedule Quality Index** is a single 0-100 score computed from 3 weighted sub-metrics:

| Sub-Metric | Weight | Range | What It Measures |
|------------|--------|-------|-----------------|
| **Conflict-Free Rate** | 46.15% | 0-100 | % of schedules with zero scheduling conflicts |
| **Room Utilization** | 30.77% | 0-100 | How efficiently rooms are being used (sweet spot: 40-80%) |
| **Time Preference Adherence** | 23.08% | 0-100 | % of schedules placed in preferred time slots (8AM-12PM) |

### Formula

$$SQI = \frac{30}{65} \times C + \frac{20}{65} \times R + \frac{15}{65} \times T$$

Where:
- $C$ = Conflict-free rate (0-100)
- $R$ = Room utilization score (0-100)
- $T$ = Time preference adherence score (0-100)

---

## Sub-Metric Calculations

### 1. Conflict-Free Rate ($C$)

```python
def calculate_conflict_free_rate(schedules, conflict_detector, settings):
    """Percentage of schedules that have zero conflicts."""
    if not schedules:
        return 100  # No schedules = no conflicts
    
    conflict_free = 0
    for schedule in schedules:
        conflicts = conflict_detector.detect_class_conflicts(
            section_id=schedule.section_id,
            day_of_week=schedule.day_of_week,
            start_time=schedule.start_time,
            end_time=schedule.end_time,
            faculty_id=schedule.faculty_id,
            room_id=schedule.room_id,
            exclude_schedule_id=schedule.id,
            all_schedules=schedules
        )
        if not conflicts:
            conflict_free += 1
    
    return round((conflict_free / len(schedules)) * 100, 1)
```

**Performance note:** This scans all schedules O(n²). For large datasets (>500 schedules), use a cached/batched approach — detect all conflicts once, then count affected schedules.

### 2. Room Utilization ($R$)

```python
def calculate_room_utilization_score(room_utilizations):
    """Score based on how close room utilization is to the sweet spot (40-80%).
    
    Rooms at 0% (unused) or 100% (overbooked) hurt the score.
    Rooms at 40-80% are ideal.
    """
    if not room_utilizations:
        return 100
    
    scores = []
    for util in room_utilizations:
        pct = util.get('utilization_pct', 0)
        if 40 <= pct <= 80:
            scores.append(100)  # Sweet spot
        elif 20 <= pct < 40 or 80 < pct <= 90:
            scores.append(80)   # Acceptable
        elif 10 <= pct < 20 or 90 < pct <= 95:
            scores.append(50)   # Concerning
        elif pct < 10:
            scores.append(20)   # Severely underutilized
        else:
            scores.append(30)   # Severely overutilized
    
    return round(sum(scores) / len(scores), 1) if scores else 100
```

### 3. Time Preference Adherence ($T$)

```python
def calculate_time_preference_score(schedules):
    """Percentage of schedules placed in preferred time slots.
    
    Uses the same preference model as the recommendation engine:
    - 8-10 AM: Preferred (full score)
    - 10-12 PM: Good (90% score)
    - 1-3 PM: Acceptable (70% score)
    - 3-5 PM: Less preferred (50% score)
    - Before 8 or after 5: Poor (30% score)
    """
    if not schedules:
        return 100
    
    TIME_SCORES = {
        range(8, 10): 100,   # Prime morning
        range(10, 12): 90,   # Late morning
        range(13, 15): 70,   # Early afternoon
        range(15, 17): 50,   # Late afternoon
        range(7, 8): 30,     # Too early
        range(17, 21): 30,   # Evening
    }
    
    total_score = 0
    for schedule in schedules:
        hour = schedule.start_time.hour if hasattr(schedule.start_time, 'hour') else schedule.start_time // 100
        
        sched_score = 30  # Default (outside all ranges)
        for time_range, score in TIME_SCORES.items():
            if hour in time_range:
                sched_score = score
                break
        
        total_score += sched_score
    
    return round(total_score / len(schedules), 1)
```

> Note: Earlier drafts included additional candidate sub-metrics (workload balance and break compliance). These were removed from the active SQI model and are now tracked as separate operational analytics when needed.

---

## Main SQI Calculation Function

```python
def calculate_sqi(academic_year=None, semester=None, user_department_ids=None):
    """Calculate the Schedule Quality Index (0-100).
    
    Returns:
        dict: {
            'sqi': float,           # Overall score 0-100
            'grade': str,           # 'Excellent' / 'Good' / 'Needs Attention' / 'Critical'
            'color': str,           # 'emerald' / 'blue' / 'amber' / 'red'
            'sub_metrics': {
                'conflict_free': float,
                'room_utilization': float,
                'time_preference': float
            },
            'insights': list[str]   # 2-3 auto-generated insight strings
        }
    """
    # ... fetch schedules, faculty, rooms ...
    
    sub_metrics = {
        'conflict_free': calculate_conflict_free_rate(schedules, conflict_detector, settings),
        'room_utilization': calculate_room_utilization_score(room_utilizations),
        'time_preference': calculate_time_preference_score(schedules)
    }
    
    # Weighted average
    sqi = (
        (30 / 65) * sub_metrics['conflict_free'] +
        (20 / 65) * sub_metrics['room_utilization'] +
        (15 / 65) * sub_metrics['time_preference']
    )
    sqi = round(sqi, 1)
    
    # Grade
    if sqi >= 80:
        grade, color = 'Excellent', 'emerald'
    elif sqi >= 65:
        grade, color = 'Good', 'blue'
    elif sqi >= 50:
        grade, color = 'Needs Attention', 'amber'
    else:
        grade, color = 'Critical', 'red'
    
    # Auto-generate insights
    insights = []
    weakest = min(sub_metrics, key=sub_metrics.get)
    strongest = max(sub_metrics, key=sub_metrics.get)
    
    METRIC_LABELS = {
        'conflict_free': 'Conflict resolution',
        'room_utilization': 'Room utilization',
        'time_preference': 'Time slot preference'
    }
    
    if sub_metrics[weakest] < 60:
        insights.append(f"{METRIC_LABELS[weakest]} needs improvement ({sub_metrics[weakest]:.0f}/100)")
    insights.append(f"Strongest area: {METRIC_LABELS[strongest]} ({sub_metrics[strongest]:.0f}/100)")
    
    return {
        'sqi': sqi,
        'grade': grade,
        'color': color,
        'sub_metrics': sub_metrics,
        'insights': insights
    }
```

---

## User-Facing Display

### 1. Dashboard Health Banner (see A2)
Shows `SQI: 82` as a colored badge + insights as inline text.

### 2. Reports Overview — SQI Card + Radar Chart

```html
<!-- SQI Score Card -->
<div class="bg-white rounded-xl border p-4 text-center">
    <p class="text-xs text-gray-500 uppercase tracking-wider mb-1">Schedule Quality Index</p>
    <div class="text-4xl font-bold text-{{ sqi_data.color }}-600">{{ sqi_data.sqi }}</div>
    <p class="text-sm font-medium text-{{ sqi_data.color }}-600 mt-1">{{ sqi_data.grade }}</p>
</div>

<!-- Radar Chart (Chart.js) -->
<canvas id="sqiRadarChart" width="300" height="300"></canvas>

<script>
new Chart(document.getElementById('sqiRadarChart'), {
    type: 'radar',
    data: {
        labels: ['Conflict-Free', 'Room Utilization', 'Time Preference'],
        datasets: [{
            label: 'Current Schedule',
            data: [
                {{ sqi_data.sub_metrics.conflict_free }},
                {{ sqi_data.sub_metrics.room_utilization }},
                {{ sqi_data.sub_metrics.time_preference }}
            ],
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            borderColor: 'rgba(59, 130, 246, 0.8)',
            borderWidth: 2,
            pointBackgroundColor: 'rgba(59, 130, 246, 1)',
            pointRadius: 4
        }]
    },
    options: {
        scales: {
            r: {
                min: 0,
                max: 100,
                ticks: { stepSize: 20 }
            }
        },
        plugins: {
            legend: { display: false }
        }
    }
});
</script>
```

### 3. Auto-Scheduler Comparison
When using batch schedule (D1), show:
> "Current SQI: 72 → Projected SQI after auto-schedule: 85 (+13)"

---

## Where SQI Gets Used

| Location | Usage |
|----------|-------|
| Dashboard Health Banner (A2) | Single badge + insights |
| Reports Overview | Full card + radar chart |
| Auto-Scheduler preview | Before/after comparison |
| What-If Analysis (B2) | Impact projection |
| Semester Comparison report | SQI diff across semesters |

---

## Chart.js Integration

### CDN Addition to `base.html`
```html
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
```

**Size:** ~65KB gzipped. Already partially used in reports overview (doughnut, bar charts exist). This adds the radar chart type.

### Note
Reports overview at [app/templates/reports/overview.html](../../app/templates/reports/overview.html) already imports Chart.js and uses it for 4 charts (Type Distribution doughnut, Weekly Distribution bar, Faculty Workload horizontal bar, Room Utilization horizontal bar). Adding the radar chart follows the same pattern.

---

## Implementation Steps

### Step 1: Create SQI Calculator
1. New file `app/services/sqi_calculator.py` (or add to existing `app/routes/reports.py`)
2. Implement all 3 active sub-metric functions
3. Implement `calculate_sqi()` main function
4. Add performance optimization: cache results for 5 minutes (optional)

### Step 2: Integrate with Reports
1. Call `calculate_sqi()` in `app/routes/reports.py` → `index()` route
2. Pass `sqi_data` to template
3. Add SQI card + radar chart to `app/templates/reports/overview.html`

### Step 3: Integrate with Dashboard
1. Call lightweight SQI in `app/routes/main.py` → `dashboard()` route
2. Pass to dashboard template for Health Banner (see A2)

### Step 4: Add Chart.js CDN
1. Add Chart.js script tag to `base.html` (if not already present)
2. Or add only to reports pages that need it

---

## Files Changed

| File | Change Type | Description |
|------|-------------|-------------|
| `app/services/sqi_calculator.py` | **New file** | SQI calculation logic (or add to reports.py) |
| `app/routes/reports.py` | **Medium edit** | Call calculate_sqi(), pass to template |
| `app/routes/main.py` | **Small edit** | Call calculate_sqi() for dashboard |
| `app/templates/reports/overview.html` | **Medium edit** | Add SQI card + radar chart |
| `app/templates/dashboard.html` | **Small edit** | Display SQI in health banner |
| `app/templates/base.html` | **Small edit** | Add Chart.js CDN (if not present) |

---

## Performance Considerations

- **Conflict-Free Rate** is the most expensive calculation (O(n²) for n schedules)
- For 200 schedules × 200 comparisons = 40,000 checks — fast in Python (<1 second)
- For 1000+ schedules, implement batched conflict checking or cache results
- Optional: compute SQI asynchronously via AJAX on dashboard load to not block page render
- Room utilization and time preference scoring are linear scans over current report scope

---

## Testing Checklist

- [ ] SQI returns 100 when no schedules exist (baseline)
- [ ] SQI decreases when conflicts are introduced
- [ ] SQI decreases when rooms are unused or overbooked
- [ ] SQI increases when schedules are in preferred time slots
- [ ] Radar chart renders correctly with 3 data points
- [ ] Radar chart handles edge cases (all 0, all 100, mixed)
- [ ] SQI color thresholds work: green (≥80), blue (≥65), amber (≥50), red (<50)
- [ ] Grade text matches score range
- [ ] Auto-generated insights correctly identify weakest/strongest metrics
- [ ] Dashboard health banner shows SQI score and color
- [ ] Reports page shows full radar chart
- [ ] SQI calculation completes in <2 seconds for 200 schedules
- [ ] Dark mode: chart and card colors adapt correctly
