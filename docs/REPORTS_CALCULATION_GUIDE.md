# Reports & Analytics Calculation Guide

> **iSchedWise V4** - Comprehensive documentation of how statistics and metrics are calculated

---

## 📊 Overview

The Reports module calculates statistics based on:
- **Academic Year** (e.g., "2025-2026")
- **Semester** (e.g., "1st Semester", "2nd Semester")
- **Department Filter** (optional, auto-applied for Deans)

All data is filtered by `is_active=True` to exclude archived/deleted records.

---

## 🔐 Access Control

| User Role | Data Access |
|-----------|-------------|
| **Admin** | All departments, can filter by any program |
| **Dean (1 program)** | Only their department's data (auto-filtered) |
| **Dean (multiple programs)** | Their assigned departments, can filter or see "All My Programs" |

---

## 📈 Statistics Calculations

### 1. Total Class Schedules

```python
total_schedules = Schedule.query.filter_by(
    is_active=True,
    academic_year=current_year,
    semester=current_semester
).count()
```

**Breakdown:**
- **Lecture Count**: Schedules where `schedule_type == 'lecture'`
- **Lab Count**: Schedules where `schedule_type == 'lab'`

---

### 2. Total Exam Schedules

```python
total_exam_schedules = ExamSchedule.query.filter_by(
    is_active=True,
    academic_year=current_year,
    semester=current_semester
).count()
```

---

### 3. Active Faculty

```python
total_faculty = Faculty.query.filter_by(
    is_active=True,
    is_archived=False,
    department_id=filter_department  # if filtered
).count()
```

**Sub-metrics:**
- **Faculty with Schedules**: Count of distinct `faculty_id` in schedules
- **Unassigned Faculty**: Faculty with 0 schedules in current period

---

### 4. Active Sections

```python
total_sections = Section.query.filter_by(
    is_active=True,
    department_id=filter_department  # if filtered
).count()
```

---

### 5. Total Available Rooms

```python
total_rooms = Room.query.filter_by(is_available=True).count()
```

**Note:** Rooms are shared across all departments; the count shows all available rooms system-wide.

---

## 👨‍🏫 Faculty Workload Calculations

### Per-Faculty Metrics

For each faculty member:

```python
# Get all schedules for this faculty
schedules = Schedule.query.filter_by(
    is_active=True,
    faculty_id=faculty.id,
    academic_year=current_year,
    semester=current_semester
).all()

# Calculate units from assigned subjects
total_units = sum(schedule.subject.total_units for schedule in schedules)
lec_units = sum(schedule.subject.lec_units for schedule in schedules)
lab_units = sum(schedule.subject.lab_units for schedule in schedules)
```

### Utilization Percentage

```python
utilization_pct = (current_units / max_units) * 100
```

Where:
- `current_units` = Total units from assigned schedules
- `max_units` = Faculty's maximum load limit (default: 24 units, or custom per faculty)

### Load Status

| Status | Condition |
|--------|-----------|
| `normal` | utilization_pct ≤ 80% |
| `warning` | 80% < utilization_pct ≤ 100% |
| `exceeded` | utilization_pct > 100% |

### Aggregate Faculty Stats

```python
avg_faculty_utilization = sum(all_utilization_pcts) / total_faculty_count

overloaded_faculty_count = count where load_status == 'exceeded'
warning_faculty_count = count where load_status == 'warning'
underutilized_faculty_count = count where utilization_pct < 50%
```

---

## 🏢 Room Utilization Calculations

### Hours-Based Approach

Room utilization is calculated using **actual hours** rather than just schedule counts.

#### Constants

```python
MAX_WEEKLY_HOURS = 72  # 6 days × 12 hours/day (7:00 AM - 7:00 PM)
```

### Per-Room Calculation

```python
# For each schedule in the room
for schedule in room_schedules:
    start_minutes = schedule.start_time.hour * 60 + schedule.start_time.minute
    end_minutes = schedule.end_time.hour * 60 + schedule.end_time.minute
    duration_hours = (end_minutes - start_minutes) / 60
    schedule_hours += duration_hours

# Same calculation for exams
for exam in room_exams:
    start_minutes = exam.start_time.hour * 60 + exam.start_time.minute
    end_minutes = exam.end_time.hour * 60 + exam.end_time.minute
    duration_hours = (end_minutes - start_minutes) / 60
    exam_hours += duration_hours

# Total hours
total_hours = schedule_hours + exam_hours

# Utilization percentage
utilization_pct = (total_hours / MAX_WEEKLY_HOURS) * 100
```

### Example Calculation

| Room | Classes | Class Hours | Exams | Exam Hours | Total Hours | Utilization |
|------|---------|-------------|-------|------------|-------------|-------------|
| CL-101 | 5 | 15.0 hrs | 2 | 4.0 hrs | 19.0 hrs | 26.4% |
| LAB-A | 3 | 9.0 hrs | 0 | 0 hrs | 9.0 hrs | 12.5% |

**Formula:** `19.0 / 72 × 100 = 26.4%`

### Building-Level Aggregation

```python
for building in buildings:
    building_stats = {
        'total_rooms': count of rooms in building,
        'total_hours': sum of all room hours in building,
        'max_hours': total_rooms × MAX_WEEKLY_HOURS,
        'in_use': rooms with total_hours > 0,
        'unused': rooms with total_hours == 0,
        'utilization_pct': (total_hours / max_hours) × 100
    }
```

