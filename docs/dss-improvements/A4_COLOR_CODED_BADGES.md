# A4 — Color-Coded Schedule List Badges

> **Category:** Part A — Simplify What Exists  
> **Priority:** 3  
> **Effort:** Low  
> **DSS Impact:** Medium  
> **Simplicity Impact:** ★★★★★ HIGH — Zero new UI elements, existing badges become meaningful  

---

## Problem Statement

The schedule management page uses badges on sections, faculty, and rooms to show how many schedules are assigned. Badges should provide visual cues about scheduling status at a glance.

---

## Current Implementation

### Section Badges — Simple Count-Based

Section badges in both class and exam tabs use a **simple count display** showing the number of schedules assigned to each section. No curriculum-based expected count is used.

#### Class Tab (`_class_tab.html`)
| Status | Color | Condition | Tooltip |
|--------|-------|-----------|---------|
| Has Schedules | `bg-blue-100 text-blue-700 border-blue-200` | `count > 0` | "X schedule(s)" |
| Empty | `bg-gray-100 text-gray-500 border-gray-200` | `count == 0` | "0 schedule(s)" |

```html
{% set s_count = section_schedule_counts.get(section.id, 0) %}
<span class="px-2 py-0.5 text-xs font-semibold rounded-full border
    {% if s_count > 0 %}bg-blue-100 text-blue-700 border-blue-200 dark:bg-blue-900/30 dark:text-blue-300 dark:border-blue-800
    {% else %}bg-gray-100 text-gray-500 border-gray-200 dark:bg-gray-700/30 dark:text-gray-400 dark:border-gray-600{% endif %}"
    title="{{ s_count }} schedule(s)">
    {{ s_count }}
</span>
```

#### Exam Tab (`_exam_tab.html`)
| Status | Color | Condition | Tooltip |
|--------|-------|-----------|---------|
| Has Exams | `bg-orange-100 text-orange-700 border-orange-200` | `count > 0` | "X exam(s)" |
| Empty | `bg-gray-100 text-gray-500 border-gray-200` | `count == 0` | "0 exam(s)" |

```html
{% set e_count = exam_section_schedule_counts.get(section.id, 0) %}
<span class="px-2 py-0.5 text-xs font-semibold rounded-full border
    {% if e_count > 0 %}bg-orange-100 text-orange-700 border-orange-200 dark:bg-orange-900/30 dark:text-orange-300 dark:border-orange-800
    {% else %}bg-gray-100 text-gray-500 border-gray-200 dark:bg-gray-700/30 dark:text-gray-400 dark:border-gray-600{% endif %}"
    title="{{ e_count }} exam(s)">
    {{ e_count }}
</span>
```

### Faculty Badges (`_faculty_tab.html`)
| Status | Color | Condition | Tooltip |
|--------|-------|-----------|---------|
| Normal | `bg-emerald-100 text-emerald-700 border-emerald-200` | `utilization < 75%` | "Normal load (12/21 units)" |
| Warning | `bg-amber-100 text-amber-700 border-amber-200` | `75% <= utilization < 100%` | "Near capacity (18/21 units)" |
| Exceeded | `bg-red-100 text-red-700 border-red-200` | `utilization >= 100%` | "Overloaded (24/21 units)" |
| No Load | `bg-gray-100 text-gray-500 border-gray-200` | `schedule_count == 0` | "No schedules assigned" |

### Room Badges (`_room_tab.html`)
| Status | Color | Condition | Tooltip |
|--------|-------|-----------|---------|
| Good Utilization | `bg-emerald-100 text-emerald-700 border-emerald-200` | `20% <= utilization <= 80%` | "Good utilization (45%)" |
| High Utilization | `bg-amber-100 text-amber-700 border-amber-200` | `utilization > 80%` | "High utilization (92%)" |
| Low Utilization | `bg-gray-100 text-gray-500 border-gray-200` | `utilization < 20%` | "Underutilized (5%)" |
| Unused | `bg-gray-100 text-gray-400 border-gray-200` | `schedule_count == 0` | "No schedules" |

---

## Schedule Completion Rate

The `schedule_completion_rate` in reports uses a **sections-based** formula (matching the dashboard):

```
sections_with_schedules / total_sections × 100
```

This counts how many sections have at least one active schedule, divided by total active sections. No curriculum-based expected subject count is involved.

---

## Files Changed

| File | Description |
|------|-------------|
| `app/routes/schedule.py` | Passes `section_schedule_counts` to templates (no expected subjects) |
| `app/routes/reports.py` | Schedule completion uses sections-based formula |
| `app/templates/schedule/_class_tab.html` | Blue/gray badge based on count |
| `app/templates/schedule/_exam_tab.html` | Orange/gray badge based on count |
| `app/templates/schedule/_faculty_tab.html` | Load-status color badges |
| `app/templates/schedule/_room_tab.html` | Utilization color badges |

---

## Testing Checklist

- [ ] Sections with schedules → blue badge (class) / orange badge (exam) with count
- [ ] Sections with 0 schedules → gray badge with "0"
- [ ] Faculty with load < 75% → green badge
- [ ] Faculty with load 75-100% → amber badge
- [ ] Faculty with load > 100% → red badge
- [ ] Faculty with 0 schedules → gray badge
- [ ] Room badges reflect utilization correctly
- [ ] Tooltip text shows meaningful info on hover
- [ ] Badge colors visible in dark mode
- [ ] Colors don't clash with selected/active section highlight
