# Export Reports Feature - Visual Guide

## 🎯 New UI Components

### Export Button Location
```
┌─────────────────────────────────────────────────────────────────┐
│  Reports & Analytics                                             │
│  2025-2026 - 1st Semester - Prelim                             │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────┐                        │
│  │ 💾 Export Report │  │ 💡 AI Analysis│                        │
│  │       ▼          │  │               │                        │
│  └──────────────────┘  └──────────────┘                        │
│         │                                                        │
│         └─► Dropdown Menu                                       │
└─────────────────────────────────────────────────────────────────┘
```

### Dropdown Menu
```
┌─────────────────────────────────────────┐
│  📊 Export to Excel                     │
│     Download as .xlsx file              │
├─────────────────────────────────────────┤
│  📄 Export to PDF                       │
│     Download as .pdf file               │
├─────────────────────────────────────────┤
│  ✓ ISO 25010 Compliant                 │
└─────────────────────────────────────────┘
```

## 📊 Excel Export Structure

### Summary Sheet
```
╔════════════════════════════════════════════════════════════════╗
║         ACADEMIC REPORTS & ANALYTICS                           ║
║    Don Mariano Marcos Memorial State University               ║
║    Mid La Union Campus - Norzagaray College                    ║
║    Academic Year: 2025-2026 | Semester: 1st Semester          ║
║    Department: Computer Studies (CS)                           ║
║    Generated: January 25, 2025 at 2:30 PM                     ║
╠════════════════════════════════════════════════════════════════╣
║                   OVERVIEW STATISTICS                          ║
╠════════════════════════════════╤═══════════════════════════════╣
║ Class Schedules        │   45  ║ Exam Schedules    │    12    ║
║ Active Faculty         │   18  ║ Active Sections   │     8    ║
║ Total Rooms           │   20  ║ Rooms in Use      │    15    ║
║ Faculty with Schedules │   16  ║ Lecture Classes   │    30    ║
║ Lab Classes           │   15  ║                   │          ║
╚════════════════════════════════╧═══════════════════════════════╝
```

### Faculty Workload Sheet
```
╔════════════════════════════════════════════════════════════════╗
║              FACULTY WORKLOAD REPORT                           ║
║    AY 2025-2026 - 1st Semester | Computer Studies (CS)        ║
╠═══╤════════════════════════╤═══════╤═══╤═══╤═══╤══════════════╣
║ # │ Faculty Name           │ Dept  │ # │Lec│Lab│Total Units   ║
╠═══╪════════════════════════╪═══════╪═══╪═══╪═══╪══════════════╣
║ 1 │ Prof. Juan dela Cruz  │  CS   │ 5 │3.0│2.0│  5.0         ║
║ 2 │ Dr. Maria Santos      │  CS   │ 4 │3.0│1.5│  4.5         ║
║ 3 │ Engr. Pedro Reyes     │  CS   │ 4 │2.0│2.0│  4.0         ║
╠═══╧════════════════════════╧═══════╧═══╧═══╧═══╧══════════════╣
║                                                                 ║
║  [BAR CHART: Top Faculty by Total Units]                       ║
║  ████████████████████████ Prof. Juan dela Cruz (5.0)          ║
║  ████████████████████ Dr. Maria Santos (4.5)                  ║
║  ██████████████████ Engr. Pedro Reyes (4.0)                   ║
╚════════════════════════════════════════════════════════════════╝
```

### Room Utilization Sheet
```
╔════════════════════════════════════════════════════════════════╗
║              ROOM UTILIZATION REPORT                           ║
║    AY 2025-2026 - 1st Semester | Computer Studies (CS)        ║
╠═══╤═════════╤═══════════════╤═══╤═══╤═══╤══════════════════════╣
║ # │ Room    │ Building      │Cls│Exm│Tot│ Status               ║
╠═══╪═════════╪═══════════════╪═══╪═══╪═══╪══════════════════════╣
║ 1 │ CS-301  │ Main Building │ 8 │ 2 │10 │ In Use               ║
║ 2 │ CS-302  │ Main Building │ 7 │ 2 │ 9 │ In Use               ║
║ 3 │ LAB-101 │ Lab Building  │ 6 │ 1 │ 7 │ In Use               ║
╠═══╧═════════╧═══════════════╧═══╧═══╧═══╧══════════════════════╣
║                                                                 ║
║  [BAR CHART: Top Rooms by Usage]                               ║
║  ████████████████████████████ CS-301 (10)                     ║
║  ████████████████████████ CS-302 (9)                          ║
║  ████████████████████ LAB-101 (7)                             ║
╚════════════════════════════════════════════════════════════════╝
```

### Weekly Distribution Sheet
```
╔════════════════════════════════════════════════════════════════╗
║           WEEKLY SCHEDULE DISTRIBUTION                         ║
║    AY 2025-2026 - 1st Semester | Computer Studies (CS)        ║
╠════════════════════╤═══════════════════════════════════════════╣
║ Day                │ Schedule Count                            ║
╠════════════════════╪═══════════════════════════════════════════╣
║ Monday             │  12                                       ║
║ Tuesday            │  10                                       ║
║ Wednesday          │  11                                       ║
║ Thursday           │   8                                       ║
║ Friday             │   9                                       ║
║ Saturday           │   5                                       ║
╠════════════════════╧═══════════════════════════════════════════╣
║                                                                 ║
║  [BAR CHART: Schedule Distribution by Day]                     ║
║  Mon  ████████████████                                         ║
║  Tue  ████████████                                             ║
║  Wed  █████████████                                            ║
║  Thu  ████████                                                 ║
║  Fri  █████████                                                ║
║  Sat  █████                                                    ║
╚════════════════════════════════════════════════════════════════╝
```