---

## 📅 Weekly Distribution

Schedule count per day of the week:

```python
schedule_by_day = {
    'Monday': schedule_query.filter(day_of_week='Monday').count(),
    'Tuesday': schedule_query.filter(day_of_week='Tuesday').count(),
    'Wednesday': schedule_query.filter(day_of_week='Wednesday').count(),
    'Thursday': schedule_query.filter(day_of_week='Thursday').count(),
    'Friday': schedule_query.filter(day_of_week='Friday').count(),
    'Saturday': schedule_query.filter(day_of_week='Saturday').count()
}
```

### Peak Day Detection

```python
peak_day = max(schedule_by_day, key=schedule_by_day.get)
low_day = min(schedule_by_day, key=schedule_by_day.get)
average_per_day = sum(schedule_by_day.values()) / 6
```

---

## 🔍 Quick Insights Cards

### Card 1: Faculty Utilization

| Metric | Calculation |
|--------|-------------|
| Assigned Faculty | Faculty with at least 1 schedule |
| Unassigned Faculty | Total faculty - Assigned faculty |
| Avg Utilization | Mean of all faculty utilization percentages |

### Card 2: Room Utilization (Hours-Based)

| Metric | Calculation |
|--------|-------------|
| Total Hours Used | Sum of all room hours |
| Max Possible Hours | Total rooms × 72 hours |
| Utilization % | (Total hours / Max hours) × 100 |
| Unused Rooms | Rooms with 0 hours of usage |

### Card 3: Unassigned Faculty

| Metric | Calculation |
|--------|-------------|
| Count | Faculty with 0 schedules |
| By Department | Grouped count per department code |

### Card 4: Unused Rooms

| Metric | Calculation |
|--------|-------------|
| Count | Rooms with 0 total hours |
| By Type | Grouped count per room type (Lecture/Lab/etc.) |

---

## 📤 Export Calculations

### Excel Export

The Excel export includes multiple sheets:

1. **Summary Sheet**
   - Quick Insights (same as dashboard cards)
   - Overview statistics

2. **Faculty Workload Sheet**
   - All faculty with units breakdown
   - Sorted by total units (descending)

3. **Room Utilization Sheet (Hours-Based)**
   - All rooms with hours breakdown
   - Schedule hours, exam hours, total hours
   - Utilization percentage per room

4. **Unassigned Faculty Sheet**
   - List of faculty with 0 schedules
   - Grouped by department

5. **Weekly Distribution Sheet**
   - Schedule counts per day
   - Visual bar representation

### PDF Export

The PDF export includes:

1. **Overview Statistics Table**
2. **Faculty Workload Summary** (Top 20)
3. **Room Utilization Summary** (Hours-based, Top 20)
4. **Building Utilization Summary** (Aggregated by building)
5. **Weekly Distribution Chart**

---

## 🤖 AI Analysis Data

The AI analyzer receives these enhanced statistics:

```python
ai_context = {
    # Overview
    'total_schedules': int,
    'total_exam_schedules': int,
    'lecture_count': int,
    'lab_count': int,
    
    # Faculty Metrics
    'total_faculty': int,
    'faculty_with_schedules': int,
    'unassigned_faculty_count': int,
    'avg_faculty_utilization': float,
    'overloaded_faculty_count': int,
    'underutilized_faculty_count': int,
    'unassigned_faculty_by_dept': dict,  # {dept_code: count}
    
    # Room Metrics (Hours-Based)
    'total_rooms': int,
    'rooms_in_use': int,
    'unused_rooms_count': int,
    'avg_room_utilization': float,
    'total_room_hours_used': float,
    'max_weekly_hours': 72,
    'unused_rooms_by_type': dict,  # {room_type: count}
    'room_utilization_by_building': dict,  # {building: stats}
    
    # Weekly Distribution
    'schedule_by_day': dict  # {day: count}
}
```

---

## 📊 Semester Comparison

Compares two academic periods side-by-side:

| Metric | Calculation |
|--------|-------------|
| Schedule Diff | Period2.schedules - Period1.schedules |
| % Change | ((Period2 - Period1) / Period1) × 100 |
| Faculty Assigned Diff | Period2.assigned - Period1.assigned |
| Rooms Used Diff | Period2.rooms - Period1.rooms |

---

## 🎯 Key Formulas Summary

| Metric | Formula |
|--------|---------|
| Faculty Utilization % | `(current_units / max_units) × 100` |
| Room Utilization % | `(total_hours / 72) × 100` |
| Building Utilization % | `(sum_room_hours / (room_count × 72)) × 100` |
| Average Faculty Util | `sum(all_utilizations) / faculty_count` |
| Schedule Duration (hrs) | `(end_minutes - start_minutes) / 60` |

---

## 📝 Notes

1. **Hours Calculation**: Uses actual schedule times, not just slot counts
2. **Department Filtering**: Applies to schedules via Section relationship
3. **Room Access**: Rooms are shared; filtering shows usage by filtered department's schedules
4. **Active Records Only**: All calculations exclude archived/inactive records
5. **Real-time Data**: Statistics are calculated fresh on each page load

---

*Last Updated: January 2026*
