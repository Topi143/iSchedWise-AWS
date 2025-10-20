# Schedule Tables - Column Reference

## Quick Column Reference for All Tabs

### 📅 Class Schedules Tab
```
┌─────────────┬──────────┬──────────┬──────┬──────┬──────┬──────────┬──────────────┬─────────┐
│ Subject     │ Faculty  │ Room     │ Day  │ Time │ Type │ Semester │ Academic Yr  │ Actions │
├─────────────┼──────────┼──────────┼──────┼──────┼──────┼──────────┼──────────────┼─────────┤
│ CS101       │ John Doe │ Room 101 │ Mon  │ 8:00 │ Lec  │ 1st Sem  │ 2024-2025    │ [E][D]  │
│ Description │          │ Building │      │ 9:00 │      │          │              │         │
└─────────────┴──────────┴──────────┴──────┴──────┴──────┴──────────┴──────────────┴─────────┘
```

### 👨‍🏫 Faculty Schedules Tab
```
┌─────────────┬──────────┬──────────┬──────┬──────┬──────┐
│ Subject     │ Section  │ Room     │ Day  │ Time │ Type │
├─────────────┼──────────┼──────────┼──────┼──────┼──────┤
│ CS101       │ CS-1A    │ Room 101 │ Mon  │ 8:00 │ Lec  │
│ Description │          │ Building │      │ 9:00 │      │
└─────────────┴──────────┴──────────┴──────┴──────┴──────┘
```

### 🏢 Room Schedules Tab
```
┌─────────────┬──────────┬──────────┬──────┬──────┬──────┐
│ Subject     │ Section  │ Faculty  │ Day  │ Time │ Type │
├─────────────┼──────────┼──────────┼──────┼──────┼──────┤
│ CS101       │ CS-1A    │ John Doe │ Mon  │ 8:00 │ Lec  │
│ Description │          │          │      │ 9:00 │      │
└─────────────┴──────────┴──────────┴──────┴──────┴──────┘
```

### 📝 Exam Schedules Tab
```
┌─────────────┬──────────┬──────────┬───────────┬──────┬────────────┬──────────┬──────────────┬─────────┐
│ Subject     │ Faculty  │ Room     │ Exam Date │ Time │ Exam Period│ Semester │ Academic Yr  │ Actions │
├─────────────┼──────────┼──────────┼───────────┼──────┼────────────┼──────────┼──────────────┼─────────┤
│ CS101       │ John Doe │ Room 101 │ Jan 15    │ 8:00 │ Prelim     │ 1st Sem  │ 2024-2025    │ [E][D]  │
│ Description │          │ Building │ 2025      │ 9:00 │            │          │              │         │
└─────────────┴──────────┴──────────┴───────────┴──────┴────────────┴──────────┴──────────────┴─────────┘
```

## 📊 Database Column Mapping

### Class Schedules (`schedules` table)
| UI Column      | Database Column   | Data Type | Notes                    |
|----------------|-------------------|-----------|--------------------------|
| Subject        | subject_id        | FK        | Shows code + description |
| Faculty        | faculty_id        | FK        | Full name or "TBA"       |
| Room           | room_id           | FK        | Room # + building        |
| Day            | day_of_week       | VARCHAR   | With color badge         |
| Time           | start_time        | TIME      | Two rows: start & end    |
|                | end_time          | TIME      |                          |
| Type           | schedule_type     | VARCHAR   | Badge: lecture/lab       |
| Semester       | semester          | VARCHAR   | From academic settings   |
| Academic Year  | academic_year     | VARCHAR   | e.g., "2024-2025"        |
| Actions        | -                 | -         | Edit & Delete buttons    |

### Faculty Schedules (`schedules` table)
| UI Column      | Database Column   | Data Type | Notes                    |
|----------------|-------------------|-----------|--------------------------|
| Subject        | subject_id        | FK        | Shows code + description |
| Section        | section_id        | FK        | Section name             |
| Room           | room_id           | FK        | Room # + building        |
| Day            | day_of_week       | VARCHAR   | With color badge         |
| Time           | start_time        | TIME      | Two rows: start & end    |
|                | end_time          | TIME      |                          |
| Type           | schedule_type     | VARCHAR   | Badge: lecture/lab       |

### Room Schedules (`schedules` table)
| UI Column      | Database Column   | Data Type | Notes                    |
|----------------|-------------------|-----------|--------------------------|
| Subject        | subject_id        | FK        | Shows code + description |
| Section        | section_id        | FK        | Section name             |
| Faculty        | faculty_id        | FK        | Full name or "TBA"       |
| Day            | day_of_week       | VARCHAR   | With color badge         |
| Time           | start_time        | TIME      | Two rows: start & end    |
|                | end_time          | TIME      |                          |
| Type           | schedule_type     | VARCHAR   | Badge: lecture/lab       |