## 📄 PDF Export Layout

```
┌────────────────────────────────────────────────────────────────┐
│                                                    [Landscape]  │
│         ACADEMIC REPORTS & ANALYTICS                           │
│    Don Mariano Marcos Memorial State University               │
│    Mid La Union Campus - Norzagaray College                    │
│    Academic Year: 2025-2026 | Semester: 1st Semester          │
│    Department: Computer Studies (CS)                           │
│    Generated: January 25, 2025 at 2:30 PM                     │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│  OVERVIEW STATISTICS                                           │
│  ┌──────────────────────┬───────┬──────────────────┬───────┐  │
│  │ Metric               │ Value │ Metric           │ Value │  │
│  ├──────────────────────┼───────┼──────────────────┼───────┤  │
│  │ Class Schedules      │   45  │ Exam Schedules   │   12  │  │
│  │ Active Faculty       │   18  │ Active Sections  │    8  │  │
│  │ Total Rooms         │   20  │ Rooms in Use     │   15  │  │
│  └──────────────────────┴───────┴──────────────────┴───────┘  │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│  TOP FACULTY BY WORKLOAD                                       │
│  ┌───┬────────────────────┬──────┬───┬────┬────┬──────┐      │
│  │ # │ Faculty Name       │ Dept │ # │Lec │Lab │Total │      │
│  ├───┼────────────────────┼──────┼───┼────┼────┼──────┤      │
│  │ 1 │ Prof. Juan...      │  CS  │ 5 │3.0 │2.0 │ 5.0  │      │
│  │ 2 │ Dr. Maria...       │  CS  │ 4 │3.0 │1.5 │ 4.5  │      │
│  └───┴────────────────────┴──────┴───┴────┴────┴──────┘      │
│                                                                 │
│                                                   [Page Break]  │
├────────────────────────────────────────────────────────────────┤
│  TOP ROOMS BY UTILIZATION                                      │
│  ┌───┬────────┬───────────┬───┬───┬───┬─────────┐            │
│  │ # │ Room   │ Building  │Cls│Exm│Tot│ Status  │            │
│  ├───┼────────┼───────────┼───┼───┼───┼─────────┤            │
│  │ 1 │ CS-301 │ Main Bldg │ 8 │ 2 │10 │ In Use  │            │
│  │ 2 │ CS-302 │ Main Bldg │ 7 │ 2 │ 9 │ In Use  │            │
│  └───┴────────┴───────────┴───┴───┴───┴─────────┘            │
│                                                                 │
├────────────────────────────────────────────────────────────────┤
│  WEEKLY SCHEDULE DISTRIBUTION                                  │
│  ┌──────────────┬────────────────┐                            │
│  │ Day          │ Schedule Count │                            │
│  ├──────────────┼────────────────┤                            │
│  │ Monday       │       12       │                            │
│  │ Tuesday      │       10       │                            │
│  └──────────────┴────────────────┘                            │
│                                                                 │
│  ─────────────────────────────────────────────────────────────│
│  This report is generated in compliance with                   │
│  ISO/IEC 25010:2011 Software Quality Standards                │
└────────────────────────────────────────────────────────────────┘
```

## 🎨 Color Scheme (ISO 25010 Compliant)

### Excel
- **Headers**: Blue (#1F4788) with white text
- **Alternating Rows**: White / Light Gray (#F8F9FA)
- **Borders**: Light Gray (#CCCCCC)
- **Charts**: Blue gradient colors

### PDF
- **Title**: Blue (#1F4788), 18pt, bold
- **Headers**: Blue (#1F4788), 14pt, bold
- **Subtitle**: Gray (#666666), 11pt, italic
- **Body Text**: Black, 10pt
- **Table Headers**: Blue (#1F4788) background, white text
- **Alternating Rows**: White / Light Gray (#F8F9FA)

## 🔄 Export Process Flow

```
User clicks "Export Report" button
            ↓
    Dropdown menu appears
            ↓
User selects Excel or PDF
            ↓
   Button shows loading spinner
   "Exporting..." appears
            ↓
  Backend processes request:
  - Gets academic settings
  - Gets user permissions
  - Applies department filter
  - Calculates statistics
  - Generates file (Excel/PDF)
            ↓
    File sent to browser
    Download starts
            ↓
 Button returns to normal
   "Export Report" appears
            ↓
      ✅ Complete!
```

## 📱 Mobile Responsive Design

```
┌──────────────────────────┐
│  Reports & Analytics     │
│  2025-2026 - 1st Sem     │
│                          │
│  ┌────────────────────┐  │
│  │ 💾 Export Report  │  │  ← Full width on mobile
│  │       ▼           │  │
│  └────────────────────┘  │
│  ┌────────────────────┐  │
│  │ 💡 AI Analysis    │  │  ← Stacked vertically
│  └────────────────────┘  │
└──────────────────────────┘
```

## 🎯 Key Features Visualization

### ISO 25010 Badge in Dropdown
```
┌─────────────────────────────────┐
│  📊 Export to Excel             │
│  📄 Export to PDF               │
├─────────────────────────────────┤
│  ✓ ISO 25010 Compliant          │  ← Quality badge
└─────────────────────────────────┘
```

### Loading State
```
Before Click:
┌──────────────────┐
│ 💾 Export Report │
│       ▼          │
└──────────────────┘

During Export:
┌──────────────────┐
│ ⏳ Exporting...  │  ← Spinner animation
└──────────────────┘

After Complete:
┌──────────────────┐
│ 💾 Export Report │  ← Back to normal
│       ▼          │
└──────────────────┘
```

---

**Visual Guide Version**: 1.0  
**Date**: January 25, 2025  
**Status**: ✅ Implementation Complete