### Exam Schedules (`exam_schedules` table)
| UI Column      | Database Column   | Data Type | Notes                    |
|----------------|-------------------|-----------|--------------------------|
| Subject        | subject_id        | FK        | Shows code + description |
| Faculty        | faculty_id        | FK        | Full name or "TBA"       |
| Room           | room_id           | FK        | Room # + building        |
| Exam Date      | exam_date         | DATE      | Formatted as "Jan 15, 2025" |
| Time           | start_time        | TIME      | Two rows: start & end    |
|                | end_time          | TIME      |                          |
| Exam Period    | exam_period       | VARCHAR   | Prelim/Midterm/Final     |
| Semester       | semester          | VARCHAR   | From academic settings   |
| Academic Year  | academic_year     | VARCHAR   | e.g., "2024-2025"        |
| Actions        | -                 | -         | Edit & Delete buttons    |

## 🎨 Visual Elements

### Day Badges (day_of_week)
- **Monday**: Blue gradient (`#dbeafe → #bfdbfe`, text: `#1e40af`)
- **Tuesday**: Pink gradient (`#fce7f3 → #fbcfe8`, text: `#9f1239`)
- **Wednesday**: Green gradient (`#dcfce7 → #bbf7d0`, text: `#166534`)
- **Thursday**: Yellow gradient (`#fef3c7 → #fde68a`, text: `#92400e`)
- **Friday**: Indigo gradient (`#e0e7ff → #c7d2fe`, text: `#3730a3`)
- **Saturday**: Purple gradient (`#f3e8ff → #e9d5ff`, text: `#6b21a8`)
- **Sunday**: Red gradient (`#fee2e2 → #fecaca`, text: `#991b1b`)

### Type Badges (schedule_type)
- **Lecture**: Blue badge (`bg-blue-100`, text: `text-blue-700`)
- **Lab**: Green badge (`bg-green-100`, text: `text-green-700`)
- **Both**: Purple badge (`bg-purple-100`, text: `text-purple-700`)

### Exam Period Badge (exam_period)
- **Prelim/Midterm/Final**: Purple badge (`bg-purple-100`, text: `text-purple-800`)

### Exam Date Badge
- Red badge (`bg-red-100`, text: `text-red-800`)

## 📐 Styling Specifications

### Table Container
```css
.table-container {
    overflow-x: auto;           /* Horizontal scroll */
    overflow-y: auto;           /* Vertical scroll */
    max-height: calc(100vh - 280px); /* Dynamic height */
    border-radius: 0.5rem;      /* Rounded corners */
}
```

### Table Headers (th)
```css
padding: 12px 16px;
font-size: 0.75rem;
font-weight: 700;
letter-spacing: 0.05em;
text-transform: uppercase;
background-color: #f9fafb;
border-bottom: 2px solid #e5e7eb;
```

### Table Cells (td)
```css
padding: 12px 16px;
vertical-align: middle;
```

### Row Styling
```css
border-bottom: 1px solid #e5e7eb;
background-color: white;
transition: all 0.15s ease;
```

```css
/* Hover state */
tr:hover {
    background-color: #f9fafb !important;
}
```

## 🔍 Cell Content Patterns

### Two-line Subject Cell
```html
<div class="text-sm font-semibold text-gray-900">CS101</div>
<div class="text-xs text-gray-500">Introduction to Computer Science</div>
```

### Two-line Room Cell
```html
<div class="text-sm text-gray-900">Room 101</div>
<div class="text-xs text-gray-500">Main Building</div>
```

### Two-line Time Cell
```html
<div class="text-sm text-gray-900">08:00 AM</div>
<div class="text-xs text-gray-500">10:00 AM</div>
```

### TBA (To Be Announced) Cell
```html
<div class="text-sm text-gray-400 italic">TBA</div>
```

### Day Badge
```html
<span class="day-badge day-monday">Monday</span>
```

### Type Badge
```html
<span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-700 border border-blue-200">
    Lecture
</span>
```

### Action Buttons
```html
<div class="flex items-center justify-end gap-1">
    <button class="text-blue-600 hover:text-blue-900 p-2 rounded-lg hover:bg-blue-50 transition-colors" title="Edit">
        <!-- Edit icon SVG -->
    </button>
    <button class="text-red-600 hover:text-red-900 p-2 rounded-lg hover:bg-red-50 transition-colors" title="Delete">
        <!-- Delete icon SVG -->
    </button>
</div>
```

## 🎯 Alignment Rules

1. **All text columns**: Left-aligned (`text-left`)
2. **Actions column**: Right-aligned (`text-right`)
3. **Badge elements**: Inline display, naturally centered within cell
4. **Multi-line cells**: Stack vertically, left-aligned
5. **Icons**: Centered within button padding

## 📱 Responsive Behavior

- **Desktop (≥1024px)**: All columns visible, full width
- **Tablet (768px-1023px)**: Horizontal scroll enabled
- **Mobile (<768px)**: Horizontal scroll required, fixed column widths

---

**Quick Reference:** Use this document when working with schedule tables to ensure consistency across all tabs and features.
